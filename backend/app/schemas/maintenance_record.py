from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


MaintenanceType = Literal["preventive", "predictive", "corrective", "inspection"]
MaintenanceStatus = Literal["planned", "in_progress", "completed", "cancelled"]


def _require_timezone(value: datetime | None) -> datetime | None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError("datetime must include timezone information")
    return value


class MaintenanceRecordCreate(BaseModel):
    maintenance_type: MaintenanceType
    description: str
    alert_id: UUID | None = None
    scheduled_for: datetime | None = None
    engineer_name: str | None = None

    model_config = ConfigDict(extra="forbid")

    _scheduled_for_timezone = field_validator("scheduled_for")(_require_timezone)


class MaintenanceRecordUpdate(BaseModel):
    maintenance_type: MaintenanceType | None = None
    description: str | None = None
    scheduled_for: datetime | None = None
    engineer_name: str | None = None
    outcome: str | None = None

    model_config = ConfigDict(extra="forbid")

    _scheduled_for_timezone = field_validator("scheduled_for")(_require_timezone)


class MaintenanceStartRequest(BaseModel):
    engineer_name: str | None = None

    model_config = ConfigDict(extra="forbid")


class MaintenanceCompleteRequest(BaseModel):
    outcome: str | None = None
    engineer_name: str | None = None

    model_config = ConfigDict(extra="forbid")


class MaintenanceCancelRequest(BaseModel):
    outcome: str | None = None

    model_config = ConfigDict(extra="forbid")


class MaintenanceRecordRead(BaseModel):
    id: UUID
    asset_id: UUID
    alert_id: UUID | None
    maintenance_type: MaintenanceType
    description: str
    status: MaintenanceStatus
    scheduled_for: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    outcome: str | None
    engineer_name: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)