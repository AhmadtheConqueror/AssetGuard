from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


ConditionStatus = Literal["insufficient_data", "normal", "watch", "anomalous"]
TrendDirection = Literal["increasing", "decreasing", "stable"]


class ConditionFinding(BaseModel):
    sensor_id: UUID
    sensor_name: str
    sensor_type: str
    unit: str
    latest_value: float | None
    baseline_value: float | None
    deviation_score: float | None
    recent_change: float | None
    trend_direction: TrendDirection
    trend_strength: float | None
    finding_status: ConditionStatus
    explanation: str


class ConditionAssessmentRead(BaseModel):
    id: UUID
    asset_id: UUID
    evaluated_at: datetime
    evaluated_through: datetime
    status: ConditionStatus
    summary: str
    findings: list[ConditionFinding]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
