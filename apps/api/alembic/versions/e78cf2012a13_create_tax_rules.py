"""create_tax_rules

Revision ID: e78cf2012a13
Revises: d08aa9752356
Create Date: 2026-10-31 09:17:55.829041

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e78cf2012a13'
down_revision: Union[str, Sequence[str], None] = 'd08aa9752356'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tax_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("tax_type", sa.String(length=20), nullable=False),
        sa.Column("rate_percent", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("jurisdiction", sa.String(length=120), nullable=True),
        sa.Column("is_inclusive", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_tax_rules_name_nonempty"),
        sa.CheckConstraint("length(trim(code)) > 0", name="ck_tax_rules_code_nonempty"),
        sa.CheckConstraint(
            "tax_type IN ('GENERIC', 'CGST', 'SGST', 'IGST', 'OTHER')",
            name="ck_tax_rules_tax_type",
        ),
        sa.CheckConstraint(
            "rate_percent >= 0 AND rate_percent <= 100",
            name="ck_tax_rules_rate_percent_range",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tax_rules_name", "tax_rules", ["name"], unique=False)
    op.create_index("ix_tax_rules_code", "tax_rules", ["code"], unique=False)
    op.create_index("ix_tax_rules_tax_type", "tax_rules", ["tax_type"], unique=False)
    op.create_index("ix_tax_rules_is_active", "tax_rules", ["is_active"], unique=False)
    op.create_index(
        "uq_tax_rules_code_normalized",
        "tax_rules",
        [sa.text("lower(trim(code))")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_tax_rules_code_normalized", table_name="tax_rules")
    op.drop_index("ix_tax_rules_is_active", table_name="tax_rules")
    op.drop_index("ix_tax_rules_tax_type", table_name="tax_rules")
    op.drop_index("ix_tax_rules_code", table_name="tax_rules")
    op.drop_index("ix_tax_rules_name", table_name="tax_rules")
    op.drop_table("tax_rules")
