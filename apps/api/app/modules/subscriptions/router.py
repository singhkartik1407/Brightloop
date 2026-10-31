from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.customer import Customer
from app.models.quotation import Quotation
from app.models.subscription import (
    Subscription,
    SubscriptionEvent,
    SubscriptionStatus,
)
from app.models.user import User, UserRole
from app.modules.subscriptions.schemas import (
    CancelRequest,
    PlanChangeRequest,
    PlanChangeResult,
    SubscriptionCreate,
    SubscriptionEventResponse,
    SubscriptionResponse,
    SubscriptionUpdate,
)
from app.modules.subscriptions.services import (
    _serialize_subscription,
    activate_subscription,
    cancel_subscription,
    change_subscription_plan,
    close_subscription,
    convert_quotation_to_subscription,
    create_direct_subscription,
    pause_subscription,
    renew_subscription,
    resume_subscription,
)

router = APIRouter(prefix="/api/v1/subscriptions", tags=["Subscriptions"])


def _get_customer_id_for_user(user: User, db: Session) -> uuid.UUID | None:
    if getattr(user, "customer_profile", None) and user.customer_profile:
        return user.customer_profile.id
    customer_id = db.scalar(
        select(Customer.id).where(Customer.user_id == user.id, Customer.is_active == True)
    )
    return customer_id


@router.get("", response_model=dict)
def list_subscriptions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    status_filter: SubscriptionStatus | None = Query(default=None, alias="status"),
    customer_id: uuid.UUID | None = Query(default=None, alias="customerId"),
    renewal_before: date | None = Query(default=None, alias="renewalBefore"),
    search: str | None = Query(default=None),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    query = select(Subscription)

    # Customer isolation
    if current_user.role in [UserRole.CUSTOMER, UserRole.CUSTOMER.value]:
        user_cust_id = _get_customer_id_for_user(current_user, db)
        if not user_cust_id:
            return {"items": [], "total": 0, "page": page, "pageSize": page_size}
        if customer_id and customer_id != user_cust_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "Customers can only view their own subscriptions"},
            )
        query = query.where(Subscription.customer_id == user_cust_id)
    else:
        if customer_id:
            query = query.where(Subscription.customer_id == customer_id)

    if status_filter:
        query = query.where(Subscription.status == status_filter.value)

    if renewal_before:
        query = query.where(Subscription.next_billing_date <= renewal_before)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.where(Subscription.subscription_number.ilike(search_pattern))

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    subscriptions = (
        db.scalars(
            query.order_by(Subscription.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .all()
    )

    items = [_serialize_subscription(s).model_dump(by_alias=True) for s in subscriptions]

    return {
        "items": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_subscription(
    payload: SubscriptionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    if current_user.role in [UserRole.CUSTOMER, UserRole.CUSTOMER.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only staff and admins can create subscriptions directly"},
        )

    subscription = create_direct_subscription(db, payload, actor=current_user)
    db.commit()
    db.refresh(subscription)
    return _serialize_subscription(subscription)


@router.post("/from-quotation/{quotation_id}", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_subscription_from_quotation(
    quotation_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    if current_user.role in [UserRole.CUSTOMER, UserRole.CUSTOMER.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only staff and admins can explicitly convert quotations"},
        )

    quotation = db.get(Quotation, quotation_id)
    if not quotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Quotation not found"},
        )

    sub = convert_quotation_to_subscription(db, quotation, actor=current_user)
    db.commit()
    db.refresh(sub)
    return _serialize_subscription(sub)


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription(
    subscription_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    subscription = db.get(Subscription, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Subscription not found"},
        )

    if current_user.role in [UserRole.CUSTOMER, UserRole.CUSTOMER.value]:
        user_cust_id = _get_customer_id_for_user(current_user, db)
        if subscription.customer_id != user_cust_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": "Subscription not found"},
            )

    return _serialize_subscription(subscription)


@router.patch("/{subscription_id}", response_model=SubscriptionResponse)
def update_subscription(
    subscription_id: uuid.UUID,
    payload: SubscriptionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    if current_user.role in [UserRole.CUSTOMER, UserRole.CUSTOMER.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only staff and admins can update subscription metadata"},
        )

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": "At least one field must be provided for update"},
        )

    subscription = db.get(Subscription, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Subscription not found"},
        )

    if "payment_terms" in update_data:
        subscription.payment_terms = update_data["payment_terms"]

    if "cancel_at_period_end" in update_data and update_data["cancel_at_period_end"] is not None:
        subscription.cancel_at_period_end = update_data["cancel_at_period_end"]

    db.commit()
    db.refresh(subscription)
    return _serialize_subscription(subscription)


@router.post("/{subscription_id}/activate", response_model=SubscriptionResponse)
def activate_sub(
    subscription_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    if current_user.role in [UserRole.CUSTOMER, UserRole.CUSTOMER.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only staff and admins can activate subscriptions"},
        )

    subscription = db.get(Subscription, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Subscription not found"},
        )

    activated = activate_subscription(db, subscription, actor=current_user)
    db.commit()
    db.refresh(activated)
    return _serialize_subscription(activated)


@router.post("/{subscription_id}/pause", response_model=SubscriptionResponse)
def pause_sub(
    subscription_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    if current_user.role in [UserRole.CUSTOMER, UserRole.CUSTOMER.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only staff and admins can pause subscriptions"},
        )

    subscription = db.get(Subscription, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Subscription not found"},
        )

    paused = pause_subscription(db, subscription, actor=current_user)
    db.commit()
    db.refresh(paused)
    return _serialize_subscription(paused)


@router.post("/{subscription_id}/resume", response_model=SubscriptionResponse)
def resume_sub(
    subscription_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    if current_user.role in [UserRole.CUSTOMER, UserRole.CUSTOMER.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only staff and admins can resume subscriptions"},
        )

    subscription = db.get(Subscription, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Subscription not found"},
        )

    resumed = resume_subscription(db, subscription, actor=current_user)
    db.commit()
    db.refresh(resumed)
    return _serialize_subscription(resumed)


@router.post("/{subscription_id}/cancel", response_model=SubscriptionResponse)
def cancel_sub(
    subscription_id: uuid.UUID,
    payload: CancelRequest | None = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    subscription = db.get(Subscription, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Subscription not found"},
        )

    if current_user.role in [UserRole.CUSTOMER, UserRole.CUSTOMER.value]:
        user_cust_id = _get_customer_id_for_user(current_user, db)
        if subscription.customer_id != user_cust_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "You can only request cancellation for your own subscription"},
            )

    cancelled = cancel_subscription(
        db=db,
        subscription=subscription,
        reason=payload.reason if payload else None,
        actor=current_user,
    )
    db.commit()
    db.refresh(cancelled)
    return _serialize_subscription(cancelled)


@router.post("/{subscription_id}/close", response_model=SubscriptionResponse)
def close_sub(
    subscription_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    if current_user.role in [UserRole.CUSTOMER, UserRole.CUSTOMER.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only staff and admins can close subscriptions early"},
        )

    subscription = db.get(Subscription, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Subscription not found"},
        )

    closed = close_subscription(db, subscription, actor=current_user)
    db.commit()
    db.refresh(closed)
    return _serialize_subscription(closed)


@router.post("/{subscription_id}/renew", response_model=SubscriptionResponse)
def renew_sub(
    subscription_id: uuid.UUID,
    expected_renewal_date: date | None = Query(default=None, alias="expectedRenewalDate"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    if current_user and current_user.role in [UserRole.CUSTOMER, UserRole.CUSTOMER.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only staff and admins can trigger manual renewals"},
        )

    renewed = renew_subscription(
        db,
        subscription_id,
        actor=current_user,
        expected_renewal_date=expected_renewal_date,
    )
    return _serialize_subscription(renewed)


@router.post("/{subscription_id}/change-plan", response_model=PlanChangeResult)
def change_plan_endpoint(
    subscription_id: uuid.UUID,
    payload: PlanChangeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    if current_user.role in [UserRole.CUSTOMER, UserRole.CUSTOMER.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only staff and admins can perform plan changes directly"},
        )

    return change_subscription_plan(
        db=db,
        subscription_id=subscription_id,
        new_plan_id=payload.new_plan_id,
        effective_at=payload.effective_at,
        actor=current_user,
    )


@router.get("/{subscription_id}/history", response_model=list[SubscriptionEventResponse])
def get_subscription_history(
    subscription_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    subscription = db.get(Subscription, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Subscription not found"},
        )

    if current_user.role in [UserRole.CUSTOMER, UserRole.CUSTOMER.value]:
        user_cust_id = _get_customer_id_for_user(current_user, db)
        if subscription.customer_id != user_cust_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": "Subscription not found"},
            )

    events = (
        db.scalars(
            select(SubscriptionEvent)
            .where(SubscriptionEvent.subscription_id == subscription_id)
            .order_by(SubscriptionEvent.created_at.desc())
        )
        .all()
    )

    return [SubscriptionEventResponse.model_validate(e) for e in events]
