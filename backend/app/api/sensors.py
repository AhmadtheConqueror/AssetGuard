from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.schemas.sensor import SensorCreate, SensorRead, SensorUpdate
from app.services import asset_service, sensor_service


router = APIRouter(tags=["sensors"], dependencies=[Depends(get_current_user)])
DatabaseSession = Annotated[Session, Depends(get_db)]


def _ensure_asset_exists(db: Session, asset_id: UUID) -> None:
    if asset_service.get_asset_by_id(db, asset_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")


def _get_sensor_or_404(db: Session, sensor_id: UUID):
    sensor = sensor_service.get_sensor_by_id(db, sensor_id)
    if sensor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor not found")
    return sensor


@router.post(
    "/api/assets/{asset_id}/sensors",
    response_model=SensorRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("admin"))],
)
def create_sensor(asset_id: UUID, sensor_data: SensorCreate, db: DatabaseSession):
    _ensure_asset_exists(db, asset_id)
    return sensor_service.create_sensor_for_asset(db, asset_id, sensor_data)


@router.get("/api/assets/{asset_id}/sensors", response_model=list[SensorRead])
def list_sensors(
    asset_id: UUID,
    db: DatabaseSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    _ensure_asset_exists(db, asset_id)
    return sensor_service.list_sensors_for_asset(db, asset_id, skip=skip, limit=limit)


@router.get("/api/sensors/{sensor_id}", response_model=SensorRead)
def get_sensor(sensor_id: UUID, db: DatabaseSession):
    return _get_sensor_or_404(db, sensor_id)


@router.patch("/api/sensors/{sensor_id}", response_model=SensorRead,
              dependencies=[Depends(require_roles("admin"))])
def update_sensor(sensor_id: UUID, sensor_data: SensorUpdate, db: DatabaseSession):
    sensor = _get_sensor_or_404(db, sensor_id)
    return sensor_service.update_sensor(db, sensor, sensor_data)


@router.delete("/api/sensors/{sensor_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles("admin"))])
def delete_sensor(sensor_id: UUID, db: DatabaseSession) -> Response:
    sensor = _get_sensor_or_404(db, sensor_id)
    sensor_service.delete_sensor(db, sensor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
