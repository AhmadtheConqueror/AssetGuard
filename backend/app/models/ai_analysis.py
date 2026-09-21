from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    asset_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    risk_score: Mapped[float | None] = mapped_column(Float)
    risk_level: Mapped[str | None] = mapped_column(String(50))
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    anomaly_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    findings: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB)
    recommended_actions: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB)
    model_provider: Mapped[str | None] = mapped_column(String(255))
    model_name: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    asset: Mapped[Asset] = relationship(back_populates="ai_analyses")
    alerts: Mapped[list[Alert]] = relationship(back_populates="ai_analysis")
