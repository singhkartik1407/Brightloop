from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDTimestampMixin


class DiscountType(str, Enum):
    FIXED = "FIXED"
    PERCENTAGE = "PERCENTAGE"


class DiscountScope(str, Enum):
    PRODUCT = "PRODUCT"
    SUBSCRIPTION = "SUBSCRIPTION"


class DiscountRule(UUIDTimestampMixin, Base):
    __tablename__ = "discount_rules"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[object] = mapped_column(Numeric(14, 2), nullable=False)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    minimum_purchase: Mapped[object | None] = mapped_column(Numeric(14, 2), nullable=True)
    minimum_quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    targets: Mapped[list["DiscountTarget"]] = relationship(
        "DiscountTarget",
        back_populates="discount_rule",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_discount_rules_name_nonempty"),
        CheckConstraint(
            "discount_type IN ('FIXED', 'PERCENTAGE')",
            name="ck_discount_rules_discount_type",
        ),
        CheckConstraint(
            "scope IN ('PRODUCT', 'SUBSCRIPTION')",
            name="ck_discount_rules_scope",
        ),
        CheckConstraint("value >= 0", name="ck_discount_rules_value_nonnegative"),
        CheckConstraint(
            "minimum_purchase IS NULL OR minimum_purchase >= 0",
            name="ck_discount_rules_min_purchase_nonnegative",
        ),
        CheckConstraint(
            "minimum_quantity IS NULL OR minimum_quantity >= 1",
            name="ck_discount_rules_min_quantity_positive",
        ),
        CheckConstraint(
            "max_uses IS NULL OR max_uses >= 1",
            name="ck_discount_rules_max_uses_positive",
        ),
        CheckConstraint("used_count >= 0", name="ck_discount_rules_used_count_nonnegative"),
        CheckConstraint("ends_at >= starts_at", name="ck_discount_rules_dates"),
        Index("ix_discount_rules_name", "name"),
        Index("ix_discount_rules_discount_type", "discount_type"),
        Index("ix_discount_rules_scope", "scope"),
        Index("ix_discount_rules_is_active", "is_active"),
    )


class DiscountTarget(Base):
    __tablename__ = "discount_targets"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    discount_rule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("discount_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    discount_rule: Mapped["DiscountRule"] = relationship(
        "DiscountRule", back_populates="targets"
    )
    product: Mapped["Product"] = relationship("Product")

    __table_args__ = (
        UniqueConstraint(
            "discount_rule_id",
            "product_id",
            name="uq_discount_targets_rule_product",
        ),
        Index("ix_discount_targets_rule_id", "discount_rule_id"),
        Index("ix_discount_targets_product_id", "product_id"),
    )
