from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.tax import TaxType


RATE_QUANTUM_4 = Decimal("0.0001")


def clean_text(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{label} cannot be empty.")
    return value


def parse_rate(value: object, label: str = "Rate percent") -> Decimal:
    if not isinstance(value, (str, int, float, Decimal)):
        raise ValueError(f"{label} must be a valid number or string.")
    if isinstance(value, str):
        val_str = value.strip()
        try:
            amount = Decimal(val_str)
        except (InvalidOperation, ValueError):
            raise ValueError(f"{label} must be a valid decimal value.")
    else:
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise ValueError(f"{label} must be a valid decimal value.")
    if not amount.is_finite() or amount < 0 or amount > 100:
        raise ValueError(f"{label} must be between 0.00 and 100.00.")
    if amount.as_tuple().exponent < -4:
        raise ValueError(f"{label} may have at most four decimal places.")
    return amount


class TaxRuleFields(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    code: str | None = Field(default=None, min_length=1, max_length=40)
    tax_type: TaxType | None = Field(default=None, validation_alias="taxType", serialization_alias="taxType")
    rate_percent: Decimal | None = Field(default=None, validation_alias="ratePercent", serialization_alias="ratePercent")
    jurisdiction: str | None = Field(default=None, max_length=120)
    is_inclusive: bool | None = Field(default=None, validation_alias="isInclusive", serialization_alias="isInclusive")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        return clean_text(value, "Tax rule name") if value is not None else value

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None) -> str | None:
        if value is not None:
            cleaned = clean_text(value, "Tax rule code").upper()
            return cleaned
        return value

    @field_validator("rate_percent", mode="before")
    @classmethod
    def validate_rate(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        return parse_rate(value, "Rate percent")

    @field_validator("jurisdiction")
    @classmethod
    def clean_jurisdiction(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class TaxRuleCreateRequest(TaxRuleFields):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=40)
    tax_type: TaxType = Field(validation_alias="taxType", serialization_alias="taxType")
    rate_percent: Decimal = Field(validation_alias="ratePercent", serialization_alias="ratePercent")
    is_inclusive: bool = Field(default=False, validation_alias="isInclusive", serialization_alias="isInclusive")
    is_active: bool = Field(default=True, validation_alias="isActive", serialization_alias="isActive")


class TaxRuleUpdateRequest(TaxRuleFields):
    is_active: bool | None = Field(default=None, validation_alias="isActive", serialization_alias="isActive")


class TaxRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=True)

    id: uuid.UUID
    name: str
    code: str
    tax_type: TaxType = Field(serialization_alias="taxType")
    rate_percent: Decimal = Field(serialization_alias="ratePercent")
    jurisdiction: str | None
    is_inclusive: bool = Field(serialization_alias="isInclusive")
    is_active: bool = Field(serialization_alias="isActive")
    created_at: datetime = Field(serialization_alias="createdAt")

    @field_serializer("rate_percent")
    def serialize_rate(self, value: Decimal) -> str:
        try:
            two_dec = value.quantize(Decimal("0.01"))
            if value == two_dec:
                return f"{two_dec:.2f}"
        except InvalidOperation:
            pass
        normalized = value.normalize()
        return f"{normalized:.2f}" if normalized.as_tuple().exponent >= -2 else f"{normalized}"


class TaxRuleListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    items: list[TaxRuleRead]
    total: int
    page: int
    page_size: int = Field(serialization_alias="pageSize")
