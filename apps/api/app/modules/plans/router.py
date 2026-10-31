from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models import BillingInterval, Plan, Product, User, UserRole
from app.modules.plans.schemas import (
    PlanCreateRequest,
    PlanListResponse,
    PlanRead,
    PlanUpdateRequest,
)


router = APIRouter(prefix="/api/v1/plans", tags=["Plans"])
admin_staff = require_roles(UserRole.ADMIN, UserRole.STAFF)


def get_plan_or_404(db: Session, plan_id: UUID) -> Plan:
    plan = db.scalar(select(Plan).where(Plan.id == plan_id))
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


def check_associated_product(db: Session, product_id: UUID | None) -> None:
    if product_id is not None:
        product = db.scalar(select(Product).where(Product.id == product_id))
        if product is None:
            raise HTTPException(status_code=404, detail="Associated product not found")


def check_duplicate_plan_name(
    db: Session,
    name: str,
    product_id: UUID | None,
    exclude_plan_id: UUID | None = None,
) -> None:
    conditions = [
        Plan.is_active.is_(True),
        func.lower(Plan.name) == name.strip().lower(),
    ]
    if product_id is not None:
        conditions.append(Plan.product_id == product_id)
    else:
        conditions.append(Plan.product_id.is_(None))
    if exclude_plan_id is not None:
        conditions.append(Plan.id != exclude_plan_id)

    existing = db.scalar(select(Plan).where(*conditions))
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="An active plan with this name already exists for the product",
        )


def save_plan(db: Session, plan: Plan) -> Plan:
    try:
        db.commit()
        db.refresh(plan)
        return plan
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Plan operation failed due to a data conflict",
        )


@router.post(
    "",
    response_model=PlanRead,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
def create_plan(
    payload: PlanCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(admin_staff),
):
    check_associated_product(db, payload.product_id)
    check_duplicate_plan_name(db, payload.name, payload.product_id)

    data = payload.model_dump(by_alias=False)
    plan = Plan(**data)
    db.add(plan)
    return save_plan(db, plan)


@router.get(
    "",
    response_model=PlanListResponse,
    response_model_by_alias=True,
)
def list_plans(
    search: str | None = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    is_active: bool | None = Query(default=None, alias="isActive"),
    product_id: UUID | None = Query(default=None, alias="productId"),
    billing_interval: BillingInterval | None = Query(default=None, alias="billingInterval"),
    db: Session = Depends(get_db),
    user: User = Depends(admin_staff),
):
    conditions = (
        [Plan.is_active.is_(True)]
        if is_active is None
        else [Plan.is_active.is_(is_active)]
    )

    search_term = (search or "").strip()
    if search_term:
        escaped = (
            search_term.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        pattern = f"%{escaped}%"
        conditions.append(
            or_(
                Plan.name.ilike(pattern, escape="\\"),
                Plan.description.ilike(pattern, escape="\\"),
            )
        )

    if product_id is not None:
        conditions.append(Plan.product_id == product_id)

    if billing_interval is not None:
        conditions.append(Plan.billing_interval == billing_interval.value)

    total = db.scalar(select(func.count(Plan.id)).where(*conditions)) or 0
    plans = (
        db.scalars(
            select(Plan)
            .where(*conditions)
            .order_by(Plan.created_at.desc(), Plan.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .all()
    )

    return PlanListResponse(
        items=plans,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{planId}",
    response_model=PlanRead,
    response_model_by_alias=True,
)
def get_plan(
    plan_id: UUID = Path(alias="planId"),
    db: Session = Depends(get_db),
    user: User = Depends(admin_staff),
):
    return get_plan_or_404(db, plan_id)


@router.patch(
    "/{planId}",
    response_model=PlanRead,
    response_model_by_alias=True,
)
def update_plan(
    payload: PlanUpdateRequest,
    plan_id: UUID = Path(alias="planId"),
    db: Session = Depends(get_db),
    user: User = Depends(admin_staff),
):
    plan = get_plan_or_404(db, plan_id)
    if not plan.is_active and payload.is_active is not True:
        raise HTTPException(
            status_code=409,
            detail="Archived plan must be restored before updating",
        )

    changes = payload.model_dump(exclude_unset=True, by_alias=False)
    if not changes:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update",
        )

    if "product_id" in payload.model_fields_set:
        check_associated_product(db, payload.product_id)

    # Validate merged date range
    new_from = (
        payload.available_from
        if "available_from" in payload.model_fields_set
        else plan.available_from
    )
    new_until = (
        payload.available_until
        if "available_until" in payload.model_fields_set
        else plan.available_until
    )
    if new_from is not None and new_until is not None and new_until < new_from:
        raise HTTPException(
            status_code=422,
            detail="Plan availability end date cannot precede start date",
        )

    # Check for duplicate name if name or product_id or active status changes
    target_name = payload.name if payload.name is not None else plan.name
    target_pid = (
        payload.product_id
        if "product_id" in payload.model_fields_set
        else plan.product_id
    )
    if (
        payload.name is not None
        or "product_id" in payload.model_fields_set
        or payload.is_active is True
    ):
        check_duplicate_plan_name(
            db,
            target_name,
            target_pid,
            exclude_plan_id=plan.id,
        )

    for field, value in changes.items():
        setattr(plan, field, value)

    return save_plan(db, plan)


@router.post(
    "/{planId}/archive",
    status_code=status.HTTP_204_NO_CONTENT,
)
def archive_plan(
    plan_id: UUID = Path(alias="planId"),
    db: Session = Depends(get_db),
    user: User = Depends(admin_staff),
):
    plan = get_plan_or_404(db, plan_id)
    if plan.is_active:
        plan.is_active = False
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{planId}/restore",
    response_model=PlanRead,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
)
def restore_plan(
    plan_id: UUID = Path(alias="planId"),
    db: Session = Depends(get_db),
    user: User = Depends(admin_staff),
):
    plan = get_plan_or_404(db, plan_id)
    if not plan.is_active:
        check_duplicate_plan_name(
            db,
            plan.name,
            plan.product_id,
            exclude_plan_id=plan.id,
        )
        plan.is_active = True
        db.commit()
        db.refresh(plan)
    return plan
