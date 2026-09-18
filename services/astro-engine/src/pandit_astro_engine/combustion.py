"""Combustion (Asta) -- a derived astrological status layered over raw
ephemeris longitudes, per docs/ASTROLOGY_STANDARDS.md "Combustion standard"
(Brihat Parashara Hora Shastra tradition, locked per explicit project-owner
decision during Phase 4). Deliberately separate from `ephemeris.py`: this
module contains no Swiss Ephemeris calls, only pure arithmetic over
longitudes already computed elsewhere -- see Phase 4 prompt §39.
"""

from __future__ import annotations

from pandit_astro_engine.models import CelestialBody, CombustionStatus

STANDARD_NAME = "brihat_parashara_hora_shastra_v1"

# Degrees of separation from the Sun within which a planet is combust.
# (direct_threshold, retrograde_threshold_or_None)
_THRESHOLDS: dict[CelestialBody, tuple[float, float | None]] = {
    CelestialBody.MOON: (12.0, None),
    CelestialBody.MARS: (17.0, None),
    CelestialBody.MERCURY: (14.0, 12.0),
    CelestialBody.JUPITER: (11.0, None),
    CelestialBody.VENUS: (10.0, 8.0),
    CelestialBody.SATURN: (15.0, None),
}


def angular_separation_degrees(longitude_a: float, longitude_b: float) -> float:
    """Shortest angular distance between two longitudes, in [0, 180]."""
    diff = abs(longitude_a - longitude_b) % 360.0
    return diff if diff <= 180.0 else 360.0 - diff


def evaluate_combustion(
    body: CelestialBody,
    body_longitude: float,
    sun_longitude: float,
    *,
    is_retrograde: bool,
) -> CombustionStatus | None:
    """Returns None for bodies this standard does not evaluate (Sun,
    Rahu, Ketu) -- not an error, just out of scope for combustion."""
    thresholds = _THRESHOLDS.get(body)
    if thresholds is None:
        return None

    direct_threshold, retrograde_threshold = thresholds
    if is_retrograde and retrograde_threshold is not None:
        threshold = retrograde_threshold
    else:
        threshold = direct_threshold

    separation = angular_separation_degrees(body_longitude, sun_longitude)
    return CombustionStatus(
        is_combust=separation <= threshold,
        angular_separation_degrees=separation,
        threshold_degrees=threshold,
        standard=STANDARD_NAME,
    )
