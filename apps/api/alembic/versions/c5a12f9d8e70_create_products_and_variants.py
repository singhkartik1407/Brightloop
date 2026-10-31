"""create products and variants

Revision ID: c5a12f9d8e70
Revises: b84387474971
Create Date: 2026-10-31 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c5a12f9d8e70"
down_revision: Union[str, Sequence[str], None] = "b84387474971"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("sales_price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("cost_price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_products_name_nonempty"),
        sa.CheckConstraint("type IN ('SOFTWARE', 'SERVICE', 'PHYSICAL', 'OTHER')", name="ck_products_type"),
        sa.CheckConstraint("sales_price >= 0", name="ck_products_sales_price_nonnegative"),
        sa.CheckConstraint("cost_price >= 0", name="ck_products_cost_price_nonnegative"),
        sa.CheckConstraint("length(currency) = 3", name="ck_products_currency_length"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_products_name", "products", ["name"], unique=False)
    op.create_table(
        "product_variants",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("attribute_name", sa.String(length=80), nullable=False),
        sa.Column("attribute_value", sa.String(length=120), nullable=False),
        sa.Column("price_adjustment", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("length(trim(attribute_name)) > 0", name="ck_product_variants_attribute_name_nonempty"),
        sa.CheckConstraint("length(trim(attribute_value)) > 0", name="ck_product_variants_attribute_value_nonempty"),
        sa.CheckConstraint("price_adjustment >= 0", name="ck_product_variants_price_adjustment_nonnegative"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "attribute_name", "attribute_value", name="uq_product_variant_configuration"),
    )
    op.create_index("ix_product_variants_product_id", "product_variants", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_product_variants_product_id", table_name="product_variants")
    op.drop_table("product_variants")
    op.drop_index("ix_products_name", table_name="products")
    op.drop_table("products")
