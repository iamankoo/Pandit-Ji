from fastapi.testclient import TestClient

from pandit_server.main import create_app

client = TestClient(create_app())


def test_liveness_ok() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_reports_shape_even_when_dependencies_are_down() -> None:
    # No real Postgres/Valkey in the unit-test environment: readiness must
    # degrade gracefully (never raise) and still report the expected shape.
    response = client.get("/readyz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ready", "not_ready"}
    assert {d["component"] for d in body["dependencies"]} == {"postgresql", "valkey"}
    assert {s["component"] for s in body["services"]} == {
        "astro-engine",
        "rule-engine",
        "agent",
        "knowledge",
        "verification",
    }


def test_request_id_is_echoed() -> None:
    response = client.get("/healthz", headers={"X-Request-ID": "test-request-id"})
    assert response.headers["X-Request-ID"] == "test-request-id"


def test_request_id_is_generated_when_absent() -> None:
    response = client.get("/healthz")
    assert response.headers["X-Request-ID"]


def test_unknown_route_returns_structured_404() -> None:
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_404"
