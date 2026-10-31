"""create_discount_rules

Revision ID: e5e13bfe8061
Revises: e78cf2012a13
Create Date: 2026-10-31 09:18:10.244467

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5e13bfe8061'
down_revision: Union[str, Sequence[str], None] = 'e78cf2012a13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "discount_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("discount_type", sa.String(length=20), nullable=False),
        sa.Column("value", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("minimum_purchase", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("minimum_quantity", sa.Integer(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_discount_rules_name_nonempty"),
        sa.CheckConstraint(
            "discount_type IN ('FIXED', 'PERCENTAGE')",
            name="ck_discount_rules_discount_type",
        ),
        sa.CheckConstraint(
            "scope IN ('PRODUCT', 'SUBSCRIPTION')",
            name="ck_discount_rules_scope",
        ),
        sa.CheckConstraint("value >= 0", name="ck_discount_rules_value_nonnegative"),
        sa.CheckConstraint(
            "minimum_purchase IS NULL OR minimum_purchase >= 0",
            name="ck_discount_rules_min_purchase_nonnegative",
        ),
        sa.CheckConstraint(
            "minimum_quantity IS NULL OR minimum_quantity >= 1",
            name="ck_discount_rules_min_quantity_positive",
        ),
        sa.CheckConstraint(
            "max_uses IS NULL OR max_uses >= 1",
            name="ck_discount_rules_max_uses_positive",
        ),
        sa.CheckConstraint("used_count >= 0", name="ck_discount_rules_used_count_nonnegative"),
        sa.CheckConstraint("ends_at >= starts_at", name="ck_discount_rules_dates"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_discount_rules_name", "discount_rules", ["name"], unique=False)
    op.create_index("ix_discount_rules_discount_type", "discount_rules", ["discount_type"], unique=False)
    op.create_index("ix_discount_rules_scope", "discount_rules", ["scope"], unique=False)
    op.create_index("ix_discount_rules_is_active", "discount_rules", ["is_active"], unique=False)

    op.create_table(
        "discount_targets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("discount_rule_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["discount_rule_id"], ["discount_rules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("discount_rule_id", "product_id", name="uq_discount_targets_rule_product"),
    )
    op.create_index("ix_discount_targets_rule_id", "discount_targets", ["discount_rule_id"], unique=False)
    op.create_index("ix_discount_targets_product_id", "discount_targets", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_discount_targets_product_id", table_name="discount_targets")
    op.drop_index("ix_discount_targets_rule_id", table_name="discount_targets")
    op.drop_table("discount_targets")
    op.drop_index("ix_discount_rules_is_active", table_name="discount_rules")
    op.drop_index("ix_discount_rules_scope", table_name="discount_rules")
    op.drop_index("ix_discount_rules_discount_type", table_name="discount_rules")
    op.drop_index("ix_discount_rules_name", table_name="discount_rules")
    op.drop_table("discount_rules")
