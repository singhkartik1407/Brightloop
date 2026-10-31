"""add normalized product variant index

Revision ID: e83d4b2a1f09
Revises: c5a12f9d8e70
Create Date: 2026-10-31 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e83d4b2a1f09"
down_revision: Union[str, Sequence[str], None] = "c5a12f9d8e70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_product_variant_configuration_normalized",
        "product_variants",
        ["product_id", sa.text("lower(attribute_name)"), sa.text("lower(attribute_value)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_product_variant_configuration_normalized", table_name="product_variants")
