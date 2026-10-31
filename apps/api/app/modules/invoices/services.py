from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceCounter, InvoiceLineItem, InvoiceStatus
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from app.models.quotation import Quotation
from app.models.subscription import PendingBillingAdjustment, Subscription
from app.models.user import User, UserRole
from app.modules.invoices.pdf import generate_invoice_pdf_content
from app.modules.invoices.schemas import (
    InvoiceCreate,
    InvoiceLine,
    InvoiceResponse,
    InvoiceTax,
)


def round_money(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def generate_invoice_number(db: Session, target_date: date | None = None) -> str:
    year = (target_date or date.today()).year
    insert_stmt = (
        pg_insert(InvoiceCounter)
        .values(year=year, next_seq=1)
        .on_conflict_do_nothing(index_elements=["year"])
    )
    db.execute(insert_stmt)

    counter = (
        db.query(InvoiceCounter)
        .filter(InvoiceCounter.year == year)
        .with_for_update()
        .first()
    )

    seq = counter.next_seq
    counter.next_seq += 1
    db.flush()
    return f"INV-{year}-{seq:04d}"


def calculate_due_date(issue_date: date, payment_terms: str | None = None) -> date:
    terms = (payment_terms or "NET_30").upper().strip()
    if "RECEIPT" in terms or "IMMEDIATE" in terms:
        return issue_date
    if "NET_15" in terms:
        return issue_date + timedelta(days=15)
    if "NET_60" in terms:
        return issue_date + timedelta(days=60)
    # Default NET_30
    return issue_date + timedelta(days=30)


def serialize_invoice(invoice: Invoice) -> InvoiceResponse:
    lines: list[InvoiceLine] = []
    for item in invoice.lines:
        tax_objs = [
            InvoiceTax(
                name=t.get("name", "Tax"),
                code=t.get("code", "TAX"),
                rate_percent=str(t.get("rate_percent", t.get("ratePercent", "0.00"))),
                amount=str(t.get("amount", "0.00")),
            )
            for t in (item.taxes_data or [])
        ]
        lines.append(
            InvoiceLine(
                product_id=item.product_id,
                description=item.description,
                quantity=item.quantity,
                unit_price=f"{Decimal(str(item.unit_price)):.2f}",
                selected_variants=item.selected_variants or [],
                taxes=tax_objs,
                line_subtotal=f"{Decimal(str(item.line_subtotal)):.2f}",
                tax_amount=f"{Decimal(str(item.tax_amount)):.2f}",
                discount_amount=f"{Decimal(str(item.discount_amount)):.2f}",
                line_total=f"{Decimal(str(item.line_total)):.2f}",
            )
        )

    customer_name = invoice.customer.display_name if invoice.customer else None

    # Check dynamic overdue status
    current_status = invoice.status
    if (
        current_status in (InvoiceStatus.CONFIRMED.value, InvoiceStatus.PARTIALLY_PAID.value)
        and invoice.due_date < date.today()
        and Decimal(str(invoice.amount_due)) > Decimal("0.00")
    ):
        current_status = InvoiceStatus.OVERDUE.value

    return InvoiceResponse(
        id=invoice.id,
        number=invoice.invoice_number,
        customer_id=invoice.customer_id,
        customer_name=customer_name,
        subscription_id=invoice.subscription_id,
        quotation_id=invoice.quotation_id,
        status=InvoiceStatus(current_status),
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        period_start=invoice.period_start,
        period_end=invoice.period_end,
        lines=lines,
        subtotal=f"{Decimal(str(invoice.subtotal)):.2f}",
        tax_total=f"{Decimal(str(invoice.tax_total)):.2f}",
        discount_total=f"{Decimal(str(invoice.discount_total)):.2f}",
        total=f"{Decimal(str(invoice.total)):.2f}",
        amount_paid=f"{Decimal(str(invoice.amount_paid)):.2f}",
        amount_due=f"{Decimal(str(invoice.amount_due)):.2f}",
        currency=invoice.currency,
        payment_terms=invoice.payment_terms,
        billing_reason=invoice.billing_reason,
        sent_at=invoice.sent_at,
        paid_at=invoice.paid_at,
        cancel_reason=invoice.cancel_reason,
        notes=invoice.notes,
        created_at=invoice.created_at,
    )


def get_user_customer_id(user: User) -> uuid.UUID | None:
    if getattr(user, "customer_profile", None) and user.customer_profile:
        return user.customer_profile.id
    return None


def assert_invoice_access(invoice: Invoice, current_user: User) -> None:
    if current_user.role in (UserRole.ADMIN.value, UserRole.STAFF.value):
        return
    cust_id = get_user_customer_id(current_user)
    if not cust_id or cust_id != invoice.customer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "INVOICE_NOT_FOUND", "message": "Invoice not found"},
        )


def create_invoice_from_subscription(
    db: Session,
    subscription: Subscription,
    period_start: date,
    period_end: date,
    billing_reason: str = "SUBSCRIPTION_CYCLE",
) -> Invoice:
    # Idempotency guard: check existing non-cancelled invoice
    existing = (
        db.query(Invoice)
        .filter(
            Invoice.subscription_id == subscription.id,
            Invoice.period_start == period_start,
            Invoice.period_end == period_end,
            Invoice.status != InvoiceStatus.CANCELLED.value,
        )
        .first()
    )
    if existing:
        return existing

    today = date.today()
    inv_number = generate_invoice_number(db, today)
    payment_terms = (
        subscription.payment_terms
        or "NET_30"
    )
    due_date = calculate_due_date(today, payment_terms)

    subtotal = Decimal("0.00")
    tax_total = Decimal("0.00")
    discount_total = Decimal("0.00")
    total = Decimal("0.00")

    invoice = Invoice(
        invoice_number=inv_number,
        customer_id=subscription.customer_id,
        subscription_id=subscription.id,
        quotation_id=subscription.quotation_id,
        status=InvoiceStatus.CONFIRMED.value,
        issue_date=today,
        due_date=due_date,
        period_start=period_start,
        period_end=period_end,
        currency=subscription.currency,
        subtotal=Decimal("0.00"),
        tax_total=Decimal("0.00"),
        discount_total=Decimal("0.00"),
        total=Decimal("0.00"),
        amount_paid=Decimal("0.00"),
        amount_due=Decimal("0.00"),
        payment_terms=payment_terms,
        billing_reason=billing_reason,
    )
    db.add(invoice)
    db.flush()

    for line in subscription.lines:
        line_sub = round_money(Decimal(str(line.line_subtotal)))
        line_tax = round_money(Decimal(str(line.tax_amount)))
        line_disc = round_money(Decimal(str(line.discount_amount)))
        line_tot = round_money(Decimal(str(line.line_total)))

        subtotal += line_sub
        tax_total += line_tax
        discount_total += line_disc
        total += line_tot

        inv_line = InvoiceLineItem(
            invoice_id=invoice.id,
            product_id=line.product_id,
            description=line.description,
            quantity=line.quantity,
            unit_price=Decimal(str(line.unit_price)),
            selected_variants=line.selected_variants or [],
            taxes_data=line.taxes_data or [],
            line_subtotal=line_sub,
            tax_amount=line_tax,
            discount_amount=line_disc,
            line_total=line_tot,
        )
        db.add(inv_line)

    invoice.subtotal = round_money(subtotal)
    invoice.tax_total = round_money(tax_total)
    invoice.discount_total = round_money(discount_total)
    invoice.total = round_money(total)
    invoice.amount_due = invoice.total

    # Create transactional notification
    notif = Notification(
        customer_id=subscription.customer_id,
        recipient_email=subscription.customer.billing_email if subscription.customer else None,
        channel=NotificationChannel.IN_APP.value,
        notification_type=NotificationType.INVOICE_ISSUED.value,
        title=f"Invoice Issued: {inv_number}",
        message=f"Invoice {inv_number} for {subscription.currency} {invoice.total:.2f} has been issued.",
        related_entity_type="INVOICE",
        related_entity_id=invoice.id,
        status=NotificationStatus.SENT.value,
    )
    db.add(notif)
    db.flush()

    return invoice


def create_invoice_for_upgrade_adjustment(
    db: Session,
    subscription: Subscription,
    adjustment: PendingBillingAdjustment,
) -> Invoice:
    if adjustment.is_billed and adjustment.invoice_id:
        existing = db.get(Invoice, adjustment.invoice_id)
        if existing and existing.status != InvoiceStatus.CANCELLED.value:
            return existing

    today = date.today()
    inv_number = generate_invoice_number(db, today)
    payment_terms = (
        subscription.payment_terms
        or "NET_30"
    )
    due_date = calculate_due_date(today, payment_terms)
    amount = round_money(Decimal(str(adjustment.amount)))

    invoice = Invoice(
        invoice_number=inv_number,
        customer_id=subscription.customer_id,
        subscription_id=subscription.id,
        quotation_id=subscription.quotation_id,
        status=InvoiceStatus.CONFIRMED.value,
        issue_date=today,
        due_date=due_date,
        period_start=subscription.current_period_start,
        period_end=subscription.current_period_end,
        currency=subscription.currency,
        subtotal=amount,
        tax_total=Decimal("0.00"),
        discount_total=Decimal("0.00"),
        total=amount,
        amount_paid=Decimal("0.00"),
        amount_due=amount,
        payment_terms=payment_terms,
        billing_reason="PLAN_UPGRADE",
    )
    db.add(invoice)
    db.flush()

    inv_line = InvoiceLineItem(
        invoice_id=invoice.id,
        product_id=None,
        description=adjustment.description or "Immediate plan upgrade price difference",
        quantity=1,
        unit_price=amount,
        selected_variants=[],
        taxes_data=[],
        line_subtotal=amount,
        tax_amount=Decimal("0.00"),
        discount_amount=Decimal("0.00"),
        line_total=amount,
    )
    db.add(inv_line)

    adjustment.is_billed = True
    adjustment.invoice_id = invoice.id

    notif = Notification(
        customer_id=subscription.customer_id,
        recipient_email=subscription.customer.billing_email if subscription.customer else None,
        channel=NotificationChannel.IN_APP.value,
        notification_type=NotificationType.INVOICE_ISSUED.value,
        title=f"Upgrade Invoice Issued: {inv_number}",
        message=f"Invoice {inv_number} for {subscription.currency} {amount:.2f} has been issued for your plan upgrade.",
        related_entity_type="INVOICE",
        related_entity_id=invoice.id,
        status=NotificationStatus.SENT.value,
    )
    db.add(notif)
    db.flush()

    return invoice


def create_invoice_from_quotation(
    db: Session,
    quotation: Quotation,
) -> Invoice:
    today = date.today()
    inv_number = generate_invoice_number(db, today)
    payment_terms = "NET_30"
    due_date = calculate_due_date(today, payment_terms)

    subtotal = Decimal("0.00")
    tax_total = Decimal("0.00")
    discount_total = Decimal("0.00")
    total = Decimal("0.00")

    invoice = Invoice(
        invoice_number=inv_number,
        customer_id=quotation.customer_id,
        subscription_id=None,
        quotation_id=quotation.id,
        status=InvoiceStatus.CONFIRMED.value,
        issue_date=today,
        due_date=due_date,
        period_start=quotation.start_date,
        period_end=None,
        currency=quotation.currency,
        subtotal=Decimal("0.00"),
        tax_total=Decimal("0.00"),
        discount_total=Decimal("0.00"),
        total=Decimal("0.00"),
        amount_paid=Decimal("0.00"),
        amount_due=Decimal("0.00"),
        payment_terms=payment_terms,
        billing_reason="QUOTATION_ACCEPTANCE",
    )
    db.add(invoice)
    db.flush()

    for line in quotation.lines:
        line_sub = round_money(Decimal(str(line.line_subtotal)))
        line_tax = round_money(Decimal(str(line.tax_amount)))
        line_disc = round_money(Decimal(str(line.discount_amount)))
        line_tot = round_money(Decimal(str(line.line_total)))

        subtotal += line_sub
        tax_total += line_tax
        discount_total += line_disc
        total += line_tot

        inv_line = InvoiceLineItem(
            invoice_id=invoice.id,
            product_id=line.product_id,
            description=line.description,
            quantity=line.quantity,
            unit_price=Decimal(str(line.unit_price)),
            selected_variants=line.selected_variants or [],
            taxes_data=line.taxes_data or [],
            line_subtotal=line_sub,
            tax_amount=line_tax,
            discount_amount=line_disc,
            line_total=line_tot,
        )
        db.add(inv_line)

    invoice.subtotal = round_money(subtotal)
    invoice.tax_total = round_money(tax_total)
    invoice.discount_total = round_money(discount_total)
    invoice.total = round_money(total)
    invoice.amount_due = invoice.total

    notif = Notification(
        customer_id=quotation.customer_id,
        recipient_email=quotation.customer.billing_email if quotation.customer else None,
        channel=NotificationChannel.IN_APP.value,
        notification_type=NotificationType.INVOICE_ISSUED.value,
        title=f"Quotation Invoice Issued: {inv_number}",
        message=f"Invoice {inv_number} for {quotation.currency} {invoice.total:.2f} has been issued.",
        related_entity_type="INVOICE",
        related_entity_id=invoice.id,
        status=NotificationStatus.SENT.value,
    )
    db.add(notif)
    db.flush()

    return invoice


def create_manual_invoice(
    db: Session,
    payload: InvoiceCreate,
    current_user: User,
) -> Invoice:
    customer = db.get(Customer, payload.customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CUSTOMER_NOT_FOUND", "message": "Customer not found"},
        )

    if current_user.role not in (UserRole.ADMIN.value, UserRole.STAFF.value):
        cust_id = get_user_customer_id(current_user)
        if not cust_id or cust_id != payload.customer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "Not authorized to create invoice for customer"},
            )

    today = payload.issue_date or date.today()
    payment_terms = payload.payment_terms or "NET_30"
    due_date = payload.due_date or calculate_due_date(today, payment_terms)
    inv_number = generate_invoice_number(db, today)

    subtotal = Decimal("0.00")
    tax_total = Decimal("0.00")
    discount_total = Decimal("0.00")
    total = Decimal("0.00")

    invoice = Invoice(
        invoice_number=inv_number,
        customer_id=payload.customer_id,
        subscription_id=payload.subscription_id,
        quotation_id=payload.quotation_id,
        status=InvoiceStatus.DRAFT.value,
        issue_date=today,
        due_date=due_date,
        currency=payload.currency.upper(),
        subtotal=Decimal("0.00"),
        tax_total=Decimal("0.00"),
        discount_total=Decimal("0.00"),
        total=Decimal("0.00"),
        amount_paid=Decimal("0.00"),
        amount_due=Decimal("0.00"),
        payment_terms=payment_terms,
        billing_reason="MANUAL",
        notes=payload.notes,
    )
    db.add(invoice)
    db.flush()

    for item in payload.lines:
        u_price = round_money(Decimal(item.unit_price))
        l_sub = round_money(u_price * item.quantity)
        d_amt = round_money(Decimal(item.discount_amount))
        tax_rate = Decimal(item.tax_rate_percent)
        t_amt = round_money((l_sub - d_amt) * tax_rate / Decimal("100")) if tax_rate > 0 else Decimal("0.00")
        l_tot = round_money(l_sub - d_amt + t_amt)

        subtotal += l_sub
        tax_total += t_amt
        discount_total += d_amt
        total += l_tot

        taxes_data = []
        if tax_rate > 0:
            taxes_data.append({
                "name": item.tax_code or "Tax",
                "code": item.tax_code or "TAX",
                "ratePercent": str(tax_rate),
                "amount": f"{t_amt:.2f}",
            })

        inv_line = InvoiceLineItem(
            invoice_id=invoice.id,
            product_id=item.product_id,
            description=item.description,
            quantity=item.quantity,
            unit_price=u_price,
            selected_variants=item.selected_variants,
            taxes_data=taxes_data,
            line_subtotal=l_sub,
            tax_amount=t_amt,
            discount_amount=d_amt,
            line_total=l_tot,
        )
        db.add(inv_line)

    invoice.subtotal = round_money(subtotal)
    invoice.tax_total = round_money(tax_total)
    invoice.discount_total = round_money(discount_total)
    invoice.total = round_money(total)
    invoice.amount_due = invoice.total

    db.commit()
    db.refresh(invoice)
    return invoice


def confirm_invoice(
    db: Session,
    invoice_id: uuid.UUID,
    current_user: User,
) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "INVOICE_NOT_FOUND", "message": "Invoice not found"},
        )
    assert_invoice_access(invoice, current_user)

    if invoice.status != InvoiceStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "INVALID_INVOICE_STATE",
                "message": f"Invoice in status {invoice.status} cannot be confirmed",
            },
        )

    invoice.status = InvoiceStatus.CONFIRMED.value
    # Overdue check
    if invoice.due_date < date.today() and Decimal(str(invoice.amount_due)) > Decimal("0.00"):
        invoice.status = InvoiceStatus.OVERDUE.value

    notif = Notification(
        customer_id=invoice.customer_id,
        recipient_email=invoice.customer.billing_email if invoice.customer else None,
        channel=NotificationChannel.IN_APP.value,
        notification_type=NotificationType.INVOICE_ISSUED.value,
        title=f"Invoice Confirmed: {invoice.invoice_number}",
        message=f"Invoice {invoice.invoice_number} has been confirmed.",
        related_entity_type="INVOICE",
        related_entity_id=invoice.id,
        status=NotificationStatus.SENT.value,
    )
    db.add(notif)
    db.commit()
    db.refresh(invoice)
    return invoice


def cancel_invoice(
    db: Session,
    invoice_id: uuid.UUID,
    reason: str | None,
    current_user: User,
) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "INVOICE_NOT_FOUND", "message": "Invoice not found"},
        )
    assert_invoice_access(invoice, current_user)

    if invoice.status == InvoiceStatus.CANCELLED.value:
        return invoice

    if Decimal(str(invoice.amount_paid)) > Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CANNOT_CANCEL_PAID_INVOICE",
                "message": "Cannot cancel an invoice with recorded payments",
            },
        )

    invoice.status = InvoiceStatus.CANCELLED.value
    invoice.cancel_reason = reason
    db.commit()
    db.refresh(invoice)
    return invoice


def send_invoice(
    db: Session,
    invoice_id: uuid.UUID,
    current_user: User,
) -> None:
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "INVOICE_NOT_FOUND", "message": "Invoice not found"},
        )
    assert_invoice_access(invoice, current_user)

    now_utc = datetime.now(timezone.utc)
    invoice.sent_at = now_utc

    notif = Notification(
        customer_id=invoice.customer_id,
        recipient_email=invoice.customer.billing_email if invoice.customer else None,
        channel=NotificationChannel.EMAIL.value,
        notification_type=NotificationType.INVOICE_ISSUED.value,
        title=f"Invoice Delivery Queued: {invoice.invoice_number}",
        message=f"Invoice {invoice.invoice_number} has been queued for delivery.",
        related_entity_type="INVOICE",
        related_entity_id=invoice.id,
        status=NotificationStatus.PENDING.value,
    )
    db.add(notif)
    db.commit()


def get_invoice_pdf_bytes(
    db: Session,
    invoice_id: uuid.UUID,
    current_user: User,
) -> bytes:
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "INVOICE_NOT_FOUND", "message": "Invoice not found"},
        )
    assert_invoice_access(invoice, current_user)

    lines_data = [
        {
            "description": line.description,
            "quantity": line.quantity,
            "unit_price": f"{Decimal(str(line.unit_price)):.2f}",
            "line_total": f"{Decimal(str(line.line_total)):.2f}",
        }
        for line in invoice.lines
    ]

    return generate_invoice_pdf_content(
        invoice_number=invoice.invoice_number,
        customer_name=invoice.customer.display_name if invoice.customer else "Valued Customer",
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        currency=invoice.currency,
        subtotal=Decimal(str(invoice.subtotal)),
        tax_total=Decimal(str(invoice.tax_total)),
        discount_total=Decimal(str(invoice.discount_total)),
        total=Decimal(str(invoice.total)),
        amount_paid=Decimal(str(invoice.amount_paid)),
        amount_due=Decimal(str(invoice.amount_due)),
        status=invoice.status,
        lines=lines_data,
    )
