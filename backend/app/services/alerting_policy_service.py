import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.alert import Alert
from app.models.condition_assessment import ConditionAssessment
from app.services import ai_analysis_service, alert_service, notification_service


logger = logging.getLogger(__name__)


def _active_automatic_alert(db: Session, asset_id) -> Alert | None:
    return db.scalar(
        select(Alert)
        .where(
            Alert.asset_id == asset_id,
            Alert.source == "condition_monitoring",
            Alert.status.in_(("open", "acknowledged")),
        )
        .order_by(Alert.detected_at.desc(), Alert.id.desc())
        .limit(1)
    )


def _latest_resolved_automatic_alert(db: Session, asset_id) -> Alert | None:
    return db.scalar(
        select(Alert)
        .where(
            Alert.asset_id == asset_id,
            Alert.source == "condition_monitoring",
            Alert.status == "resolved",
        )
        .order_by(Alert.resolved_at.desc(), Alert.id.desc())
        .limit(1)
    )


def _has_required_persistence(
    db: Session,
    assessment: ConditionAssessment,
    since=None,
) -> bool:
    required = max(settings.ALERT_ANOMALOUS_ASSESSMENTS_REQUIRED, 1)
    statement = (
        select(ConditionAssessment.status)
        .where(
            ConditionAssessment.asset_id == assessment.asset_id,
            ConditionAssessment.evaluated_at <= assessment.evaluated_at,
        )
        .order_by(ConditionAssessment.evaluated_at.desc(), ConditionAssessment.id.desc())
        .limit(required)
    )
    if since is not None:
        statement = statement.where(ConditionAssessment.evaluated_at > since)
    statuses = list(db.scalars(statement).all())
    return len(statuses) == required and all(status == "anomalous" for status in statuses)


def _enrich_alert_with_ai(db: Session, alert: Alert) -> None:
    if not settings.AUTO_AI_ESCALATION_ENABLED:
        return
    if alert.ai_analysis_id is not None or alert.ai_escalation_status is not None:
        return

    alert.ai_escalation_status = "pending"
    db.commit()
    try:
        analysis = ai_analysis_service.create_ai_analysis(db, alert.asset_id, limit_per_sensor=50)
        current_alert = db.get(Alert, alert.id)
        if current_alert is None:
            return
        current_alert.ai_analysis_id = analysis.id
        current_alert.ai_escalation_status = "completed"
        db.commit()
    except Exception:
        db.rollback()
        current_alert = db.get(Alert, alert.id)
        if current_alert is not None:
            current_alert.ai_escalation_status = "failed"
            db.commit()
        logger.exception("Automatic AI enrichment failed for alert %s", alert.id)


def process_new_assessment(
    db: Session,
    assessment: ConditionAssessment,
) -> Alert | None:
    if not settings.ALERTING_ENABLED or assessment.status != "anomalous":
        return None

    active = _active_automatic_alert(db, assessment.asset_id)
    if active is not None:
        return active

    resolved = _latest_resolved_automatic_alert(db, assessment.asset_id)
    if resolved is not None and resolved.resolved_at is not None:
        cooldown_end = resolved.resolved_at + timedelta(minutes=settings.ALERT_COOLDOWN_MINUTES)
        if assessment.evaluated_at < cooldown_end:
            return None
        persistence_since = cooldown_end
    else:
        persistence_since = None

    if not _has_required_persistence(db, assessment, since=persistence_since):
        return None

    existing = db.scalar(
        select(Alert).where(Alert.condition_assessment_id == assessment.id)
    )
    if existing is not None:
        return existing

    try:
        alert = alert_service.create_condition_monitoring_alert(db, assessment)
    except IntegrityError:
        db.rollback()
        alert = db.scalar(
            select(Alert)
            .where(
                Alert.asset_id == assessment.asset_id,
                Alert.source == "condition_monitoring",
                Alert.status.in_(("open", "acknowledged")),
            )
            .order_by(Alert.detected_at.desc(), Alert.id.desc())
            .limit(1)
        )
        if alert is None:
            raise

    try:
        notification_service.record_alert_event(db, alert.id)
    except Exception:
        db.rollback()
        logger.exception("Notification event creation failed for alert %s", alert.id)

    _enrich_alert_with_ai(db, alert)
    return db.get(Alert, alert.id)
