from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.sensor_reading import SensorReading
from app.schemas.sensor_reading import SensorReadingCreate
from app.schemas.ingestion import IngestionReading


def create_sensor_reading(
    db: Session,
    sensor_id: UUID,
    reading_data: SensorReadingCreate,
) -> SensorReading:
    reading = SensorReading(sensor_id=sensor_id, **reading_data.model_dump())
    db.add(reading)
    db.commit()
    db.refresh(reading)
    return reading


def get_sensor_reading_by_id(db: Session, reading_id: UUID) -> SensorReading | None:
    return db.get(SensorReading, reading_id)


def list_sensor_readings(
    db: Session,
    sensor_id: UUID,
    skip: int = 0,
    limit: int = 100,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[SensorReading]:
    statement = select(SensorReading).where(SensorReading.sensor_id == sensor_id)
    if start_time is not None:
        statement = statement.where(SensorReading.recorded_at >= start_time)
    if end_time is not None:
        statement = statement.where(SensorReading.recorded_at <= end_time)
    statement = statement.order_by(SensorReading.recorded_at, SensorReading.id).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def get_latest_sensor_reading(db: Session, sensor_id: UUID) -> SensorReading | None:
    statement = (
        select(SensorReading)
        .where(SensorReading.sensor_id == sensor_id)
        .order_by(SensorReading.recorded_at.desc(), SensorReading.id.desc())
        .limit(1)
    )
    return db.scalar(statement)


def create_sensor_readings_idempotently(
    db: Session,
    readings: list[IngestionReading],
) -> tuple[int, int]:
    values = [reading.model_dump() for reading in readings]
    statement = (
        insert(SensorReading)
        .values(values)
        .on_conflict_do_nothing(index_elements=["sensor_id", "recorded_at"])
        .returning(SensorReading.id)
    )
    accepted_count = len(db.scalars(statement).all())
    db.commit()
    return accepted_count, len(readings) - accepted_count
