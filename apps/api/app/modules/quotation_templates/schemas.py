from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class SubscriptionLineInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    product_id: uuid.UUID = Field(
        validation_alias="productId", serialization_alias="productId"
    )
    quantity: int = Field(ge=1, default=1)
    selected_variant_ids: list[uuid.UUID] = Field(
        default_factory=list,
        validation_alias="selectedVariantIds",
        serialization_alias="selectedVariantIds",
    )
    tax_rule_ids: list[uuid.UUID] | None = Field(
        default=None,
        validation_alias="taxRuleIds",
        serialization_alias="taxRuleIds",
    )


class QuoteTemplateCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    validity_days: int = Field(
        ge=1, default=30, validation_alias="validityDays", serialization_alias="validityDays"
    )
    plan_id: uuid.UUID = Field(
        validation_alias="planId", serialization_alias="planId"
    )
    lines: list[SubscriptionLineInput] = Field(min_length=1)


class QuoteTemplateUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=160)
    validity_days: int | None = Field(
        default=None, ge=1, validation_alias="validityDays", serialization_alias="validityDays"
    )
    plan_id: uuid.UUID | None = Field(
        default=None, validation_alias="planId", serialization_alias="planId"
    )
    lines: list[SubscriptionLineInput] | None = Field(default=None, min_length=1)
    is_active: bool | None = Field(
        default=None, validation_alias="isActive", serialization_alias="isActive"
    )


class QuoteTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    name: str
    validity_days: int = Field(
        validation_alias="validity_days", serialization_alias="validityDays"
    )
    plan_id: uuid.UUID = Field(
        validation_alias="plan_id", serialization_alias="planId"
    )
    lines: list[SubscriptionLineInput]
    is_active: bool = Field(
        validation_alias="is_active", serialization_alias="isActive"
    )
    created_at: datetime = Field(
        validation_alias="created_at", serialization_alias="createdAt"
    )
