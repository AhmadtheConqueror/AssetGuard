from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.notification_event import NotificationEvent


AUTOMATIC_ALERT_CREATED = "automatic_alert_created"


def record_alert_event(
    db: Session,
    alert_id: UUID,
    event_type: str = AUTOMATIC_ALERT_CREATED,
) -> NotificationEvent:
    existing = db.scalar(
        select(NotificationEvent).where(
            NotificationEvent.alert_id == alert_id,
            NotificationEvent.event_type == event_type,
        )
    )
    if existing is not None:
        return existing

    event = NotificationEvent(
        alert_id=alert_id,
        event_type=event_type,
        delivery_status="pending",
    )
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(NotificationEvent).where(
                NotificationEvent.alert_id == alert_id,
                NotificationEvent.event_type == event_type,
            )
        )
        if existing is None:
            raise
        return existing
    db.refresh(event)
    return event
