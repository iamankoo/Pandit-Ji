"""Stable identifiers and constants for the Western module (Phase 9 WP-D;
`docs/ASTROLOGY_STANDARDS.md` v1.14.0, WD-01 to WD-20)."""

from __future__ import annotations

from enum import Enum

#: Standards version recorded on every Western result (WD-19).
WESTERN_STANDARDS_VERSION = "1.14.0"

#: System tag recorded on every Western result (WD-18). Never "vedic".
WESTERN_SYSTEM_ID = "western_tropical"


class WesternBody(str, Enum):
    """Western body identifiers. Deliberately a separate enum from the
    Vedic `CelestialBody` (no Rahu/Ketu names, no shared iteration), so
    adding the outer planets here cannot change any Vedic calculation."""

    SUN = "sun"
    MOON = "moon"
    MERCURY = "mercury"
    VENUS = "venus"
    MARS = "mars"
    JUPITER = "jupiter"
    SATURN = "saturn"
    URANUS = "uranus"
    NEPTUNE = "neptune"
    PLUTO = "pluto"
    NORTH_NODE = "north_node"
    SOUTH_NODE = "south_node"


class TropicalSign(str, Enum):
    """The twelve tropical signs in zodiacal order from 0 degrees Aries
    (WD-02). Separate from the Vedic `Rashi` identifiers."""

    ARIES = "aries"
    TAURUS = "taurus"
    GEMINI = "gemini"
    CANCER = "cancer"
    LEO = "leo"
    VIRGO = "virgo"
    LIBRA = "libra"
    SCORPIO = "scorpio"
    SAGITTARIUS = "sagittarius"
    CAPRICORN = "capricorn"
    AQUARIUS = "aquarius"
    PISCES = "pisces"


SIGN_ORDER: tuple[TropicalSign, ...] = tuple(TropicalSign)


class AspectType(str, Enum):
    CONJUNCTION = "conjunction"
    SEXTILE = "sextile"
    SQUARE = "square"
    TRINE = "trine"
    OPPOSITION = "opposition"


#: Exact angles of the supported aspects, degrees (WD-09).
ASPECT_ANGLE: dict[AspectType, float] = {
    AspectType.CONJUNCTION: 0.0,
    AspectType.SEXTILE: 60.0,
    AspectType.SQUARE: 90.0,
    AspectType.TRINE: 120.0,
    AspectType.OPPOSITION: 180.0,
}

NODES: tuple[WesternBody, ...] = (WesternBody.NORTH_NODE, WesternBody.SOUTH_NODE)
