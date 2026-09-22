from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models import Alert, Asset, MaintenanceRecord, Sensor, SensorReading, User
from app.schemas.user import UserCreate
from app.services import user_service


client = TestClient(app)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(email: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_authentication_and_rbac_end_to_end() -> None:
    marker = uuid4().hex
    password = f"Strong-{token_urlsafe(18)}"
    users: dict[str, User] = {}
    asset_id: UUID | None = None

    with SessionLocal() as db:
        for role in ("admin", "engineer", "technician", "viewer"):
            users[role] = user_service.create_user(
                db,
                UserCreate(email=f"phase9-{role}-{marker}@example.test",
                           full_name=f"Temporary {role.title()}", password=password, role=role),
            )
        inactive = user_service.create_user(
            db,
            UserCreate(email=f"phase9-inactive-{marker}@example.test",
                       full_name="Temporary Inactive", password=password, role="viewer"),
        )
        inactive.is_active = False
        db.commit()
        user_ids = [user.id for user in [*users.values(), inactive]]

    try:
        health = client.get("/health")
        assert health.status_code == 200
        assert client.get("/api/assets").status_code == 401
        assert client.get("/api/assets", headers=_auth("not-a-token")).status_code == 401

        expired = create_access_token(
            users["viewer"].id, "viewer", now=datetime.now(UTC) - timedelta(hours=2)
        )
        assert client.get("/api/assets", headers=_auth(expired)).status_code == 401

        unknown = client.post("/api/auth/login", json={"email": f"missing-{marker}@example.test",
                                                        "password": password})
        wrong = client.post("/api/auth/login", json={"email": users["viewer"].email,
                                                      "password": "incorrect-password"})
        inactive_login = client.post("/api/auth/login", json={"email": inactive.email,
                                                               "password": password})
        assert unknown.status_code == wrong.status_code == inactive_login.status_code == 401
        assert unknown.json()["detail"] == wrong.json()["detail"] == inactive_login.json()["detail"]
        inactive_token = create_access_token(inactive.id, "viewer")
        assert client.get("/api/auth/me", headers=_auth(inactive_token)).status_code == 401

        tokens = {role: _login(user.email.upper(), password) for role, user in users.items()}
        me = client.get("/api/auth/me", headers=_auth(tokens["admin"]))
        assert me.status_code == 200
        assert me.json()["email"] == users["admin"].email
        assert client.post("/api/auth/logout", headers=_auth(tokens["admin"])).status_code == 200

        with SessionLocal() as db:
            stored = db.get(User, users["admin"].id)
            assert stored is not None and stored.last_login_at is not None
            assert stored.password_hash.startswith("$argon2")
            assert password not in stored.password_hash

        assert client.get("/api/users", headers=_auth(tokens["viewer"])).status_code == 403
        api_user_response = client.post(
            "/api/users", headers=_auth(tokens["admin"]),
            json={"email": f"phase9-created-{marker}@example.test", "full_name": "API Created User",
                  "password": password, "role": "viewer"},
        )
        assert api_user_response.status_code == 201, api_user_response.text
        api_user_id = UUID(api_user_response.json()["id"])
        user_ids.append(api_user_id)
        assert client.get("/api/users", headers=_auth(tokens["admin"])).status_code == 200
        assert client.get(f"/api/users/{api_user_id}", headers=_auth(tokens["admin"])).status_code == 200
        assert client.patch(f"/api/users/{api_user_id}", headers=_auth(tokens["admin"]),
                            json={"role": "technician"}).status_code == 200
        assert client.patch(
            f"/api/users/{users['admin'].id}", headers=_auth(tokens["admin"]), json={"role": "viewer"}
        ).status_code == 409
        assert client.patch(
            f"/api/users/{users['admin'].id}", headers=_auth(tokens["admin"]), json={"is_active": False}
        ).status_code == 409
        assert client.patch(
            f"/api/users/{users['technician'].id}", headers=_auth(tokens["admin"]),
            json={"full_name": "Temporary Field Technician"},
        ).status_code == 200
        duplicate = client.post(
            "/api/users", headers=_auth(tokens["admin"]),
            json={"email": users["viewer"].email.upper(), "full_name": "Duplicate",
                  "password": password, "role": "viewer"},
        )
        assert duplicate.status_code == 409

        for role, token in tokens.items():
            response = client.get("/api/assets", headers=_auth(token))
            assert response.status_code == 200, (role, response.text)

        asset_payload = {"name": "Phase 9 Temporary Asset", "asset_code": f"AUTH-{marker[:10]}",
                         "asset_type": "test fixture", "status": "active"}
        assert client.post("/api/assets", headers=_auth(tokens["engineer"]),
                           json=asset_payload).status_code == 403
        asset_response = client.post("/api/assets", headers=_auth(tokens["admin"]), json=asset_payload)
        assert asset_response.status_code == 201, asset_response.text
        asset_id = UUID(asset_response.json()["id"])
        assert client.get(f"/api/assets/{asset_id}",
                          headers=_auth(tokens["viewer"])).status_code == 200
        disposable_asset = client.post(
            "/api/assets", headers=_auth(tokens["admin"]),
            json={**asset_payload, "name": "Disposable Admin Asset",
                  "asset_code": f"DEL-{marker[:10]}"},
        )
        disposable_asset_id = disposable_asset.json()["id"]
        assert client.patch(f"/api/assets/{disposable_asset_id}", headers=_auth(tokens["admin"]),
                            json={"status": "inactive"}).status_code == 200
        assert client.delete(f"/api/assets/{disposable_asset_id}",
                             headers=_auth(tokens["admin"])).status_code == 204

        sensor_response = client.post(
            f"/api/assets/{asset_id}/sensors", headers=_auth(tokens["admin"]),
            json={"name": "Temporary temperature", "sensor_type": "temperature", "unit": "C"},
        )
        assert sensor_response.status_code == 201, sensor_response.text
        sensor_id = sensor_response.json()["id"]
        disposable_sensor = client.post(
            f"/api/assets/{asset_id}/sensors", headers=_auth(tokens["admin"]),
            json={"name": "Disposable sensor", "sensor_type": "test", "unit": "n/a"},
        )
        disposable_sensor_id = disposable_sensor.json()["id"]
        assert client.patch(f"/api/sensors/{disposable_sensor_id}", headers=_auth(tokens["admin"]),
                            json={"status": "inactive"}).status_code == 200
        assert client.delete(f"/api/sensors/{disposable_sensor_id}",
                             headers=_auth(tokens["admin"])).status_code == 204
        assert client.post(
            f"/api/sensors/{sensor_id}/readings", headers=_auth(tokens["technician"]),
            json={"recorded_at": datetime.now(UTC).isoformat(), "value": 42.0},
        ).status_code == 403
        assert client.post(
            f"/api/sensors/{sensor_id}/readings", headers=_auth(tokens["admin"]),
            json={"recorded_at": datetime.now(UTC).isoformat(), "value": 42.0, "quality": "good"},
        ).status_code == 201
        assert client.get(f"/api/sensors/{sensor_id}/readings",
                          headers=_auth(tokens["viewer"])).status_code == 200

        alert_payload = {"title": "Temporary authorization alert", "severity": "moderate"}
        assert client.post(f"/api/assets/{asset_id}/alerts", headers=_auth(tokens["viewer"]),
                           json=alert_payload).status_code == 403
        assert client.post(f"/api/assets/{asset_id}/alerts", headers=_auth(tokens["technician"]),
                           json=alert_payload).status_code == 403
        alert_response = client.post(f"/api/assets/{asset_id}/alerts",
                                     headers=_auth(tokens["engineer"]), json=alert_payload)
        assert alert_response.status_code == 201, alert_response.text
        alert_id = alert_response.json()["id"]
        assert client.get(f"/api/alerts/{alert_id}",
                          headers=_auth(tokens["technician"])).status_code == 200
        assert client.post(f"/api/alerts/{alert_id}/acknowledge",
                           headers=_auth(tokens["technician"])).status_code == 200
        assert client.post(f"/api/alerts/{alert_id}/resolve", headers=_auth(tokens["technician"]),
                           json={}).status_code == 403
        assert client.post(f"/api/alerts/{alert_id}/resolve", headers=_auth(tokens["engineer"]),
                           json={"engineer_notes": "Temporary test resolved"}).status_code == 200
        engineer_alert = client.post(f"/api/assets/{asset_id}/alerts",
                                     headers=_auth(tokens["engineer"]), json=alert_payload)
        engineer_alert_id = engineer_alert.json()["id"]
        assert client.post(f"/api/alerts/{engineer_alert_id}/acknowledge",
                           headers=_auth(tokens["engineer"])).status_code == 200
        assert client.post(f"/api/alerts/{engineer_alert_id}/resolve",
                           headers=_auth(tokens["engineer"]), json={}).status_code == 200

        maintenance_payload = {"maintenance_type": "inspection",
                               "description": "Temporary authorization inspection"}
        assert client.post(f"/api/assets/{asset_id}/maintenance-records",
                           headers=_auth(tokens["viewer"]), json=maintenance_payload).status_code == 403
        assert client.post(f"/api/assets/{asset_id}/maintenance-records",
                           headers=_auth(tokens["technician"]), json=maintenance_payload).status_code == 403
        record_response = client.post(f"/api/assets/{asset_id}/maintenance-records",
                                      headers=_auth(tokens["engineer"]), json=maintenance_payload)
        assert record_response.status_code == 201, record_response.text
        record_id = record_response.json()["id"]
        assert client.get(f"/api/maintenance-records/{record_id}",
                          headers=_auth(tokens["technician"])).status_code == 200
        assert client.post(f"/api/maintenance-records/{record_id}/start",
                           headers=_auth(tokens["technician"]), json={}).status_code == 200
        assert client.post(f"/api/maintenance-records/{record_id}/complete",
                           headers=_auth(tokens["technician"]),
                           json={"outcome": "Temporary test complete"}).status_code == 200

        cancellable = client.post(f"/api/assets/{asset_id}/maintenance-records",
                                  headers=_auth(tokens["engineer"]), json=maintenance_payload)
        cancellable_id = cancellable.json()["id"]
        assert client.patch(f"/api/maintenance-records/{cancellable_id}",
                            headers=_auth(tokens["engineer"]),
                            json={"description": "Temporary edited inspection"}).status_code == 200
        assert client.post(f"/api/maintenance-records/{cancellable_id}/cancel",
                           headers=_auth(tokens["engineer"]), json={}).status_code == 200
        engineer_record = client.post(f"/api/assets/{asset_id}/maintenance-records",
                                      headers=_auth(tokens["engineer"]), json=maintenance_payload)
        engineer_record_id = engineer_record.json()["id"]
        assert client.post(f"/api/maintenance-records/{engineer_record_id}/start",
                           headers=_auth(tokens["engineer"]), json={}).status_code == 200
        assert client.post(f"/api/maintenance-records/{engineer_record_id}/complete",
                           headers=_auth(tokens["engineer"]), json={}).status_code == 200

        assert client.post(f"/api/assets/{asset_id}/ai-analyses",
                           headers=_auth(tokens["viewer"])).status_code == 403
        assert client.post(f"/api/assets/{asset_id}/ai-analyses",
                           headers=_auth(tokens["technician"])).status_code == 403
        # This asset has insufficient telemetry, so authorization is proven without contacting Gemini.
        assert client.post(f"/api/assets/{asset_id}/ai-analyses",
                           headers=_auth(tokens["engineer"])).status_code == 422
    finally:
        with SessionLocal() as db:
            if asset_id is not None:
                sensor_ids = list(db.scalars(select(Sensor.id).where(Sensor.asset_id == asset_id)))
                if sensor_ids:
                    db.execute(delete(SensorReading).where(SensorReading.sensor_id.in_(sensor_ids)))
                db.execute(delete(MaintenanceRecord).where(MaintenanceRecord.asset_id == asset_id))
                db.execute(delete(Alert).where(Alert.asset_id == asset_id))
                db.execute(delete(Sensor).where(Sensor.asset_id == asset_id))
                db.execute(delete(Asset).where(Asset.id == asset_id))
            db.execute(delete(User).where(User.id.in_(user_ids)))
            db.commit()
