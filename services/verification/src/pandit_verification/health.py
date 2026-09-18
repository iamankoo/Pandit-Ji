from __future__ import annotations

from pandit_contracts import HealthStatus

from pandit_verification._version import __version__


def get_health() -> HealthStatus:
    return HealthStatus(component="verification", version=__version__)
