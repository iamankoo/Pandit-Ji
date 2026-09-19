"""Shared vocabulary for the Phase 6 rule engine: bodies, signs, sign
classes, and the structured result reason codes.

Everything here is a closed, language-neutral identifier set (stable IDs,
never natural-language phrases -- `docs/ASTROLOGY_STANDARDS.md` §"Language
and multilingual interaction"). The sign order and modality mirror the
Phase 5 standards (`docs/ASTROLOGY_STANDARDS.md` §"Default Vedic profile")
but are declared here so the rule engine consumes Phase 5 output without
importing `astro-engine` (facts flow one direction; no direct coupling).
"""

from __future__ import annotations

from enum import Enum


class Body(str, Enum):
    SUN = "sun"
    MOON = "moon"
    MARS = "mars"
    MERCURY = "mercury"
    JUPITER = "jupiter"
    VENUS = "venus"
    SATURN = "saturn"
    RAHU = "rahu"
    KETU = "ketu"


#: The seven classical grahas (Sun..Saturn); the nodes are handled only by
#: the explicit node policy (`docs/ASTROLOGY_STANDARDS.md` §"Node policy").
CLASSICAL_BODIES: tuple[Body, ...] = (
    Body.SUN,
    Body.MOON,
    Body.MARS,
    Body.MERCURY,
    Body.JUPITER,
    Body.VENUS,
    Body.SATURN,
)
NODES: tuple[Body, ...] = (Body.RAHU, Body.KETU)
ALL_BODIES: tuple[Body, ...] = CLASSICAL_BODIES + NODES


class Sign(str, Enum):
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


#: Zodiacal order; index 0 = Aries.
SIGN_ORDER: tuple[Sign, ...] = tuple(Sign)
SIGN_INDEX: dict[Sign, int] = {sign: index for index, sign in enumerate(SIGN_ORDER)}


class Modality(str, Enum):
    MOVABLE = "movable"
    FIXED = "fixed"
    DUAL = "dual"


SIGN_MODALITY: dict[Sign, Modality] = {
    sign: (Modality.MOVABLE, Modality.FIXED, Modality.DUAL)[index % 3]
    for index, sign in enumerate(SIGN_ORDER)
}


class Dignity(str, Enum):
    """Mirrors the Phase 5 dignity model (`docs/ASTROLOGY_STANDARDS.md`
    §"Planetary dignity standard"). Moolatrikona is a separate Phase 6
    fact, never a member of this enum."""

    EXALTED = "exalted"
    DEBILITATED = "debilitated"
    OWN_SIGN = "own_sign"
    NEUTRAL = "neutral"


class Reason(str, Enum):
    """Structured `NOT_EVALUABLE` reason codes
    (`docs/ASTROLOGY_STANDARDS.md` §"Result statuses and reason codes").
    There is deliberately no generic "unknown" member."""

    READING_AMBIGUOUS = "reading_ambiguous"
    MISSING_DEPENDENCY = "missing_dependency"
    REQUIRES_SHADBALA = "requires_shadbala"
    REQUIRES_DASHA = "requires_dasha"
    REQUIRES_PARTIAL_DRISHTI = "requires_partial_drishti"
    REQUIRES_GENDER = "requires_gender"
    REQUIRES_PARTNER_CHART = "requires_partner_chart"
    REQUIRES_MOOLATRIKONA = "requires_moolatrikona"
    NODE_PARTICIPATION_UNSPECIFIED = "node_participation_unspecified"
    VARGA_SCHEME_CONFLICT = "varga_scheme_conflict"
    TIME_BASE_UNSPECIFIED = "time_base_unspecified"
    SOURCE_PROFILE_NOT_SELECTED = "source_profile_not_selected"
    SCOPE = "scope"
    NOT_SPECIFIED_BY_SOURCE = "not_specified_by_source"
    CONDITION_ABSENT_IN_SOURCE = "condition_absent_in_source"


class Status(str, Enum):
    """Runtime result statuses. `NOT_EVALUABLE` always carries a `Reason`."""

    TRIGGERED = "TRIGGERED"
    NOT_TRIGGERED = "NOT_TRIGGERED"
    CANCELLED = "CANCELLED"
    PARTIALLY_CANCELLED = "PARTIALLY_CANCELLED"
    NOT_EVALUABLE = "NOT_EVALUABLE"


def sign_index(sign: Sign) -> int:
    return SIGN_INDEX[sign]


def house_from(base: Sign, target: Sign) -> int:
    """1-based house count of `target` counted forward from `base` (whole-sign)."""
    return (SIGN_INDEX[target] - SIGN_INDEX[base]) % 12 + 1
