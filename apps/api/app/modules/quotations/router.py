from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.customer import Customer
from app.models.discount import DiscountRule
from app.models.plan import Plan
from app.models.quotation import (
    Quotation,
    QuotationCounter,
    QuotationLine,
    QuotationStatus,
)
from app.models.quote_template import QuoteTemplate
from app.models.user import User, UserRole
from app.modules.quotation_templates.schemas import SubscriptionLineInput
from app.modules.quotations.pricing import calculate_quotation
from app.modules.quotations.schemas import (
    InvoiceLine,
    InvoiceTax,
    QuotationCreate,
    QuotationResponse,
    QuotationUpdate,
)

router = APIRouter(prefix="/api/v1/quotations", tags=["Quotations"])


def _generate_quotation_number(db: Session) -> str:
    current_year = datetime.now(timezone.utc).year
    prefix = f"QUO-{current_year}-"

    max_num_record = (
        db.query(Quotation.quotation_number)
        .filter(Quotation.quotation_number.like(f"{prefix}%"))
        .order_by(Quotation.quotation_number.desc())
        .first()
    )
    initial_seq = 1
    if max_num_record and max_num_record[0]:
        try:
            initial_seq = int(max_num_record[0].replace(prefix, "")) + 1
        except ValueError:
            initial_seq = 1

    # Atomic initialization: INSERT ON CONFLICT DO NOTHING guarantees concurrent first-time
    # requests cannot crash with unique constraint violations or create duplicate counter rows.
    insert_stmt = (
        pg_insert(QuotationCounter)
        .values(year=current_year, next_seq=initial_seq)
        .on_conflict_do_nothing(index_elements=["year"])
    )
    db.execute(insert_stmt)

    # Now that the row is guaranteed to exist, acquire row lock via with_for_update()
    counter = (
        db.query(QuotationCounter)
        .filter(QuotationCounter.year == current_year)
        .with_for_update()
        .first()
    )

    seq = counter.next_seq
    counter.next_seq += 1
    db.flush()

    return f"{prefix}{seq:04d}"


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _get_effective_status(quotation: Quotation) -> QuotationStatus:
    now_utc = datetime.now(timezone.utc)
    if quotation.status in [QuotationStatus.DRAFT.value, QuotationStatus.QUOTATION.value]:
        exp = ensure_utc(quotation.expires_at)
        if exp and exp <= now_utc:
            return QuotationStatus.EXPIRED
    return QuotationStatus(quotation.status)


def _serialize_quotation(quotation: Quotation) -> QuotationResponse:
    lines = [
        InvoiceLine(
            product_id=line.product_id,
            description=line.description,
            quantity=line.quantity,
            unit_price=f"{line.unit_price:.2f}",
            selected_variants=line.selected_variants or [],
            taxes=[
                InvoiceTax(
                    name=t["name"],
                    code=t["code"],
                    rate_percent=str(t["ratePercent"]),
                    amount=str(t["amount"]),
                )
                for t in (line.taxes_data or [])
            ],
            line_subtotal=f"{line.line_subtotal:.2f}",
            tax_amount=f"{line.tax_amount:.2f}",
            discount_amount=f"{line.discount_amount:.2f}",
            line_total=f"{line.line_total:.2f}",
        )
        for line in quotation.lines
    ]

    customer_name = (
        quotation.customer.display_name
        if quotation.customer
        else (quotation.snapshot_data or {}).get("customerName", "")
    )
    plan_name = (
        quotation.plan.name
        if quotation.plan
        else (quotation.snapshot_data or {}).get("planName", "")
    )

    effective_status = _get_effective_status(quotation)

    return QuotationResponse(
        id=quotation.id,
        number=quotation.quotation_number,
        customer_id=quotation.customer_id,
        customer_name=customer_name,
        plan_id=quotation.plan_id,
        plan_name=plan_name,
        status=effective_status,
        start_date=quotation.start_date,
        expires_at=quotation.expires_at,
        payment_terms=quotation.payment_terms,
        lines=lines,
        subtotal=f"{quotation.subtotal:.2f}",
        tax_total=f"{quotation.tax_total:.2f}",
        discount_total=f"{quotation.discount_total:.2f}",
        total=f"{quotation.total:.2f}",
        currency=quotation.currency,
        subscription_id=quotation.subscription_id,
        created_at=quotation.created_at,
    )


def _get_customer_id_for_user(user: User, db: Session) -> uuid.UUID | None:
    if getattr(user, "customer_profile", None) and user.customer_profile:
        return user.customer_profile.id
    customer_id = db.scalar(
        select(Customer.id).where(Customer.user_id == user.id, Customer.is_active == True)
    )
    return customer_id


@router.get("", response_model=dict)
def list_quotations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    status_filter: QuotationStatus | None = Query(default=None, alias="status"),
    customer_id: uuid.UUID | None = Query(default=None, alias="customerId"),
    search: str | None = Query(default=None),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    query = select(Quotation)

    # Customer isolation
    if current_user.role in [UserRole.CUSTOMER, UserRole.CUSTOMER.value]:
        user_cust_id = _get_customer_id_for_user(current_user, db)
        if not user_cust_id:
            return {"items": [], "total": 0, "page": page, "pageSize": page_size}
        if customer_id and customer_id != user_cust_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "Customers can only view their own quotations"},
            )
        query = query.where(Quotation.customer_id == user_cust_id)
    else:
        if customer_id:
            query = query.where(Quotation.customer_id == customer_id)

    if status_filter:
        query = query.where(Quotation.status == status_filter.value)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.where(Quotation.quotation_number.ilike(search_pattern))

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    quotations = (
        db.scalars(
            query.order_by(Quotation.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .all()
    )

    items = [_serialize_quotation(q).model_dump(by_alias=True) for q in quotations]

    return {
        "items": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.post("", response_model=QuotationResponse, status_code=status.HTTP_201_CREATED)
def create_quotation(
    payload: QuotationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    if current_user.role == UserRole.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only staff and admins can create quotations"},
        )

    # Customer check
    customer = db.get(Customer, payload.customer_id)
    if not customer or not customer.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": "Customer not found or is inactive"},
        )

    # Template check and default lines/plan
    template: QuoteTemplate | None = None
    if payload.template_id:
        template = db.get(QuoteTemplate, payload.template_id)
        if not template or not template.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "BAD_REQUEST", "message": "Quotation template not found or is inactive"},
            )

    plan_id = payload.plan_id or (template.plan_id if template else None)
    if not plan_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "VALIDATION_ERROR", "message": "planId is required"},
        )

    plan = db.get(Plan, plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": "Plan not found or is inactive"},
        )

    # Plan availability check
    today = date.today()
    if plan.available_from and plan.available_from > today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": "Plan is not yet available"},
        )
    if plan.available_until and plan.available_until < today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": "Plan has expired and is no longer available"},
        )

    lines_input = payload.lines
    if lines_input is None and template:
        lines_input = [
            SubscriptionLineInput(
                product_id=tl.product_id,
                quantity=tl.quantity,
                selected_variant_ids=[uuid.UUID(str(v)) for v in tl.selected_variant_ids],
                tax_rule_ids=[uuid.UUID(str(t)) for t in tl.tax_rule_ids],
            )
            for tl in template.lines
        ]

    if not lines_input:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "VALIDATION_ERROR", "message": "At least one line item is required"},
        )

    # Validity
    validity_days = payload.validity_days or (template.validity_days if template else 30)
    now_utc = datetime.now(timezone.utc)
    expires_at = now_utc + timedelta(days=validity_days)

    # Calculate pricing, taxes, highest saving discount
    calc = calculate_quotation(
        db=db,
        customer=customer,
        plan=plan,
        input_lines=lines_input,
        discount_code=payload.discount_code,
        template_name=template.name if template else None,
    )

    quote_number = _generate_quotation_number(db)

    quotation = Quotation(
        quotation_number=quote_number,
        customer_id=customer.id,
        template_id=template.id if template else None,
        plan_id=plan.id,
        status=QuotationStatus.DRAFT.value,
        start_date=payload.start_date,
        expires_at=expires_at,
        payment_terms=payload.payment_terms,
        subtotal=calc.subtotal,
        tax_total=calc.tax_total,
        discount_total=calc.discount_total,
        total=calc.total,
        currency=calc.currency,
        discount_rule_id=calc.discount_rule_id,
        snapshot_data=calc.snapshot_data,
    )

    for cline in calc.lines:
        qline = QuotationLine(
            product_id=cline.product_id,
            description=cline.description,
            quantity=cline.quantity,
            unit_price=cline.unit_price,
            selected_variants=cline.selected_variants,
            taxes_data=cline.taxes_data,
            line_subtotal=cline.line_subtotal,
            tax_amount=cline.tax_amount,
            discount_amount=cline.discount_amount,
            line_total=cline.line_total,
        )
        quotation.lines.append(qline)

    db.add(quotation)
    db.commit()
    db.refresh(quotation)

    return _serialize_quotation(quotation)


@router.get("/{quotation_id}", response_model=QuotationResponse)
def get_quotation(
    quotation_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Quotation not found"},
        )

    if current_user.role in [UserRole.CUSTOMER, UserRole.CUSTOMER.value]:
        user_cust_id = _get_customer_id_for_user(current_user, db)
        if quotation.customer_id != user_cust_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": "Quotation not found"},
            )

    return _serialize_quotation(quotation)


@router.patch("/{quotation_id}", response_model=QuotationResponse)
def update_quotation(
    quotation_id: uuid.UUID,
    payload: QuotationUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    if current_user.role == UserRole.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only staff and admins can update quotations"},
        )

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": "At least one field must be provided for update"},
        )

    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Quotation not found"},
        )

    if quotation.status != QuotationStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CONFLICT",
                "message": f"Cannot modify quotation in '{quotation.status}' status. Only DRAFT quotations can be edited.",
            },
        )

    now_utc = datetime.now(timezone.utc)
    exp = ensure_utc(quotation.expires_at)
    if exp and exp <= now_utc:
        quotation.status = QuotationStatus.EXPIRED.value
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": "Quotation has already expired and cannot be modified."},
        )

    plan = quotation.plan
    if "plan_id" in update_data and update_data["plan_id"] is not None:
        new_plan = db.get(Plan, update_data["plan_id"])
        if not new_plan or not new_plan.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "BAD_REQUEST", "message": "Plan not found or is inactive"},
            )
        plan = new_plan
        quotation.plan_id = plan.id

    if "start_date" in update_data and update_data["start_date"] is not None:
        quotation.start_date = update_data["start_date"]

    if "payment_terms" in update_data:
        quotation.payment_terms = update_data["payment_terms"]

    if "validity_days" in update_data and update_data["validity_days"] is not None:
        quotation.expires_at = datetime.now(timezone.utc) + timedelta(days=update_data["validity_days"])

    # If lines or plan changed, recalculate
    if "lines" in update_data and update_data["lines"] is not None:
        lines_input = payload.lines
    else:
        # Reconstruct lines from existing product lines
        lines_input = [
            SubscriptionLineInput(
                product_id=l.product_id,
                quantity=l.quantity,
                selected_variant_ids=[],
                tax_rule_ids=[],
            )
            for l in quotation.lines
            if l.product_id and l.product_id != plan.product_id
        ]
        if not lines_input:
            lines_input = [
                SubscriptionLineInput(
                    product_id=quotation.lines[0].product_id,
                    quantity=quotation.lines[0].quantity,
                    selected_variant_ids=[],
                    tax_rule_ids=[],
                )
            ]

    calc = calculate_quotation(
        db=db,
        customer=quotation.customer,
        plan=plan,
        input_lines=lines_input,
        discount_code=payload.discount_code,
        template_name=(quotation.snapshot_data or {}).get("templateName"),
    )

    quotation.subtotal = calc.subtotal
    quotation.tax_total = calc.tax_total
    quotation.discount_total = calc.discount_total
    quotation.total = calc.total
    quotation.discount_rule_id = calc.discount_rule_id
    quotation.snapshot_data = calc.snapshot_data

    quotation.lines.clear()
    for cline in calc.lines:
        qline = QuotationLine(
            product_id=cline.product_id,
            description=cline.description,
            quantity=cline.quantity,
            unit_price=cline.unit_price,
            selected_variants=cline.selected_variants,
            taxes_data=cline.taxes_data,
            line_subtotal=cline.line_subtotal,
            tax_amount=cline.tax_amount,
            discount_amount=cline.discount_amount,
            line_total=cline.line_total,
        )
        quotation.lines.append(qline)

    db.commit()
    db.refresh(quotation)
    return _serialize_quotation(quotation)


@router.post("/{quotation_id}/send", response_model=QuotationResponse)
def send_quotation(
    quotation_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    if current_user.role == UserRole.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only staff and admins can issue/send quotations"},
        )

    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Quotation not found"},
        )

    if quotation.status != QuotationStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": f"Cannot send quotation in '{quotation.status}' status"},
        )

    now_utc = datetime.now(timezone.utc)
    exp = ensure_utc(quotation.expires_at)
    if exp and exp <= now_utc:
        quotation.status = QuotationStatus.EXPIRED.value
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": "Quotation has already expired"},
        )

    quotation.status = QuotationStatus.QUOTATION.value
    quotation.sent_at = now_utc
    db.commit()
    db.refresh(quotation)
    return _serialize_quotation(quotation)


@router.post("/{quotation_id}/accept", response_model=QuotationResponse)
def accept_quotation(
    quotation_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    quotation = (
        db.query(Quotation)
        .filter(Quotation.id == quotation_id)
        .with_for_update()
        .first()
    )
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Quotation not found"},
        )

    if current_user.role in [UserRole.CUSTOMER, UserRole.CUSTOMER.value]:
        user_cust_id = _get_customer_id_for_user(current_user, db)
        if quotation.customer_id != user_cust_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "You can only accept your own quotation"},
            )

    now_utc = datetime.now(timezone.utc)
    exp = ensure_utc(quotation.expires_at)
    if (exp and exp <= now_utc) or quotation.status == QuotationStatus.EXPIRED.value:
        quotation.status = QuotationStatus.EXPIRED.value
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": "Quotation has expired and cannot be accepted"},
        )

    if quotation.status not in [QuotationStatus.QUOTATION.value, QuotationStatus.DRAFT.value]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": f"Cannot accept quotation in '{quotation.status}' status"},
        )

    # Transition to CONFIRMED
    quotation.status = QuotationStatus.CONFIRMED.value
    quotation.accepted_at = now_utc

    # Discount redemption tracking: increment usedCount if quotation applied a discount
    if quotation.discount_rule_id:
        discount_rule = (
            db.query(DiscountRule)
            .filter(DiscountRule.id == quotation.discount_rule_id)
            .with_for_update()
            .first()
        )
        if discount_rule:
            if discount_rule.max_uses is not None and discount_rule.used_count >= discount_rule.max_uses:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "DISCOUNT_CAP_REACHED",
                        "message": f"Discount code '{discount_rule.code}' has reached its maximum usage limit",
                    },
                )
            discount_rule.used_count += 1

    # Automatically convert confirmed quotation into a subscription
    from app.modules.subscriptions.services import convert_quotation_to_subscription
    convert_quotation_to_subscription(db, quotation, actor=current_user)

    db.commit()
    db.refresh(quotation)
    return _serialize_quotation(quotation)


@router.post("/{quotation_id}/reject", response_model=QuotationResponse)
def reject_quotation(
    quotation_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Quotation not found"},
        )

    if current_user.role in [UserRole.CUSTOMER, UserRole.CUSTOMER.value]:
        user_cust_id = _get_customer_id_for_user(current_user, db)
        if quotation.customer_id != user_cust_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "You can only reject your own quotation"},
            )

    if quotation.status in [QuotationStatus.CONFIRMED.value, QuotationStatus.REJECTED.value, QuotationStatus.EXPIRED.value]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": f"Cannot reject quotation in '{quotation.status}' status"},
        )

    quotation.status = QuotationStatus.REJECTED.value
    quotation.rejected_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(quotation)
    return _serialize_quotation(quotation)
