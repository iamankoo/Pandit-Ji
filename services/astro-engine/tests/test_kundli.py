"""Functional tests for `KundliCalculationService` -- Phase 5 (Birth Chart /
Kundli Engine). Wraps Phase 4's `AstronomicalCalculationService`; never
duplicates a Swiss Ephemeris call outside `ephemeris.py`."""

from __future__ import annotations

from pandit_astro_engine.dignity import DignityStatus
from pandit_astro_engine.kundli import KundliCalculationService
from pandit_astro_engine.models import (
    AstronomicalCalculationRequest,
    CelestialBody,
    LocalDateTimeInput,
    Location,
)
from pandit_astro_engine.rashi import Rashi
from pandit_astro_engine.vargas import SUPPORTED_VARGAS

_DELHI = Location(latitude=28.6139, longitude=77.2090, altitude_meters=216)


def _request(
    year: int, month: int, day: int, hour: int, minute: int = 0
) -> AstronomicalCalculationRequest:
    return AstronomicalCalculationRequest(
        local_datetime=LocalDateTimeInput(
            year=year, month=month, day=day, hour=hour, minute=minute, timezone="Asia/Kolkata"
        ),
        location=_DELHI,
        include_solar_events=False,
    )


def test_golden_india_independence_chart() -> None:
    """India's Independence chart (15 Aug 1947, 00:00 IST, New Delhi) is a
    widely published reference chart -- its Ascendant (Taurus) and Moon
    sign (Cancer) are independently documented (e.g. astrotheme.com,
    jyotishgram.com), genuinely independent of this codebase, unlike an
    internal-consistency check."""
    result = KundliCalculationService().calculate(_request(1947, 8, 15, 0, 0))
    assert result.lagna.rashi is Rashi.TAURUS
    moon = next(p for p in result.planets if p.body == CelestialBody.MOON)
    assert moon.rashi is Rashi.CANCER


def test_ascendant_is_always_house_one() -> None:
    result = KundliCalculationService().calculate(_request(2000, 1, 1, 6, 30))
    assert result.houses[0].house == 1
    assert result.houses[0].rashi is result.lagna.rashi


def test_house_lord_matches_sign_lord_table() -> None:
    from pandit_astro_engine.lordship import sign_lord

    result = KundliCalculationService().calculate(_request(2000, 1, 1, 6, 30))
    for house in result.houses:
        assert house.lord == sign_lord(house.rashi)


def test_all_sixteen_vargas_present() -> None:
    result = KundliCalculationService().calculate(_request(2000, 1, 1, 6, 30))
    assert set(result.charts) == set(SUPPORTED_VARGAS)
    for varga in SUPPORTED_VARGAS:
        assert result.charts[varga].label == f"D{varga}"


def test_rahu_ketu_dignity_never_evaluated() -> None:
    result = KundliCalculationService().calculate(_request(2000, 1, 1, 6, 30))
    rahu = next(p for p in result.planets if p.body == CelestialBody.RAHU)
    ketu = next(p for p in result.planets if p.body == CelestialBody.KETU)
    assert rahu.dignity is None
    assert ketu.dignity is None


def test_other_planets_dignity_is_populated() -> None:
    result = KundliCalculationService().calculate(_request(2000, 1, 1, 6, 30))
    for planet in result.planets:
        if planet.body in (CelestialBody.RAHU, CelestialBody.KETU):
            continue
        assert isinstance(planet.dignity, DignityStatus)


def test_chandra_chart_uses_moon_as_house_one() -> None:
    result = KundliCalculationService().calculate(_request(2000, 1, 1, 6, 30))
    moon = next(p for p in result.planets if p.body == CelestialBody.MOON)
    assert result.chandra_chart is not None
    assert result.chandra_chart.ascendant_rashi is moon.rashi
    assert result.chandra_chart.houses[0].rashi is moon.rashi


def test_partial_body_request_still_places_ascendant_and_houses() -> None:
    request = AstronomicalCalculationRequest(
        local_datetime=LocalDateTimeInput(
            year=2000, month=1, day=1, hour=6, minute=30, timezone="Asia/Kolkata"
        ),
        location=_DELHI,
        bodies=[CelestialBody.MOON],
        include_solar_events=False,
    )
    result = KundliCalculationService().calculate(request)
    assert len(result.houses) == 12
    assert len(result.planets) == 1
    assert result.planets[0].body == CelestialBody.MOON
    assert result.chandra_chart is not None
    for varga in SUPPORTED_VARGAS:
        assert len(result.charts[varga].planets) == 1


def test_no_moon_requested_leaves_chandra_chart_unset() -> None:
    request = AstronomicalCalculationRequest(
        local_datetime=LocalDateTimeInput(
            year=2000, month=1, day=1, hour=6, minute=30, timezone="Asia/Kolkata"
        ),
        location=_DELHI,
        bodies=[CelestialBody.SUN],
        include_solar_events=False,
    )
    result = KundliCalculationService().calculate(request)
    assert result.chandra_chart is None


def test_astronomical_facts_are_embedded_not_recomputed() -> None:
    request = _request(2000, 1, 1, 6, 30)
    kundli_result = KundliCalculationService().calculate(request)

    from pandit_astro_engine.service import AstronomicalCalculationService

    direct_result = AstronomicalCalculationService().calculate(request)
    assert kundli_result.astronomical.planets.sun.longitude == direct_result.planets.sun.longitude
