"""Large-scale (hundreds/thousands of cases) internal-consistency and
determinism testing (Phase 4 prompt §27C/§28's volume requirement).

Honesty note: this validates internal consistency and determinism at scale,
NOT independent astronomical accuracy at scale -- see test_reference_validation.py's
docstring and services/astro-engine/README.md "Known limitations" for why a
true bulk independent-reference comparison was not performed.
"""

from __future__ import annotations

import random

import pytest

from pandit_astro_engine import ephemeris
from pandit_astro_engine import planets as planets_module
from pandit_astro_engine.models import CalculationConfig, CelestialBody

N_CASES = 2000


@pytest.fixture(autouse=True)
def _no_ephemeris_path() -> None:
    ephemeris.configure_ephemeris_path(None)


def _random_julian_days(count: int, seed: int = 42) -> list[float]:
    rng = random.Random(seed)
    # Roughly 1900-01-01 to 2100-01-01 in Julian Day terms.
    return [rng.uniform(2415021.0, 2488070.0) for _ in range(count)]


def test_determinism_across_many_random_instants() -> None:
    config = CalculationConfig()
    mismatches = 0
    for jd in _random_julian_days(N_CASES):
        states1, mode1 = planets_module.calculate_all_bodies(jd, config, list(CelestialBody))
        states2, mode2 = planets_module.calculate_all_bodies(jd, config, list(CelestialBody))
        if mode1 != mode2 or any(
            states1[b].model_dump() != states2[b].model_dump() for b in CelestialBody
        ):
            mismatches += 1
    assert mismatches == 0, f"{mismatches}/{N_CASES} cases were non-deterministic"


def test_rahu_ketu_180_degrees_across_many_random_instants() -> None:
    config = CalculationConfig()
    max_error = 0.0
    for jd in _random_julian_days(N_CASES):
        states, _mode = planets_module.calculate_all_bodies(
            jd, config, [CelestialBody.RAHU, CelestialBody.KETU]
        )
        diff = (states[CelestialBody.KETU].longitude - states[CelestialBody.RAHU].longitude) % 360
        max_error = max(max_error, abs(diff - 180.0))
    assert max_error < 1e-6, f"max Rahu/Ketu deviation from 180 deg: {max_error}"


def test_all_longitudes_in_valid_range_across_many_random_instants() -> None:
    config = CalculationConfig()
    for jd in _random_julian_days(N_CASES):
        states, _mode = planets_module.calculate_all_bodies(jd, config, list(CelestialBody))
        for body, state in states.items():
            msg = f"{body} out of range at {jd=}: {state.longitude}"
            assert 0.0 <= state.longitude < 360.0, msg


def test_retrograde_flag_matches_speed_sign_across_many_random_instants() -> None:
    config = CalculationConfig()
    for jd in _random_julian_days(N_CASES):
        states, _mode = planets_module.calculate_all_bodies(jd, config, list(CelestialBody))
        for body, state in states.items():
            assert state.retrograde == (state.speed_longitude < 0), (
                f"{body} retrograde flag inconsistent with speed sign at jd={jd}"
            )


def test_combustion_threshold_consistent_with_standard_across_many_random_instants() -> None:
    config = CalculationConfig()
    combustion_eligible = (
        CelestialBody.MOON,
        CelestialBody.MARS,
        CelestialBody.MERCURY,
        CelestialBody.JUPITER,
        CelestialBody.VENUS,
        CelestialBody.SATURN,
    )
    for jd in _random_julian_days(500):  # smaller sample; still hundreds
        states, _mode = planets_module.calculate_all_bodies(jd, config, list(CelestialBody))
        for body in combustion_eligible:
            status = states[body].combustion
            assert status is not None
            assert status.is_combust == (
                status.angular_separation_degrees <= status.threshold_degrees
            )
