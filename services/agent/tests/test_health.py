from pandit_contracts.health import HealthState

from pandit_agent import get_health


def test_health_reports_ok() -> None:
    health = get_health()
    assert health.component == "agent"
    assert health.state == HealthState.OK
    assert health.version


def test_voice_and_reports_subpackages_import() -> None:
    import pandit_agent.reports  # noqa: F401
    import pandit_agent.voice  # noqa: F401
