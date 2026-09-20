"""Vimshottari constants -- the single authoritative sequence and years
(docs/ASTROLOGY_STANDARDS.md "Vimshottari Dasha").

The lord sequence is *derived* from the Phase 5 Nakshatra-lord table
(`nakshatra.NAKSHATRA_LORD`) rather than restated, so the two can never
drift apart. Only the year values live here.
"""

from __future__ import annotations

from enum import Enum

from pandit_astro_engine.models import CelestialBody
from pandit_astro_engine.nakshatra import NAKSHATRA_LORD, NAKSHATRA_ORDER

SYSTEM_ID = "vimshottari"

#: Standards version under which Phase 7 results are produced
#: (docs/ASTROLOGY_STANDARDS.md v1.5.0, Phase 7 methodology lock).
DASHA_STANDARDS_VERSION = "1.5.0"

#: Pandit Ji engineering convention (not a classical source statement).
BOUNDARY_CONVENTION = "half_open_start_inclusive_end_exclusive"
TIME_BASE = "utc"

#: The nine lords, in dasha order, starting from Ketu.
VIMSHOTTARI_SEQUENCE: tuple[CelestialBody, ...] = tuple(
    NAKSHATRA_LORD[nakshatra] for nakshatra in NAKSHATRA_ORDER[:9]
)

#: Full Mahadasha years per lord (BPHS Ch. 46 v. 15 and Phaladeepika XIX sl. 2,
#: translation level; see research/ASTROLOGY_SOURCES.md).
VIMSHOTTARI_YEARS: dict[CelestialBody, int] = {
    CelestialBody.KETU: 7,
    CelestialBody.VENUS: 20,
    CelestialBody.SUN: 6,
    CelestialBody.MOON: 10,
    CelestialBody.MARS: 7,
    CelestialBody.RAHU: 18,
    CelestialBody.JUPITER: 16,
    CelestialBody.SATURN: 19,
    CelestialBody.MERCURY: 17,
}

VIMSHOTTARI_TOTAL_YEARS = 120


class DashaLevel(str, Enum):
    MAHADASHA = "mahadasha"
    ANTARDASHA = "antardasha"
    PRATYANTAR = "pratyantar"


#: Hierarchy depth -> levels generated. Sookshma and Prana are out of scope.
LEVEL_ORDER: tuple[DashaLevel, ...] = (
    DashaLevel.MAHADASHA,
    DashaLevel.ANTARDASHA,
    DashaLevel.PRATYANTAR,
)
MAX_DEPTH = len(LEVEL_ORDER)

#: Identifier prefix per level, used in stable period IDs.
LEVEL_ID_PREFIX: dict[DashaLevel, str] = {
    DashaLevel.MAHADASHA: "m",
    DashaLevel.ANTARDASHA: "a",
    DashaLevel.PRATYANTAR: "p",
}


def _validate_constants() -> None:
    if len(VIMSHOTTARI_SEQUENCE) != 9 or len(set(VIMSHOTTARI_SEQUENCE)) != 9:
        raise RuntimeError("Vimshottari sequence must contain nine distinct lords")
    if set(VIMSHOTTARI_SEQUENCE) != set(VIMSHOTTARI_YEARS):
        raise RuntimeError("Vimshottari years must cover exactly the nine sequence lords")
    if sum(VIMSHOTTARI_YEARS.values()) != VIMSHOTTARI_TOTAL_YEARS:
        raise RuntimeError("Vimshottari years must total 120")


_validate_constants()
