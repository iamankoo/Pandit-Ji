from __future__ import annotations

from pandit_contracts import HealthStatus

from pandit_knowledge._version import __version__


def get_health() -> HealthStatus:
    return HealthStatus(component="knowledge", version=__version__)
