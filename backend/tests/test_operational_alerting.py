from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import (
    AIAnalysis,
    Alert,
    Asset,
    ConditionAssessment,
    MaintenanceRecord,
    NotificationEvent,
    Sensor,
    SensorReading,
)
from app.schemas.alert import AlertCreate, AlertResolveRequest
from app.services import alert_service, alerting_policy_service, condition_assessment_service


@pytest.fixture
def alerting_fixture(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "ALERTING_ENABLED", True)
    monkeypatch.setattr(settings, "ALERT_ANOMALOUS_ASSESSMENTS_REQUIRED", 2)
    monkeypatch.setattr(settings, "ALERT_COOLDOWN_MINUTES", 60)
    monkeypatch.setattr(settings, "AUTO_AI_ESCALATION_ENABLED", False)
    with SessionLocal() as db:
        asset = Asset(
            name="Phase 12 Temporary Asset",
            asset_code=f"ALERT-{uuid4().hex[:10]}",
            asset_type="test fixture",
            status="active",
        )
        db.add(asset)
        db.commit()
        asset_id = asset.id
        asset_code = asset.asset_code

    yield asset_id, asset_code

    with SessionLocal() as db:
        alert_ids = list(db.scalars(select(Alert.id).where(Alert.asset_id == asset_id)))
        if alert_ids:
            db.execute(delete(NotificationEvent).where(NotificationEvent.alert_id.in_(alert_ids)))
        db.execute(delete(MaintenanceRecord).where(MaintenanceRecord.asset_id == asset_id))
        db.execute(delete(Alert).where(Alert.asset_id == asset_id))
        db.execute(delete(AIAnalysis).where(AIAnalysis.asset_id == asset_id))
        db.execute(delete(ConditionAssessment).where(ConditionAssessment.asset_id == asset_id))
        sensor_ids = list(db.scalars(select(Sensor.id).where(Sensor.asset_id == asset_id)))
        if sensor_ids:
            db.execute(delete(SensorReading).where(SensorReading.sensor_id.in_(sensor_ids)))
            db.execute(delete(Sensor).where(Sensor.id.in_(sensor_ids)))
        db.execute(delete(Asset).where(Asset.id == asset_id))
        db.commit()


def _assessment(db, asset_id, status: str, evaluated_at: datetime) -> ConditionAssessment:
    assessment = ConditionAssessment(
        asset_id=asset_id,
        evaluated_at=evaluated_at,
        evaluated_through=evaluated_at,
        status=status,
        summary=f"Deterministic {status} assessment.",
        findings=[
            {
                "sensor_id": str(uuid4()),
                "sensor_name": "Test vibration",
                "sensor_type": "vibration",
                "unit": "mm/s",
                "latest_value": 8.0,
                "baseline_value": 3.0,
                "deviation_score": 6.0,
                "recent_change": 2.0,
                "trend_direction": "increasing",
                "trend_strength": 4.0,
                "finding_status": status,
                "explanation": "Deterministic test finding.",
            }
        ],
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


def _count(db, model, asset_id) -> int:
    return db.scalar(select(func.count()).select_from(model).where(model.asset_id == asset_id))


def test_normal_watch_and_first_anomaly_do_not_alert(alerting_fixture) -> None:
    asset_id, _ = alerting_fixture
    start = datetime(2026, 2, 1, tzinfo=UTC)
    with SessionLocal() as db:
        for index, status in enumerate(("normal", "watch", "anomalous")):
            assessment = _assessment(db, asset_id, status, start + timedelta(minutes=index))
            assert alerting_policy_service.process_new_assessment(db, assessment) is None
        assert _count(db, Alert, asset_id) == 0


def test_persistent_anomaly_creates_one_traceable_alert(alerting_fixture) -> None:
    asset_id, asset_code = alerting_fixture
    start = datetime(2026, 2, 2, tzinfo=UTC)
    with SessionLocal() as db:
        first = _assessment(db, asset_id, "anomalous", start)
        assert alerting_policy_service.process_new_assessment(db, first) is None
        triggering = _assessment(db, asset_id, "anomalous", start + timedelta(minutes=5))
        alert = alerting_policy_service.process_new_assessment(db, triggering)
        assert alert is not None
        assert alert.source == "condition_monitoring"
        assert alert.condition_assessment_id == triggering.id
        assert alert.severity == "moderate"
        assert asset_code in alert.title

        retried = alerting_policy_service.process_new_assessment(db, triggering)
        assert retried is not None and retried.id == alert.id
        assert _count(db, Alert, asset_id) == 1
        assert db.scalar(
            select(func.count()).select_from(NotificationEvent).where(
                NotificationEvent.alert_id == alert.id
            )
        ) == 1
        assert _count(db, MaintenanceRecord, asset_id) == 0


def test_active_alert_deduplication_and_human_resolution(alerting_fixture) -> None:
    asset_id, _ = alerting_fixture
    start = datetime(2026, 2, 3, tzinfo=UTC)
    with SessionLocal() as db:
        first = _assessment(db, asset_id, "anomalous", start)
        alerting_policy_service.process_new_assessment(db, first)
        second = _assessment(db, asset_id, "anomalous", start + timedelta(minutes=5))
        alert = alerting_policy_service.process_new_assessment(db, second)
        assert alert is not None

        alert = alert_service.acknowledge_alert(db, alert)
        third = _assessment(db, asset_id, "anomalous", start + timedelta(minutes=10))
        assert alerting_policy_service.process_new_assessment(db, third).id == alert.id
        assert _count(db, Alert, asset_id) == 1

        normal = _assessment(db, asset_id, "normal", start + timedelta(minutes=15))
        assert alerting_policy_service.process_new_assessment(db, normal) is None
        assert db.get(Alert, alert.id).status == "acknowledged"

        resolved = alert_service.resolve_alert(db, alert, AlertResolveRequest())
        resolved.resolved_at = start + timedelta(minutes=20)
        db.commit()
        during_cooldown = _assessment(db, asset_id, "anomalous", start + timedelta(minutes=30))
        assert alerting_policy_service.process_new_assessment(db, during_cooldown) is None
        after_cooldown_one = _assessment(db, asset_id, "anomalous", start + timedelta(minutes=85))
        assert alerting_policy_service.process_new_assessment(db, after_cooldown_one) is None
        after_cooldown_two = _assessment(db, asset_id, "anomalous", start + timedelta(minutes=90))
        new_alert = alerting_policy_service.process_new_assessment(db, after_cooldown_two)
        assert new_alert is not None and new_alert.id != alert.id
        assert _count(db, Alert, asset_id) == 2


def test_manual_alerts_are_unaffected(alerting_fixture) -> None:
    asset_id, _ = alerting_fixture
    with SessionLocal() as db:
        manual = alert_service.create_alert(
            db,
            asset_id,
            AlertCreate(title="Manual inspection signal", severity="high"),
        )
        assert manual.source == "manual"
        assert manual.condition_assessment_id is None
        assert manual.ai_escalation_status is None


def test_ai_escalation_disabled_never_invokes_service(
    alerting_fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    asset_id, _ = alerting_fixture
    calls = 0

    def unexpected_ai(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("AI should remain disabled")

    monkeypatch.setattr(
        "app.services.alerting_policy_service.ai_analysis_service.create_ai_analysis",
        unexpected_ai,
    )
    start = datetime(2026, 2, 4, tzinfo=UTC)
    with SessionLocal() as db:
        alerting_policy_service.process_new_assessment(
            db, _assessment(db, asset_id, "anomalous", start)
        )
        alerting_policy_service.process_new_assessment(
            db, _assessment(db, asset_id, "anomalous", start + timedelta(minutes=5))
        )
        assert calls == 0


def test_enabled_ai_runs_once_and_links_analysis(
    alerting_fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    asset_id, _ = alerting_fixture
    monkeypatch.setattr(settings, "AUTO_AI_ESCALATION_ENABLED", True)
    calls = 0

    def fake_ai(db, requested_asset_id, limit_per_sensor):
        nonlocal calls
        calls += 1
        analysis = AIAnalysis(
            asset_id=requested_asset_id,
            summary="Mock explanatory enrichment.",
            anomaly_detected=True,
            findings=[],
            recommended_actions=[],
            model_provider="mock",
            model_name="mock",
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        return analysis

    monkeypatch.setattr(
        "app.services.alerting_policy_service.ai_analysis_service.create_ai_analysis",
        fake_ai,
    )
    start = datetime(2026, 2, 5, tzinfo=UTC)
    with SessionLocal() as db:
        alerting_policy_service.process_new_assessment(
            db, _assessment(db, asset_id, "anomalous", start)
        )
        triggering = _assessment(db, asset_id, "anomalous", start + timedelta(minutes=5))
        alert = alerting_policy_service.process_new_assessment(db, triggering)
        assert alert is not None
        assert alert.ai_analysis_id is not None
        assert alert.ai_escalation_status == "completed"
        alerting_policy_service.process_new_assessment(db, triggering)
        assert calls == 1


def test_ai_failure_does_not_rollback_operational_records(
    alerting_fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    asset_id, _ = alerting_fixture
    monkeypatch.setattr(settings, "AUTO_AI_ESCALATION_ENABLED", True)

    def failed_ai(*_args, **_kwargs):
        raise RuntimeError("mock provider unavailable")

    monkeypatch.setattr(
        "app.services.alerting_policy_service.ai_analysis_service.create_ai_analysis",
        failed_ai,
    )
    start = datetime(2026, 2, 6, tzinfo=UTC)
    with SessionLocal() as db:
        sensor = Sensor(
            asset_id=asset_id,
            name="Persistent test sensor",
            sensor_type="vibration",
            unit="mm/s",
        )
        db.add(sensor)
        db.flush()
        reading = SensorReading(
            sensor_id=sensor.id,
            recorded_at=start,
            value=8.0,
            quality="good",
        )
        db.add(reading)
        db.commit()
        alerting_policy_service.process_new_assessment(
            db, _assessment(db, asset_id, "anomalous", start)
        )
        triggering = _assessment(db, asset_id, "anomalous", start + timedelta(minutes=5))
        alert = alerting_policy_service.process_new_assessment(db, triggering)
        assert alert is not None
        assert db.get(Alert, alert.id).status == "open"
        assert db.get(Alert, alert.id).ai_escalation_status == "failed"
        assert db.get(ConditionAssessment, triggering.id) is not None
        assert db.get(SensorReading, reading.id) is not None
        assert _count(db, MaintenanceRecord, asset_id) == 0


def test_notification_failure_does_not_rollback_alert(
    alerting_fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    asset_id, _ = alerting_fixture

    def failed_notification(*_args, **_kwargs):
        raise RuntimeError("mock notification persistence failure")

    monkeypatch.setattr(
        "app.services.alerting_policy_service.notification_service.record_alert_event",
        failed_notification,
    )
    start = datetime(2026, 2, 7, tzinfo=UTC)
    with SessionLocal() as db:
        alerting_policy_service.process_new_assessment(
            db, _assessment(db, asset_id, "anomalous", start)
        )
        triggering = _assessment(db, asset_id, "anomalous", start + timedelta(minutes=5))
        alert = alerting_policy_service.process_new_assessment(db, triggering)
        assert alert is not None
        assert db.get(Alert, alert.id) is not None
        assert db.get(ConditionAssessment, triggering.id) is not None


def test_alert_policy_failure_does_not_rollback_telemetry_or_assessment(
    alerting_fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    asset_id, _ = alerting_fixture

    def failed_policy(*_args, **_kwargs):
        raise RuntimeError("mock alert policy failure")

    monkeypatch.setattr(
        "app.services.alerting_policy_service.process_new_assessment",
        failed_policy,
    )
    start = datetime(2026, 2, 8, tzinfo=UTC)
    with SessionLocal() as db:
        sensor = Sensor(
            asset_id=asset_id,
            name="Stable test sensor",
            sensor_type="temperature",
            unit="C",
        )
        db.add(sensor)
        db.flush()
        readings = [
            SensorReading(
                sensor_id=sensor.id,
                recorded_at=start + timedelta(minutes=index),
                value=100.0,
                quality="good",
            )
            for index in range(17)
        ]
        db.add_all(readings)
        db.commit()
        assessment = condition_assessment_service.evaluate_asset(db, asset_id)
        assert assessment.status == "normal"
        assert db.get(ConditionAssessment, assessment.id) is not None
        assert db.scalar(
            select(func.count()).select_from(SensorReading).where(
                SensorReading.sensor_id == sensor.id
            )
        ) == 17
