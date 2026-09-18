"""astro-engine: deterministic astronomical and chart calculation engine.

Phase 4 (Astronomical Calculation Engine) scope: Swiss Ephemeris-backed
planetary positions (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn,
Rahu, Ketu), retrograde, combustion, sunrise/sunset, and deterministic
timezone conversion -- see `docs/ARCHITECTURE.md` §"Astrology Engine
Architecture" and `docs/ASTROLOGY_STANDARDS.md` for the standards this
package implements.

Chart/Kundli domain concepts (houses, ascendant, nakshatra/pada
assignment, divisional charts, dignity, lords) are Phase 5 and
deliberately not implemented here.

This package remains a pure library: no HTTP, no database access, no
dependency on `agent`, `rule-engine`, `knowledge`, or `verification`.
"""

from pandit_astro_engine._version import __version__
from pandit_astro_engine.health import get_health
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
]
