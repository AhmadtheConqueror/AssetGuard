import argparse
import math
import os
import random
import sys
import time
from datetime import UTC, datetime
from typing import Any

import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_BASELINES = {
    "temperature": 72.0,
    "pressure": 5.0,
    "vibration": 2.5,
    "flow": 100.0,
}
NORMAL_NOISE = {
    "temperature": 0.12,
    "pressure": 0.025,
    "vibration": 0.035,
    "flow": 0.18,
}
DEGRADING_DRIFT = {
    "temperature": 0.18,
    "pressure": 0.04,
    "vibration": 0.06,
    "flow": -0.22,
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send synthetic condition telemetry to AssetGuard.")
    parser.add_argument("--asset-code", default="COMP-001")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--cycles", type=int, default=20)
    parser.add_argument("--scenario", choices=("normal", "degrading"), default="normal")
    parser.add_argument(
        "--intensity",
        type=float,
        default=1.0,
        help="Scale synthetic directional degradation without changing random noise.",
    )
    parser.add_argument("--seed", type=int)
    args = parser.parse_args(argv)
    if args.interval < 0:
        parser.error("--interval must be zero or greater")
    if args.cycles < 1:
        parser.error("--cycles must be at least 1")
    if not math.isfinite(args.intensity) or args.intensity <= 0:
        parser.error("--intensity must be a finite number greater than 0")
    return args


def sensor_kind(sensor: dict[str, Any]) -> str:
    descriptor = f"{sensor['sensor_type']} {sensor['name']}".lower()
    return next((kind for kind in DEFAULT_BASELINES if kind in descriptor), "other")


def next_value(
    current: float,
    kind: str,
    scenario: str,
    rng: random.Random,
    intensity: float = 1.0,
) -> float:
    noise = NORMAL_NOISE.get(kind, max(abs(current) * 0.002, 0.02))
    drift = DEGRADING_DRIFT.get(kind, 0.0) * intensity if scenario == "degrading" else 0.0
    return round(current + drift + rng.uniform(-noise, noise), 4)


def run(args: argparse.Namespace) -> int:
    api_key = os.environ.get("INGESTION_API_KEY")
    if not api_key:
        print("INGESTION_API_KEY is not set.", file=sys.stderr)
        return 2

    headers = {"X-AssetGuard-Ingestion-Key": api_key}
    base_url = args.base_url.rstrip("/")
    rng = random.Random(args.seed)

    try:
        with httpx.Client(base_url=base_url, headers=headers, timeout=10.0) as client:
            response = client.get(f"/api/ingestion/assets/{args.asset_code}/sensors")
            response.raise_for_status()
            discovery = response.json()
            sensors = discovery["sensors"]
            if not sensors:
                print(f"No sensors found for {args.asset_code}.", file=sys.stderr)
                return 1

            values = {
                sensor["id"]: float(sensor["latest_value"])
                if sensor["latest_value"] is not None
                else DEFAULT_BASELINES.get(sensor_kind(sensor), 0.0)
                for sensor in sensors
            }
            intensity_label = f", intensity {args.intensity:g}" if args.intensity != 1.0 else ""
            print(
                f"Simulating {args.scenario} telemetry for {discovery['asset']['asset_code']} "
                f"({len(sensors)} sensors, {args.cycles} cycles{intensity_label})."
            )

            for cycle in range(1, args.cycles + 1):
                recorded_at = datetime.now(UTC).isoformat()
                readings = []
                for sensor in sensors:
                    sensor_id = sensor["id"]
                    values[sensor_id] = next_value(
                        values[sensor_id], sensor_kind(sensor), args.scenario, rng, args.intensity
                    )
                    readings.append(
                        {
                            "sensor_id": sensor_id,
                            "recorded_at": recorded_at,
                            "value": values[sensor_id],
                            "quality": "good",
                        }
                    )

                response = client.post(
                    "/api/ingestion/readings",
                    json={"source": "gateway-simulator", "readings": readings},
                )
                response.raise_for_status()
                result = response.json()
                print(
                    f"Cycle {cycle}/{args.cycles}: accepted {result['accepted_count']}, "
                    f"duplicates {result['duplicate_count']}"
                )
                if cycle < args.cycles:
                    time.sleep(args.interval)
    except httpx.HTTPStatusError as exc:
        print(f"Gateway request failed with HTTP {exc.response.status_code}.", file=sys.stderr)
        return 1
    except httpx.RequestError as exc:
        print(f"Could not reach AssetGuard: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nSimulation stopped.")
        return 130

    print("Simulation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
