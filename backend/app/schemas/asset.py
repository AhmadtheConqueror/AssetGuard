from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class AssetCreate(BaseModel):
    name: str
    asset_code: str
    asset_type: str
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    location: str | None = None
    status: str = "active"
    commissioned_at: datetime | None = None


class AssetUpdate(BaseModel):
    name: str | None = None
    asset_code: str | None = None
    asset_type: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    location: str | None = None
    status: str | None = None
    commissioned_at: datetime | None = None

    @model_validator(mode="after")
    def required_fields_cannot_be_null(self) -> "AssetUpdate":
        required_fields = {"name", "asset_code", "asset_type", "status"}
        for field_name in required_fields & self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class AssetRead(BaseModel):
    id: UUID
    name: str
    asset_code: str
    asset_type: str
    manufacturer: str | None
    model: str | None
    serial_number: str | None
    location: str | None
    status: str
    commissioned_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
