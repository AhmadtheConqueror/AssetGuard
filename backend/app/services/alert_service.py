from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_analysis import AIAnalysis
from app.models.alert import Alert
from app.models.asset import Asset
from app.models.condition_assessment import ConditionAssessment
from app.schemas.alert import AlertCreate, AlertResolveRequest, AlertSeverity, AlertStatus, AlertUpdate


class AssetNotFoundError(Exception):
    pass


class AIAnalysisNotFoundError(Exception):
    pass


class AIAnalysisAssetConflictError(Exception):
    pass


class InvalidAlertTransitionError(Exception):
    pass


def create_alert(db: Session, asset_id: UUID, alert_data: AlertCreate) -> Alert:
    if db.get(Asset, asset_id) is None:
        raise AssetNotFoundError

    if alert_data.ai_analysis_id is not None:
        analysis = db.get(AIAnalysis, alert_data.ai_analysis_id)
        if analysis is None:
            raise AIAnalysisNotFoundError
        if analysis.asset_id != asset_id:
            raise AIAnalysisAssetConflictError

    values = alert_data.model_dump(exclude={"detected_at"})
    alert = Alert(
        asset_id=asset_id,
        detected_at=alert_data.detected_at or datetime.now(UTC),
        status="open",
        **values,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def create_condition_monitoring_alert(
    db: Session,
    assessment: ConditionAssessment,
) -> Alert:
    asset = db.get(Asset, assessment.asset_id)
    if asset is None:
        raise AssetNotFoundError

    notable_findings = [
        finding.get("sensor_name", "Sensor")
        for finding in assessment.findings
        if finding.get("finding_status") == "anomalous"
    ]
    sensor_context = ", ".join(notable_findings) if notable_findings else "asset telemetry"
    alert = Alert(
        asset_id=asset.id,
        condition_assessment_id=assessment.id,
        source="condition_monitoring",
        title=f"Statistical condition anomaly detected - {asset.asset_code}",
        description=(
            f"{assessment.summary} Anomalous statistical findings: {sensor_context}. "
            "This signal is based on recent historical behaviour, not an OEM safety limit."
        ),
        severity="moderate",
        status="open",
        detected_at=assessment.evaluated_at,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def get_alert_by_id(db: Session, alert_id: UUID) -> Alert | None:
    return db.get(Alert, alert_id)


def list_alerts_for_asset(
    db: Session,
    asset_id: UUID,
    skip: int = 0,
    limit: int = 100,
    alert_status: AlertStatus | None = None,
    severity: AlertSeverity | None = None,
) -> list[Alert]:
    if db.get(Asset, asset_id) is None:
        raise AssetNotFoundError

    statement = select(Alert).where(Alert.asset_id == asset_id)
    if alert_status is not None:
        statement = statement.where(Alert.status == alert_status)
    if severity is not None:
        statement = statement.where(Alert.severity == severity)
    statement = statement.order_by(Alert.detected_at.desc(), Alert.id.desc()).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def update_alert(db: Session, alert: Alert, alert_data: AlertUpdate) -> Alert:
    for field_name, value in alert_data.model_dump(exclude_unset=True).items():
        setattr(alert, field_name, value)
    db.commit()
    db.refresh(alert)
    return alert


def acknowledge_alert(db: Session, alert: Alert) -> Alert:
    if alert.status == "resolved":
        raise InvalidAlertTransitionError("A resolved Alert cannot be acknowledged")
    if alert.status == "acknowledged":
        return alert

    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(UTC)
    db.commit()
    db.refresh(alert)
    return alert


def resolve_alert(db: Session, alert: Alert, resolve_data: AlertResolveRequest) -> Alert:
    if alert.status == "resolved":
        return alert

    alert.status = "resolved"
    alert.resolved_at = datetime.now(UTC)
    if "engineer_notes" in resolve_data.model_fields_set:
        alert.engineer_notes = resolve_data.engineer_notes
    db.commit()
    db.refresh(alert)
    return alert
