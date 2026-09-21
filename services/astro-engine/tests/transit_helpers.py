"""Shared helpers for the Phase 8 transit tests: exact synthetic motion."""

from __future__ import annotations

import datetime as dt
import math
from collections.abc import Callable

from pandit_astro_engine.dashas.models import BirthTimeStatus
from pandit_astro_engine.models import CelestialBody, EphemerisMode
from pandit_astro_engine.transits import NatalReference, TransitConfiguration
from pandit_astro_engine.transits.positions import BodyPosition, datetime_to_jd

UTC = dt.timezone.utc
T0 = dt.datetime(2024, 1, 1, tzinfo=UTC)
JD0 = datetime_to_jd(T0)

Motion = Callable[[float], tuple[float, float]]  # jd -> (longitude, speed deg/day)


def static(longitude: float) -> Motion:
    return lambda jd: (longitude, 0.0)


def linear(longitude_at_jd0: float, speed: float) -> Motion:
    return lambda jd: (longitude_at_jd0 + speed * (jd - JD0), speed)


def sinusoid(center: float, amplitude: float, period_days: float, drift: float = 0.0) -> Motion:
    """center + drift * t + amplitude * sin(2 pi t / period), with exact speed."""
    omega = 2.0 * math.pi / period_days

    def motion(jd: float) -> tuple[float, float]:
        t = jd - JD0
        return (
            center + drift * t + amplitude * math.sin(omega * t),
            drift + amplitude * omega * math.cos(omega * t),
        )

    return motion


def parabola(peak_longitude: float, peak_day: float, curvature: float) -> Motion:
    """peak - curvature * (t - peak_day)^2: a station at `peak_day`, exact speed."""

    def motion(jd: float) -> tuple[float, float]:
        t = jd - JD0
        return (
            peak_longitude - curvature * (t - peak_day) ** 2,
            -2.0 * curvature * (t - peak_day),
        )

    return motion


class SyntheticProvider:
    """A `PositionProvider` whose bodies follow exact motion functions. Bodies
    without a motion stand still at 0 degrees."""

    def __init__(
        self,
        motions: dict[CelestialBody, Motion] | None = None,
        mode: EphemerisMode = EphemerisMode.MOSHIER,
    ) -> None:
        self.motions = motions or {}
        self.mode = mode
        self.calls = 0

    def position(self, julian_day_ut: float, body: CelestialBody) -> BodyPosition:
        self.calls += 1
        longitude, speed = self.motions.get(body, static(0.0))(julian_day_ut)
        return BodyPosition(longitude % 360.0, speed, self.mode)


def natal(
    moon: float = 15.0,
    *,
    lagna: float | None = 100.0,
    planets: dict[CelestialBody, float] | None = None,
) -> NatalReference:
    """An exact natal reference (the Moon at `moon` degrees by default)."""
    natal_planets = {CelestialBody.MOON: moon}
    natal_planets.update(planets or {})
    return NatalReference(
        precision=BirthTimeStatus.EXACT,
        moon_longitude=moon,
        lagna_longitude=lagna,
        natal_planets=natal_planets,
    )


def config(**overrides: object) -> TransitConfiguration:
    return TransitConfiguration(**overrides)  # type: ignore[arg-type]


def days(count: float) -> dt.timedelta:
    return dt.timedelta(days=count)
