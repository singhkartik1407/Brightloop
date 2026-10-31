from __future__ import annotations

import math
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.plan import Plan
from app.models.product import Product, ProductVariant
from app.models.quote_template import QuoteTemplate, QuoteTemplateLine
from app.models.tax import TaxRule
from app.models.user import User, UserRole
from app.modules.quotation_templates.schemas import (
    QuoteTemplateCreate,
    QuoteTemplateResponse,
    QuoteTemplateUpdate,
    SubscriptionLineInput,
)

router = APIRouter(prefix="/api/v1/quote-templates", tags=["Quote Templates"])


def _validate_template_lines(db: Session, lines: list[SubscriptionLineInput], plan_id: uuid.UUID | None = None) -> None:
    if not lines:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "VALIDATION_ERROR", "message": "At least one line item is required"},
        )

    for line in lines:
        product = db.get(Product, line.product_id)
        if not product or not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "BAD_REQUEST", "message": f"Product '{line.product_id}' not found or is inactive"},
            )

        if line.selected_variant_ids:
            seen_attributes = set()
            for variant_id in line.selected_variant_ids:
                variant = db.get(ProductVariant, variant_id)
                if not variant or variant.product_id != line.product_id or not variant.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "code": "BAD_REQUEST",
                            "message": f"Product variant '{variant_id}' does not belong to product '{line.product_id}' or is inactive",
                        },
                    )
                attr_lower = variant.attribute_name.lower().strip()
                if attr_lower in seen_attributes:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "code": "BAD_REQUEST",
                            "message": f"Duplicate variant attribute '{variant.attribute_name}' on the same line",
                        },
                    )
                seen_attributes.add(attr_lower)

        if line.tax_rule_ids:
            for tax_id in line.tax_rule_ids:
                tax_rule = db.get(TaxRule, tax_id)
                if not tax_rule or not tax_rule.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={"code": "BAD_REQUEST", "message": f"Tax rule '{tax_id}' not found or is inactive"},
                    )


def _serialize_template(template: QuoteTemplate) -> QuoteTemplateResponse:
    lines = [
        SubscriptionLineInput(
            product_id=line.product_id,
            quantity=line.quantity,
            selected_variant_ids=[uuid.UUID(str(v)) for v in line.selected_variant_ids],
            tax_rule_ids=[uuid.UUID(str(t)) for t in line.tax_rule_ids],
        )
        for line in template.lines
    ]
    return QuoteTemplateResponse(
        id=template.id,
        name=template.name,
        validity_days=template.validity_days,
        plan_id=template.plan_id,
        lines=lines,
        is_active=template.is_active,
        created_at=template.created_at,
    )


@router.get("", response_model=dict)
def list_quote_templates(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    search: str | None = Query(default=None),
    is_active: bool | None = Query(default=None, alias="isActive"),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: Session = Depends(get_db),
):
    if current_user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only admin and staff can access quotation templates"},
        )

    query = select(QuoteTemplate)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.where(QuoteTemplate.name.ilike(search_pattern))

    if is_active is not None:
        query = query.where(QuoteTemplate.is_active == is_active)

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    templates = (
        db.scalars(
            query.order_by(QuoteTemplate.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .all()
    )

    items = [_serialize_template(t).model_dump(by_alias=True) for t in templates]

    return {
        "items": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.post("", response_model=QuoteTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_quote_template(
    payload: QuoteTemplateCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only admins can create quotation templates"},
        )

    plan = db.get(Plan, payload.plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": "Plan not found or is inactive"},
        )

    _validate_template_lines(db, payload.lines, payload.plan_id)

    template = QuoteTemplate(
        name=payload.name.strip(),
        validity_days=payload.validity_days,
        plan_id=payload.plan_id,
        is_active=True,
    )

    for line_in in payload.lines:
        line_model = QuoteTemplateLine(
            product_id=line_in.product_id,
            quantity=line_in.quantity,
            selected_variant_ids=[str(v) for v in line_in.selected_variant_ids],
            tax_rule_ids=[str(t) for t in (line_in.tax_rule_ids or [])],
        )
        template.lines.append(line_model)

    db.add(template)
    db.commit()
    db.refresh(template)

    return _serialize_template(template)


@router.get("/{template_id}", response_model=QuoteTemplateResponse)
def get_quote_template(
    template_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    if current_user.role not in [UserRole.ADMIN, UserRole.STAFF]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only admin and staff can view quotation templates"},
        )

    template = db.get(QuoteTemplate, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Quotation template not found"},
        )

    return _serialize_template(template)


@router.patch("/{template_id}", response_model=QuoteTemplateResponse)
def update_quote_template(
    template_id: uuid.UUID,
    payload: QuoteTemplateUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only admins can update quotation templates"},
        )

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": "At least one field must be provided for update"},
        )

    template = db.get(QuoteTemplate, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Quotation template not found"},
        )

    if "name" in update_data and update_data["name"] is not None:
        template.name = update_data["name"].strip()

    if "validity_days" in update_data and update_data["validity_days"] is not None:
        template.validity_days = update_data["validity_days"]

    if "plan_id" in update_data and update_data["plan_id"] is not None:
        new_plan = db.get(Plan, update_data["plan_id"])
        if not new_plan or not new_plan.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "BAD_REQUEST", "message": "Plan not found or is inactive"},
            )
        template.plan_id = update_data["plan_id"]

    if "is_active" in update_data and update_data["is_active"] is not None:
        template.is_active = update_data["is_active"]

    if "lines" in update_data and update_data["lines"] is not None:
        _validate_template_lines(db, payload.lines, template.plan_id)
        template.lines.clear()
        for line_in in payload.lines:
            template.lines.append(
                QuoteTemplateLine(
                    product_id=line_in.product_id,
                    quantity=line_in.quantity,
                    selected_variant_ids=[str(v) for v in line_in.selected_variant_ids],
                    tax_rule_ids=[str(t) for t in (line_in.tax_rule_ids or [])],
                )
            )

    db.commit()
    db.refresh(template)
    return _serialize_template(template)


@router.post("/{template_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
def archive_quote_template(
    template_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only admins can archive quotation templates"},
        )

    template = db.get(QuoteTemplate, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Quotation template not found"},
        )

    template.is_active = False
    db.commit()


@router.post("/{template_id}/restore", response_model=QuoteTemplateResponse)
def restore_quote_template(
    template_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Only admins can restore quotation templates"},
        )

    template = db.get(QuoteTemplate, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Quotation template not found"},
        )

    template.is_active = True
    db.commit()
    db.refresh(template)
    return _serialize_template(template)
