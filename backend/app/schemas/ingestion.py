from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.sensor_reading import SensorReadingCreate


class IngestionReading(SensorReadingCreate):
    sensor_id: UUID


class IngestionBatch(BaseModel):
    source: str = Field(min_length=1, max_length=100)
    readings: list[IngestionReading] = Field(min_length=1, max_length=500)


class IngestionResult(BaseModel):
    source: str
    received_count: int
    accepted_count: int
    duplicate_count: int


class IngestionAssetIdentity(BaseModel):
    id: UUID
    asset_code: str
    name: str


class IngestionSensor(BaseModel):
    id: UUID
    name: str
    sensor_type: str
    unit: str
    latest_value: float | None
    latest_recorded_at: datetime | None


class IngestionSensorDiscovery(BaseModel):
    asset: IngestionAssetIdentity
    sensors: list[IngestionSensor]
