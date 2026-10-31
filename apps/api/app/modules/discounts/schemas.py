from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from app.models.discount import DiscountScope, DiscountType


MONEY_QUANTUM = Decimal("0.01")
MAX_MONEY = Decimal("999999999999.99")


def clean_text(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{label} cannot be empty.")
    return value


def parse_decimal_value(value: object, label: str = "Discount value") -> Decimal:
    if isinstance(value, str):
        val_str = value.strip()
        try:
            amount = Decimal(val_str)
        except (InvalidOperation, ValueError):
            raise ValueError(f"{label} must be a valid decimal value.")
    elif isinstance(value, (int, float, Decimal)):
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise ValueError(f"{label} must be a valid decimal value.")
    else:
        raise ValueError(f"{label} must be a valid decimal value or decimal string.")

    if not amount.is_finite() or amount < 0:
        raise ValueError(f"{label} must be non-negative.")
    if amount.as_tuple().exponent < -2:
        raise ValueError(f"{label} may have at most two decimal places.")
    return amount.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


class DiscountRuleFields(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True)

    name: str | None = Field(default=None, min_length=1, max_length=160)
    code: str | None = Field(default=None, max_length=50)
    discount_type: DiscountType | None = Field(default=None, validation_alias="discountType", serialization_alias="discountType")
    value: Decimal | None = Field(default=None, validation_alias="value", serialization_alias="value")
    scope: DiscountScope | None = Field(default=None, validation_alias="scope", serialization_alias="scope")
    product_ids: list[uuid.UUID] | None = Field(default=None, validation_alias="productIds", serialization_alias="productIds")
    minimum_purchase: Decimal | None = Field(default=None, validation_alias="minimumPurchase", serialization_alias="minimumPurchase")
    minimum_quantity: int | None = Field(default=None, ge=1, validation_alias="minimumQuantity", serialization_alias="minimumQuantity")
    starts_at: datetime | None = Field(default=None, validation_alias="startsAt", serialization_alias="startsAt")
    ends_at: datetime | None = Field(default=None, validation_alias="endsAt", serialization_alias="endsAt")
    max_uses: int | None = Field(default=None, ge=1, validation_alias="maxUses", serialization_alias="maxUses")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        return clean_text(value, "Discount name") if value is not None else value

    @field_validator("code")
    @classmethod
    def clean_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().upper()
        return cleaned or None

    @field_validator("value", mode="before")
    @classmethod
    def validate_value(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        return parse_decimal_value(value, "Discount value")

    @field_validator("minimum_purchase", mode="before")
    @classmethod
    def validate_min_purchase(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        return parse_decimal_value(value, "Minimum purchase")

    @model_validator(mode="after")
    def validate_dates_and_type(self):
        if self.starts_at is not None and self.ends_at is not None:
            starts = self.starts_at if self.starts_at.tzinfo else self.starts_at.replace(tzinfo=timezone.utc)
            ends = self.ends_at if self.ends_at.tzinfo else self.ends_at.replace(tzinfo=timezone.utc)
            if ends < starts:
                raise ValueError("Discount end date cannot precede start date.")
        if self.discount_type == DiscountType.PERCENTAGE and self.value is not None:
            if self.value > 100:
                raise ValueError("Percentage discount value cannot exceed 100.00.")
        return self


class DiscountRuleCreateRequest(DiscountRuleFields):
    name: str = Field(min_length=1, max_length=160)
    discount_type: DiscountType = Field(validation_alias="discountType", serialization_alias="discountType")
    value: Decimal = Field(validation_alias="value", serialization_alias="value")
    scope: DiscountScope = Field(validation_alias="scope", serialization_alias="scope")
    starts_at: datetime = Field(validation_alias="startsAt", serialization_alias="startsAt")
    ends_at: datetime = Field(validation_alias="endsAt", serialization_alias="endsAt")
    is_active: bool = Field(default=True, validation_alias="isActive", serialization_alias="isActive")


class DiscountRuleUpdateRequest(DiscountRuleFields):
    is_active: bool | None = Field(default=None, validation_alias="isActive", serialization_alias="isActive")


class DiscountRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=True)

    id: uuid.UUID
    name: str
    code: str | None
    discount_type: DiscountType = Field(serialization_alias="discountType")
    value: Decimal = Field(serialization_alias="value")
    scope: DiscountScope = Field(serialization_alias="scope")
    product_ids: list[uuid.UUID] = Field(default_factory=list, serialization_alias="productIds")
    minimum_purchase: Decimal | None = Field(default=None, serialization_alias="minimumPurchase")
    minimum_quantity: int | None = Field(default=None, serialization_alias="minimumQuantity")
    starts_at: datetime = Field(serialization_alias="startsAt")
    ends_at: datetime = Field(serialization_alias="endsAt")
    max_uses: int | None = Field(default=None, serialization_alias="maxUses")
    used_count: int = Field(default=0, serialization_alias="usedCount")
    is_active: bool = Field(serialization_alias="isActive")
    created_at: datetime = Field(serialization_alias="createdAt")

    @field_serializer("value")
    def serialize_value(self, value: Decimal) -> str:
        return f"{value:.2f}"

    @field_serializer("minimum_purchase")
    def serialize_min_purchase(self, value: Decimal | None) -> str | None:
        return f"{value:.2f}" if value is not None else None


class DiscountRuleListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    items: list[DiscountRuleRead]
    total: int
    page: int
    page_size: int = Field(serialization_alias="pageSize")
