from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.payment import Payment
from app.models.user import User, UserRole
from app.modules.invoices.services import get_user_customer_id
from app.modules.payments.schemas import PaymentCreate, PaymentResponse
from app.modules.payments.services import (
    assert_payment_access,
    record_payment,
    serialize_payment,
)


router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


@router.get("", response_model=dict[str, Any])
def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    invoice_id: uuid.UUID | None = Query(None, alias="invoiceId"),
    customer_id: uuid.UUID | None = Query(None, alias="customerId"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    query = select(Payment)

    if current_user.role not in (UserRole.ADMIN.value, UserRole.STAFF.value):
        cust_id = get_user_customer_id(current_user)
        if not cust_id:
            return {"items": [], "total": 0, "page": page, "pageSize": page_size}
        query = query.where(Payment.customer_id == cust_id)
    else:
        if customer_id:
            query = query.where(Payment.customer_id == customer_id)

    if invoice_id:
        query = query.where(Payment.invoice_id == invoice_id)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    payments = (
        db.scalars(
            query.order_by(Payment.paid_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .all()
    )

    return {
        "items": [serialize_payment(p).model_dump(by_alias=True) for p in payments],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    payment = record_payment(
        db=db,
        payload=payload,
        current_user=current_user,
        idempotency_key=idempotency_key,
    )
    return serialize_payment(payment)


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PAYMENT_NOT_FOUND", "message": "Payment not found"},
        )
    assert_payment_access(payment, current_user)
    return serialize_payment(payment)


@router.post("/gateway-intents", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def create_gateway_intent(
    payload: dict[str, Any],
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    current_user: User = Depends(get_current_user),
) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "code": "GATEWAY_NOT_CONFIGURED",
            "message": "No payment gateway provider is configured. Please use manual payments.",
        },
    )


@router.post("/webhooks/{provider}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def receive_webhook(
    provider: str,
    payload: dict[str, Any],
) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "code": "GATEWAY_PROVIDER_NOT_CONFIGURED",
            "message": f"Payment gateway webhook provider '{provider}' is not configured or enabled.",
        },
    )
