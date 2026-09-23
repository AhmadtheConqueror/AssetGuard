"""add condition assessments

Revision ID: f9c8d7e6b5a4
Revises: e8b7c6d5a4f3
Create Date: 2026-09-23 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f9c8d7e6b5a4"
down_revision: Union[str, Sequence[str], None] = "e8b7c6d5a4f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "condition_assessments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("asset_id", sa.UUID(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluated_through", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("findings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ux_condition_assessments_asset_evaluated_through",
        "condition_assessments",
        ["asset_id", "evaluated_through"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ux_condition_assessments_asset_evaluated_through",
        table_name="condition_assessments",
    )
    op.drop_table("condition_assessments")
