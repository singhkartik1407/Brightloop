from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDTimestampMixin


class QuoteTemplate(UUIDTimestampMixin, Base):
    __tablename__ = "quote_templates"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    validity_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=30, server_default="30"
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    plan: Mapped["Plan"] = relationship("Plan")
    lines: Mapped[list["QuoteTemplateLine"]] = relationship(
        "QuoteTemplateLine",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="QuoteTemplateLine.created_at",
    )

    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_quote_templates_name_nonempty"),
        CheckConstraint("validity_days >= 1", name="ck_quote_templates_validity_days_min"),
        Index("ix_quote_templates_name", "name"),
        Index("ix_quote_templates_plan_id", "plan_id"),
        Index("ix_quote_templates_is_active", "is_active"),
    )


class QuoteTemplateLine(UUIDTimestampMixin, Base):
    __tablename__ = "quote_template_lines"

    template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("quote_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    selected_variant_ids: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )
    tax_rule_ids: Mapped[list[Any]] = mapped_column(
        JSON, nullable=False, default=list
    )

    template: Mapped[QuoteTemplate] = relationship("QuoteTemplate", back_populates="lines")
    product: Mapped["Product"] = relationship("Product")

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_quote_template_lines_quantity_min"),
        Index("ix_quote_template_lines_template_id", "template_id"),
        Index("ix_quote_template_lines_product_id", "product_id"),
    )
