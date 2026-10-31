from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models import (
    DiscountRule,
    DiscountScope,
    DiscountTarget,
    DiscountType,
    Product,
    User,
    UserRole,
)
from app.modules.discounts.schemas import (
    DiscountRuleCreateRequest,
    DiscountRuleListResponse,
    DiscountRuleRead,
    DiscountRuleUpdateRequest,
)


router = APIRouter(prefix="/api/v1/discount-rules", tags=["Discounts"])
admin_only = require_roles(UserRole.ADMIN)
admin_staff = require_roles(UserRole.ADMIN, UserRole.STAFF)


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_discount_rule_or_404(db: Session, discount_rule_id: UUID) -> DiscountRule:
    rule = db.scalar(
        select(DiscountRule)
        .options(selectinload(DiscountRule.targets))
        .where(DiscountRule.id == discount_rule_id)
    )
    if rule is None:
        raise HTTPException(status_code=404, detail="Discount rule not found")
    return rule


def serialize_discount_rule(rule: DiscountRule) -> DiscountRuleRead:
    p_ids = [target.product_id for target in rule.targets]
    read_obj = DiscountRuleRead.model_validate(rule)
    read_obj.product_ids = p_ids
    return read_obj


def verify_product_ids(db: Session, product_ids: list[UUID] | None) -> None:
    if not product_ids:
        return
    unique_ids = list(set(product_ids))
    existing = db.scalars(
        select(Product.id).where(Product.id.in_(unique_ids))
    ).all()
    missing = set(unique_ids) - set(existing)
    if missing:
        missing_id = next(iter(missing))
        raise HTTPException(
            status_code=404,
            detail=f"Product with id {missing_id} not found",
        )


def check_duplicate_code(
    db: Session,
    code: str | None,
    exclude_id: UUID | None = None,
) -> None:
    if not code:
        return
    conditions = [
        func.lower(func.trim(DiscountRule.code)) == code.strip().lower(),
    ]
    if exclude_id is not None:
        conditions.append(DiscountRule.id != exclude_id)
    existing = db.scalar(select(DiscountRule).where(*conditions))
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="A discount rule with this code already exists",
        )


def save_discount_rule(db: Session, rule: DiscountRule) -> DiscountRule:
    try:
        db.commit()
        db.refresh(rule)
        return rule
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Discount rule operation failed due to a data conflict",
        )


@router.post(
    "",
    response_model=DiscountRuleRead,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
def create_discount_rule(
    payload: DiscountRuleCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(admin_only),
):
    check_duplicate_code(db, payload.code)
    verify_product_ids(db, payload.product_ids)

    data = payload.model_dump(exclude={"product_ids"}, by_alias=False)
    rule = DiscountRule(**data)
    for pid in set(payload.product_ids or []):
        rule.targets.append(DiscountTarget(product_id=pid))

    db.add(rule)
    saved = save_discount_rule(db, rule)
    return serialize_discount_rule(saved)


@router.get(
    "",
    response_model=DiscountRuleListResponse,
    response_model_by_alias=True,
)
def list_discount_rules(
    search: str | None = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    is_active: bool | None = Query(default=None, alias="isActive"),
    discount_type: DiscountType | None = Query(default=None, alias="discountType"),
    scope: DiscountScope | None = Query(default=None, alias="scope"),
    db: Session = Depends(get_db),
    user: User = Depends(admin_staff),
):
    conditions = (
        [DiscountRule.is_active.is_(True)]
        if is_active is None
        else [DiscountRule.is_active.is_(is_active)]
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
                DiscountRule.name.ilike(pattern, escape="\\"),
                DiscountRule.code.ilike(pattern, escape="\\"),
            )
        )

    if discount_type is not None:
        conditions.append(DiscountRule.discount_type == discount_type.value)

    if scope is not None:
        conditions.append(DiscountRule.scope == scope.value)

    total = db.scalar(select(func.count(DiscountRule.id)).where(*conditions)) or 0
    rules = (
        db.scalars(
            select(DiscountRule)
            .options(selectinload(DiscountRule.targets))
            .where(*conditions)
            .order_by(DiscountRule.created_at.desc(), DiscountRule.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .all()
    )

    items = [serialize_discount_rule(r) for r in rules]
    return DiscountRuleListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{discountRuleId}",
    response_model=DiscountRuleRead,
    response_model_by_alias=True,
)
def get_discount_rule(
    discount_rule_id: UUID = Path(alias="discountRuleId"),
    db: Session = Depends(get_db),
    user: User = Depends(admin_staff),
):
    rule = get_discount_rule_or_404(db, discount_rule_id)
    return serialize_discount_rule(rule)


@router.patch(
    "/{discountRuleId}",
    response_model=DiscountRuleRead,
    response_model_by_alias=True,
)
def update_discount_rule(
    payload: DiscountRuleUpdateRequest,
    discount_rule_id: UUID = Path(alias="discountRuleId"),
    db: Session = Depends(get_db),
    user: User = Depends(admin_only),
):
    rule = get_discount_rule_or_404(db, discount_rule_id)
    if not rule.is_active and payload.is_active is not True:
        raise HTTPException(
            status_code=409,
            detail="Archived discount rule must be restored before updating",
        )

    changes = payload.model_dump(
        exclude_unset=True, exclude={"product_ids"}, by_alias=False
    )
    if not changes and "product_ids" not in payload.model_fields_set:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update",
        )

    if payload.code is not None:
        check_duplicate_code(db, payload.code, exclude_id=rule.id)

    # Validate merged date range
    new_starts = ensure_utc(
        payload.starts_at if payload.starts_at is not None else rule.starts_at
    )
    new_ends = ensure_utc(
        payload.ends_at if payload.ends_at is not None else rule.ends_at
    )
    if new_ends is not None and new_starts is not None and new_ends < new_starts:
        raise HTTPException(
            status_code=422,
            detail="Discount end date cannot precede start date",
        )

    # Validate merged percentage value
    new_type = (
        payload.discount_type
        if payload.discount_type is not None
        else rule.discount_type
    )
    new_value = (
        payload.value if payload.value is not None else rule.value
    )
    if new_type == DiscountType.PERCENTAGE.value and new_value > 100:
        raise HTTPException(
            status_code=422,
            detail="Percentage discount value cannot exceed 100.00",
        )

    if "product_ids" in payload.model_fields_set:
        verify_product_ids(db, payload.product_ids)
        rule.targets.clear()
        for pid in set(payload.product_ids or []):
            rule.targets.append(DiscountTarget(product_id=pid))

    for field, value in changes.items():
        setattr(rule, field, value)

    saved = save_discount_rule(db, rule)
    return serialize_discount_rule(saved)


@router.post(
    "/{discountRuleId}/archive",
    status_code=status.HTTP_204_NO_CONTENT,
)
def archive_discount_rule(
    discount_rule_id: UUID = Path(alias="discountRuleId"),
    db: Session = Depends(get_db),
    user: User = Depends(admin_only),
):
    rule = get_discount_rule_or_404(db, discount_rule_id)
    if rule.is_active:
        rule.is_active = False
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{discountRuleId}/restore",
    response_model=DiscountRuleRead,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
)
def restore_discount_rule(
    discount_rule_id: UUID = Path(alias="discountRuleId"),
    db: Session = Depends(get_db),
    user: User = Depends(admin_only),
):
    rule = get_discount_rule_or_404(db, discount_rule_id)
    if not rule.is_active:
        check_duplicate_code(db, rule.code, exclude_id=rule.id)
        rule.is_active = True
        db.commit()
        db.refresh(rule)
    return serialize_discount_rule(rule)
