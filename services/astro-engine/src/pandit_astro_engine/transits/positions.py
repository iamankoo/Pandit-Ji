"""Position sources and time conversion for the transit engine (Phase 8).

The calculators are pure functions of a `PositionProvider`, so tests can drive
them with exact synthetic motion. The Swiss-backed provider goes through the
Phase 4 ephemeris adapter (`ephemeris.py`); nothing here imports Swiss
Ephemeris.

Time: an aware UTC instant is converted to Julian Day UT with the same Phase 4
function that the natal calculation used (`ephemeris.utc_to_julian_day`), so
transit and natal share one time scale. The inverse is solved by correction
against that forward function, so the round trip agrees to about a
microsecond. The sub-second UT1-UTC difference is not modelled (as in Phase 4).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Protocol

from pandit_astro_engine import ephemeris
from pandit_astro_engine.models import CalculationConfig, CelestialBody, EphemerisMode, ZodiacType

UTC = dt.timezone.utc
_J2000_JD = 2_451_545.0
_J2000_UTC = dt.datetime(2000, 1, 1, 12, 0, 0, tzinfo=UTC)


@dataclass(frozen=True)
class BodyPosition:
    longitude: float  # sidereal degrees, [0, 360)
    speed_longitude: float  # degrees per day, sign preserved
    ephemeris_mode: EphemerisMode

    @property
    def retrograde(self) -> bool:
        """Speed-sign semantics, identical to Phase 4 (`speed < 0`)."""
        return self.speed_longitude < 0.0


class PositionProvider(Protocol):
    def position(self, julian_day_ut: float, body: CelestialBody) -> BodyPosition: ...


class SwissPositionProvider:
    """Geocentric sidereal positions through the Phase 4 adapter."""

    def __init__(self, config: CalculationConfig) -> None:
        if config.zodiac != ZodiacType.SIDEREAL or config.ayanamsa is None:
            raise ValueError("the transit engine requires the sidereal zodiac")
        self._config = config

    def position(self, julian_day_ut: float, body: CelestialBody) -> BodyPosition:
        config = self._config
        assert config.ayanamsa is not None
        # The sidereal mode is process-global state; set it on every call so
        # another service cannot change it under us.
        ephemeris.set_sidereal_mode(config.ayanamsa)
        if body in (CelestialBody.RAHU, CelestialBody.KETU):
            raw = ephemeris.calculate_body(
                julian_day_ut,
                ephemeris.SWE_NODE_ID[config.node_convention.value],
                sidereal=True,
                allow_moshier_fallback=config.allow_moshier_fallback,
            )
            longitude = raw.longitude
            if body == CelestialBody.KETU:
                longitude = (longitude + 180.0) % 360.0
            return BodyPosition(longitude, raw.speed_longitude, raw.mode)
        raw = ephemeris.calculate_body(
            julian_day_ut,
            ephemeris.SWE_BODY_ID[body.value],
            sidereal=True,
            allow_moshier_fallback=config.allow_moshier_fallback,
        )
        return BodyPosition(raw.longitude, raw.speed_longitude, raw.mode)


def datetime_to_jd(instant: dt.datetime) -> float:
    """Julian Day UT of an aware datetime (Phase 4 conversion)."""
    utc = instant.astimezone(UTC)
    second = utc.second + utc.microsecond / 1_000_000.0
    _, jd_ut = ephemeris.utc_to_julian_day(
        utc.year, utc.month, utc.day, utc.hour, utc.minute, second
    )
    return float(jd_ut)


def jd_to_datetime(julian_day_ut: float) -> dt.datetime:
    """Inverse of `datetime_to_jd`, to about a microsecond (two corrections)."""
    guess = _J2000_UTC + dt.timedelta(days=julian_day_ut - _J2000_JD)
    for _ in range(2):
        error_days = julian_day_ut - datetime_to_jd(guess)
        guess = guess + dt.timedelta(days=error_days)
    return guess
