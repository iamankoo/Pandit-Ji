from pandit_contracts import HealthStatus
from pandit_contracts.health import HealthState


def test_health_status_defaults_to_ok() -> None:
    status = HealthStatus(component="astro-engine", version="0.1.0")
    assert status.state == HealthState.OK
    assert status.detail is None


def test_health_status_serializes() -> None:
    status = HealthStatus(component="agent", version="0.1.0", state=HealthState.DEGRADED)
    payload = status.model_dump()
    assert payload["component"] == "agent"
    assert payload["state"] == "degraded"
