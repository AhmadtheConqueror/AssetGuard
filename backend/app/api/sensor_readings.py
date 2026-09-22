from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.schemas.sensor_reading import SensorReadingCreate, SensorReadingRead
from app.services import sensor_reading_service, sensor_service


router = APIRouter(tags=["sensor readings"], dependencies=[Depends(get_current_user)])
DatabaseSession = Annotated[Session, Depends(get_db)]


def _ensure_sensor_exists(db: Session, sensor_id: UUID) -> None:
    if sensor_service.get_sensor_by_id(db, sensor_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")


def _ensure_timezone_aware(value: datetime | None, field_name: str) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} must include timezone information",
        )


@router.post(
    "/api/sensors/{sensor_id}/readings",
    response_model=SensorReadingRead,
    status_code=status.HTTP_201_CREATED,
    # Replace this user role gate with a scoped machine credential when device ingestion is introduced.
    dependencies=[Depends(require_roles("admin"))],
)
def create_sensor_reading(sensor_id: UUID, reading_data: SensorReadingCreate, db: DatabaseSession):
    _ensure_sensor_exists(db, sensor_id)
    return sensor_reading_service.create_sensor_reading(db, sensor_id, reading_data)


@router.get("/api/sensors/{sensor_id}/readings", response_model=list[SensorReadingRead])
def list_sensor_readings(
    sensor_id: UUID,
    db: DatabaseSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
):
    _ensure_sensor_exists(db, sensor_id)
    _ensure_timezone_aware(start_time, "start_time")
    _ensure_timezone_aware(end_time, "end_time")
    if start_time is not None and end_time is not None and start_time > end_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="start_time must be before or equal to end_time",
        )
    return sensor_reading_service.list_sensor_readings(
        db,
        sensor_id,
        skip=skip,
        limit=limit,
        start_time=start_time,
        end_time=end_time,
    )


@router.get("/api/sensors/{sensor_id}/readings/latest", response_model=SensorReadingRead)
def get_latest_sensor_reading(sensor_id: UUID, db: DatabaseSession):
    _ensure_sensor_exists(db, sensor_id)
    reading = sensor_reading_service.get_latest_sensor_reading(db, sensor_id)
    if reading is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor has no readings")
    return reading


@router.get("/api/readings/{reading_id}", response_model=SensorReadingRead)
def get_sensor_reading(reading_id: UUID, db: DatabaseSession):
    reading = sensor_reading_service.get_sensor_reading_by_id(db, reading_id)
    if reading is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor reading not found")
    return reading
