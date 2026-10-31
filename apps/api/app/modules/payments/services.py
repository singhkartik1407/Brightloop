from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceStatus
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
    NotificationType,
)
from app.models.payment import Payment, PaymentCounter, PaymentMethod, PaymentStatus
from app.models.user import User, UserRole
from app.modules.invoices.services import get_user_customer_id, round_money
from app.modules.payments.schemas import PaymentCreate, PaymentResponse


def generate_payment_reference(db: Session, target_date: date | None = None) -> str:
    year = (target_date or date.today()).year
    insert_stmt = (
        pg_insert(PaymentCounter)
        .values(year=year, next_seq=1)
        .on_conflict_do_nothing(index_elements=["year"])
    )
    db.execute(insert_stmt)

    counter = (
        db.query(PaymentCounter)
        .filter(PaymentCounter.year == year)
        .with_for_update()
        .first()
    )

    seq = counter.next_seq
    counter.next_seq += 1
    db.flush()
    return f"PAY-{year}-{seq:04d}"


def serialize_payment(payment: Payment) -> PaymentResponse:
    customer_name = payment.customer.display_name if payment.customer else None
    invoice_number = payment.invoice.invoice_number if payment.invoice else None

    return PaymentResponse(
        id=payment.id,
        reference=payment.reference,
        payment_reference=payment.payment_reference,
        invoice_id=payment.invoice_id,
        invoice_number=invoice_number,
        customer_id=payment.customer_id,
        customer_name=customer_name,
        method=PaymentMethod(payment.method),
        amount=f"{Decimal(str(payment.amount)):.2f}",
        currency=payment.currency,
        status=PaymentStatus(payment.status),
        paid_at=payment.paid_at,
        note=payment.note,
        created_at=payment.created_at,
    )


def assert_payment_access(payment: Payment, current_user: User) -> None:
    if current_user.role in (UserRole.ADMIN.value, UserRole.STAFF.value):
        return
    cust_id = get_user_customer_id(current_user)
    if not cust_id or cust_id != payment.customer_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PAYMENT_NOT_FOUND", "message": "Payment not found"},
        )


def record_payment(
    db: Session,
    payload: PaymentCreate,
    current_user: User,
    idempotency_key: str | None = None,
) -> Payment:
    # 1. Idempotency check
    if idempotency_key:
        existing = (
            db.query(Payment)
            .filter(Payment.idempotency_key == idempotency_key)
            .first()
        )
        if existing:
            return existing

    # 2. Lock invoice row
    stmt = select(Invoice).where(Invoice.id == payload.invoice_id).with_for_update()
    invoice = db.execute(stmt).scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "INVOICE_NOT_FOUND", "message": "Invoice not found"},
        )

    # 3. Ownership check
    if current_user.role not in (UserRole.ADMIN.value, UserRole.STAFF.value):
        cust_id = get_user_customer_id(current_user)
        if not cust_id or cust_id != invoice.customer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "Not authorized to pay this invoice"},
            )

    # 4. State validation
    if invoice.status == InvoiceStatus.CANCELLED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "INVOICE_CANCELLED", "message": "Cannot apply payment to a cancelled invoice"},
        )

    if invoice.status == InvoiceStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "INVOICE_NOT_CONFIRMED", "message": "Cannot apply payment to a draft invoice"},
        )

    if invoice.status == InvoiceStatus.PAID.value or Decimal(str(invoice.amount_due)) <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "INVOICE_ALREADY_PAID", "message": "Invoice has already been fully paid"},
        )

    # 5. Currency check
    if payload.currency.upper() != invoice.currency.upper():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CURRENCY_MISMATCH",
                "message": f"Payment currency '{payload.currency}' does not match invoice currency '{invoice.currency}'",
            },
        )

    # 6. Amount validation
    try:
        pay_amount = round_money(Decimal(payload.amount))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_AMOUNT", "message": "Invalid payment amount"},
        )

    if pay_amount <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_AMOUNT", "message": "Payment amount must be greater than zero"},
        )

    current_due = Decimal(str(invoice.amount_due))
    if pay_amount > current_due:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "OVERPAYMENT_NOT_ALLOWED",
                "message": f"Payment amount ({pay_amount}) exceeds outstanding invoice amount due ({current_due})",
            },
        )

    # 7. Settlement update
    new_paid = round_money(Decimal(str(invoice.amount_paid)) + pay_amount)
    new_due = round_money(Decimal(str(invoice.total)) - new_paid)

    invoice.amount_paid = new_paid
    invoice.amount_due = new_due

    if new_due == Decimal("0.00"):
        invoice.status = InvoiceStatus.PAID.value
        invoice.paid_at = payload.paid_at
    else:
        invoice.status = InvoiceStatus.PARTIALLY_PAID.value

    # 8. Record Payment
    ref_number = generate_payment_reference(db, payload.paid_at.date())
    payment = Payment(
        payment_reference=ref_number,
        invoice_id=invoice.id,
        customer_id=invoice.customer_id,
        method=payload.method.value,
        amount=pay_amount,
        currency=invoice.currency,
        status=PaymentStatus.SUCCEEDED.value,
        paid_at=payload.paid_at,
        note=payload.note,
        reference=payload.reference,
        idempotency_key=idempotency_key,
    )
    db.add(payment)
    db.flush()

    # 9. Create Notification
    notif = Notification(
        customer_id=invoice.customer_id,
        recipient_email=invoice.customer.billing_email if invoice.customer else None,
        channel=NotificationChannel.IN_APP.value,
        notification_type=NotificationType.PAYMENT_RECEIVED.value,
        title=f"Payment Received: {ref_number}",
        message=f"Payment of {invoice.currency} {pay_amount:.2f} received for Invoice {invoice.invoice_number}. New balance: {invoice.currency} {new_due:.2f}.",
        related_entity_type="PAYMENT",
        related_entity_id=payment.id,
        status=NotificationStatus.SENT.value,
    )
    db.add(notif)

    db.commit()
    db.refresh(payment)
    db.refresh(invoice)

    return payment
