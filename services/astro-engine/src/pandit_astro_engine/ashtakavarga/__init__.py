"""Ashtakavarga engine (Phase 9 WP-A1, extended by WP-A2/A3): Bhinnashtakavarga
and Sarvashtakavarga across four independent source profiles, and -- BPHS
profiles only -- Trikona/Ekadhipatya Shodhana reductions and Pinda Sadhana.
No winner is chosen among the source readings anywhere in this package.

See `docs/ASTROLOGY_STANDARDS.md` "Ashtakavarga standards" (v1.8.0, AV-01 to
AV-13) for the locked methodology this package implements.

Out of scope here (deferred, not silently dropped): Ch. 70 and 72's
interpretive effect-judgments; Ch. 71's Ashtakavarga-based longevity
(blocked under the product's Ayurdaya policy -- lifespan/death-timing
claims); any use of Ashtakavarga by Shadbala's Drik Bala or by Gochara
(Phase 8); Jaimini, Shadbala, Western, KP and every other Phase 9 work
package.
"""

from pandit_astro_engine.ashtakavarga.constants import (
    ASHTAKAVARGA_STANDARDS_VERSION,
    CROSS_TABLE_CONFLICTS,
    GRAHA_MULTIPLIER,
    LORDSHIP_PAIRS,
    MERCURY_GRAHA_MULTIPLIER_CANDIDATES,
    RASI_MULTIPLIER,
    SYSTEM_ID,
    TRIKONA_GROUPS,
    Contributor,
)
from pandit_astro_engine.ashtakavarga.models import (
    AshtakavargaFacts,
    AshtakavargaReason,
    AshtakavargaReductionFacts,
    AshtakavargaReductionRequest,
    AshtakavargaRequest,
    AshtakavargaStatus,
    ChartReduction,
    ChartResult,
    EkadhipatyaConflict,
    GrahaPindaContribution,
    GrahaPindaReason,
    GrahaPindaStatus,
    HouseMark,
    NatalPositions,
    PindaResult,
    SarvashtakavargaResult,
)
from pandit_astro_engine.ashtakavarga.profiles import (
    ALL_PROFILE_IDS,
    BPHS_GRID_ID,
    BPHS_VERSE_ID,
    BRIHAT_JATAKA_ID,
    PHALADEEPIKA_ID,
    PROFILES,
)
from pandit_astro_engine.ashtakavarga.service import AshtakavargaCalculationService

__all__ = [
    "SYSTEM_ID",
    "ASHTAKAVARGA_STANDARDS_VERSION",
    "Contributor",
    "CROSS_TABLE_CONFLICTS",
    "TRIKONA_GROUPS",
    "LORDSHIP_PAIRS",
    "RASI_MULTIPLIER",
    "GRAHA_MULTIPLIER",
    "MERCURY_GRAHA_MULTIPLIER_CANDIDATES",
    "AshtakavargaCalculationService",
    "AshtakavargaRequest",
    "AshtakavargaFacts",
    "AshtakavargaStatus",
    "AshtakavargaReason",
    "AshtakavargaReductionRequest",
    "AshtakavargaReductionFacts",
    "ChartReduction",
    "EkadhipatyaConflict",
    "PindaResult",
    "GrahaPindaContribution",
    "GrahaPindaStatus",
    "GrahaPindaReason",
    "ChartResult",
    "HouseMark",
    "NatalPositions",
    "SarvashtakavargaResult",
    "ALL_PROFILE_IDS",
    "BRIHAT_JATAKA_ID",
    "PHALADEEPIKA_ID",
    "BPHS_GRID_ID",
    "BPHS_VERSE_ID",
    "PROFILES",
]
