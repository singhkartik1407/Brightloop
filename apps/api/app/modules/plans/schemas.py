from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from app.models.plan import BillingInterval


MONEY_QUANTUM = Decimal("0.01")
MAX_MONEY = Decimal("999999999999.99")


def clean_text(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{label} cannot be empty.")
    return value


def parse_money(value: object, label: str) -> Decimal:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a decimal string.")
    try:
        amount = Decimal(value.strip())
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label} must be a valid decimal value.")
    if not amount.is_finite() or amount < 0 or amount > MAX_MONEY:
        raise ValueError(f"{label} must be between 0.00 and {MAX_MONEY}.")
    if amount.as_tuple().exponent < -2:
        raise ValueError(f"{label} may have at most two decimal places.")
    return amount.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


class PlanFields(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True)

    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    product_id: uuid.UUID | None = Field(default=None, validation_alias="productId", serialization_alias="productId")
    price: Decimal | None = Field(default=None, validation_alias="price", serialization_alias="price")
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    billing_interval: BillingInterval | None = Field(default=None, validation_alias="billingInterval", serialization_alias="billingInterval")
    interval_count: int | None = Field(default=None, ge=1, validation_alias="intervalCount", serialization_alias="intervalCount")
    min_quantity: int | None = Field(default=None, ge=1, validation_alias="minQuantity", serialization_alias="minQuantity")
    available_from: date | None = Field(default=None, validation_alias="availableFrom", serialization_alias="availableFrom")
    available_until: date | None = Field(default=None, validation_alias="availableUntil", serialization_alias="availableUntil")
    auto_close_at_end: bool | None = Field(default=None, validation_alias="autoCloseAtEnd", serialization_alias="autoCloseAtEnd")
    allow_early_close: bool | None = Field(default=None, validation_alias="allowEarlyClose", serialization_alias="allowEarlyClose")
    allow_pause: bool | None = Field(default=None, validation_alias="allowPause", serialization_alias="allowPause")
    allow_renewal: bool | None = Field(default=None, validation_alias="allowRenewal", serialization_alias="allowRenewal")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        return clean_text(value, "Plan name") if value is not None else value

    @field_validator("price", mode="before")
    @classmethod
    def validate_price(cls, value: object, info) -> Decimal | None:
        if value is None:
            raise ValueError(f"{info.field_name.replace('_', ' ').capitalize()} cannot be null.")
        return parse_money(value, "Price")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise ValueError("Currency must be a three-letter code.")
        return value

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @model_validator(mode="after")
    def validate_date_range(self):
        if self.available_from is not None and self.available_until is not None:
            if self.available_until < self.available_from:
                raise ValueError("Plan availability end date cannot precede start date.")
        return self


class PlanCreateRequest(PlanFields):
    name: str = Field(min_length=1, max_length=160)
    price: Decimal = Field(validation_alias="price", serialization_alias="price")
    currency: str = Field(min_length=3, max_length=3)
    billing_interval: BillingInterval = Field(validation_alias="billingInterval", serialization_alias="billingInterval")
    interval_count: int = Field(default=1, ge=1, validation_alias="intervalCount", serialization_alias="intervalCount")
    min_quantity: int = Field(default=1, ge=1, validation_alias="minQuantity", serialization_alias="minQuantity")
    auto_close_at_end: bool = Field(default=False, validation_alias="autoCloseAtEnd", serialization_alias="autoCloseAtEnd")
    allow_early_close: bool = Field(default=False, validation_alias="allowEarlyClose", serialization_alias="allowEarlyClose")
    allow_pause: bool = Field(default=False, validation_alias="allowPause", serialization_alias="allowPause")
    allow_renewal: bool = Field(default=True, validation_alias="allowRenewal", serialization_alias="allowRenewal")


class PlanUpdateRequest(PlanFields):
    is_active: bool | None = Field(default=None, validation_alias="isActive", serialization_alias="isActive")


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=True)

    id: uuid.UUID
    name: str
    description: str | None
    product_id: uuid.UUID | None = Field(default=None, serialization_alias="productId")
    price: Decimal = Field(serialization_alias="price")
    currency: str
    billing_interval: BillingInterval = Field(serialization_alias="billingInterval")
    interval_count: int = Field(serialization_alias="intervalCount")
    min_quantity: int = Field(serialization_alias="minQuantity")
    available_from: date | None = Field(default=None, serialization_alias="availableFrom")
    available_until: date | None = Field(default=None, serialization_alias="availableUntil")
    auto_close_at_end: bool = Field(serialization_alias="autoCloseAtEnd")
    allow_early_close: bool = Field(serialization_alias="allowEarlyClose")
    allow_pause: bool = Field(serialization_alias="allowPause")
    allow_renewal: bool = Field(serialization_alias="allowRenewal")
    is_active: bool = Field(serialization_alias="isActive")
    created_at: datetime = Field(serialization_alias="createdAt")

    @field_serializer("price")
    def serialize_price(self, value: Decimal) -> str:
        return f"{value:.2f}"


class PlanListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    items: list[PlanRead]
    total: int
    page: int
    page_size: int = Field(serialization_alias="pageSize")
