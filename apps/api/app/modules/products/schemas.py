import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.product import ProductType


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


class ProductVariantInput(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True)

    attribute_name: str = Field(min_length=1, max_length=80, validation_alias="attributeName", serialization_alias="attributeName")
    attribute_value: str = Field(min_length=1, max_length=120, validation_alias="attributeValue", serialization_alias="attributeValue")
    price_adjustment: Decimal = Field(validation_alias="priceAdjustment", serialization_alias="priceAdjustment")

    @field_validator("attribute_name", "attribute_value")
    @classmethod
    def validate_variant_text(cls, value: str) -> str:
        return clean_text(value, "Variant attribute")

    @field_validator("price_adjustment", mode="before")
    @classmethod
    def validate_price_adjustment(cls, value: object) -> Decimal:
        return parse_money(value, "Price adjustment")


class ProductFields(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True)

    name: str | None = Field(default=None, min_length=1, max_length=160)
    type: ProductType | None = None
    sales_price: Decimal | None = Field(default=None, validation_alias="salesPrice", serialization_alias="salesPrice")
    cost_price: Decimal | None = Field(default=None, validation_alias="costPrice", serialization_alias="costPrice")
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    notes: str | None = Field(default=None, max_length=2000)
    variants: list[ProductVariantInput] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        return clean_text(value, "Product name") if value is not None else value

    @field_validator("sales_price", "cost_price", mode="before")
    @classmethod
    def validate_prices(cls, value: object, info) -> Decimal | None:
        if value is None:
            raise ValueError(f"{info.field_name.replace('_', ' ').capitalize()} cannot be null.")
        return parse_money(value, info.field_name.replace("_", " ").capitalize())

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise ValueError("Currency must be a three-letter code.")
        return value

    @field_validator("notes")
    @classmethod
    def clean_notes(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @model_validator(mode="after")
    def reject_duplicate_variants(self):
        if self.variants is None:
            return self
        seen: set[tuple[str, str]] = set()
        for variant in self.variants:
            key = (variant.attribute_name.casefold(), variant.attribute_value.casefold())
            if key in seen:
                raise ValueError("Duplicate variant attribute/value configuration.")
            seen.add(key)
        return self


class ProductCreateRequest(ProductFields):
    name: str = Field(min_length=1, max_length=160)
    type: ProductType
    sales_price: Decimal = Field(validation_alias="salesPrice", serialization_alias="salesPrice")
    cost_price: Decimal = Field(validation_alias="costPrice", serialization_alias="costPrice")
    currency: str = Field(min_length=3, max_length=3)


class ProductUpdateRequest(ProductFields):
    is_active: bool | None = Field(default=None, validation_alias="isActive", serialization_alias="isActive")


class ProductVariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=True)

    id: uuid.UUID
    attribute_name: str = Field(serialization_alias="attributeName")
    attribute_value: str = Field(serialization_alias="attributeValue")
    price_adjustment: Decimal = Field(serialization_alias="priceAdjustment")
    is_active: bool = Field(serialization_alias="isActive")


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=True)

    id: uuid.UUID
    name: str
    type: ProductType
    sales_price: Decimal = Field(serialization_alias="salesPrice")
    cost_price: Decimal | None = Field(serialization_alias="costPrice")
    currency: str
    notes: str | None
    variants: list[ProductVariantRead]
    is_active: bool = Field(serialization_alias="isActive")
    created_at: datetime = Field(serialization_alias="createdAt")


class ProductListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    items: list[ProductRead]
    total: int
    page: int
    page_size: int = Field(serialization_alias="pageSize")
