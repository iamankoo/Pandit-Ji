"""astro-engine: deterministic astronomical and chart calculation engine.

Phase 3 (Repository & Engineering Foundation) scope only: package
boundary, config, and a health check. Domain logic (Swiss Ephemeris
integration, chart/dasha/transit/panchang calculation) is implemented
starting `Phases.md` Phase 4 -- see `docs/ARCHITECTURE.md` §"Astrology
Engine Architecture" and `docs/ASTROLOGY_STANDARDS.md` for the contract
this package must eventually satisfy.

This package must remain a pure library: no HTTP, no database access, no
dependency on `agent`, `rule-engine`, `knowledge`, or `verification`.
"""

from pandit_astro_engine._version import __version__
from pandit_astro_engine.health import get_health

__all__ = ["get_health", "__version__"]
