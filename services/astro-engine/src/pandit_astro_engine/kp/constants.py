"""Stable identifiers and constants for the KP (Krishnamurti Paddhati)
module (Phase 9 WP-E; `docs/ASTROLOGY_STANDARDS.md` v1.15.0, KP-01 to KP-16).

The star and sub division reuses the locked Vimshottari lord cycle and years
(`nakshatra.NAKSHATRA_LORD`, `dashas.constants.VIMSHOTTARI_YEARS`): KP
Reader III states that each constellation is divided among the nine lords
"in the proportion in which they are allotted the total number of years in
Vimshothari dasa system", so the proportions are the same data, not a copy.
"""

from __future__ import annotations

from enum import Enum

#: Standards version recorded on every KP result (KP-15).
KP_STANDARDS_VERSION = "1.15.0"

#: System tag recorded on every KP result. Never "vedic" or "western".
KP_SYSTEM_ID = "kp_krishnamurti_paddhati"

#: Exact spans in arcseconds (a nakshatra is 13 degrees 20 minutes).
ARCSEC_PER_DEGREE = 3600
SIGN_ARCSEC = 30 * ARCSEC_PER_DEGREE
NAKSHATRA_ARCSEC = 48_000
ZODIAC_ARCSEC = 360 * ARCSEC_PER_DEGREE

#: A longitude within this many degrees of a star, sub or sub-sub boundary is
#: flagged `near_boundary` (a numeric epsilon, about 0.0036 arcseconds, the
#: same value as the Phase 5 Nakshatra flag; not an astrological judgment).
BOUNDARY_EPSILON_DEGREES = 1e-6

#: Number of entries in the KP sign-star-sub table (KP Reader III: 243 subs,
#: plus 6 subs split by a sign boundary).
KP_TABLE_SIZE = 249


class KpTimePrecision(str, Enum):
    """EXACT: the birth time is known. UNKNOWN: only the date is known; every
    time-sensitive KP fact (cusps, star and sub lords, significators) is
    not evaluated (KP-12)."""

    EXACT = "exact"
    UNKNOWN = "unknown"


class KpStatus(str, Enum):
    SUCCESS = "success"
    NOT_EVALUABLE = "not_evaluable"


class KpReason(str, Enum):
    BIRTH_TIME_UNKNOWN = "birth_time_unknown"
    PLACIDUS_POLAR_CIRCLE = "placidus_polar_circle"
    PLACIDUS_NOT_COMPUTABLE = "placidus_not_computable"
    HORARY_ASCENDANT_NOT_SOLVABLE = "horary_ascendant_not_solvable"
    SUNRISE_UNAVAILABLE = "sunrise_unavailable"
    NODE_RETROGRESSION_UNRESOLVED = "node_retrogression_unresolved"


class DayLordConvention(str, Enum):
    """How the weekday of a Ruling Planets moment is fixed (KP-10). KP
    Reader VI names "the name of the day" without saying where a day
    begins, so there is no default."""

    LOCAL_CIVIL_DATE = "local_civil_date"
    SUNRISE_TO_SUNRISE = "sunrise_to_sunrise"
