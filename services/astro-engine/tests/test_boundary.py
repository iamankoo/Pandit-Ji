"""Boundary/edge-case tests (Phase 4 prompt §27E): degree wraparound,
retrograde station transitions, date/timezone/midnight boundaries.
"""

from __future__ import annotations

import pytest

from pandit_astro_engine import ephemeris
from pandit_astro_engine import planets as planets_module
from pandit_astro_engine.models import (
    CalculationConfig,
    CelestialBody,
    LocalDateTimeInput,
    Location,
    ZodiacType,
)
from pandit_astro_engine.service import AstronomicalCalculationService


@pytest.fixture(autouse=True)
def _no_ephemeris_path() -> None:
    ephemeris.configure_ephemeris_path(None)


def test_longitude_wraps_correctly_near_zero_and_360() -> None:
    # A date where the Sun's tropical longitude is very close to 0/360
    # (northward equinox, ~March 20).
    jd_ut, _ = ephemeris.utc_to_julian_day(2024, 3, 20, 3, 0, 0.0)
    config = CalculationConfig(zodiac=ZodiacType.TROPICAL, ayanamsa=None)
    states, _mode = planets_module.calculate_all_bodies(jd_ut, config, [CelestialBody.SUN])
    longitude = states[CelestialBody.SUN].longitude
    assert 0.0 <= longitude < 360.0
    # Should be near the 0/360 boundary either from below or from just past it.
    assert longitude < 2.0 or longitude > 358.0


def test_degree_components_never_negative_or_over_60() -> None:
    config = CalculationConfig()
    for jd_offset in range(0, 3650, 37):  # sparse sample across ~10 years
        jd_ut = 2451545.0 + jd_offset
        states, _mode = planets_module.calculate_all_bodies(jd_ut, config, [CelestialBody.MOON])
        components = states[CelestialBody.MOON].degree_components
        assert 0 <= components.degrees < 360
        assert 0 <= components.minutes < 60
        assert 0.0 <= components.seconds < 60.0


def test_mercury_retrograde_station_direction_change() -> None:
    # Mercury's retrograde period around late 2023/early 2024 is a
    # well-documented station -- verify the engine reports a sign change
    # in speed (direct -> retrograde -> direct) across it, without
    # asserting a specific literature-sourced date/time (only the
    # documented existence of a station in this window).
    config = CalculationConfig()
    speeds = []
    for day in range(-20, 10, 2):
        jd_ut, _ = ephemeris.utc_to_julian_day(2023, 12, 13, 0, 0, 0.0)
        jd_ut += day
        states, _mode = planets_module.calculate_all_bodies(jd_ut, config, [CelestialBody.MERCURY])
        speeds.append(states[CelestialBody.MERCURY].speed_longitude)
    signs = [s < 0 for s in speeds]
    assert any(signs) and not all(signs), "expected both direct and retrograde speeds here"


def test_midnight_boundary_local_date_rolls_correctly() -> None:
    svc = AstronomicalCalculationService(ephemeris_path=None)
    just_before_midnight = svc.calculate(_request(hour=23, minute=59, second=59))
    just_after_midnight = svc.calculate(_request(day=2, hour=0, minute=0, second=1))
    # Distinct instants -> should not be bit-for-bit identical, but both valid.
    assert just_before_midnight.metadata.time_resolution.julian_day_ut != (
        just_after_midnight.metadata.time_resolution.julian_day_ut
    )


def test_timezone_boundary_date_line_west_vs_east() -> None:
    svc = AstronomicalCalculationService(ephemeris_path=None)
    west = svc.calculate(
        _request(timezone="Pacific/Kiritimati", longitude=-157.4, latitude=1.87)
    )  # UTC+14
    east = svc.calculate(_request(timezone="Etc/GMT+12", longitude=176.5, latitude=-44.0))  # UTC-12
    # Same nominal local wall-clock date/time, ~26 hours apart in real UTC.
    delta = abs(
        (
            west.metadata.time_resolution.utc_datetime - east.metadata.time_resolution.utc_datetime
        ).total_seconds()
    )
    assert delta == pytest.approx(26 * 3600, abs=1)


def _request(
    year: int = 2024,
    month: int = 1,
    day: int = 1,
    hour: int = 12,
    minute: int = 0,
    second: float = 0.0,
    timezone: str = "Asia/Kolkata",
    latitude: float = 28.6139,
    longitude: float = 77.2090,
):
    from pandit_astro_engine.models import AstronomicalCalculationRequest

    return AstronomicalCalculationRequest(
        local_datetime=LocalDateTimeInput(
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            second=second,
            timezone=timezone,
        ),
        location=Location(latitude=latitude, longitude=longitude),
    )
