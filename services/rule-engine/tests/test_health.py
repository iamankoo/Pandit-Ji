from pandit_contracts.health import HealthState

from pandit_rule_engine import get_health


def test_health_reports_ok() -> None:
    health = get_health()
    assert health.component == "rule-engine"
    assert health.state == HealthState.OK
    assert health.version
