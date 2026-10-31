"""create_quotations

Revision ID: a2b3c4d5e6f7
Revises: f1a23b4c5d6e
Create Date: 2026-10-31 09:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = 'f1a23b4c5d6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quotations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("quotation_number", sa.String(length=50), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=True),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="DRAFT", nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payment_terms", sa.String(length=500), nullable=True),
        sa.Column("subtotal", sa.Numeric(precision=14, scale=2), server_default="0.00", nullable=False),
        sa.Column("tax_total", sa.Numeric(precision=14, scale=2), server_default="0.00", nullable=False),
        sa.Column("discount_total", sa.Numeric(precision=14, scale=2), server_default="0.00", nullable=False),
        sa.Column("total", sa.Numeric(precision=14, scale=2), server_default="0.00", nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("subscription_id", sa.Uuid(), nullable=True),
        sa.Column("discount_rule_id", sa.Uuid(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snapshot_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("length(trim(quotation_number)) > 0", name="ck_quotations_number_nonempty"),
        sa.CheckConstraint("subtotal >= 0", name="ck_quotations_subtotal_nonnegative"),
        sa.CheckConstraint("tax_total >= 0", name="ck_quotations_tax_total_nonnegative"),
        sa.CheckConstraint("discount_total >= 0", name="ck_quotations_discount_total_nonnegative"),
        sa.CheckConstraint("total >= 0", name="ck_quotations_total_nonnegative"),
        sa.CheckConstraint("length(currency) = 3", name="ck_quotations_currency_length"),
        sa.CheckConstraint("status IN ('DRAFT', 'QUOTATION', 'CONFIRMED', 'REJECTED', 'EXPIRED')", name="ck_quotations_status_valid"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["template_id"], ["quote_templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["discount_rule_id"], ["discount_rules.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("quotation_number", name="uq_quotations_number"),
    )
    op.create_index("ix_quotations_customer_id", "quotations", ["customer_id"])
    op.create_index("ix_quotations_plan_id", "quotations", ["plan_id"])
    op.create_index("ix_quotations_status", "quotations", ["status"])
    op.create_index("ix_quotations_expires_at", "quotations", ["expires_at"])
    op.create_index("ix_quotations_number", "quotations", ["quotation_number"])

    op.create_table(
        "quotation_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("quotation_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("selected_variants", sa.JSON(), nullable=False),
        sa.Column("taxes_data", sa.JSON(), nullable=False),
        sa.Column("line_subtotal", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(precision=14, scale=2), server_default="0.00", nullable=False),
        sa.Column("discount_amount", sa.Numeric(precision=14, scale=2), server_default="0.00", nullable=False),
        sa.Column("line_total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("quantity >= 1", name="ck_quotation_lines_quantity_min"),
        sa.CheckConstraint("unit_price >= 0", name="ck_quotation_lines_unit_price_nonnegative"),
        sa.CheckConstraint("line_subtotal >= 0", name="ck_quotation_lines_line_subtotal_nonnegative"),
        sa.CheckConstraint("tax_amount >= 0", name="ck_quotation_lines_tax_amount_nonnegative"),
        sa.CheckConstraint("discount_amount >= 0", name="ck_quotation_lines_discount_amount_nonnegative"),
        sa.CheckConstraint("line_total >= 0", name="ck_quotation_lines_line_total_nonnegative"),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quotation_lines_quotation_id", "quotation_lines", ["quotation_id"])
    op.create_index("ix_quotation_lines_product_id", "quotation_lines", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_quotation_lines_product_id", table_name="quotation_lines")
    op.drop_index("ix_quotation_lines_quotation_id", table_name="quotation_lines")
    op.drop_table("quotation_lines")

    op.drop_index("ix_quotations_number", table_name="quotations")
    op.drop_index("ix_quotations_expires_at", table_name="quotations")
    op.drop_index("ix_quotations_status", table_name="quotations")
    op.drop_index("ix_quotations_plan_id", table_name="quotations")
    op.drop_index("ix_quotations_customer_id", table_name="quotations")
    op.drop_table("quotations")
