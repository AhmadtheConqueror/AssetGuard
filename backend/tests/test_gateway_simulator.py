import random

import pytest

from scripts.simulate_gateway import DEGRADING_DRIFT, NORMAL_NOISE, next_value, parse_args


def _legacy_next_value(current: float, kind: str, scenario: str, rng: random.Random) -> float:
    noise = NORMAL_NOISE.get(kind, max(abs(current) * 0.002, 0.02))
    drift = DEGRADING_DRIFT.get(kind, 0.0) if scenario == "degrading" else 0.0
    return round(current + drift + rng.uniform(-noise, noise), 4)


def test_default_intensity_preserves_existing_cli_and_generation() -> None:
    args = parse_args(["--scenario", "degrading", "--seed", "42"])
    assert args.intensity == 1.0

    for scenario in ("normal", "degrading"):
        expected_rng = random.Random(42)
        actual_rng = random.Random(42)
        expected = _legacy_next_value(72.0, "temperature", scenario, expected_rng)
        actual = next_value(72.0, "temperature", scenario, actual_rng)
        assert actual == expected


def test_degrading_intensity_scales_drift_but_not_noise() -> None:
    base_rng = random.Random(7)
    stronger_rng = random.Random(7)
    base = next_value(10.0, "pressure", "degrading", base_rng, intensity=1.0)
    stronger = next_value(10.0, "pressure", "degrading", stronger_rng, intensity=3.0)
    assert stronger - base == pytest.approx(DEGRADING_DRIFT["pressure"] * 2, abs=0.0001)


def test_normal_scenario_is_independent_of_intensity() -> None:
    base_rng = random.Random(99)
    stronger_rng = random.Random(99)
    assert next_value(2.5, "vibration", "normal", base_rng, intensity=1.0) == next_value(
        2.5, "vibration", "normal", stronger_rng, intensity=8.0
    )


def test_seeded_generation_remains_reproducible() -> None:
    def sequence() -> list[float]:
        rng = random.Random(123)
        values = [100.0]
        for _ in range(8):
            values.append(next_value(values[-1], "flow", "degrading", rng, intensity=3.0))
        return values

    assert sequence() == sequence()


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf"])
def test_intensity_must_be_positive_and_finite(value: str) -> None:
    with pytest.raises(SystemExit):
        parse_args(["--intensity", value])
