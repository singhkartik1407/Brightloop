from __future__ import annotations

import uuid
from datetime import date
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDTimestampMixin


class BillingInterval(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    YEARLY = "YEARLY"


class Plan(UUIDTimestampMixin, Base):
    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=True,
    )
    price: Mapped[object] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(20), nullable=False)
    interval_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    min_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    available_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    available_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    auto_close_at_end: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    allow_early_close: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    allow_pause: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    allow_renewal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    product: Mapped["Product | None"] = relationship("Product", back_populates="plans")

    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_plans_name_nonempty"),
        CheckConstraint("price >= 0", name="ck_plans_price_nonnegative"),
        CheckConstraint("length(currency) = 3", name="ck_plans_currency_length"),
        CheckConstraint("billing_interval IN ('DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY')", name="ck_plans_billing_interval"),
        CheckConstraint("interval_count >= 1", name="ck_plans_interval_count_positive"),
        CheckConstraint("min_quantity >= 1", name="ck_plans_min_quantity_positive"),
        CheckConstraint(
            "available_until IS NULL OR available_from IS NULL OR available_until >= available_from",
            name="ck_plans_availability_dates",
        ),
        Index("ix_plans_name", "name"),
        Index("ix_plans_product_id", "product_id"),
        Index("ix_plans_billing_interval", "billing_interval"),
        Index("ix_plans_is_active", "is_active"),
    )
