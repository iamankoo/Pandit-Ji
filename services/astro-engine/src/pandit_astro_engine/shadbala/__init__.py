"""Shadbala -- the six-fold planetary strength of BPHS Ch. 27 (Phase 9 WP-F;
`docs/ASTROLOGY_STANDARDS.md` v1.16.0, "Shadbala standards", SB-01 to SB-20).

Component-level facts for the seven planets from the Sun to Saturn under
one verse-literal profile (`SHADBALA_BPHS_SANTHANAM_27_VERSE`). Components
whose method exists only in the translator's notes, or whose verse and
notes disagree, are NOT_EVALUABLE with a reason code; consequently no
Shadbala Pinda (total) is produced, and the partial sum of the evaluated
components is labelled as partial. No strength judgment, no interpretation.

A second, separately labelled modern profile, `SHADBALA_RAMAN_GRAHA_BHAVA_BALAS`
(standards v1.21.0, SR-01 to SR-24), follows B. V. Raman's *Graha and Bhava
Balas* and does produce totals; it has its own request, service and
provenance (`RamanShadbalaService`) and is never mixed with the BPHS profile.

Method policy (v1.22.0, SM-01 to SM-12): `ShadbalaMethodService` selects
exactly one method -- `MODERN_RAMAN`, the default for user-facing Shadbala, or
`BPHS_VERSE_REFERENCE` -- and reports its version, sources, assumptions,
methodology choices, not-evaluable components and total status.
"""

from pandit_astro_engine.shadbala.constants import (
    SHADBALA_BODIES,
    SHADBALA_STANDARDS_VERSION,
    SHADBALA_SYSTEM_ID,
)
from pandit_astro_engine.shadbala.method import (
    DEFAULT_USER_FACING_METHOD,
    ShadbalaMethod,
    ShadbalaMethodRequest,
    ShadbalaMethodResult,
    ShadbalaMethodService,
)
from pandit_astro_engine.shadbala.models import (
    ComponentResult,
    ComponentStatus,
    DayNight,
    PlanetShadbala,
    RamanShadbalaFacts,
    RamanShadbalaRequest,
    SaptavargaPlacement,
    ShadbalaFacts,
    ShadbalaReason,
    ShadbalaRequest,
    ShadbalaTimePrecision,
)
from pandit_astro_engine.shadbala.profiles import PROFILE_ID, RAMAN_PROFILE_ID, Component
from pandit_astro_engine.shadbala.raman import DrekkanaReading, MoonPakshaReading
from pandit_astro_engine.shadbala.raman_service import RAMAN_STANDARDS_VERSION, RamanShadbalaService
from pandit_astro_engine.shadbala.service import LEAF_COMPONENTS, ShadbalaService

__all__ = [
    "DEFAULT_USER_FACING_METHOD",
    "LEAF_COMPONENTS",
    "PROFILE_ID",
    "RAMAN_PROFILE_ID",
    "RAMAN_STANDARDS_VERSION",
    "SHADBALA_BODIES",
    "SHADBALA_STANDARDS_VERSION",
    "SHADBALA_SYSTEM_ID",
    "Component",
    "ComponentResult",
    "ComponentStatus",
    "DayNight",
    "DrekkanaReading",
    "MoonPakshaReading",
    "PlanetShadbala",
    "RamanShadbalaFacts",
    "RamanShadbalaRequest",
    "RamanShadbalaService",
    "SaptavargaPlacement",
    "ShadbalaFacts",
    "ShadbalaMethod",
    "ShadbalaMethodRequest",
    "ShadbalaMethodResult",
    "ShadbalaMethodService",
    "ShadbalaReason",
    "ShadbalaRequest",
    "ShadbalaService",
    "ShadbalaTimePrecision",
]
