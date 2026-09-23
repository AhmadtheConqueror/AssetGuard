import logging
from datetime import UTC, datetime
from statistics import median
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.asset import Asset
from app.models.condition_assessment import ConditionAssessment
from app.models.sensor import Sensor
from app.models.sensor_reading import SensorReading
from app.schemas.condition_assessment import ConditionFinding, ConditionStatus


logger = logging.getLogger(__name__)


class AssetNotFoundError(Exception):
    pass


class NoTelemetryError(Exception):
    pass


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _robust_scale(values: list[float], center: float) -> float:
    mad_scale = median([abs(value - center) for value in values]) * 1.4826
    iqr_scale = (_percentile(values, 0.75) - _percentile(values, 0.25)) / 1.349
    relative_floor = abs(center) * settings.MONITORING_MIN_SCALE_RATIO
    return max(mad_scale, iqr_scale, relative_floor, settings.MONITORING_MIN_ABSOLUTE_SCALE)


def _linear_slope(values: list[float]) -> float:
    x_center = (len(values) - 1) / 2
    y_center = sum(values) / len(values)
    denominator = sum((index - x_center) ** 2 for index in range(len(values)))
    if denominator == 0:
        return 0.0
    return sum(
        (index - x_center) * (value - y_center) for index, value in enumerate(values)
    ) / denominator


def evaluate_sensor_values(
    sensor: Sensor,
    values: list[float],
) -> ConditionFinding:
    latest_value = values[-1] if values else None
    required_count = settings.MONITORING_MIN_HISTORY + settings.MONITORING_RECENT_WINDOW
    if len(values) < required_count:
        return ConditionFinding(
            sensor_id=sensor.id,
            sensor_name=sensor.name,
            sensor_type=sensor.sensor_type,
            unit=sensor.unit,
            latest_value=latest_value,
            baseline_value=None,
            deviation_score=None,
            recent_change=None,
            trend_direction="stable",
            trend_strength=None,
            finding_status="insufficient_data",
            explanation=(
                f"{sensor.name} has {len(values)} readings; at least {required_count} are needed "
                "for a historical baseline and recent observation window."
            ),
        )

    recent_values = values[-settings.MONITORING_RECENT_WINDOW :]
    baseline_values = values[: -settings.MONITORING_RECENT_WINDOW][
        -settings.MONITORING_BASELINE_WINDOW :
    ]
    baseline_value = median(baseline_values)
    recent_value = median(recent_values)
    scale = _robust_scale(baseline_values, baseline_value)
    signed_deviation = (recent_value - baseline_value) / scale
    direction_sign = 1 if signed_deviation > 0 else -1 if signed_deviation < 0 else 0
    persistent_points = sum(
        1
        for value in recent_values
        if direction_sign != 0
        and ((value - baseline_value) / scale) * direction_sign
        >= settings.MONITORING_WATCH_THRESHOLD
    )
    persistence = persistent_points / len(recent_values)

    trend_values = values[-settings.MONITORING_TREND_WINDOW :]
    normalized_trend = (
        _linear_slope(trend_values) * (len(trend_values) - 1) / scale
        if len(trend_values) >= 2
        else 0.0
    )
    if abs(normalized_trend) < settings.MONITORING_TREND_THRESHOLD:
        trend_direction = "stable"
    else:
        trend_direction = "increasing" if normalized_trend > 0 else "decreasing"

    absolute_deviation = abs(signed_deviation)
    if (
        absolute_deviation >= settings.MONITORING_DEVIATION_THRESHOLD
        and persistence >= settings.MONITORING_PERSISTENCE_RATIO
    ):
        finding_status: ConditionStatus = "anomalous"
    elif (
        absolute_deviation >= settings.MONITORING_WATCH_THRESHOLD
        and persistence >= settings.MONITORING_PERSISTENCE_RATIO
    ) or abs(normalized_trend) >= settings.MONITORING_TREND_THRESHOLD:
        finding_status = "watch"
    else:
        finding_status = "normal"

    recent_change = recent_values[-1] - recent_values[0]
    if finding_status == "normal":
        explanation = f"{sensor.name} remains consistent with its recent historical baseline."
    elif finding_status == "watch":
        explanation = (
            f"{sensor.name} shows a sustained {trend_direction} statistical change worth observing."
            if trend_direction != "stable"
            else f"{sensor.name} is moderately displaced from its recent historical baseline."
        )
    else:
        direction = "above" if signed_deviation > 0 else "below"
        explanation = (
            f"{sensor.name} is persistently and materially {direction} its recent historical baseline"
            f" with a {trend_direction} recent pattern."
        )

    return ConditionFinding(
        sensor_id=sensor.id,
        sensor_name=sensor.name,
        sensor_type=sensor.sensor_type,
        unit=sensor.unit,
        latest_value=latest_value,
        baseline_value=round(baseline_value, 10),
        deviation_score=round(signed_deviation, 4),
        recent_change=round(recent_change, 10),
        trend_direction=trend_direction,
        trend_strength=round(normalized_trend, 4),
        finding_status=finding_status,
        explanation=explanation,
    )


def _asset_status(findings: list[ConditionFinding]) -> ConditionStatus:
    evaluable = [finding.finding_status for finding in findings if finding.finding_status != "insufficient_data"]
    if not evaluable:
        return "insufficient_data"
    if "anomalous" in evaluable:
        return "anomalous"
    if "watch" in evaluable:
        return "watch"
    return "normal"


def _summary(status: ConditionStatus, findings: list[ConditionFinding]) -> str:
    if status == "insufficient_data":
        return "There is not yet enough historical telemetry for a reliable statistical comparison."
    notable = [finding.sensor_name for finding in findings if finding.finding_status in {"watch", "anomalous"}]
    if status == "normal":
        return "Current telemetry is consistent with the asset's recent historical behaviour."
    if status == "watch":
        return f"Sustained statistical change is emerging in {', '.join(notable)}."
    return f"Persistent unusual statistical behaviour is present in {', '.join(notable)}."


def _readings_for_sensor(db: Session, sensor_id: UUID) -> list[SensorReading]:
    limit = settings.MONITORING_BASELINE_WINDOW + max(
        settings.MONITORING_RECENT_WINDOW,
        settings.MONITORING_TREND_WINDOW,
    )
    statement = (
        select(SensorReading)
        .where(SensorReading.sensor_id == sensor_id)
        .order_by(SensorReading.recorded_at.desc(), SensorReading.id.desc())
        .limit(limit)
    )
    return list(reversed(db.scalars(statement).all()))


def evaluate_asset(db: Session, asset_id: UUID) -> ConditionAssessment:
    if db.get(Asset, asset_id) is None:
        raise AssetNotFoundError

    sensors = list(
        db.scalars(
            select(Sensor).where(Sensor.asset_id == asset_id).order_by(Sensor.name, Sensor.id)
        ).all()
    )
    sensor_readings = [(sensor, _readings_for_sensor(db, sensor.id)) for sensor in sensors]
    timestamps = [reading.recorded_at for _, readings in sensor_readings for reading in readings]
    if not timestamps:
        raise NoTelemetryError("Asset has no telemetry to evaluate")
    evaluated_through = max(timestamps)

    existing = db.scalar(
        select(ConditionAssessment).where(
            ConditionAssessment.asset_id == asset_id,
            ConditionAssessment.evaluated_through == evaluated_through,
        )
    )
    if existing is not None:
        return existing

    findings = [
        evaluate_sensor_values(sensor, [reading.value for reading in readings])
        for sensor, readings in sensor_readings
    ]
    status = _asset_status(findings)
    assessment = ConditionAssessment(
        asset_id=asset_id,
        evaluated_at=datetime.now(UTC),
        evaluated_through=evaluated_through,
        status=status,
        summary=_summary(status, findings),
        findings=[finding.model_dump(mode="json") for finding in findings],
    )
    db.add(assessment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(ConditionAssessment).where(
                ConditionAssessment.asset_id == asset_id,
                ConditionAssessment.evaluated_through == evaluated_through,
            )
        )
        if existing is None:
            raise
        return existing
    db.refresh(assessment)
    try:
        from app.services import alerting_policy_service

        alerting_policy_service.process_new_assessment(db, assessment)
    except Exception:
        db.rollback()
        logger.exception("Operational alert policy failed for assessment %s", assessment.id)
    return assessment


def get_assessment_by_id(db: Session, assessment_id: UUID) -> ConditionAssessment | None:
    return db.get(ConditionAssessment, assessment_id)


def list_assessments(
    db: Session, asset_id: UUID, skip: int = 0, limit: int = 100
) -> list[ConditionAssessment]:
    if db.get(Asset, asset_id) is None:
        raise AssetNotFoundError
    statement = (
        select(ConditionAssessment)
        .where(ConditionAssessment.asset_id == asset_id)
        .order_by(ConditionAssessment.evaluated_at.desc(), ConditionAssessment.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def get_latest_assessment(db: Session, asset_id: UUID) -> ConditionAssessment | None:
    if db.get(Asset, asset_id) is None:
        raise AssetNotFoundError
    statement = (
        select(ConditionAssessment)
        .where(ConditionAssessment.asset_id == asset_id)
        .order_by(ConditionAssessment.evaluated_at.desc(), ConditionAssessment.id.desc())
        .limit(1)
    )
    return db.scalar(statement)
