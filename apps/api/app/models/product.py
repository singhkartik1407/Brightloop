from __future__ import annotations

import uuid
from enum import Enum

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDTimestampMixin


class ProductType(str, Enum):
    SOFTWARE = "SOFTWARE"
    SERVICE = "SERVICE"
    PHYSICAL = "PHYSICAL"
    OTHER = "OTHER"


class Product(UUIDTimestampMixin, Base):
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    sales_price: Mapped[object] = mapped_column(Numeric(14, 2), nullable=False)
    cost_price: Mapped[object] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    variants: Mapped[list["ProductVariant"]] = relationship(
        "ProductVariant", back_populates="product", cascade="save-update, merge"
    )

    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_products_name_nonempty"),
        CheckConstraint("type IN ('SOFTWARE', 'SERVICE', 'PHYSICAL', 'OTHER')", name="ck_products_type"),
        CheckConstraint("sales_price >= 0", name="ck_products_sales_price_nonnegative"),
        CheckConstraint("cost_price >= 0", name="ck_products_cost_price_nonnegative"),
        CheckConstraint("length(currency) = 3", name="ck_products_currency_length"),
        Index("ix_products_name", "name"),
    )


class ProductVariant(UUIDTimestampMixin, Base):
    __tablename__ = "product_variants"

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    attribute_name: Mapped[str] = mapped_column(String(80), nullable=False)
    attribute_value: Mapped[str] = mapped_column(String(120), nullable=False)
    price_adjustment: Mapped[object] = mapped_column(Numeric(14, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    product: Mapped[Product] = relationship("Product", back_populates="variants")

    __table_args__ = (
        CheckConstraint("length(trim(attribute_name)) > 0", name="ck_product_variants_attribute_name_nonempty"),
        CheckConstraint("length(trim(attribute_value)) > 0", name="ck_product_variants_attribute_value_nonempty"),
        CheckConstraint("price_adjustment >= 0", name="ck_product_variants_price_adjustment_nonnegative"),
        UniqueConstraint("product_id", "attribute_name", "attribute_value", name="uq_product_variant_configuration"),
        Index("ix_product_variants_product_id", "product_id"),
    )


Index(
    "uq_product_variant_configuration_normalized",
    ProductVariant.product_id,
    func.lower(ProductVariant.attribute_name),
    func.lower(ProductVariant.attribute_value),
    unique=True,
)
