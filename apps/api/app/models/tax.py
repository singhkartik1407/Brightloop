from __future__ import annotations

from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDTimestampMixin


class TaxType(str, Enum):
    GENERIC = "GENERIC"
    CGST = "CGST"
    SGST = "SGST"
    IGST = "IGST"
    OTHER = "OTHER"


class TaxRule(UUIDTimestampMixin, Base):
    __tablename__ = "tax_rules"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    tax_type: Mapped[str] = mapped_column(String(20), nullable=False)
    rate_percent: Mapped[object] = mapped_column(Numeric(6, 4), nullable=False)
    jurisdiction: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_inclusive: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_tax_rules_name_nonempty"),
        CheckConstraint("length(trim(code)) > 0", name="ck_tax_rules_code_nonempty"),
        CheckConstraint(
            "tax_type IN ('GENERIC', 'CGST', 'SGST', 'IGST', 'OTHER')",
            name="ck_tax_rules_tax_type",
        ),
        CheckConstraint(
            "rate_percent >= 0 AND rate_percent <= 100",
            name="ck_tax_rules_rate_percent_range",
        ),
        Index("ix_tax_rules_name", "name"),
        Index("ix_tax_rules_code", "code"),
        Index("ix_tax_rules_tax_type", "tax_type"),
        Index("ix_tax_rules_is_active", "is_active"),
        Index(
            "uq_tax_rules_code_normalized",
            func.lower(func.trim(code)),
            unique=True,
        ),
    )
