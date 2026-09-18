"""Reference validation against independently published astronomical facts
(Phase 4 prompt §28/29). See datasets/fixtures/astro_engine/ for sourcing.

Honesty note (Phase 4 prompt §29/53): this is a small, genuinely independent
golden set (published equinox/solstice UTC instants, source-cited), not a
self-generated "our code agrees with our code" comparison. It is NOT the
"hundreds/thousands of cases against a bulk trusted reference dataset" the
roadmap describes -- no legitimate bulk independent reference dataset
(e.g. licensed JPL Horizons batch output) was available in this environment.
That gap is reported, not papered over, in services/astro-engine/README.md
"Known limitations" and the Phase 4 completion report. `test_consistency.py`
covers the "hundreds/thousands of cases" volume requirement for what it can
actually validate: internal determinism and invariants, at scale.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from pandit_astro_engine import ephemeris
from pandit_astro_engine import planets as planets_module
from pandit_astro_engine.models import CalculationConfig, CelestialBody, ZodiacType

_FIXTURE_PATH = (
    Path(__file__).resolve().parents[3]
    / "datasets"
    / "fixtures"
    / "astro_engine"
    / "golden_solstice_equinox.json"
)


def _load_cases() -> dict:
    with open(_FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(autouse=True)
def _no_ephemeris_path() -> None:
    ephemeris.configure_ephemeris_path(None)


def test_golden_fixture_file_exists_and_is_well_formed() -> None:
    data = _load_cases()
    assert data["cases"], "golden fixture must not be empty"
    assert data["source"], "every reference dataset must record its source (Phase 4 prompt §28)"


def test_tropical_sun_matches_published_equinox_solstice_instants() -> None:
    data = _load_cases()
    tolerance = data["tolerance_degrees"]
    config = CalculationConfig(zodiac=ZodiacType.TROPICAL, ayanamsa=None)

    results = []
    for case in data["cases"]:
        utc = dt.datetime.fromisoformat(case["utc"])
        _jd_et, jd_ut = ephemeris.utc_to_julian_day(
            utc.year, utc.month, utc.day, utc.hour, utc.minute, float(utc.second)
        )
        states, _mode = planets_module.calculate_all_bodies(jd_ut, config, [CelestialBody.SUN])
        actual = states[CelestialBody.SUN].longitude
        expected = case["expected_tropical_sun_longitude"]
        # Handle the 0/360 wraparound case explicitly.
        diff = actual - expected
        error = min(abs(diff), abs(diff + 360), abs(diff - 360))
        results.append((case["name"], expected, actual, error))

    max_error = max(r[3] for r in results)
    report_lines = [
        f"  {name}: expected={expected:.4f} actual={actual:.4f} error={error:.6f}"
        for name, expected, actual, error in results
    ]
    report = (
        f"Reference validation report (source: {data['source']})\n"
        f"  cases: {len(results)}, tolerance: {tolerance} deg, max error: {max_error:.6f} deg\n"
        + "\n".join(report_lines)
    )
    print(report)

    for name, _expected, _actual, error in results:
        assert error <= tolerance, f"{name}: error {error} exceeds tolerance {tolerance}"
