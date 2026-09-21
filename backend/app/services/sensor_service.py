from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sensor import Sensor
from app.schemas.sensor import SensorCreate, SensorUpdate


def create_sensor_for_asset(db: Session, asset_id: UUID, sensor_data: SensorCreate) -> Sensor:
    sensor = Sensor(asset_id=asset_id, **sensor_data.model_dump())
    db.add(sensor)
    db.commit()
    db.refresh(sensor)
    return sensor


def get_sensor_by_id(db: Session, sensor_id: UUID) -> Sensor | None:
    return db.get(Sensor, sensor_id)


def list_sensors_for_asset(db: Session, asset_id: UUID, skip: int = 0, limit: int = 100) -> list[Sensor]:
    statement = (
        select(Sensor)
        .where(Sensor.asset_id == asset_id)
        .order_by(Sensor.created_at, Sensor.id)
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def update_sensor(db: Session, sensor: Sensor, sensor_data: SensorUpdate) -> Sensor:
    for field_name, value in sensor_data.model_dump(exclude_unset=True).items():
        setattr(sensor, field_name, value)
    db.commit()
    db.refresh(sensor)
    return sensor


def delete_sensor(db: Session, sensor: Sensor) -> None:
    db.delete(sensor)
    db.commit()
