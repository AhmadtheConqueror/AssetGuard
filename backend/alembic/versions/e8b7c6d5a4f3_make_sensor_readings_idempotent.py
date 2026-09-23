"""make sensor readings idempotent

Revision ID: e8b7c6d5a4f3
Revises: c4a8f1d2e6b9
Create Date: 2026-09-23 00:00:00
"""
from typing import Sequence, Union

from alembic import op


revision: str = "e8b7c6d5a4f3"
down_revision: Union[str, Sequence[str], None] = "c4a8f1d2e6b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_sensor_readings_sensor_id_recorded_at", table_name="sensor_readings")
    op.create_index(
        "ix_sensor_readings_sensor_id_recorded_at",
        "sensor_readings",
        ["sensor_id", "recorded_at"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_sensor_readings_sensor_id_recorded_at", table_name="sensor_readings")
    op.create_index(
        "ix_sensor_readings_sensor_id_recorded_at",
        "sensor_readings",
        ["sensor_id", "recorded_at"],
        unique=False,
    )
