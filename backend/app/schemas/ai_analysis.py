from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AIAnalysisRead(BaseModel):
    id: UUID
    asset_id: UUID
    analyzed_at: datetime
    risk_score: float | None
    risk_level: str | None
    summary: str
    anomaly_detected: bool
    findings: dict[str, Any] | list[Any] | None
    recommended_actions: dict[str, Any] | list[Any] | None
    model_provider: str | None
    model_name: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
