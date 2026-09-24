"""Swiss Ephemeris adapter -- the one place this codebase touches `swisseph`.

Phase 4 prompt §38: "Do not scatter direct Swiss Ephemeris calls throughout
the codebase... Raw astronomical retrieval belongs in the adapter. Derived
Phase 4 calculations [combustion, retrograde interpretation] should be
explicit [elsewhere]." This module returns raw ephemeris output plus which
mode actually produced it (never a silent Moshier fallback -- see
`EphemerisMode`); it does not decide what "combust" or "retrograde" means.

Licensing (LEGAL_REGULATIONS.md, services/astro-engine/README.md
"Ephemeris data"): Swiss Ephemeris data files themselves are licensed the
same way as the software (locked: Professional License for production
distribution, not yet purchased). This adapter never bundles or commits
those files; it only reads a configured path if one is provided, and
otherwise uses Swiss Ephemeris's own built-in Moshier analytical mode,
explicitly flagged in every result.
"""

from __future__ import annotations

import swisseph as swe

from pandit_astro_engine.errors import (
    EphemerisCalculationError,
    EphemerisDataUnavailableError,
    HouseSystemUnavailableError,
)
from pandit_astro_engine.models import Ayanamsa, EphemerisMode

_AYANAMSA_TO_SWE = {
    Ayanamsa.LAHIRI: swe.SIDM_LAHIRI,
}

SWE_BODY_ID = {
    "sun": swe.SUN,
    "moon": swe.MOON,
    "mars": swe.MARS,
    "mercury": swe.MERCURY,
    "jupiter": swe.JUPITER,
    "venus": swe.VENUS,
    "saturn": swe.SATURN,
}

#: Swiss Ephemeris body IDs for the lunar node conventions (keyed by the
#: `NodeConvention` value). Public so that consumers (Phase 8 transit position
#: provider) never need their own `swisseph` import.
SWE_NODE_ID = {
    "mean": swe.MEAN_NODE,
    "true": swe.TRUE_NODE,
}

#: Swiss Ephemeris body IDs for the modern (outer) planets used only by the
#: Western module (Phase 9 WP-D, WD-03). Kept separate from `SWE_BODY_ID` so
#: no Vedic code path can pick them up by iterating that table.
SWE_WESTERN_OUTER_BODY_ID = {
    "uranus": swe.URANUS,
    "neptune": swe.NEPTUNE,
    "pluto": swe.PLUTO,
}

_EPHE_PATH_CONFIGURED: str | None = None


def swisseph_version() -> str:
    return str(swe.version)


def configure_ephemeris_path(path: str | None) -> None:
    """Set (or clear) the Swiss Ephemeris data-file search path. Safe to
    call multiple times; idempotent for the same path."""
    global _EPHE_PATH_CONFIGURED
    if path:
        swe.set_ephe_path(path)
    else:
        swe.set_ephe_path("")
    _EPHE_PATH_CONFIGURED = path


def configured_ephemeris_path() -> str | None:
    return _EPHE_PATH_CONFIGURED


def utc_to_julian_day(
    year: int, month: int, day: int, hour: int, minute: int, second: float
) -> tuple[float, float]:
    """Returns (julian_day_et, julian_day_ut) -- Ephemeris/Terrestrial Time
    and Universal Time (UT1) respectively (Phase 4 prompt §9's required
    LOCAL CIVIL TIME / UTC / EPHEMERIS TIME distinction)."""
    jd_et, jd_ut = swe.utc_to_jd(year, month, day, hour, minute, second, swe.GREG_CAL)
    return jd_et, jd_ut


def set_sidereal_mode(ayanamsa: Ayanamsa) -> None:
    swe.set_sid_mode(_AYANAMSA_TO_SWE[ayanamsa], 0, 0)


def get_ayanamsa_degrees(julian_day_ut: float) -> float:
    return float(swe.get_ayanamsa_ut(julian_day_ut))


def _decode_ephemeris_mode(result_flags: int, *, allow_moshier_fallback: bool) -> EphemerisMode:
    if result_flags & swe.FLG_SWIEPH:
        return EphemerisMode.SWISS_EPHEMERIS_FILES
    if result_flags & swe.FLG_JPLEPH:
        return EphemerisMode.JPL
    if result_flags & swe.FLG_MOSEPH:
        if not allow_moshier_fallback:
            raise EphemerisDataUnavailableError(_EPHE_PATH_CONFIGURED)
        return EphemerisMode.MOSHIER
    # Should not happen given the flags we request, but never fabricate a mode.
    raise EphemerisCalculationError(
        f"Swiss Ephemeris returned an unrecognized mode flag: {result_flags}"
    )


class RawBodyPosition:
    __slots__ = (
        "longitude",
        "latitude",
        "distance_au",
        "speed_longitude",
        "speed_latitude",
        "speed_distance",
        "mode",
    )

    def __init__(
        self,
        longitude: float,
        latitude: float,
        distance_au: float,
        speed_longitude: float,
        speed_latitude: float,
        speed_distance: float,
        mode: EphemerisMode,
    ) -> None:
        self.longitude = longitude
        self.latitude = latitude
        self.distance_au = distance_au
        self.speed_longitude = speed_longitude
        self.speed_latitude = speed_latitude
        self.speed_distance = speed_distance
        self.mode = mode


def calculate_body(
    julian_day_ut: float,
    swe_body_id: int,
    *,
    sidereal: bool,
    allow_moshier_fallback: bool,
) -> RawBodyPosition:
    """Raw geocentric ecliptic position + speed for one body. `swe_body_id`
    is one of `SWE_BODY_ID`'s values or `swe.MEAN_NODE`/`swe.TRUE_NODE`."""
    flags = swe.FLG_SPEED
    flags |= swe.FLG_SIDEREAL if sidereal else 0
    try:
        result, result_flags = swe.calc_ut(julian_day_ut, swe_body_id, flags)
    except swe.Error as exc:  # pragma: no cover - defensive; swisseph raises rarely
        raise EphemerisCalculationError(str(exc)) from exc

    mode = _decode_ephemeris_mode(result_flags, allow_moshier_fallback=allow_moshier_fallback)
    longitude, latitude, distance, speed_lon, speed_lat, speed_dist = result
    return RawBodyPosition(
        longitude=longitude % 360.0,
        latitude=latitude,
        distance_au=distance,
        speed_longitude=speed_lon,
        speed_latitude=speed_lat,
        speed_distance=speed_dist,
        mode=mode,
    )


def rise_or_set(
    julian_day_ut_search_start: float,
    *,
    event: str,
    longitude: float,
    latitude: float,
    altitude_meters: float,
) -> tuple[bool, float | None]:
    """`event` is 'rise' or 'set'. Returns (occurred, julian_day_ut). When
    the event does not occur (circumpolar day/night), returns (False, None)
    -- never a fabricated time."""
    rsmi = swe.CALC_RISE if event == "rise" else swe.CALC_SET
    geopos = (longitude, latitude, altitude_meters)
    try:
        return_code, times = swe.rise_trans(
            julian_day_ut_search_start, swe.SUN, rsmi, geopos, 0.0, 0.0
        )
    except swe.Error as exc:  # pragma: no cover - defensive
        raise EphemerisCalculationError(str(exc)) from exc

    if return_code == -2:
        return False, None
    if return_code != 0:  # pragma: no cover - defensive
        raise EphemerisCalculationError(f"rise_trans returned unexpected code {return_code}")
    return True, times[0]


def calculate_ascendant(
    julian_day_ut: float,
    *,
    latitude: float,
    longitude: float,
    sidereal: bool,
) -> float:
    """Ascendant/Lagna longitude, degrees [0, 360) -- the one new Swiss
    Ephemeris primitive Phase 5 needs (docs/ASTROLOGY_STANDARDS.md
    "Default Vedic profile": Vedic whole-sign house baseline). Uses Swiss
    Ephemeris's Whole Sign house system (hsys=b'W') for consistency with
    that baseline; only the Ascendant point (`ascmc[0]`) is used here --
    house-by-house Bhava/Rashi mapping is computed from this single degree
    via `rashi.py`, not from `houses_ex`'s cusp array, so this adapter
    never needs to special-case a different house system."""
    flags = swe.FLG_SIDEREAL if sidereal else 0
    try:
        _cusps, ascmc = swe.houses_ex(julian_day_ut, latitude, longitude, b"W", flags)
    except swe.Error as exc:  # pragma: no cover - defensive
        raise EphemerisCalculationError(str(exc)) from exc
    return float(ascmc[0]) % 360.0


def true_obliquity_degrees(julian_day_ut: float) -> float:
    """True obliquity of the ecliptic of date, degrees (Swiss Ephemeris
    `SE_ECL_NUT`, first element). Used by the Western module's polar-circle
    check for Placidus (Phase 9 WP-D, WD-07)."""
    try:
        result, _flags = swe.calc_ut(julian_day_ut, swe.ECL_NUT, 0)
    except swe.Error as exc:  # pragma: no cover - defensive
        raise EphemerisCalculationError(str(exc)) from exc
    return float(result[0])


class RawHouses:
    __slots__ = ("cusps", "ascendant", "midheaven", "armc")

    def __init__(
        self, cusps: tuple[float, ...], ascendant: float, midheaven: float, armc: float
    ) -> None:
        self.cusps = cusps
        self.ascendant = ascendant
        self.midheaven = midheaven
        self.armc = armc


def calculate_placidus_houses(
    julian_day_ut: float, *, latitude: float, longitude: float
) -> RawHouses:
    """Tropical Placidus cusps 1-12, Ascendant, MC and ARMC (Phase 9 WP-D,
    WD-06/WD-07). Swiss Ephemeris cannot compute Placidus inside the polar
    circles (or when its iteration does not converge) and then substitutes
    Porphyry cusps; pyswisseph surfaces that as an error. This adapter raises
    `HouseSystemUnavailableError` with Swiss Ephemeris's own message instead
    of ever returning the substitute cusps."""
    try:
        cusps, ascmc = swe.houses_ex(julian_day_ut, latitude, longitude, b"P", 0)
    except swe.Error as exc:
        raise HouseSystemUnavailableError(str(exc)) from exc
    if len(cusps) != 12:  # pragma: no cover - defensive
        raise EphemerisCalculationError(f"expected 12 house cusps, got {len(cusps)}")
    return RawHouses(
        cusps=tuple(float(c) % 360.0 for c in cusps),
        ascendant=float(ascmc[0]) % 360.0,
        midheaven=float(ascmc[1]) % 360.0,
        armc=float(ascmc[2]) % 360.0,
    )


def julian_day_to_utc_datetime_parts(julian_day_ut: float) -> tuple[int, int, int, int, int, float]:
    """Returns (year, month, day, hour, minute, second) in UTC."""
    year, month, day, hour_float = swe.revjul(julian_day_ut, swe.GREG_CAL)
    hour = int(hour_float)
    minute_float = (hour_float - hour) * 60
    minute = int(minute_float)
    second = (minute_float - minute) * 60
    return year, month, day, hour, minute, second
