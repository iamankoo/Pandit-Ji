from __future__ import annotations

from pandit_contracts import HealthStatus

from pandit_rule_engine._version import __version__


def get_health() -> HealthStatus:
    return HealthStatus(component="rule-engine", version=__version__)
