"""add operational alerting traceability

Revision ID: a1b2c3d4e5f6
Revises: f9c8d7e6b5a4
Create Date: 2026-09-23 00:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f9c8d7e6b5a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "alerts",
        sa.Column("condition_assessment_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "alerts",
        sa.Column("source", sa.String(length=50), server_default="manual", nullable=False),
    )
    op.add_column(
        "alerts",
        sa.Column("ai_escalation_status", sa.String(length=50), nullable=True),
    )
    op.create_foreign_key(
        "fk_alerts_condition_assessment_id",
        "alerts",
        "condition_assessments",
        ["condition_assessment_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_alerts_condition_assessment_id",
        "alerts",
        ["condition_assessment_id"],
    )
    op.create_index(
        "ux_alerts_active_condition_monitoring_asset",
        "alerts",
        ["asset_id"],
        unique=True,
        postgresql_where=sa.text(
            "source = 'condition_monitoring' AND status IN ('open', 'acknowledged')"
        ),
    )
    op.create_table(
        "notification_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("alert_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("delivery_status", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alert_id", "event_type", name="uq_notification_events_alert_type"),
    )


def downgrade() -> None:
    op.drop_table("notification_events")
    op.drop_index("ux_alerts_active_condition_monitoring_asset", table_name="alerts")
    op.drop_constraint("uq_alerts_condition_assessment_id", "alerts", type_="unique")
    op.drop_constraint("fk_alerts_condition_assessment_id", "alerts", type_="foreignkey")
    op.drop_column("alerts", "ai_escalation_status")
    op.drop_column("alerts", "source")
    op.drop_column("alerts", "condition_assessment_id")
