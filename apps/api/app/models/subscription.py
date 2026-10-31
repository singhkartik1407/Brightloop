from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDTimestampMixin


class SubscriptionStatus(str, Enum):
    DRAFT = "DRAFT"
    QUOTATION = "QUOTATION"
    CONFIRMED = "CONFIRMED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"


class Subscription(UUIDTimestampMixin, Base):
    __tablename__ = "subscriptions"

    subscription_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quotation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("quotations.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SubscriptionStatus.DRAFT.value,
        server_default=SubscriptionStatus.DRAFT.value,
    )

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    next_billing_date: Mapped[date] = mapped_column(Date, nullable=False)
    current_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    current_period_end: Mapped[date] = mapped_column(Date, nullable=False)

    billing_interval: Mapped[str] = mapped_column(String(20), nullable=False)
    interval_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    recurring_subtotal: Mapped[object] = mapped_column(
        Numeric(14, 2), nullable=False, default=0.00, server_default="0.00"
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    cancellation_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pending_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("plans.id", ondelete="SET NULL"),
        nullable=True,
    )
    billing_cycle_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    payment_terms: Mapped[str | None] = mapped_column(String(500), nullable=True)

    snapshot_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    customer: Mapped["Customer"] = relationship("Customer")
    plan: Mapped["Plan"] = relationship("Plan", foreign_keys=[plan_id])
    pending_plan: Mapped["Plan | None"] = relationship("Plan", foreign_keys=[pending_plan_id])
    quotation: Mapped["Quotation | None"] = relationship("Quotation", foreign_keys=[quotation_id])

    lines: Mapped[list["SubscriptionLine"]] = relationship(
        "SubscriptionLine",
        back_populates="subscription",
        cascade="all, delete-orphan",
        order_by="SubscriptionLine.created_at",
    )
    events: Mapped[list["SubscriptionEvent"]] = relationship(
        "SubscriptionEvent",
        back_populates="subscription",
        cascade="all, delete-orphan",
        order_by="SubscriptionEvent.created_at.desc()",
    )
    billing_adjustments: Mapped[list["PendingBillingAdjustment"]] = relationship(
        "PendingBillingAdjustment",
        back_populates="subscription",
        cascade="all, delete-orphan",
    )
    renewal_records: Mapped[list["SubscriptionRenewalRecord"]] = relationship(
        "SubscriptionRenewalRecord",
        back_populates="subscription",
        cascade="all, delete-orphan",
        order_by="SubscriptionRenewalRecord.cycle_number.desc()",
    )

    __table_args__ = (
        CheckConstraint("length(trim(subscription_number)) > 0", name="ck_subscriptions_number_nonempty"),
        CheckConstraint("recurring_subtotal >= 0", name="ck_subscriptions_recurring_subtotal_nonnegative"),
        CheckConstraint("interval_count >= 1", name="ck_subscriptions_interval_count_min"),
        CheckConstraint("length(currency) = 3", name="ck_subscriptions_currency_length"),
        CheckConstraint(
            "status IN ('DRAFT', 'QUOTATION', 'CONFIRMED', 'ACTIVE', 'PAUSED', 'CLOSED')",
            name="ck_subscriptions_status_valid",
        ),
        Index("ix_subscriptions_customer_id", "customer_id"),
        Index("ix_subscriptions_plan_id", "plan_id"),
        Index("ix_subscriptions_quotation_id", "quotation_id"),
        Index("ix_subscriptions_status", "status"),
        Index("ix_subscriptions_next_billing_date", "next_billing_date"),
        Index("ix_subscriptions_number", "subscription_number"),
    )


class SubscriptionLine(UUIDTimestampMixin, Base):
    __tablename__ = "subscription_lines"

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=True,
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    unit_price: Mapped[object] = mapped_column(Numeric(14, 2), nullable=False)
    selected_variants: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    taxes_data: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    line_subtotal: Mapped[object] = mapped_column(Numeric(14, 2), nullable=False)
    tax_amount: Mapped[object] = mapped_column(
        Numeric(14, 2), nullable=False, default=0.00, server_default="0.00"
    )
    discount_amount: Mapped[object] = mapped_column(
        Numeric(14, 2), nullable=False, default=0.00, server_default="0.00"
    )
    line_total: Mapped[object] = mapped_column(Numeric(14, 2), nullable=False)

    subscription: Mapped[Subscription] = relationship("Subscription", back_populates="lines")
    product: Mapped["Product | None"] = relationship("Product")

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_subscription_lines_quantity_min"),
        CheckConstraint("unit_price >= 0", name="ck_subscription_lines_unit_price_nonnegative"),
        CheckConstraint("line_subtotal >= 0", name="ck_subscription_lines_line_subtotal_nonnegative"),
        CheckConstraint("tax_amount >= 0", name="ck_subscription_lines_tax_amount_nonnegative"),
        CheckConstraint("discount_amount >= 0", name="ck_subscription_lines_discount_amount_nonnegative"),
        CheckConstraint("line_total >= 0", name="ck_subscription_lines_line_total_nonnegative"),
        Index("ix_subscription_lines_subscription_id", "subscription_id"),
        Index("ix_subscription_lines_product_id", "product_id"),
    )


class SubscriptionCounter(Base):
    __tablename__ = "subscription_counters"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    next_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class SubscriptionEvent(UUIDTimestampMixin, Base):
    __tablename__ = "subscription_events"

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    event_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    subscription: Mapped[Subscription] = relationship("Subscription", back_populates="events")
    actor: Mapped["User | None"] = relationship("User")

    __table_args__ = (
        Index("ix_subscription_events_subscription_id", "subscription_id"),
        Index("ix_subscription_events_event_type", "event_type"),
    )


class PendingBillingAdjustment(UUIDTimestampMixin, Base):
    __tablename__ = "pending_billing_adjustments"

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount: Mapped[object] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    adjustment_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    is_billed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)

    subscription: Mapped[Subscription] = relationship("Subscription", back_populates="billing_adjustments")

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_pending_billing_adjustments_amount_nonnegative"),
        CheckConstraint("length(currency) = 3", name="ck_pending_billing_adjustments_currency_length"),
        Index("ix_pending_billing_adjustments_subscription_id", "subscription_id"),
        Index("ix_pending_billing_adjustments_is_billed", "is_billed"),
    )


class SubscriptionRenewalRecord(UUIDTimestampMixin, Base):
    __tablename__ = "subscription_renewal_records"

    subscription_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=False,
    )
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[object] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PROCESSED", server_default="PROCESSED")

    subscription: Mapped[Subscription] = relationship("Subscription", back_populates="renewal_records")

    __table_args__ = (
        UniqueConstraint("subscription_id", "period_start", "period_end", name="uq_subscription_renewals_cycle"),
        CheckConstraint("cycle_number >= 1", name="ck_subscription_renewals_cycle_min"),
        CheckConstraint("amount >= 0", name="ck_subscription_renewals_amount_nonnegative"),
        Index("ix_subscription_renewals_sub_id", "subscription_id"),
    )
