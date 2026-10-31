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
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDTimestampMixin


class QuotationStatus(str, Enum):
    DRAFT = "DRAFT"
    QUOTATION = "QUOTATION"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class Quotation(UUIDTimestampMixin, Base):
    __tablename__ = "quotations"

    quotation_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("quote_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=QuotationStatus.DRAFT.value,
        server_default=QuotationStatus.DRAFT.value,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payment_terms: Mapped[str | None] = mapped_column(String(500), nullable=True)

    subtotal: Mapped[object] = mapped_column(
        Numeric(14, 2), nullable=False, default=0.00, server_default="0.00"
    )
    tax_total: Mapped[object] = mapped_column(
        Numeric(14, 2), nullable=False, default=0.00, server_default="0.00"
    )
    discount_total: Mapped[object] = mapped_column(
        Numeric(14, 2), nullable=False, default=0.00, server_default="0.00"
    )
    total: Mapped[object] = mapped_column(
        Numeric(14, 2), nullable=False, default=0.00, server_default="0.00"
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    discount_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("discount_rules.id", ondelete="SET NULL"),
        nullable=True,
    )

    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Historical snapshots: customer name/code, plan details, template, applied discount
    snapshot_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    customer: Mapped["Customer"] = relationship("Customer")
    plan: Mapped["Plan"] = relationship("Plan")
    template: Mapped["QuoteTemplate | None"] = relationship("QuoteTemplate")
    discount_rule: Mapped["DiscountRule | None"] = relationship("DiscountRule")
    lines: Mapped[list["QuotationLine"]] = relationship(
        "QuotationLine",
        back_populates="quotation",
        cascade="all, delete-orphan",
        order_by="QuotationLine.created_at",
    )

    __table_args__ = (
        CheckConstraint("length(trim(quotation_number)) > 0", name="ck_quotations_number_nonempty"),
        CheckConstraint("subtotal >= 0", name="ck_quotations_subtotal_nonnegative"),
        CheckConstraint("tax_total >= 0", name="ck_quotations_tax_total_nonnegative"),
        CheckConstraint("discount_total >= 0", name="ck_quotations_discount_total_nonnegative"),
        CheckConstraint("total >= 0", name="ck_quotations_total_nonnegative"),
        CheckConstraint("length(currency) = 3", name="ck_quotations_currency_length"),
        CheckConstraint(
            "status IN ('DRAFT', 'QUOTATION', 'CONFIRMED', 'REJECTED', 'EXPIRED')",
            name="ck_quotations_status_valid",
        ),
        Index("ix_quotations_customer_id", "customer_id"),
        Index("ix_quotations_plan_id", "plan_id"),
        Index("ix_quotations_status", "status"),
        Index("ix_quotations_expires_at", "expires_at"),
        Index("ix_quotations_number", "quotation_number"),
    )


class QuotationLine(UUIDTimestampMixin, Base):
    __tablename__ = "quotation_lines"

    quotation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("quotations.id", ondelete="CASCADE"),
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

    quotation: Mapped[Quotation] = relationship("Quotation", back_populates="lines")
    product: Mapped["Product | None"] = relationship("Product")

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_quotation_lines_quantity_min"),
        CheckConstraint("unit_price >= 0", name="ck_quotation_lines_unit_price_nonnegative"),
        CheckConstraint("line_subtotal >= 0", name="ck_quotation_lines_line_subtotal_nonnegative"),
        CheckConstraint("tax_amount >= 0", name="ck_quotation_lines_tax_amount_nonnegative"),
        CheckConstraint("discount_amount >= 0", name="ck_quotation_lines_discount_amount_nonnegative"),
        CheckConstraint("line_total >= 0", name="ck_quotation_lines_line_total_nonnegative"),
        Index("ix_quotation_lines_quotation_id", "quotation_id"),
        Index("ix_quotation_lines_product_id", "product_id"),
    )


class QuotationCounter(Base):
    __tablename__ = "quotation_counters"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    next_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

