"""Numerology (Phase 11; `docs/ASTROLOGY_STANDARDS.md` v1.25.0, NU-01 to NU-16).

Two separate, never-mixed profiles: `NUMEROLOGY_CHALDEAN_CHEIRO_1926_V1`
(the default: Cheiro, *Book of Numbers*) and
`NUMEROLOGY_PYTHAGOREAN_BALLIETT_1908_V1` (L. Dow Balliett, *The Philosophy
of Numbers*). Moolank, the Phase 1 Bhagyank, each profile's own date
numbers, the name number from an explicitly supplied Latin spelling (no
transliteration), Cheiro's associated ("lucky") numbers, and references to
where the source interprets a number. Interpretation text is deferred to
the knowledge phase. Numerology is recorded as a modern tradition.
"""

from pandit_astro_engine.numerology.calculator import (
    calculate_numerology,
    normalize_latin_name,
    reduce_number,
)
from pandit_astro_engine.numerology.constants import (
    BALLIETT_LETTER_VALUES,
    CHEIRO_LETTER_VALUES,
    DEFAULT_PROFILE,
    NUMEROLOGY_STANDARDS_VERSION,
    ItemReason,
    ItemStatus,
    MasterNumberPolicy,
    NumerologyProfileId,
    NumerologySystem,
)
from pandit_astro_engine.numerology.models import (
    AssociatedNumbers,
    NameInput,
    NameNumber,
    NumberItem,
    NumerologyFacts,
    NumerologyRequest,
    Reduction,
)

__all__ = [
    "BALLIETT_LETTER_VALUES",
    "CHEIRO_LETTER_VALUES",
    "DEFAULT_PROFILE",
    "NUMEROLOGY_STANDARDS_VERSION",
    "AssociatedNumbers",
    "ItemReason",
    "ItemStatus",
    "MasterNumberPolicy",
    "NameInput",
    "NameNumber",
    "NumberItem",
    "NumerologyFacts",
    "NumerologyProfileId",
    "NumerologyRequest",
    "NumerologySystem",
    "Reduction",
    "calculate_numerology",
    "normalize_latin_name",
    "reduce_number",
]
