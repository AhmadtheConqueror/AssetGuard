from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class SensorCreate(BaseModel):
    name: str
    sensor_type: str
    unit: str
    status: str = "active"


class SensorUpdate(BaseModel):
    name: str | None = None
    sensor_type: str | None = None
    unit: str | None = None
    status: str | None = None

    @model_validator(mode="after")
    def required_fields_cannot_be_null(self) -> "SensorUpdate":
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class SensorRead(BaseModel):
    id: UUID
    asset_id: UUID
    name: str
    sensor_type: str
    unit: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
