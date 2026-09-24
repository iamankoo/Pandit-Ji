"""Western astrology facts (Phase 9 WP-D; `docs/ASTROLOGY_STANDARDS.md`
v1.14.0, "Western standards", WD-01 to WD-20).

Tropical zodiac (0 Aries at the vernal point, longitude of date), explicit
body profiles (classical seven; modern ten, the default; modern ten plus
the lunar nodes, positions only), Placidus houses (not evaluable inside the
polar circles, never substituted), the five Ptolemaic aspects with explicit
orb profiles (a Pandit Ji fixed-orb default and Lilly's per-planet moieties)
and applying/separating state from instantaneous speeds.

Kept apart from every Vedic module: its own body and sign identifiers, no
ayanamsa, and no use of graha drishti, Rashi Drishti or Partial/Degree
Drishti. Facts and provenance only; no interpretation.
"""

from pandit_astro_engine.western.constants import (
    ASPECT_ANGLE,
    WESTERN_STANDARDS_VERSION,
    WESTERN_SYSTEM_ID,
    AspectType,
    TropicalSign,
    WesternBody,
)
from pandit_astro_engine.western.models import (
    MotionState,
    NotEvaluablePair,
    ProfileIds,
    ProvenanceEntry,
    WesternAspect,
    WesternAspects,
    WesternBodyPosition,
    WesternChartFacts,
    WesternChartRequest,
    WesternHouses,
    WesternReason,
    WesternStatus,
    WesternTimePrecision,
)
from pandit_astro_engine.western.profiles import (
    ASPECTS_PTOLEMAIC_5_ID,
    BODIES_CLASSICAL_7_ID,
    BODIES_MODERN_10_ID,
    BODIES_MODERN_10_NODES_ID,
    HOUSES_PLACIDUS_ID,
    MOTION_INSTANTANEOUS_ID,
    ORB_FIXED_V1_ID,
    ORB_LILLY_MOIETY_ID,
    ZODIAC_TROPICAL_ID,
)
from pandit_astro_engine.western.service import WesternChartService

__all__ = [
    "ASPECTS_PTOLEMAIC_5_ID",
    "ASPECT_ANGLE",
    "BODIES_CLASSICAL_7_ID",
    "BODIES_MODERN_10_ID",
    "BODIES_MODERN_10_NODES_ID",
    "HOUSES_PLACIDUS_ID",
    "MOTION_INSTANTANEOUS_ID",
    "ORB_FIXED_V1_ID",
    "ORB_LILLY_MOIETY_ID",
    "WESTERN_STANDARDS_VERSION",
    "WESTERN_SYSTEM_ID",
    "ZODIAC_TROPICAL_ID",
    "AspectType",
    "MotionState",
    "NotEvaluablePair",
    "ProfileIds",
    "ProvenanceEntry",
    "TropicalSign",
    "WesternAspect",
    "WesternAspects",
    "WesternBody",
    "WesternBodyPosition",
    "WesternChartFacts",
    "WesternChartRequest",
    "WesternChartService",
    "WesternHouses",
    "WesternReason",
    "WesternStatus",
    "WesternTimePrecision",
]
