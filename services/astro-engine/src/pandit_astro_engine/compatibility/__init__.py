"""Compatibility (Kundli matching) facts (Phase 11; `docs/ASTROLOGY_STANDARDS.md`
v1.25.0, CM-01 to CM-12, AK-01 to AK-16, TP-01 to TP-14).

Two separate systems, never merged:

- `NORTH_INDIAN_ASHTAKOOT`, profile `ASHTAKOOT_MUHURTA_CHINTAMANI_VIVAHA_21_37_V1`:
  the eight kutas of Muhurta Chintamani's Vivaha Prakarana with the Daivajna
  Manohara points (1 to 8, 36 in all);
- `SOUTH_INDIAN_TEN_PORUTHAM`, profile `TEN_PORUTHAM_KALAPRAKASIKA_IYER_1917_XIII_V1`:
  the ten considerations of Kalaprakasika Ch. XIII, as agreement or
  disagreement (the source gives no points).

The two people are labelled A and B; no role or gender is collected, so a
factor the source judges from the bride or the groom is not evaluable unless
both assignments agree, and the 36-point total is given only when every kuta
is evaluated. Matching is refused for anyone under 18. Factor-level facts
only: no verdict and no statements of effect. "Tara Kuta" is not the Phase 10
Tara Bala; "Nadi Kuta" is not the Phase 9 Nadi Astrology.
"""

from pandit_astro_engine.compatibility.age_gate import completed_years
from pandit_astro_engine.compatibility.ashtakoot import evaluate_ashtakoot
from pandit_astro_engine.compatibility.constants import (
    COMPATIBILITY_STANDARDS_VERSION,
    MINIMUM_AGE_YEARS,
    Classification,
    CompatibilityProfileId,
    CompatibilitySystem,
    DoshaState,
    FactorReason,
    FactorStatus,
    MatchReason,
    MatchStatus,
    Participant,
)
from pandit_astro_engine.compatibility.models import (
    AshtakootTotal,
    CompatibilityFacts,
    CompatibilityRequest,
    DoshaRecord,
    FactorResult,
    MatchParticipantInput,
    MoonPlacement,
    PoruthamSummary,
)
from pandit_astro_engine.compatibility.porutham import evaluate_ten_porutham
from pandit_astro_engine.compatibility.service import CompatibilityService

__all__ = [
    "COMPATIBILITY_STANDARDS_VERSION",
    "MINIMUM_AGE_YEARS",
    "AshtakootTotal",
    "Classification",
    "CompatibilityFacts",
    "CompatibilityProfileId",
    "CompatibilityRequest",
    "CompatibilityService",
    "CompatibilitySystem",
    "DoshaRecord",
    "DoshaState",
    "FactorReason",
    "FactorResult",
    "FactorStatus",
    "MatchParticipantInput",
    "MatchReason",
    "MatchStatus",
    "MoonPlacement",
    "Participant",
    "PoruthamSummary",
    "completed_years",
    "evaluate_ashtakoot",
    "evaluate_ten_porutham",
]
