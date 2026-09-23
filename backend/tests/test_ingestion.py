from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import delete, func, select

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models import Asset, Sensor, SensorReading, User
from app.schemas.user import UserCreate
from app.services import user_service


client = TestClient(app)
HEADER_NAME = "X-AssetGuard-Ingestion-Key"
TEST_KEY = "phase-10-test-ingestion-key"


@pytest.fixture
def ingestion_fixture(monkeypatch: pytest.MonkeyPatch):
    marker = uuid4().hex
    monkeypatch.setattr(settings, "INGESTION_API_KEY", SecretStr(TEST_KEY))
    with SessionLocal() as db:
        asset = Asset(
            name="Phase 10 Temporary Compressor",
            asset_code=f"INGEST-{marker[:10]}",
            asset_type="compressor",
            status="active",
        )
        db.add(asset)
        db.flush()
        sensors = [
            Sensor(asset_id=asset.id, name="Temperature", sensor_type="temperature", unit="C"),
            Sensor(asset_id=asset.id, name="Pressure", sensor_type="pressure", unit="bar"),
        ]
        db.add_all(sensors)
        db.commit()
        asset_id = asset.id
        asset_code = asset.asset_code
        sensor_ids = [sensor.id for sensor in sensors]

    yield asset_code, sensor_ids

    with SessionLocal() as db:
        db.execute(delete(SensorReading).where(SensorReading.sensor_id.in_(sensor_ids)))
        db.execute(delete(Sensor).where(Sensor.id.in_(sensor_ids)))
        db.execute(delete(Asset).where(Asset.id == asset_id))
        db.commit()


def _payload(sensor_ids: list, recorded_at: datetime | None = None) -> dict:
    timestamp = (recorded_at or datetime.now(UTC)).isoformat()
    return {
        "source": "test-gateway",
        "readings": [
            {"sensor_id": str(sensor_id), "recorded_at": timestamp, "value": 40.0 + index, "quality": "good"}
            for index, sensor_id in enumerate(sensor_ids)
        ],
    }


def test_ingestion_authentication(ingestion_fixture, monkeypatch: pytest.MonkeyPatch) -> None:
    _, sensor_ids = ingestion_fixture
    payload = _payload(sensor_ids[:1])
    assert client.post("/api/ingestion/readings", json=payload).status_code == 401
    assert client.post(
        "/api/ingestion/readings", json=payload, headers={HEADER_NAME: "wrong-key"}
    ).status_code == 401

    monkeypatch.setattr(settings, "INGESTION_API_KEY", None)
    assert client.post(
        "/api/ingestion/readings", json=payload, headers={HEADER_NAME: TEST_KEY}
    ).status_code == 503


def test_batch_ingestion_and_duplicate_retry(ingestion_fixture) -> None:
    _, sensor_ids = ingestion_fixture
    payload = _payload(sensor_ids)
    headers = {HEADER_NAME: TEST_KEY}

    accepted = client.post("/api/ingestion/readings", json=payload, headers=headers)
    assert accepted.status_code == 201, accepted.text
    assert accepted.json() == {
        "source": "test-gateway",
        "received_count": 2,
        "accepted_count": 2,
        "duplicate_count": 0,
    }

    duplicate = client.post("/api/ingestion/readings", json=payload, headers=headers)
    assert duplicate.status_code == 201, duplicate.text
    assert duplicate.json()["accepted_count"] == 0
    assert duplicate.json()["duplicate_count"] == 2
    with SessionLocal() as db:
        count = db.scalar(select(func.count()).select_from(SensorReading).where(SensorReading.sensor_id.in_(sensor_ids)))
        assert count == 2


def test_ingestion_validation_is_atomic(ingestion_fixture) -> None:
    _, sensor_ids = ingestion_fixture
    headers = {HEADER_NAME: TEST_KEY}
    timestamp = datetime.now(UTC)
    unknown_payload = _payload([sensor_ids[0], uuid4()], timestamp)
    response = client.post("/api/ingestion/readings", json=unknown_payload, headers=headers)
    assert response.status_code == 422
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(SensorReading).where(SensorReading.sensor_id == sensor_ids[0])) == 0

    invalid_timestamp = _payload(sensor_ids[:1])
    invalid_timestamp["readings"][0]["recorded_at"] = "2026-09-23T10:00:00"
    assert client.post("/api/ingestion/readings", json=invalid_timestamp, headers=headers).status_code == 422

    for value in ("NaN", "Infinity", "-Infinity"):
        invalid_value = _payload(sensor_ids[:1], timestamp + timedelta(seconds=1))
        invalid_value["readings"][0]["value"] = value
        assert client.post("/api/ingestion/readings", json=invalid_value, headers=headers).status_code == 422


def test_discovery_and_existing_jwt_api(ingestion_fixture) -> None:
    asset_code, sensor_ids = ingestion_fixture
    headers = {HEADER_NAME: TEST_KEY}
    discovery = client.get(f"/api/ingestion/assets/{asset_code}/sensors", headers=headers)
    assert discovery.status_code == 200, discovery.text
    assert discovery.json()["asset"]["asset_code"] == asset_code
    assert {sensor["id"] for sensor in discovery.json()["sensors"]} == {str(sensor_id) for sensor_id in sensor_ids}
    assert all(sensor["latest_value"] is None for sensor in discovery.json()["sensors"])

    comp_discovery = client.get("/api/ingestion/assets/COMP-001/sensors", headers=headers)
    assert comp_discovery.status_code == 200, comp_discovery.text
    assert comp_discovery.json()["asset"]["asset_code"] == "COMP-001"
    assert len(comp_discovery.json()["sensors"]) == 4

    password = f"Strong-{token_urlsafe(18)}"
    with SessionLocal() as db:
        user = user_service.create_user(
            db,
            UserCreate(
                email=f"phase10-{uuid4().hex}@example.test",
                full_name="Phase 10 Viewer",
                password=password,
                role="viewer",
            ),
        )
        user_id = user.id
    try:
        token = create_access_token(user_id, "viewer")
        response = client.get("/api/assets", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
    finally:
        with SessionLocal() as db:
            db.execute(delete(User).where(User.id == user_id))
            db.commit()
