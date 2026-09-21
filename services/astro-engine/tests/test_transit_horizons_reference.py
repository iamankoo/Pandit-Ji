"""Independent JPL Horizons reference for planetary longitude (docs
TR-10, `TRANSIT_ACCURACY_HORIZONS_V1`).

This is ENGINEERING EVIDENCE, not a validation of the transit engine or of the
Lahiri ayanamsa: 42 samples (7 bodies x 6 dates, 1950-2060) of NASA/JPL Horizons
geocentric apparent ecliptic longitude of date, retrieved 2026-09-21. The
comparison converts the engine's sidereal longitude back to the tropical
longitude of date with the engine's own ayanamsa, so it checks the planetary
position only."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pandit_astro_engine import ephemeris
from pandit_astro_engine.models import CalculationConfig, CelestialBody
from pandit_astro_engine.transits.constants import HORIZONS_EVIDENCE

FIXTURE = Path(__file__).parent / "fixtures" / "horizons_transit_reference.json"
DOCUMENT = json.loads(FIXTURE.read_text(encoding="utf-8"))
SAMPLES = DOCUMENT["samples"]

#: Tolerances in arcseconds. The measured maxima (Moshier) were 0.38 (planets) and 4.78 (Moon);
#: these leave headroom and also hold for full Swiss Ephemeris data files.
TOLERANCE_ARCSEC = {"moon": 6.0}
DEFAULT_TOLERANCE_ARCSEC = 1.0


def test_the_fixture_is_dated_sourced_and_complete() -> None:
    assert DOCUMENT["retrieved_on"] == "2026-09-21"
    assert DOCUMENT["source"].startswith("https://ssd.jpl.nasa.gov/")
    assert DOCUMENT["sample_count"] == len(SAMPLES) == 42
    assert {s["body"] for s in SAMPLES} == {
        "sun",
        "moon",
        "mars",
        "mercury",
        "jupiter",
        "venus",
        "saturn",
    }
    assert len({s["julian_day_ut"] for s in SAMPLES}) == 6
    assert "engineering evidence" in DOCUMENT["description"].lower()
    for sample in SAMPLES:
        assert 0.0 <= sample["ecliptic_longitude_of_date_deg"] < 360.0
        assert sample["horizons_time_ut"]


def test_the_recorded_evidence_statement_matches_the_fixture() -> None:
    assert "42-sample" in HORIZONS_EVIDENCE and "2026-09-21" in HORIZONS_EVIDENCE


def tropical_longitude(jd: float, body: CelestialBody) -> float:
    """Swiss Ephemeris tropical longitude of date, through the Phase 4 adapter."""
    return ephemeris.calculate_body(
        jd, ephemeris.SWE_BODY_ID[body.value], sidereal=False, allow_moshier_fallback=True
    ).longitude


def arcsec_difference(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0) * 3600.0


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda s: f"{s['body']}-{s['horizons_time_ut']}")
def test_engine_longitude_agrees_with_horizons(sample: dict[str, object]) -> None:
    jd = float(sample["julian_day_ut"])  # type: ignore[arg-type]
    body = CelestialBody(sample["body"])
    reference = float(sample["ecliptic_longitude_of_date_deg"])  # type: ignore[arg-type]
    difference = arcsec_difference(tropical_longitude(jd, body), reference)
    limit = TOLERANCE_ARCSEC.get(body.value, DEFAULT_TOLERANCE_ARCSEC)
    assert difference <= limit, f"{difference:.2f} arcsec"


def test_the_measured_maxima_support_the_documented_numbers() -> None:
    worst: dict[str, float] = {}
    for sample in SAMPLES:
        body = CelestialBody(sample["body"])
        difference = arcsec_difference(
            tropical_longitude(float(sample["julian_day_ut"]), body),
            float(sample["ecliptic_longitude_of_date_deg"]),
        )
        worst[body.value] = max(worst.get(body.value, 0.0), difference)
    if ephemeris.configured_ephemeris_path() is None:
        # Moshier mode: the numbers recorded in the standards (TR-10).
        assert worst["moon"] == pytest.approx(4.78, abs=0.05)
        assert worst["saturn"] == pytest.approx(0.27, abs=0.05)
        assert worst["jupiter"] == pytest.approx(0.38, abs=0.05)
    assert max(v for k, v in worst.items() if k != "moon") < 1.0


def test_the_implied_ayanamsa_differs_from_the_adapter_value_at_nutation_scale() -> None:
    """Documented observation (TR-10): the ayanamsa implied by the sidereal calculation is not
    the value get_ayanamsa_degrees returns; the difference is at the scale of nutation."""
    config = CalculationConfig()
    assert config.ayanamsa is not None
    ephemeris.set_sidereal_mode(config.ayanamsa)
    differences = []
    for sample in SAMPLES:
        jd = float(sample["julian_day_ut"])
        body = CelestialBody(sample["body"])
        sidereal = ephemeris.calculate_body(
            jd, ephemeris.SWE_BODY_ID[body.value], sidereal=True, allow_moshier_fallback=True
        ).longitude
        implied = (tropical_longitude(jd, body) - sidereal) % 360.0
        differences.append((implied - ephemeris.get_ayanamsa_degrees(jd)) * 3600.0)
    assert max(abs(d) for d in differences) < 17.5  # bounded by nutation in longitude
    assert max(differences) > 10.0 and min(differences) < -10.0  # and it does reach that scale
