from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.sensor import Sensor
from app.models.sensor_reading import SensorReading


ASSET_ID = UUID("cb5dcd98-f677-4aea-9d67-a1d1ecc20131")
TIMESTAMPS = [
    datetime.fromisoformat(value)
    for value in (
        "2026-09-21T13:00:00+01:00",
        "2026-09-21T13:05:00+01:00",
        "2026-09-21T13:10:00+01:00",
        "2026-09-21T13:15:00+01:00",
        "2026-09-21T13:20:00+01:00",
        "2026-09-21T13:25:00+01:00",
        "2026-09-21T13:30:00+01:00",
        "2026-09-21T13:35:00+01:00",
        "2026-09-21T13:40:00+01:00",
        "2026-09-21T13:45:00+01:00",
    )
]
SENSOR_SERIES = {
    "Temperature": (
        UUID("3e8cf56e-4a2d-470a-bfff-67edc0f40554"),
        [71.2, 71.4, 71.7, 72.0, 72.2, 72.5, 73.0, 74.1, 76.0, 78.4],
    ),
    "Pressure": (
        UUID("268186c2-7ef9-4896-9b2c-3a2bb58a591f"),
        [8.2, 8.2, 8.3, 8.2, 8.3, 8.4, 8.6, 8.9, 9.3, 9.7],
    ),
    "Vibration": (
        UUID("72b9d7b9-3ec4-4b99-a085-8f015358e6a8"),
        [2.1, 2.2, 2.2, 2.3, 2.4, 2.5, 2.8, 3.4, 4.2, 5.1],
    ),
    "Flow": (
        UUID("8067f362-0bda-4776-b5b8-04364ceada7e"),
        [520.0, 519.0, 521.0, 520.0, 518.0, 517.0, 515.0, 509.0, 500.0, 487.0],
    ),
}


def main() -> None:
    inserted = 0
    skipped = 0

    with SessionLocal() as db:
        sensor_ids = [sensor_id for sensor_id, _ in SENSOR_SERIES.values()]
        sensors = {
            sensor.id: sensor
            for sensor in db.scalars(select(Sensor).where(Sensor.id.in_(sensor_ids)))
        }
        missing_sensor_ids = set(sensor_ids) - set(sensors)
        if missing_sensor_ids:
            missing = ", ".join(sorted(str(sensor_id) for sensor_id in missing_sensor_ids))
            raise RuntimeError(f"Required demo Sensors are missing: {missing}")
        if any(sensor.asset_id != ASSET_ID for sensor in sensors.values()):
            raise RuntimeError("A demo Sensor is not linked to the expected COMP-001 Asset")

        existing_pairs = {
            (sensor_id, recorded_at)
            for sensor_id, recorded_at in db.execute(
                select(SensorReading.sensor_id, SensorReading.recorded_at).where(
                    SensorReading.sensor_id.in_(sensor_ids),
                    SensorReading.recorded_at.in_(TIMESTAMPS),
                )
            )
        }

        for sensor_id, values in SENSOR_SERIES.values():
            for recorded_at, value in zip(TIMESTAMPS, values, strict=True):
                if (sensor_id, recorded_at) in existing_pairs:
                    skipped += 1
                    continue
                db.add(
                    SensorReading(
                        sensor_id=sensor_id,
                        recorded_at=recorded_at,
                        value=value,
                        quality="good",
                    )
                )
                inserted += 1

        db.commit()

        totals = dict(
            db.execute(
                select(SensorReading.sensor_id, func.count(SensorReading.id))
                .where(SensorReading.sensor_id.in_(sensor_ids))
                .group_by(SensorReading.sensor_id)
            ).all()
        )

    print(f"Readings inserted: {inserted}")
    print(f"Readings skipped: {skipped}")
    for sensor_name, (sensor_id, _) in SENSOR_SERIES.items():
        print(f"{sensor_name} total readings: {totals.get(sensor_id, 0)}")


if __name__ == "__main__":
    main()
