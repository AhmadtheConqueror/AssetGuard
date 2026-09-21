from datetime import UTC, datetime
from statistics import fmean
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.base import AIAssetAnalyzer
from app.ai.gemini import GeminiAssetAnalyzer
from app.ai.schemas import (
    AnalysisWindow,
    AssetTelemetryContext,
    SensorTelemetrySummary,
    TelemetryPoint,
)
from app.core.config import settings
from app.models.ai_analysis import AIAnalysis
from app.models.asset import Asset
from app.models.sensor import Sensor
from app.models.sensor_reading import SensorReading


class AssetNotFoundError(Exception):
    pass


class InsufficientTelemetryError(Exception):
    pass


def _get_latest_readings(db: Session, sensor_id: UUID, limit: int) -> list[SensorReading]:
    statement = (
        select(SensorReading)
        .where(SensorReading.sensor_id == sensor_id)
        .order_by(SensorReading.recorded_at.desc(), SensorReading.id.desc())
        .limit(limit)
    )
    return list(reversed(db.scalars(statement).all()))


def _summarize_sensor(sensor: Sensor, readings: list[SensorReading]) -> SensorTelemetrySummary:
    points = [
        TelemetryPoint(recorded_at=reading.recorded_at, value=reading.value, quality=reading.quality)
        for reading in readings
    ]
    if not readings:
        return SensorTelemetrySummary(
            sensor_id=str(sensor.id),
            sensor_name=sensor.name,
            sensor_type=sensor.sensor_type,
            unit=sensor.unit,
            reading_count=0,
            first_timestamp=None,
            last_timestamp=None,
            first_value=None,
            latest_value=None,
            minimum=None,
            maximum=None,
            arithmetic_mean=None,
            absolute_change=None,
            percentage_change=None,
            series=points,
        )

    values = [reading.value for reading in readings]
    change = round(values[-1] - values[0], 10)
    percentage_change = None if values[0] == 0 else round((change / values[0]) * 100, 10)
    return SensorTelemetrySummary(
        sensor_id=str(sensor.id),
        sensor_name=sensor.name,
        sensor_type=sensor.sensor_type,
        unit=sensor.unit,
        reading_count=len(readings),
        first_timestamp=readings[0].recorded_at,
        last_timestamp=readings[-1].recorded_at,
        first_value=values[0],
        latest_value=values[-1],
        minimum=min(values),
        maximum=max(values),
        arithmetic_mean=round(fmean(values), 10),
        absolute_change=change,
        percentage_change=percentage_change,
        series=points,
    )


def prepare_telemetry_context(db: Session, asset_id: UUID, limit_per_sensor: int) -> AssetTelemetryContext:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise AssetNotFoundError

    sensors = list(
        db.scalars(select(Sensor).where(Sensor.asset_id == asset_id).order_by(Sensor.name, Sensor.id)).all()
    )
    summaries = [_summarize_sensor(sensor, _get_latest_readings(db, sensor.id, limit_per_sensor)) for sensor in sensors]
    if not any(summary.reading_count >= 2 for summary in summaries):
        raise InsufficientTelemetryError("At least one Sensor must have two or more readings")

    timestamps = [
        timestamp
        for summary in summaries
        for timestamp in (summary.first_timestamp, summary.last_timestamp)
        if timestamp is not None
    ]
    return AssetTelemetryContext(
        asset_id=str(asset.id),
        asset_code=asset.asset_code,
        asset_name=asset.name,
        asset_type=asset.asset_type,
        analysis_window=AnalysisWindow(
            limit_per_sensor=limit_per_sensor,
            earliest_timestamp=min(timestamps) if timestamps else None,
            latest_timestamp=max(timestamps) if timestamps else None,
            sensors_with_readings=sum(summary.reading_count > 0 for summary in summaries),
            sensors_without_readings=[summary.sensor_name for summary in summaries if summary.reading_count == 0],
        ),
        sensors=summaries,
    )


def create_ai_analysis(
    db: Session,
    asset_id: UUID,
    limit_per_sensor: int,
    analyzer: AIAssetAnalyzer | None = None,
) -> AIAnalysis:
    context = prepare_telemetry_context(db, asset_id, limit_per_sensor)
    execution = (analyzer or GeminiAssetAnalyzer()).analyze(context)
    result = execution.result
    analysis = AIAnalysis(
        asset_id=asset_id,
        analyzed_at=datetime.now(UTC),
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        summary=result.summary,
        anomaly_detected=result.anomaly_detected,
        findings={
            "model_findings": [finding.model_dump(mode="json") for finding in result.findings],
            "limitations": result.limitations,
            "analysis_window": context.analysis_window.model_dump(mode="json"),
            "deterministic_sensor_metrics": [sensor.model_dump(mode="json") for sensor in context.sensors],
            "provider_execution": {
                "primary_model": execution.primary_model,
                "model_used": execution.model_used,
                "fallback_used": execution.fallback_used,
            },
        },
        recommended_actions=[action.model_dump(mode="json") for action in result.recommended_actions],
        model_provider="google",
        model_name=execution.model_used,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def get_ai_analysis_by_id(db: Session, analysis_id: UUID) -> AIAnalysis | None:
    return db.get(AIAnalysis, analysis_id)


def list_ai_analyses(db: Session, asset_id: UUID, skip: int = 0, limit: int = 100) -> list[AIAnalysis]:
    if db.get(Asset, asset_id) is None:
        raise AssetNotFoundError
    statement = (
        select(AIAnalysis)
        .where(AIAnalysis.asset_id == asset_id)
        .order_by(AIAnalysis.analyzed_at.desc(), AIAnalysis.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def get_latest_ai_analysis(db: Session, asset_id: UUID) -> AIAnalysis | None:
    if db.get(Asset, asset_id) is None:
        raise AssetNotFoundError
    statement = (
        select(AIAnalysis)
        .where(AIAnalysis.asset_id == asset_id)
        .order_by(AIAnalysis.analyzed_at.desc(), AIAnalysis.id.desc())
        .limit(1)
    )
    return db.scalar(statement)
