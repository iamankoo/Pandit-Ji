"""Rashi (zodiac sign) identification -- Phase 5 (Birth Chart / Kundli Engine).

docs/ASTROLOGY_STANDARDS.md "Default Vedic profile" locks the Vedic
whole-sign house baseline: every downstream Bhava/house/varga computation
in this package is built on top of "which of the 12 signs does this
sidereal longitude fall in, and how far into it" -- this module is the
single place that answers that question, so sign-boundary arithmetic is
never duplicated or subtly re-derived elsewhere.
"""

from __future__ import annotations

from enum import Enum


class Rashi(str, Enum):
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


#: Zodiacal order, index 0 = Aries .. index 11 = Pisces. This ordering is
#: the backbone of every "Nth sign from" varga/aspect/house rule.
RASHI_ORDER: tuple[Rashi, ...] = (
    Rashi.ARIES,
    Rashi.TAURUS,
    Rashi.GEMINI,
    Rashi.CANCER,
    Rashi.LEO,
    Rashi.VIRGO,
    Rashi.LIBRA,
    Rashi.SCORPIO,
    Rashi.SAGITTARIUS,
    Rashi.CAPRICORN,
    Rashi.AQUARIUS,
    Rashi.PISCES,
)

_RASHI_TO_INDEX: dict[Rashi, int] = {rashi: index for index, rashi in enumerate(RASHI_ORDER)}


class Modality(str, Enum):
    MOVABLE = "movable"
    FIXED = "fixed"
    DUAL = "dual"


#: Chara/Sthira/Dwiswabhava classification, used by several varga starting-
#: point rules (D9, D16, D20, D27, D45).
RASHI_MODALITY: dict[Rashi, Modality] = {
    Rashi.ARIES: Modality.MOVABLE,
    Rashi.CANCER: Modality.MOVABLE,
    Rashi.LIBRA: Modality.MOVABLE,
    Rashi.CAPRICORN: Modality.MOVABLE,
    Rashi.TAURUS: Modality.FIXED,
    Rashi.LEO: Modality.FIXED,
    Rashi.SCORPIO: Modality.FIXED,
    Rashi.AQUARIUS: Modality.FIXED,
    Rashi.GEMINI: Modality.DUAL,
    Rashi.VIRGO: Modality.DUAL,
    Rashi.SAGITTARIUS: Modality.DUAL,
    Rashi.PISCES: Modality.DUAL,
}


def rashi_index(rashi: Rashi) -> int:
    """Zodiacal index, 0 (Aries) .. 11 (Pisces)."""
    return _RASHI_TO_INDEX[rashi]


def rashi_from_index(index: int) -> Rashi:
    """Inverse of `rashi_index`; `index` is normalized modulo 12 first, so
    callers can pass an unwrapped running offset (e.g. `rashi_index(x) + 8`)
    without pre-computing the modulus themselves."""
    return RASHI_ORDER[index % 12]


def sign_index_from_longitude(longitude: float) -> int:
    """0 (Aries) .. 11 (Pisces) for an absolute sidereal longitude in
    [0, 360)."""
    normalized = longitude % 360.0
    return int(normalized // 30.0) % 12


def rashi_from_longitude(longitude: float) -> Rashi:
    return rashi_from_index(sign_index_from_longitude(longitude))


def degree_within_sign(longitude: float) -> float:
    """0.0 (inclusive) .. 30.0 (exclusive), the planet's position within its
    own sign -- this is the value every varga division formula operates on."""
    normalized = longitude % 360.0
    return normalized - (int(normalized // 30.0) * 30.0)


def offset_sign(rashi: Rashi, houses_forward: int) -> Rashi:
    """The sign reached by counting `houses_forward` signs forward from
    `rashi`, counting `rashi` itself as 1 (so `offset_sign(x, 1) == x`,
    `offset_sign(x, 5)` is "the 5th sign from x", etc.) -- this is the
    counting convention every "Nth sign from" rule in
    docs/ASTROLOGY_STANDARDS.md uses (Vargas, aspects, and lordship alike)."""
    return rashi_from_index(rashi_index(rashi) + (houses_forward - 1))
