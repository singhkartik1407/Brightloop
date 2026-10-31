"""create_plans

Revision ID: d08aa9752356
Revises: e83d4b2a1f09
Create Date: 2026-10-31 08:53:03.169695

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd08aa9752356'
down_revision: Union[str, Sequence[str], None] = 'e83d4b2a1f09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("billing_interval", sa.String(length=20), nullable=False),
        sa.Column("interval_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("min_quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("available_from", sa.Date(), nullable=True),
        sa.Column("available_until", sa.Date(), nullable=True),
        sa.Column("auto_close_at_end", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("allow_early_close", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("allow_pause", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("allow_renewal", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_plans_name_nonempty"),
        sa.CheckConstraint("price >= 0", name="ck_plans_price_nonnegative"),
        sa.CheckConstraint("length(currency) = 3", name="ck_plans_currency_length"),
        sa.CheckConstraint(
            "billing_interval IN ('DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY')",
            name="ck_plans_billing_interval",
        ),
        sa.CheckConstraint("interval_count >= 1", name="ck_plans_interval_count_positive"),
        sa.CheckConstraint("min_quantity >= 1", name="ck_plans_min_quantity_positive"),
        sa.CheckConstraint(
            "available_until IS NULL OR available_from IS NULL OR available_until >= available_from",
            name="ck_plans_availability_dates",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_plans_name", "plans", ["name"], unique=False)
    op.create_index("ix_plans_product_id", "plans", ["product_id"], unique=False)
    op.create_index("ix_plans_billing_interval", "plans", ["billing_interval"], unique=False)
    op.create_index("ix_plans_is_active", "plans", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_plans_is_active", table_name="plans")
    op.drop_index("ix_plans_billing_interval", table_name="plans")
    op.drop_index("ix_plans_product_id", table_name="plans")
    op.drop_index("ix_plans_name", table_name="plans")
    op.drop_table("plans")
