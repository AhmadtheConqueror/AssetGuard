from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AIFinding(BaseModel):
    sensor: str
    observation: str
    evidence: str
    significance: str


class AIRecommendedAction(BaseModel):
    action: str
    rationale: str
    priority: Literal["low", "moderate", "high", "critical"]


class AIAnalysisResult(BaseModel):
    anomaly_detected: bool
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_level: Literal["low", "moderate", "high", "critical"]
    summary: str
    findings: list[AIFinding]
    recommended_actions: list[AIRecommendedAction]
    limitations: list[str]


class AIAnalysisExecution(BaseModel):
    result: AIAnalysisResult
    primary_model: str
    model_used: str
    fallback_used: bool


class TelemetryPoint(BaseModel):
    recorded_at: datetime
    value: float
    quality: str | None


class SensorTelemetrySummary(BaseModel):
    sensor_id: str
    sensor_name: str
    sensor_type: str
    unit: str
    reading_count: int
    first_timestamp: datetime | None
    last_timestamp: datetime | None
    first_value: float | None
    latest_value: float | None
    minimum: float | None
    maximum: float | None
    arithmetic_mean: float | None
    absolute_change: float | None
    percentage_change: float | None
    series: list[TelemetryPoint]


class AnalysisWindow(BaseModel):
    limit_per_sensor: int
    earliest_timestamp: datetime | None
    latest_timestamp: datetime | None
    sensors_with_readings: int
    sensors_without_readings: list[str]


class AssetTelemetryContext(BaseModel):
    asset_id: str
    asset_code: str
    asset_name: str
    asset_type: str
    analysis_window: AnalysisWindow
    sensors: list[SensorTelemetrySummary]
