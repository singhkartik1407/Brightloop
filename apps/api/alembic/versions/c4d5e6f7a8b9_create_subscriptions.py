"""create_subscriptions

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-10-31 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4d5e6f7a8b9'
down_revision: Union[str, Sequence[str], None] = 'b3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. subscriptions
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subscription_number", sa.String(length=50), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("quotation_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="DRAFT", nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("next_billing_date", sa.Date(), nullable=False),
        sa.Column("current_period_start", sa.Date(), nullable=False),
        sa.Column("current_period_end", sa.Date(), nullable=False),
        sa.Column("billing_interval", sa.String(length=20), nullable=False),
        sa.Column("interval_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("recurring_subtotal", sa.Numeric(precision=14, scale=2), server_default="0.00", nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("cancel_at_period_end", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("cancellation_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.String(length=500), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pending_plan_id", sa.Uuid(), nullable=True),
        sa.Column("billing_cycle_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("payment_terms", sa.String(length=500), nullable=True),
        sa.Column("snapshot_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("length(trim(subscription_number)) > 0", name="ck_subscriptions_number_nonempty"),
        sa.CheckConstraint("recurring_subtotal >= 0", name="ck_subscriptions_recurring_subtotal_nonnegative"),
        sa.CheckConstraint("interval_count >= 1", name="ck_subscriptions_interval_count_min"),
        sa.CheckConstraint("length(currency) = 3", name="ck_subscriptions_currency_length"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'QUOTATION', 'CONFIRMED', 'ACTIVE', 'PAUSED', 'CLOSED')",
            name="ck_subscriptions_status_valid",
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pending_plan_id"], ["plans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subscription_number", name="uq_subscriptions_number"),
    )
    op.create_index("ix_subscriptions_customer_id", "subscriptions", ["customer_id"])
    op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"])
    op.create_index("ix_subscriptions_quotation_id", "subscriptions", ["quotation_id"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
    op.create_index("ix_subscriptions_next_billing_date", "subscriptions", ["next_billing_date"])
    op.create_index("ix_subscriptions_number", "subscriptions", ["subscription_number"])

    # 2. subscription_lines
    op.create_table(
        "subscription_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subscription_id", sa.Uuid(), nullable=False),
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
        sa.CheckConstraint("quantity >= 1", name="ck_subscription_lines_quantity_min"),
        sa.CheckConstraint("unit_price >= 0", name="ck_subscription_lines_unit_price_nonnegative"),
        sa.CheckConstraint("line_subtotal >= 0", name="ck_subscription_lines_line_subtotal_nonnegative"),
        sa.CheckConstraint("tax_amount >= 0", name="ck_subscription_lines_tax_amount_nonnegative"),
        sa.CheckConstraint("discount_amount >= 0", name="ck_subscription_lines_discount_amount_nonnegative"),
        sa.CheckConstraint("line_total >= 0", name="ck_subscription_lines_line_total_nonnegative"),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscription_lines_subscription_id", "subscription_lines", ["subscription_id"])
    op.create_index("ix_subscription_lines_product_id", "subscription_lines", ["product_id"])

    # 3. subscription_counters
    op.create_table(
        "subscription_counters",
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("next_seq", sa.Integer(), server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("year"),
    )

    # 4. subscription_events
    op.create_table(
        "subscription_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subscription_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("actor_role", sa.String(length=20), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("event_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscription_events_subscription_id", "subscription_events", ["subscription_id"])
    op.create_index("ix_subscription_events_event_type", "subscription_events", ["event_type"])

    # 5. pending_billing_adjustments
    op.create_table(
        "pending_billing_adjustments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subscription_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("adjustment_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("is_billed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount >= 0", name="ck_pending_billing_adjustments_amount_nonnegative"),
        sa.CheckConstraint("length(currency) = 3", name="ck_pending_billing_adjustments_currency_length"),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pending_billing_adjustments_subscription_id", "pending_billing_adjustments", ["subscription_id"])
    op.create_index("ix_pending_billing_adjustments_is_billed", "pending_billing_adjustments", ["is_billed"])

    # 6. subscription_renewal_records
    op.create_table(
        "subscription_renewal_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subscription_id", sa.Uuid(), nullable=False),
        sa.Column("cycle_number", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="PROCESSED", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("cycle_number >= 1", name="ck_subscription_renewals_cycle_min"),
        sa.CheckConstraint("amount >= 0", name="ck_subscription_renewals_amount_nonnegative"),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("subscription_id", "period_start", "period_end", name="uq_subscription_renewals_cycle"),
    )
    op.create_index("ix_subscription_renewals_sub_id", "subscription_renewal_records", ["subscription_id"])


def downgrade() -> None:
    op.drop_table("subscription_renewal_records")
    op.drop_table("pending_billing_adjustments")
    op.drop_table("subscription_events")
    op.drop_table("subscription_counters")
    op.drop_table("subscription_lines")
    op.drop_table("subscriptions")
