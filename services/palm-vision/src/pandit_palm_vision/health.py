from __future__ import annotations

from pandit_contracts import HealthStatus

from pandit_palm_vision._version import __version__


def get_health() -> HealthStatus:
    return HealthStatus(component="palm-vision", version=__version__)
