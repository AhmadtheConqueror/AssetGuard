from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index(
            "ux_alerts_active_condition_monitoring_asset",
            "asset_id",
            unique=True,
            postgresql_where=text(
                "source = 'condition_monitoring' AND status IN ('open', 'acknowledged')"
            ),
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    asset_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    ai_analysis_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("ai_analyses.id"))
    condition_assessment_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("condition_assessments.id"), unique=True
    )
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="manual", server_default="manual"
    )
    ai_escalation_status: Mapped[str | None] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="open", server_default="open")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    engineer_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    asset: Mapped[Asset] = relationship(back_populates="alerts")
    ai_analysis: Mapped[AIAnalysis | None] = relationship(back_populates="alerts")
    condition_assessment: Mapped[ConditionAssessment | None] = relationship(back_populates="alert")
    notification_events: Mapped[list[NotificationEvent]] = relationship(back_populates="alert")
    maintenance_records: Mapped[list[MaintenanceRecord]] = relationship(back_populates="alert")

    @property
    def condition_assessment_evaluated_at(self) -> datetime | None:
        return self.condition_assessment.evaluated_at if self.condition_assessment else None
