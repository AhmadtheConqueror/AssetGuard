from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.asset import Asset
from app.models.maintenance_record import MaintenanceRecord
from app.schemas.maintenance_record import (
    MaintenanceCancelRequest,
    MaintenanceCompleteRequest,
    MaintenanceRecordCreate,
    MaintenanceRecordUpdate,
    MaintenanceStartRequest,
    MaintenanceStatus,
    MaintenanceType,
)


class AssetNotFoundError(Exception):
    pass


class AlertNotFoundError(Exception):
    pass


class AlertAssetConflictError(Exception):
    pass


class InvalidMaintenanceTransitionError(Exception):
    pass


def create_maintenance_record(
    db: Session, asset_id: UUID, record_data: MaintenanceRecordCreate
) -> MaintenanceRecord:
    if db.get(Asset, asset_id) is None:
        raise AssetNotFoundError

    if record_data.alert_id is not None:
        alert = db.get(Alert, record_data.alert_id)
        if alert is None:
            raise AlertNotFoundError
        if alert.asset_id != asset_id:
            raise AlertAssetConflictError

    record = MaintenanceRecord(
        asset_id=asset_id,
        status="planned",
        **record_data.model_dump(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_maintenance_record_by_id(db: Session, record_id: UUID) -> MaintenanceRecord | None:
    return db.get(MaintenanceRecord, record_id)


def list_maintenance_records_for_asset(
    db: Session,
    asset_id: UUID,
    skip: int = 0,
    limit: int = 100,
    record_status: MaintenanceStatus | None = None,
    maintenance_type: MaintenanceType | None = None,
) -> list[MaintenanceRecord]:
    if db.get(Asset, asset_id) is None:
        raise AssetNotFoundError

    statement = select(MaintenanceRecord).where(MaintenanceRecord.asset_id == asset_id)
    if record_status is not None:
        statement = statement.where(MaintenanceRecord.status == record_status)
    if maintenance_type is not None:
        statement = statement.where(MaintenanceRecord.maintenance_type == maintenance_type)
    statement = statement.order_by(MaintenanceRecord.created_at.desc(), MaintenanceRecord.id.desc())
    statement = statement.offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def update_maintenance_record(
    db: Session, record: MaintenanceRecord, record_data: MaintenanceRecordUpdate
) -> MaintenanceRecord:
    for field_name, value in record_data.model_dump(exclude_unset=True).items():
        setattr(record, field_name, value)
    db.commit()
    db.refresh(record)
    return record


def start_maintenance(
    db: Session, record: MaintenanceRecord, request: MaintenanceStartRequest
) -> MaintenanceRecord:
    if record.status == "in_progress":
        return record
    if record.status != "planned":
        raise InvalidMaintenanceTransitionError(
            f"A {record.status} maintenance record cannot be started"
        )

    record.status = "in_progress"
    record.started_at = datetime.now(UTC)
    if "engineer_name" in request.model_fields_set:
        record.engineer_name = request.engineer_name
    db.commit()
    db.refresh(record)
    return record


def complete_maintenance(
    db: Session, record: MaintenanceRecord, request: MaintenanceCompleteRequest
) -> MaintenanceRecord:
    if record.status == "completed":
        return record
    if record.status != "in_progress":
        raise InvalidMaintenanceTransitionError(
            f"A {record.status} maintenance record cannot be completed"
        )

    record.status = "completed"
    record.completed_at = datetime.now(UTC)
    if "outcome" in request.model_fields_set:
        record.outcome = request.outcome
    if "engineer_name" in request.model_fields_set:
        record.engineer_name = request.engineer_name
    db.commit()
    db.refresh(record)
    return record


def cancel_maintenance(
    db: Session, record: MaintenanceRecord, request: MaintenanceCancelRequest
) -> MaintenanceRecord:
    if record.status == "cancelled":
        return record
    if record.status == "completed":
        raise InvalidMaintenanceTransitionError("A completed maintenance record cannot be cancelled")

    record.status = "cancelled"
    if "outcome" in request.model_fields_set:
        record.outcome = request.outcome
    db.commit()
    db.refresh(record)
    return record