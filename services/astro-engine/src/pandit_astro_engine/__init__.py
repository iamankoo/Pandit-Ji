"""astro-engine: deterministic astronomical and chart calculation engine.

Phase 4 (Astronomical Calculation Engine): Swiss Ephemeris-backed
planetary positions (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn,
Rahu, Ketu), retrograde, combustion, sunrise/sunset, and deterministic
timezone conversion.

Phase 5 (Birth Chart / Kundli Engine): Ascendant/Lagna, whole-sign
houses/Bhavas, Rashi placement, Nakshatra/Pada, house lords, planetary
aspects (graha drishti), planetary dignity, and the full locked
Shodashvarga set of divisional charts (D1, D2, D3, D4, D7, D9, D10, D12,
D16, D20, D24, D27, D30, D40, D45, D60) plus the Chandra (Moon) chart --
see `docs/ARCHITECTURE.md` §"Astrology Engine Architecture" and
`docs/ASTROLOGY_STANDARDS.md` for the standards this package implements.

Dasha, Transit, Yoga/Dosha rule evaluation, interpretation/narration, and
any AI/LLM involvement remain out of scope here and belong to later
phases and other services (`rule-engine`, `agent`, `knowledge`) -- see
each phase's boundary section in `Phases.md`.

This package remains a pure library: no HTTP, no database access, no
dependency on `agent`, `rule-engine`, `knowledge`, or `verification`.
"""

from pandit_astro_engine._version import __version__
from pandit_astro_engine.health import get_health
from pandit_astro_engine.kundli import KundliCalculationService
from pandit_astro_engine.kundli_models import Kundli
from pandit_astro_engine.models import (
    AstronomicalCalculationRequest,
    CalculationResult,
    CelestialBody,
)
from pandit_astro_engine.service import AstronomicalCalculationService

__all__ = [
    "get_health",
    "__version__",
    "AstronomicalCalculationService",
    "AstronomicalCalculationRequest",
    "CalculationResult",
    "CelestialBody",
    "KundliCalculationService",
    "Kundli",
]
