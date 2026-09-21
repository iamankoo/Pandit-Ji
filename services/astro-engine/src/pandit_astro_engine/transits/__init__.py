"""Transit / Gochar Engine -- Phase 8 (`Phases.md` Phase 8).

Deterministic transit facts and their provenance: each planet's sign, degree,
speed and retrograde state; structural relations to the natal Moon (and
optionally the Lagna); favourable-set readings kept per source; the
Phaladeepika-specific Vedha fact; sign-based contacts with natal planets;
ingress and station instants; and the Sade Sati sign-band timeline (a
MODERN_TRADITION profile).

Interpretation (good or bad verdicts, predictions, remedies, alerts) is not
implemented here: later phases consume these facts. Ashtakavarga scoring,
degree or orb contacts, Dhaiya, Ashtama Shani and degree-based Sade Sati
variants are out of scope (`docs/ASTROLOGY_STANDARDS.md` TR-01).
"""

from pandit_astro_engine.transits.calculator import calculate_transit
from pandit_astro_engine.transits.constants import (
    MAX_EVENTS,
    MAX_WINDOW_YEARS,
    SYSTEM_ID,
    TRANSIT_STANDARDS_VERSION,
)
from pandit_astro_engine.transits.models import (
    EventKind,
    NatalReference,
    SadeSatiFacts,
    TransitConfiguration,
    TransitEvent,
    TransitFacts,
    TransitReason,
    TransitRequest,
    TransitSnapshot,
    TransitStatus,
)
from pandit_astro_engine.transits.positions import (
    BodyPosition,
    PositionProvider,
    SwissPositionProvider,
)
from pandit_astro_engine.transits.service import TransitCalculationService

__all__ = [
    "MAX_EVENTS",
    "MAX_WINDOW_YEARS",
    "SYSTEM_ID",
    "TRANSIT_STANDARDS_VERSION",
    "BodyPosition",
    "EventKind",
    "NatalReference",
    "PositionProvider",
    "SadeSatiFacts",
    "SwissPositionProvider",
    "TransitCalculationService",
    "TransitConfiguration",
    "TransitEvent",
    "TransitFacts",
    "TransitReason",
    "TransitRequest",
    "TransitSnapshot",
    "TransitStatus",
    "calculate_transit",
]
