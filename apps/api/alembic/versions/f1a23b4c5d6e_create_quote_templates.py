"""create_quote_templates

Revision ID: f1a23b4c5d6e
Revises: e5e13bfe8061
Create Date: 2026-10-31 09:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a23b4c5d6e'
down_revision: Union[str, Sequence[str], None] = 'e5e13bfe8061'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "quote_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("validity_days", sa.Integer(), server_default="30", nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_quote_templates_name_nonempty"),
        sa.CheckConstraint("validity_days >= 1", name="ck_quote_templates_validity_days_min"),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quote_templates_name", "quote_templates", ["name"])
    op.create_index("ix_quote_templates_plan_id", "quote_templates", ["plan_id"])
    op.create_index("ix_quote_templates_is_active", "quote_templates", ["is_active"])

    op.create_table(
        "quote_template_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("selected_variant_ids", sa.JSON(), nullable=False),
        sa.Column("tax_rule_ids", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("quantity >= 1", name="ck_quote_template_lines_quantity_min"),
        sa.ForeignKeyConstraint(["template_id"], ["quote_templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quote_template_lines_template_id", "quote_template_lines", ["template_id"])
    op.create_index("ix_quote_template_lines_product_id", "quote_template_lines", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_quote_template_lines_product_id", table_name="quote_template_lines")
    op.drop_index("ix_quote_template_lines_template_id", table_name="quote_template_lines")
    op.drop_table("quote_template_lines")

    op.drop_index("ix_quote_templates_is_active", table_name="quote_templates")
    op.drop_index("ix_quote_templates_plan_id", table_name="quote_templates")
    op.drop_index("ix_quote_templates_name", table_name="quote_templates")
    op.drop_table("quote_templates")
