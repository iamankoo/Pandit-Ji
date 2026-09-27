"""Compatibility constants shared by both matching profiles (Phase 11;
`docs/ASTROLOGY_STANDARDS.md` v1.25.0, CM-01 to CM-12, AK-01 to AK-16,
TP-01 to TP-14; sources in `research/ASTROLOGY_SOURCES.md` Group 24).

Two systems, never merged: the North Indian eight-kuta Ashtakoot of
Muhurta Chintamani (Vivaha Prakarana v. 21-37) and the South Indian ten
poruthams of Kalaprakasika Ch. XIII. The ten poruthams are not a spelling
variant of the Ashtakoot. "Tara Kuta" here is a matching factor and is not
the Phase 10 Muhurta Tara Bala; "Nadi Kuta" is a matching factor and is not
the deferred Phase 9 Nadi Astrology.
"""

from __future__ import annotations

from enum import Enum
from types import MappingProxyType
from typing import Final

COMPATIBILITY_STANDARDS_VERSION: Final = "1.25.0"

#: Product policy (CM-04): marriage matching is not produced for anyone
#: under 18 on the caller-supplied date. 18 is the age below which the DPDP
#: Act 2023 treats a person as a child; it is a Pandit Ji policy value.
MINIMUM_AGE_YEARS: Final = 18


class CompatibilitySystem(str, Enum):
    NORTH_INDIAN_ASHTAKOOT = "NORTH_INDIAN_ASHTAKOOT"
    SOUTH_INDIAN_TEN_PORUTHAM = "SOUTH_INDIAN_TEN_PORUTHAM"


class CompatibilityProfileId(str, Enum):
    ASHTAKOOT_MUHURTA_CHINTAMANI = "ASHTAKOOT_MUHURTA_CHINTAMANI_VIVAHA_21_37_V1"
    TEN_PORUTHAM_KALAPRAKASIKA = "TEN_PORUTHAM_KALAPRAKASIKA_IYER_1917_XIII_V1"


PROFILE_SYSTEM: Final = MappingProxyType(
    {
        CompatibilityProfileId.ASHTAKOOT_MUHURTA_CHINTAMANI: (
            CompatibilitySystem.NORTH_INDIAN_ASHTAKOOT
        ),
        CompatibilityProfileId.TEN_PORUTHAM_KALAPRAKASIKA: (
            CompatibilitySystem.SOUTH_INDIAN_TEN_PORUTHAM
        ),
    }
)

METHODOLOGY_VERSION: Final = MappingProxyType(
    {
        CompatibilityProfileId.ASHTAKOOT_MUHURTA_CHINTAMANI: "1.0.0",
        CompatibilityProfileId.TEN_PORUTHAM_KALAPRAKASIKA: "1.0.0",
    }
)


class Participant(str, Enum):
    """Neutral labels. No role (bride or groom), gender or relationship is
    collected, inferred or assumed (CM-02)."""

    A = "A"
    B = "B"


class MatchStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    NOT_EVALUABLE = "not_evaluable"
    BLOCKED_BY_POLICY = "blocked_by_policy"
    INVALID_INPUT = "invalid_input"
    INTERNAL_ERROR = "internal_error"


class MatchReason(str, Enum):
    PARTICIPANT_UNDER_MINIMUM_AGE = "participant_under_minimum_age"
    AGE_NOT_VERIFIABLE = "age_not_verifiable"
    INVALID_BIRTH_DATE = "invalid_birth_date"
    INVALID_TIMEZONE = "invalid_timezone"
    AMBIGUOUS_LOCAL_TIME = "ambiguous_local_time"
    NONEXISTENT_LOCAL_TIME = "nonexistent_local_time"
    EPHEMERIS_UNAVAILABLE = "ephemeris_unavailable"
    SIDEREAL_ZODIAC_REQUIRED = "sidereal_zodiac_required"
    NO_FACTOR_EVALUABLE = "no_factor_evaluable"
    INTERNAL_ERROR = "internal_error"


class FactorStatus(str, Enum):
    EVALUATED = "evaluated"
    NOT_EVALUABLE = "not_evaluable"
    DEFERRED = "deferred"


class FactorReason(str, Enum):
    #: The source counts or judges from one named partner (bride or groom)
    #: and the result differs with the assignment; no role is collected.
    ROLE_REQUIRED_NOT_COLLECTED = "role_required_not_collected"
    MOON_POSITION_UNCERTAIN = "moon_position_uncertain"
    BIRTH_TIME_NOT_EVALUABLE = "birth_time_not_evaluable"
    READING_AMBIGUOUS = "reading_ambiguous"
    SOURCE_TABLE_ASYMMETRIC = "source_table_asymmetric"
    SOURCE_TABLE_INCOMPLETE = "source_table_incomplete"
    RELATION_NOT_SPECIFIED_BY_SOURCE = "relation_not_specified_by_source"
    NOT_SPECIFIED_BY_SOURCE = "not_specified_by_source"
    CANCELLATION_SCHEME_DISPUTED = "cancellation_scheme_disputed"
    FACTOR_NOT_EVALUABLE = "factor_not_evaluable"


class Classification(str, Enum):
    """Ten-porutham outcomes as the source states them (no scoring exists
    in Kalaprakasika Ch. XIII)."""

    AGREEMENT = "agreement"
    DISAGREEMENT = "disagreement"
    NEUTRAL = "neutral"


class DoshaState(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    NOT_EVALUABLE = "not_evaluable"
