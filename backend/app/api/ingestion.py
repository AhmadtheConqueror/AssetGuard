import logging
from secrets import compare_digest
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.sensor import Sensor
from app.schemas.ingestion import (
    IngestionAssetIdentity,
    IngestionBatch,
    IngestionResult,
    IngestionSensor,
    IngestionSensorDiscovery,
)
from app.services import (
    asset_service,
    condition_assessment_service,
    sensor_reading_service,
    sensor_service,
)


router = APIRouter(prefix="/api/ingestion", tags=["ingestion"])
DatabaseSession = Annotated[Session, Depends(get_db)]
logger = logging.getLogger(__name__)


def require_ingestion_key(
    provided_key: Annotated[str | None, Header(alias="X-AssetGuard-Ingestion-Key")] = None,
) -> None:
    configured_key = settings.INGESTION_API_KEY
    if configured_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telemetry ingestion is not configured",
        )
    expected_key = configured_key.get_secret_value()
    if not provided_key or not compare_digest(provided_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid ingestion credentials",
        )


IngestionAuth = Annotated[None, Depends(require_ingestion_key)]


@router.post("/readings", response_model=IngestionResult, status_code=status.HTTP_201_CREATED)
def ingest_readings(batch: IngestionBatch, db: DatabaseSession, _: IngestionAuth) -> IngestionResult:
    sensor_ids = {reading.sensor_id for reading in batch.readings}
    known_ids = set(db.scalars(select(Sensor.id).where(Sensor.id.in_(sensor_ids))).all())
    unknown_ids = sorted(str(sensor_id) for sensor_id in sensor_ids - known_ids)
    if unknown_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"message": "One or more sensors do not exist", "sensor_ids": unknown_ids},
        )

    accepted_count, duplicate_count = sensor_reading_service.create_sensor_readings_idempotently(
        db, batch.readings
    )
    if accepted_count:
        asset_ids = set(
            db.scalars(select(Sensor.asset_id).where(Sensor.id.in_(sensor_ids))).all()
        )
        for asset_id in asset_ids:
            try:
                condition_assessment_service.evaluate_asset(db, asset_id)
            except Exception:
                db.rollback()
                logger.exception("Condition monitoring failed after telemetry ingestion")
    return IngestionResult(
        source=batch.source,
        received_count=len(batch.readings),
        accepted_count=accepted_count,
        duplicate_count=duplicate_count,
    )


@router.get("/assets/{asset_code}/sensors", response_model=IngestionSensorDiscovery)
def discover_sensors(
    asset_code: str,
    db: DatabaseSession,
    _: IngestionAuth,
) -> IngestionSensorDiscovery:
    asset = asset_service.get_asset_by_code(db, asset_code)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    sensors = sensor_service.list_sensors_for_asset(db, asset.id)
    return IngestionSensorDiscovery(
        asset=IngestionAssetIdentity(id=asset.id, asset_code=asset.asset_code, name=asset.name),
        sensors=[
            IngestionSensor(
                id=sensor.id,
                name=sensor.name,
                sensor_type=sensor.sensor_type,
                unit=sensor.unit,
                latest_value=latest.value if (latest := sensor_reading_service.get_latest_sensor_reading(db, sensor.id)) else None,
                latest_recorded_at=latest.recorded_at if latest else None,
            )
            for sensor in sensors
        ],
    )
