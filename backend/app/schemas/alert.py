from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


AlertSeverity = Literal["low", "moderate", "high", "critical"]
AlertStatus = Literal["open", "acknowledged", "resolved"]
AlertSource = Literal["manual", "condition_monitoring"]


class AlertCreate(BaseModel):
    title: str
    description: str | None = None
    severity: AlertSeverity
    detected_at: datetime | None = None
    ai_analysis_id: UUID | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("detected_at")
    @classmethod
    def detected_at_must_be_timezone_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("detected_at must include timezone information")
        return value


class AlertUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    severity: AlertSeverity | None = None
    engineer_notes: str | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def required_fields_cannot_be_null(self) -> "AlertUpdate":
        for field_name in {"title", "severity"} & self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class AlertResolveRequest(BaseModel):
    engineer_notes: str | None = None

    model_config = ConfigDict(extra="forbid")


class AlertRead(BaseModel):
    id: UUID
    asset_id: UUID
    ai_analysis_id: UUID | None
    condition_assessment_id: UUID | None
    condition_assessment_evaluated_at: datetime | None
    source: AlertSource
    ai_escalation_status: str | None
    title: str
    description: str | None
    severity: AlertSeverity
    status: AlertStatus
    detected_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    engineer_notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
