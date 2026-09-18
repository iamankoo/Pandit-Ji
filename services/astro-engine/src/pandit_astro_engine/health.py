"""Health check for astro-engine.

A library service has no external dependency of its own to probe yet (no
DB, no network) -- this simply confirms the package imports and reports
its version, which is enough for `server/`'s readiness check to include it.
"""

from __future__ import annotations

from pandit_contracts import HealthStatus

from pandit_astro_engine._version import __version__


def get_health() -> HealthStatus:
    return HealthStatus(component="astro-engine", version=__version__)
