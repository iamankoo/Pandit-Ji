"""Pandit Ji shared contracts.

Phase 3 (Repository & Engineering Foundation) establishes only the package
boundary and the `HealthStatus` contract shared by `server/` and every
`services/*` component's health check.

The Astrology Service Interfaces (`ChartRequest`/`ChartResponse`,
`DashaRequest`/`DashaResponse`, etc. -- see `docs/ARCHITECTURE.md` "Astrology
Service Interfaces") are domain contracts and are added starting with the
phase that implements the corresponding engine (Phases.md Phase 4 onward),
not speculatively defined here.
"""

from pandit_contracts.health import HealthStatus

__all__ = ["HealthStatus"]

__version__ = "0.1.0"
