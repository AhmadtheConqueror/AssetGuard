from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.schemas.maintenance_record import (
    MaintenanceCancelRequest,
    MaintenanceCompleteRequest,
    MaintenanceRecordCreate,
    MaintenanceRecordRead,
    MaintenanceRecordUpdate,
    MaintenanceStartRequest,
    MaintenanceStatus,
    MaintenanceType,
)
from app.services import maintenance_record_service


router = APIRouter(tags=["maintenance-records"], dependencies=[Depends(get_current_user)])
DatabaseSession = Annotated[Session, Depends(get_db)]


def _get_record_or_404(db: Session, record_id: UUID):
    record = maintenance_record_service.get_maintenance_record_by_id(db, record_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance record not found")
    return record


def _transition_error(exc: maintenance_record_service.InvalidMaintenanceTransitionError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post(
    "/api/assets/{asset_id}/maintenance-records",
    response_model=MaintenanceRecordRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("engineer", "admin"))],
)
def create_maintenance_record(asset_id: UUID, record_data: MaintenanceRecordCreate, db: DatabaseSession):
    try:
        return maintenance_record_service.create_maintenance_record(db, asset_id, record_data)
    except maintenance_record_service.AssetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found") from exc
    except maintenance_record_service.AlertNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found") from exc
    except maintenance_record_service.AlertAssetConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Alert belongs to a different Asset",
        ) from exc


@router.get("/api/assets/{asset_id}/maintenance-records", response_model=list[MaintenanceRecordRead])
def list_maintenance_records(
    asset_id: UUID,
    db: DatabaseSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    record_status: Annotated[MaintenanceStatus | None, Query(alias="status")] = None,
    maintenance_type: MaintenanceType | None = None,
):
    try:
        return maintenance_record_service.list_maintenance_records_for_asset(
            db,
            asset_id,
            skip=skip,
            limit=limit,
            record_status=record_status,
            maintenance_type=maintenance_type,
        )
    except maintenance_record_service.AssetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found") from exc


@router.get("/api/maintenance-records/{record_id}", response_model=MaintenanceRecordRead)
def get_maintenance_record(record_id: UUID, db: DatabaseSession):
    return _get_record_or_404(db, record_id)


@router.patch("/api/maintenance-records/{record_id}", response_model=MaintenanceRecordRead,
              dependencies=[Depends(require_roles("engineer", "admin"))])
def update_maintenance_record(
    record_id: UUID, record_data: MaintenanceRecordUpdate, db: DatabaseSession
):
    record = _get_record_or_404(db, record_id)
    return maintenance_record_service.update_maintenance_record(db, record, record_data)


@router.post("/api/maintenance-records/{record_id}/start", response_model=MaintenanceRecordRead,
             dependencies=[Depends(require_roles("technician", "engineer", "admin"))])
def start_maintenance(record_id: UUID, request: MaintenanceStartRequest, db: DatabaseSession):
    record = _get_record_or_404(db, record_id)
    try:
        return maintenance_record_service.start_maintenance(db, record, request)
    except maintenance_record_service.InvalidMaintenanceTransitionError as exc:
        raise _transition_error(exc) from exc


@router.post("/api/maintenance-records/{record_id}/complete", response_model=MaintenanceRecordRead,
             dependencies=[Depends(require_roles("technician", "engineer", "admin"))])
def complete_maintenance(record_id: UUID, request: MaintenanceCompleteRequest, db: DatabaseSession):
    record = _get_record_or_404(db, record_id)
    try:
        return maintenance_record_service.complete_maintenance(db, record, request)
    except maintenance_record_service.InvalidMaintenanceTransitionError as exc:
        raise _transition_error(exc) from exc


@router.post("/api/maintenance-records/{record_id}/cancel", response_model=MaintenanceRecordRead,
             dependencies=[Depends(require_roles("engineer", "admin"))])
def cancel_maintenance(record_id: UUID, request: MaintenanceCancelRequest, db: DatabaseSession):
    record = _get_record_or_404(db, record_id)
    try:
        return maintenance_record_service.cancel_maintenance(db, record, request)
    except maintenance_record_service.InvalidMaintenanceTransitionError as exc:
        raise _transition_error(exc) from exc
