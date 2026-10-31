"""create_invoices

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-10-31 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, Sequence[str], None] = 'c4d5e6f7a8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. invoices table
    op.create_table(
        "invoices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("invoice_number", sa.String(length=50), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("subscription_id", sa.Uuid(), nullable=True),
        sa.Column("quotation_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="DRAFT", nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("tax_total", sa.Numeric(precision=14, scale=2), server_default="0.00", nullable=False),
        sa.Column("discount_total", sa.Numeric(precision=14, scale=2), server_default="0.00", nullable=False),
        sa.Column("total", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("amount_paid", sa.Numeric(precision=14, scale=2), server_default="0.00", nullable=False),
        sa.Column("amount_due", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("payment_terms", sa.String(length=50), nullable=True),
        sa.Column("billing_reason", sa.String(length=50), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.String(length=500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("subtotal >= 0", name="ck_invoices_subtotal_nonnegative"),
        sa.CheckConstraint("tax_total >= 0", name="ck_invoices_tax_total_nonnegative"),
        sa.CheckConstraint("discount_total >= 0", name="ck_invoices_discount_total_nonnegative"),
        sa.CheckConstraint("total >= 0", name="ck_invoices_total_nonnegative"),
        sa.CheckConstraint("amount_paid >= 0", name="ck_invoices_amount_paid_nonnegative"),
        sa.CheckConstraint("amount_due >= 0", name="ck_invoices_amount_due_nonnegative"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'CONFIRMED', 'PARTIALLY_PAID', 'PAID', 'OVERDUE', 'CANCELLED')",
            name="ck_invoices_status_valid",
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_number"),
    )
    op.create_index("ix_invoices_invoice_number", "invoices", ["invoice_number"], unique=True)
    op.create_index("ix_invoices_customer_id", "invoices", ["customer_id"], unique=False)
    op.create_index("ix_invoices_subscription_id", "invoices", ["subscription_id"], unique=False)
    op.create_index("ix_invoices_quotation_id", "invoices", ["quotation_id"], unique=False)
    op.create_index("ix_invoices_status", "invoices", ["status"], unique=False)
    op.create_index("ix_invoices_due_date", "invoices", ["due_date"], unique=False)

    # 2. invoice_lines table
    op.create_table(
        "invoice_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
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
        sa.CheckConstraint("quantity >= 1", name="ck_invoice_lines_quantity_min"),
        sa.CheckConstraint("unit_price >= 0", name="ck_invoice_lines_unit_price_nonnegative"),
        sa.CheckConstraint("line_subtotal >= 0", name="ck_invoice_lines_line_subtotal_nonnegative"),
        sa.CheckConstraint("tax_amount >= 0", name="ck_invoice_lines_tax_amount_nonnegative"),
        sa.CheckConstraint("discount_amount >= 0", name="ck_invoice_lines_discount_amount_nonnegative"),
        sa.CheckConstraint("line_total >= 0", name="ck_invoice_lines_line_total_nonnegative"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoice_lines_invoice_id", "invoice_lines", ["invoice_id"], unique=False)
    op.create_index("ix_invoice_lines_product_id", "invoice_lines", ["product_id"], unique=False)

    # 3. invoice_counters table
    op.create_table(
        "invoice_counters",
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("next_seq", sa.Integer(), server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("year"),
    )


def downgrade() -> None:
    op.drop_table("invoice_counters")
    op.drop_index("ix_invoice_lines_product_id", table_name="invoice_lines")
    op.drop_index("ix_invoice_lines_invoice_id", table_name="invoice_lines")
    op.drop_table("invoice_lines")
    op.drop_index("ix_invoices_due_date", table_name="invoices")
    op.drop_index("ix_invoices_status", table_name="invoices")
    op.drop_index("ix_invoices_quotation_id", table_name="invoices")
    op.drop_index("ix_invoices_subscription_id", table_name="invoices")
    op.drop_index("ix_invoices_customer_id", table_name="invoices")
    op.drop_index("ix_invoices_invoice_number", table_name="invoices")
    op.drop_table("invoices")
