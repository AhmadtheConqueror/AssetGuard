from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SensorReadingCreate(BaseModel):
    recorded_at: datetime
    value: float = Field(allow_inf_nan=False)
    quality: str | None = Field(default=None, max_length=50)

    @field_validator("recorded_at")
    @classmethod
    def recorded_at_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_at must include timezone information")
        return value


class SensorReadingRead(BaseModel):
    id: UUID
    sensor_id: UUID
    recorded_at: datetime
    value: float
    quality: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
