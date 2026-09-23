from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class NotificationEvent(Base):
    __tablename__ = "notification_events"
    __table_args__ = (
        UniqueConstraint("alert_id", "event_type", name="uq_notification_events_alert_type"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    alert_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("alerts.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    delivery_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", server_default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    alert: Mapped[Alert] = relationship(back_populates="notification_events")
