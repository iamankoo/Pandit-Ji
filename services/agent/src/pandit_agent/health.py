from __future__ import annotations

from pandit_contracts import HealthStatus

from pandit_agent._version import __version__


def get_health() -> HealthStatus:
    return HealthStatus(component="agent", version=__version__)
