from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models import TaxRule, TaxType, User, UserRole
from app.modules.taxes.schemas import (
    TaxRuleCreateRequest,
    TaxRuleListResponse,
    TaxRuleRead,
    TaxRuleUpdateRequest,
)


router = APIRouter(prefix="/api/v1/tax-rules", tags=["Taxes"])
admin_staff = require_roles(UserRole.ADMIN, UserRole.STAFF)


def get_tax_rule_or_404(db: Session, tax_rule_id: UUID) -> TaxRule:
    rule = db.scalar(select(TaxRule).where(TaxRule.id == tax_rule_id))
    if rule is None:
        raise HTTPException(status_code=404, detail="Tax rule not found")
    return rule


def check_duplicate_tax_code(
    db: Session,
    code: str,
    exclude_id: UUID | None = None,
) -> None:
    conditions = [
        func.lower(func.trim(TaxRule.code)) == code.strip().lower(),
    ]
    if exclude_id is not None:
        conditions.append(TaxRule.id != exclude_id)

    existing = db.scalar(select(TaxRule).where(*conditions))
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="A tax rule with this code already exists",
        )


def save_tax_rule(db: Session, tax_rule: TaxRule) -> TaxRule:
    try:
        db.commit()
        db.refresh(tax_rule)
        return tax_rule
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Tax rule operation failed due to a data conflict",
        )


@router.post(
    "",
    response_model=TaxRuleRead,
    response_model_by_alias=True,
    status_code=status.HTTP_201_CREATED,
)
def create_tax_rule(
    payload: TaxRuleCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(admin_staff),
):
    check_duplicate_tax_code(db, payload.code)
    data = payload.model_dump(by_alias=False)
    rule = TaxRule(**data)
    db.add(rule)
    return save_tax_rule(db, rule)


@router.get(
    "",
    response_model=TaxRuleListResponse,
    response_model_by_alias=True,
)
def list_tax_rules(
    search: str | None = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    is_active: bool | None = Query(default=None, alias="isActive"),
    tax_type: TaxType | None = Query(default=None, alias="taxType"),
    jurisdiction: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
    user: User = Depends(admin_staff),
):
    conditions = (
        [TaxRule.is_active.is_(True)]
        if is_active is None
        else [TaxRule.is_active.is_(is_active)]
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
                TaxRule.name.ilike(pattern, escape="\\"),
                TaxRule.code.ilike(pattern, escape="\\"),
                TaxRule.jurisdiction.ilike(pattern, escape="\\"),
            )
        )

    if tax_type is not None:
        conditions.append(TaxRule.tax_type == tax_type.value)

    if jurisdiction is not None:
        conditions.append(TaxRule.jurisdiction.ilike(f"%{jurisdiction.strip()}%"))

    total = db.scalar(select(func.count(TaxRule.id)).where(*conditions)) or 0
    rules = (
        db.scalars(
            select(TaxRule)
            .where(*conditions)
            .order_by(TaxRule.created_at.desc(), TaxRule.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .all()
    )

    return TaxRuleListResponse(
        items=rules,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{taxRuleId}",
    response_model=TaxRuleRead,
    response_model_by_alias=True,
)
def get_tax_rule(
    tax_rule_id: UUID = Path(alias="taxRuleId"),
    db: Session = Depends(get_db),
    user: User = Depends(admin_staff),
):
    return get_tax_rule_or_404(db, tax_rule_id)


@router.patch(
    "/{taxRuleId}",
    response_model=TaxRuleRead,
    response_model_by_alias=True,
)
def update_tax_rule(
    payload: TaxRuleUpdateRequest,
    tax_rule_id: UUID = Path(alias="taxRuleId"),
    db: Session = Depends(get_db),
    user: User = Depends(admin_staff),
):
    rule = get_tax_rule_or_404(db, tax_rule_id)
    if not rule.is_active and payload.is_active is not True:
        raise HTTPException(
            status_code=409,
            detail="Archived tax rule must be restored before updating",
        )

    changes = payload.model_dump(exclude_unset=True, by_alias=False)
    if not changes:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update",
        )

    if payload.code is not None:
        check_duplicate_tax_code(db, payload.code, exclude_id=rule.id)

    for field, value in changes.items():
        setattr(rule, field, value)

    return save_tax_rule(db, rule)


@router.post(
    "/{taxRuleId}/archive",
    status_code=status.HTTP_204_NO_CONTENT,
)
def archive_tax_rule(
    tax_rule_id: UUID = Path(alias="taxRuleId"),
    db: Session = Depends(get_db),
    user: User = Depends(admin_staff),
):
    rule = get_tax_rule_or_404(db, tax_rule_id)
    if rule.is_active:
        rule.is_active = False
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{taxRuleId}/restore",
    response_model=TaxRuleRead,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
)
def restore_tax_rule(
    tax_rule_id: UUID = Path(alias="taxRuleId"),
    db: Session = Depends(get_db),
    user: User = Depends(admin_staff),
):
    rule = get_tax_rule_or_404(db, tax_rule_id)
    if not rule.is_active:
        check_duplicate_tax_code(db, rule.code, exclude_id=rule.id)
        rule.is_active = True
        db.commit()
        db.refresh(rule)
    return rule
