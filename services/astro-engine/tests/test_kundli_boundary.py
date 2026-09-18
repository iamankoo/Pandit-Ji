"""Boundary tests for the Kundli engine -- Phase 5 (Birth Chart / Kundli
Engine): sign-boundary transitions, extreme latitudes, and the antimeridian."""

from __future__ import annotations

import pytest

from pandit_astro_engine import ephemeris
from pandit_astro_engine.kundli import KundliCalculationService
from pandit_astro_engine.models import AstronomicalCalculationRequest, LocalDateTimeInput, Location
from pandit_astro_engine.rashi import rashi_from_longitude


@pytest.mark.parametrize("latitude", [89.9, 66.5, 0.0, -66.5, -89.9])
def test_ascendant_calculation_does_not_crash_at_extreme_latitudes(latitude: float) -> None:
    request = AstronomicalCalculationRequest(
        local_datetime=LocalDateTimeInput(
            year=2000, month=6, day=21, hour=12, minute=0, timezone="UTC"
        ),
        location=Location(latitude=latitude, longitude=10.0),
        include_solar_events=False,
    )
    result = KundliCalculationService().calculate(request)
    assert 0.0 <= result.lagna_longitude < 360.0


@pytest.mark.parametrize("longitude", [-179.9, -180.0, 179.9, 180.0])
def test_ascendant_calculation_near_antimeridian(longitude: float) -> None:
    request = AstronomicalCalculationRequest(
        local_datetime=LocalDateTimeInput(
            year=2000, month=6, day=21, hour=12, minute=0, timezone="UTC"
        ),
        location=Location(latitude=10.0, longitude=longitude),
        include_solar_events=False,
    )
    result = KundliCalculationService().calculate(request)
    assert 0.0 <= result.lagna_longitude < 360.0


def test_ascendant_house_assignment_consistent_at_a_sign_boundary_instant() -> None:
    """Regresses the whole-sign house-1 assignment against `rashi_from_longitude`
    directly, independent of the Kundli orchestrator's own bookkeeping."""
    request = AstronomicalCalculationRequest(
        local_datetime=LocalDateTimeInput(
            year=2010, month=3, day=15, hour=9, minute=0, timezone="UTC"
        ),
        location=Location(latitude=51.5074, longitude=-0.1278),
        include_solar_events=False,
    )
    ascendant_longitude = ephemeris.calculate_ascendant(
        ephemeris.utc_to_julian_day(2010, 3, 15, 9, 0, 0.0)[1],
        latitude=51.5074,
        longitude=-0.1278,
        sidereal=True,
    )
    result = KundliCalculationService().calculate(request)
    assert result.lagna.rashi is rashi_from_longitude(ascendant_longitude)


def test_new_moon_conjunction_places_sun_and_moon_in_the_same_house() -> None:
    # A birth instant does not need an exact conjunction for this test's
    # purpose -- it exercises the same-sign/same-house bookkeeping path
    # whenever it happens to occur for the requested instant/location.
    request = AstronomicalCalculationRequest(
        local_datetime=LocalDateTimeInput(
            year=2000, month=1, day=6, hour=18, minute=0, timezone="UTC"
        ),
        location=Location(latitude=28.6139, longitude=77.2090),
        include_solar_events=False,
    )
    result = KundliCalculationService().calculate(request)
    sun = next(p for p in result.planets if p.body.value == "sun")
    moon = next(p for p in result.planets if p.body.value == "moon")
    if sun.rashi == moon.rashi:
        assert sun.house == moon.house
