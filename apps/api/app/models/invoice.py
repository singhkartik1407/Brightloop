from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any

from sqlalchemy import (
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


class InvoiceStatus(str, Enum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class Invoice(UUIDTimestampMixin, Base):
    __tablename__ = "invoices"

    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    quotation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("quotations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=InvoiceStatus.DRAFT.value,
        server_default=InvoiceStatus.DRAFT.value,
        index=True,
    )
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    subtotal: Mapped[object] = mapped_column(Numeric(14, 2), nullable=False)
    tax_total: Mapped[object] = mapped_column(
        Numeric(14, 2), nullable=False, default=0.00, server_default="0.00"
    )
    discount_total: Mapped[object] = mapped_column(
        Numeric(14, 2), nullable=False, default=0.00, server_default="0.00"
    )
    total: Mapped[object] = mapped_column(Numeric(14, 2), nullable=False)
    amount_paid: Mapped[object] = mapped_column(
        Numeric(14, 2), nullable=False, default=0.00, server_default="0.00"
    )
    amount_due: Mapped[object] = mapped_column(Numeric(14, 2), nullable=False)

    payment_terms: Mapped[str | None] = mapped_column(String(50), nullable=True)
    billing_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    customer: Mapped["Customer"] = relationship("Customer")
    subscription: Mapped["Subscription | None"] = relationship("Subscription")
    quotation: Mapped["Quotation | None"] = relationship("Quotation")
    lines: Mapped[list["InvoiceLineItem"]] = relationship(
        "InvoiceLineItem",
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceLineItem.created_at",
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="invoice",
        order_by="Payment.paid_at",
    )

    __table_args__ = (
        CheckConstraint("subtotal >= 0", name="ck_invoices_subtotal_nonnegative"),
        CheckConstraint("tax_total >= 0", name="ck_invoices_tax_total_nonnegative"),
        CheckConstraint("discount_total >= 0", name="ck_invoices_discount_total_nonnegative"),
        CheckConstraint("total >= 0", name="ck_invoices_total_nonnegative"),
        CheckConstraint("amount_paid >= 0", name="ck_invoices_amount_paid_nonnegative"),
        CheckConstraint("amount_due >= 0", name="ck_invoices_amount_due_nonnegative"),
    )


class InvoiceLineItem(UUIDTimestampMixin, Base):
    __tablename__ = "invoice_lines"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    unit_price: Mapped[object] = mapped_column(Numeric(14, 2), nullable=False)
    selected_variants: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    taxes_data: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    line_subtotal: Mapped[object] = mapped_column(Numeric(14, 2), nullable=False)
    tax_amount: Mapped[object] = mapped_column(
        Numeric(14, 2), nullable=False, default=0.00, server_default="0.00"
    )
    discount_amount: Mapped[object] = mapped_column(
        Numeric(14, 2), nullable=False, default=0.00, server_default="0.00"
    )
    line_total: Mapped[object] = mapped_column(Numeric(14, 2), nullable=False)

    invoice: Mapped[Invoice] = relationship("Invoice", back_populates="lines")
    product: Mapped["Product | None"] = relationship("Product")

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_invoice_lines_quantity_min"),
        CheckConstraint("unit_price >= 0", name="ck_invoice_lines_unit_price_nonnegative"),
        CheckConstraint("line_subtotal >= 0", name="ck_invoice_lines_line_subtotal_nonnegative"),
        CheckConstraint("tax_amount >= 0", name="ck_invoice_lines_tax_amount_nonnegative"),
        CheckConstraint("discount_amount >= 0", name="ck_invoice_lines_discount_amount_nonnegative"),
        CheckConstraint("line_total >= 0", name="ck_invoice_lines_line_total_nonnegative"),
    )


class InvoiceCounter(Base):
    __tablename__ = "invoice_counters"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    next_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
