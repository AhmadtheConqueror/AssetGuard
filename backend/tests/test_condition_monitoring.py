from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models import AIAnalysis, Alert, Asset, ConditionAssessment, Sensor, SensorReading, User
from app.schemas.user import UserCreate
from app.services import condition_assessment_service, user_service


client = TestClient(app)


def _sensor(sensor_type: str = "temperature") -> Sensor:
    return Sensor(
        id=uuid4(),
        asset_id=uuid4(),
        name=f"Test {sensor_type}",
        sensor_type=sensor_type,
        unit="units",
    )


def test_insufficient_and_stable_telemetry() -> None:
    sensor = _sensor()
    insufficient = condition_assessment_service.evaluate_sensor_values(sensor, [100.0] * 16)
    assert insufficient.finding_status == "insufficient_data"

    stable_values = [99.8, 100.0, 100.2] * 4 + [99.9, 100.1, 100.0, 99.9, 100.1]
    stable = condition_assessment_service.evaluate_sensor_values(sensor, stable_values)
    assert stable.finding_status == "normal"
    assert stable.trend_direction == "stable"


def test_watch_and_anomalous_sustained_changes() -> None:
    sensor = _sensor()
    baseline = [99.5, 100.0, 100.5] * 4
    watch = condition_assessment_service.evaluate_sensor_values(
        sensor, baseline + [102.5, 102.7, 102.9, 103.1, 103.3]
    )
    anomalous = condition_assessment_service.evaluate_sensor_values(
        sensor, baseline + [109.0, 109.5, 110.0, 110.5, 111.0]
    )
    assert watch.finding_status == "watch"
    assert anomalous.finding_status == "anomalous"


def test_increasing_decreasing_and_zero_mad_fallback() -> None:
    increasing = condition_assessment_service.evaluate_sensor_values(
        _sensor("temperature"), [99.5, 100.0, 100.5] * 4 + [101, 102, 103, 104, 105]
    )
    decreasing = condition_assessment_service.evaluate_sensor_values(
        _sensor("flow"), [99.5, 100.0, 100.5] * 4 + [99, 98, 97, 96, 95]
    )
    zero_mad = condition_assessment_service.evaluate_sensor_values(_sensor(), [100.0] * 17)
    near_zero_mad = condition_assessment_service.evaluate_sensor_values(
        _sensor(), [0.0] * 12 + [0.000004] * 5
    )
    assert increasing.trend_direction == "increasing"
    assert decreasing.trend_direction == "decreasing"
    assert zero_mad.finding_status == "normal"
    assert near_zero_mad.finding_status == "watch"
    assert near_zero_mad.deviation_score == pytest.approx(4.0)


@pytest.fixture
def monitoring_fixture():
    marker = uuid4().hex
    password = f"Strong-{token_urlsafe(18)}"
    with SessionLocal() as db:
        asset = Asset(
            name="Phase 11 Temporary Asset",
            asset_code=f"MON-{marker[:10]}",
            asset_type="test fixture",
            status="active",
        )
        db.add(asset)
        db.flush()
        sensors = [
            Sensor(asset_id=asset.id, name="Stable temperature", sensor_type="temperature", unit="C"),
            Sensor(asset_id=asset.id, name="Changing flow", sensor_type="flow", unit="m3/h"),
        ]
        db.add_all(sensors)
        db.flush()
        start = datetime(2026, 1, 1, tzinfo=UTC)
        stable_values = [99.8, 100.0, 100.2] * 4 + [100.0] * 5
        changing_values = [99.5, 100.0, 100.5] * 4 + [109, 109.5, 110, 110.5, 111]
        for sensor, values in zip(sensors, (stable_values, changing_values), strict=True):
            db.add_all(
                SensorReading(
                    sensor_id=sensor.id,
                    recorded_at=start + timedelta(minutes=index),
                    value=value,
                    quality="good",
                )
                for index, value in enumerate(values)
            )
        users = {
            role: user_service.create_user(
                db,
                UserCreate(
                    email=f"phase11-{role}-{marker}@example.test",
                    full_name=f"Phase 11 {role.title()}",
                    password=password,
                    role=role,
                ),
            )
            for role in ("admin", "engineer", "technician", "viewer")
        }
        db.commit()
        asset_id = asset.id
        sensor_ids = [sensor.id for sensor in sensors]
        user_ids = [user.id for user in users.values()]
        tokens = {role: create_access_token(user.id, role) for role, user in users.items()}

    yield asset_id, tokens

    with SessionLocal() as db:
        db.execute(delete(ConditionAssessment).where(ConditionAssessment.asset_id == asset_id))
        db.execute(delete(SensorReading).where(SensorReading.sensor_id.in_(sensor_ids)))
        db.execute(delete(Sensor).where(Sensor.id.in_(sensor_ids)))
        db.execute(delete(Asset).where(Asset.id == asset_id))
        db.execute(delete(User).where(User.id.in_(user_ids)))
        db.commit()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_multi_sensor_assessment_and_endpoint_rbac(monitoring_fixture) -> None:
    asset_id, tokens = monitoring_fixture
    assert client.get(f"/api/assets/{asset_id}/condition-assessments").status_code == 401
    assert client.post(
        f"/api/assets/{asset_id}/condition-assessments", headers=_auth(tokens["viewer"])
    ).status_code == 403
    assert client.post(
        f"/api/assets/{asset_id}/condition-assessments", headers=_auth(tokens["technician"])
    ).status_code == 403

    created = client.post(
        f"/api/assets/{asset_id}/condition-assessments", headers=_auth(tokens["engineer"])
    )
    assert created.status_code == 200, created.text
    payload = created.json()
    assert payload["status"] == "anomalous"
    assert len(payload["findings"]) == 2
    assert {finding["finding_status"] for finding in payload["findings"]} == {"normal", "anomalous"}

    repeated = client.post(
        f"/api/assets/{asset_id}/condition-assessments", headers=_auth(tokens["admin"])
    )
    assert repeated.status_code == 200
    assert repeated.json()["id"] == payload["id"]

    for role, token in tokens.items():
        listed = client.get(
            f"/api/assets/{asset_id}/condition-assessments", headers=_auth(token)
        )
        latest = client.get(
            f"/api/assets/{asset_id}/condition-assessments/latest", headers=_auth(token)
        )
        by_id = client.get(
            f"/api/condition-assessments/{payload['id']}", headers=_auth(token)
        )
        assert listed.status_code == latest.status_code == by_id.status_code == 200, role

    with SessionLocal() as db:
        assert db.scalar(
            select(func.count()).select_from(ConditionAssessment).where(
                ConditionAssessment.asset_id == asset_id
            )
        ) == 1
        assert db.scalar(select(func.count()).select_from(Alert).where(Alert.asset_id == asset_id)) == 0
        assert db.scalar(select(func.count()).select_from(AIAnalysis).where(AIAnalysis.asset_id == asset_id)) == 0
