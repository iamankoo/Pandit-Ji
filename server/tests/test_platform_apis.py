"""Reports (background job), memory, notifications, voice, jobs, WebSocket, health and metrics."""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from conftest import auth, create_profile, make_container, make_settings, make_token
from fastapi.testclient import TestClient
from llm_double import GOOD, GOOD_TEXT, scripted_llm
from starlette.websockets import WebSocketDisconnect

from pandit_server import jobs
from pandit_server.main import create_app


def _app(script: list[str] | None = None, **settings: Any) -> tuple[TestClient, Any]:
    factory, _ = scripted_llm(script or [])
    container = make_container(
        make_settings(**settings), llm_factory=factory if script is not None else None
    )
    jobs.set_container(container)
    return TestClient(create_app(container.settings, container)), container


# ---- reports and jobs ---------------------------------------------------------------------------


def test_a_report_is_generated_by_a_job_and_holds_only_structure_and_verified_claims() -> None:
    client, _ = _app([GOOD])
    with client:
        pid = create_profile(client, "r")["id"]
        created = client.post(
            "/api/v1/reports",
            json={"profile_id": pid, "domains": ["CAREER", "STARTUP", "MARRIAGE"]},
            headers=auth("r"),
        )
        assert created.status_code == 202
        job = client.get(f"/api/v1/jobs/{created.json()['job_id']}", headers=auth("r")).json()
        assert job["status"] == "succeeded" and job["attempts"] == 1
        report = client.get(f"/api/v1/reports/{created.json()['id']}", headers=auth("r")).json()
    assert report["status"] == "ready"
    sections = {s["domain"]: s for s in report["content"]["sections"]}
    assert (
        sections["CAREER"]["status"] == "EVALUATED"
        and sections["CAREER"]["narration"]["state"] == "verified"
    )
    assert [c["text"] for c in sections["CAREER"]["narration"]["claims"]] == [GOOD_TEXT]
    # a not-evaluable domain is reported as such, with no narration and no generic text
    assert (
        sections["STARTUP"]["status"] == "NOT_EVALUABLE"
        and sections["STARTUP"]["narration"]["claims"] == []
    )
    # a policy-blocked domain (adulthood not confirmed) is reported as blocked
    assert (
        sections["MARRIAGE"]["status"] == "POLICY_BLOCKED"
        and sections["MARRIAGE"]["narration"]["claims"] == []
    )
    assert report["content"]["verification"]["released"] == "verified_claims_only"
    assert report["content"]["versions"]["knowledge_version"] == "KV-4da4248a7fb5589c"


def test_a_report_never_fails_because_the_model_is_unavailable() -> None:
    client, _ = _app(None)  # the default test factory raises: no model
    with client:
        pid = create_profile(client, "r")["id"]
        r = client.post(
            "/api/v1/reports", json={"profile_id": pid, "domains": ["CAREER"]}, headers=auth("r")
        )
        report = client.get(f"/api/v1/reports/{r.json()['id']}", headers=auth("r")).json()
    assert report["status"] == "ready"
    assert report["content"]["sections"][0]["narration"] == {
        "state": "unavailable",
        "reason": "llm_unavailable",
        "claims": [],
    }


def test_report_validation_and_ownership() -> None:
    client, _ = _app([GOOD])
    with client:
        pid = create_profile(client, "r")["id"]
        post = lambda body, who="r": client.post("/api/v1/reports", json=body, headers=auth(who))  # noqa: E731
        assert post({"profile_id": pid, "domains": ["NOT_A_DOMAIN"]}).status_code == 422
        assert post({"profile_id": pid, "domains": []}).status_code == 422
        assert post({"profile_id": pid, "domains": ["CAREER"]}, "intruder").status_code == 404
        ok = post({"profile_id": pid, "domains": ["CAREER"]}).json()
        for who in ("intruder",):
            assert client.get(f"/api/v1/reports/{ok['id']}", headers=auth(who)).status_code == 404
            assert client.get(f"/api/v1/jobs/{ok['job_id']}", headers=auth(who)).status_code == 404
            assert (
                client.delete(f"/api/v1/reports/{ok['id']}", headers=auth(who)).status_code == 404
            )
        assert client.delete(f"/api/v1/reports/{ok['id']}", headers=auth("r")).status_code == 204
        assert client.get("/api/v1/reports", headers=auth("intruder")).json()["items"] == []


def test_a_job_is_claimed_once_and_a_duplicate_delivery_does_nothing() -> None:
    client, container = _app([GOOD])
    with client:
        pid = create_profile(client, "r")["id"]
        r = client.post(
            "/api/v1/reports", json={"profile_id": pid, "domains": ["CAREER"]}, headers=auth("r")
        ).json()
    import uuid

    first_attempts = client.get(f"/api/v1/jobs/{r['job_id']}", headers=auth("r")).json()["attempts"]
    assert (
        jobs.execute_report_job(container, uuid.UUID(r["job_id"]), uuid.UUID(r["id"])) == "skipped"
    )
    assert (
        client.get(f"/api/v1/jobs/{r['job_id']}", headers=auth("r")).json()["attempts"]
        == first_attempts
    )


def test_a_failing_job_ends_failed_with_a_short_code_and_no_payload(monkeypatch: Any) -> None:
    client, _ = _app([GOOD])

    def boom(container: Any, report_id: Any) -> None:
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr("pandit_server.compose.reports.generate_report", boom)
    with client:
        pid = create_profile(client, "r")["id"]
        r = client.post(
            "/api/v1/reports", json={"profile_id": pid, "domains": ["CAREER"]}, headers=auth("r")
        ).json()
        job = client.get(f"/api/v1/jobs/{r['job_id']}", headers=auth("r")).json()
    assert job["status"] == "failed" and job["error_code"] == "RuntimeError"
    assert "secret" not in str(job)


def test_an_unavailable_queue_is_a_typed_503(monkeypatch: Any) -> None:
    client, _ = _app([GOOD])
    monkeypatch.setattr(
        jobs, "enqueue_report", lambda *a: (_ for _ in ()).throw(ConnectionError("down"))
    )
    with client:
        pid = create_profile(client, "r")["id"]
        r = client.post(
            "/api/v1/reports", json={"profile_id": pid, "domains": ["CAREER"]}, headers=auth("r")
        )
    assert r.status_code == 503 and r.json()["error"]["code"] == "queue_unavailable"


# ---- memory -------------------------------------------------------------------------------------


def test_memory_is_consent_gated_isolated_validated_and_retention_limited(
    client: TestClient, container
) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy import update

    from pandit_server.db.models import MemoryItem

    h, other = auth("m"), auth("m2")
    client.put("/api/v1/users/me/privacy", json={"memory_consent": True}, headers=h)
    client.put("/api/v1/users/me/privacy", json={"memory_consent": True}, headers=other)
    assert (
        client.put("/api/v1/memory/language", json={"value": {"v": "hi"}}, headers=h).status_code
        == 200
    )
    assert client.put("/api/v1/memory/bad key!", json={"value": {}}, headers=h).status_code in (
        404,
        422,
    )
    assert (
        client.put(
            "/api/v1/memory/language", json={"value": "not-an-object"}, headers=h
        ).status_code
        == 422
    )
    assert client.get("/api/v1/memory", headers=other).json()["items"] == []  # isolation
    assert client.delete("/api/v1/memory/language", headers=h).status_code == 204
    client.put("/api/v1/memory/old", json={"value": {"a": 1}}, headers=h)
    with container.db.session() as s:  # simulate retention expiry
        s.execute(
            update(MemoryItem).values(expires_at=dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc))
        )
    assert client.get("/api/v1/memory", headers=h).json()["items"] == []
    client.put("/api/v1/memory/a", json={"value": {}}, headers=h)
    assert client.delete("/api/v1/memory", headers=h).status_code == 204
    assert client.get("/api/v1/memory", headers=h).json()["items"] == []


# ---- notifications ------------------------------------------------------------------------------


def test_notifications_need_consent_future_times_and_belong_to_their_owner(
    client: TestClient,
) -> None:
    h = auth("n")
    soon = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)).isoformat()
    body = {"topic": "daily_guidance", "message": "A reminder", "scheduled_for": soon}
    assert client.post("/api/v1/notifications", json=body, headers=h).status_code == 403
    assert (
        client.put(
            "/api/v1/notifications/subscriptions", json={"channel": "push", "topic": "t"}, headers=h
        ).status_code
        == 403
    )
    assert (
        client.put(
            "/api/v1/notifications/subscriptions",
            json={"channel": "inapp", "topic": "t"},
            headers=h,
        ).status_code
        == 200
    )
    client.put("/api/v1/users/me/privacy", json={"notification_consent": True}, headers=h)
    created = client.post("/api/v1/notifications", json=body, headers=h)
    assert (
        created.status_code == 201 and created.json()["delivery"] == "not_available_until_phase_20"
    )
    past = {**body, "scheduled_for": "2001-01-01T00:00:00+00:00"}
    assert client.post("/api/v1/notifications", json=past, headers=h).status_code == 422
    assert (
        client.post(
            "/api/v1/notifications",
            json={**body, "scheduled_for": "2099-01-01T00:00:00"},
            headers=h,
        ).status_code
        == 422
    )
    nid = created.json()["id"]
    assert client.delete(f"/api/v1/notifications/{nid}", headers=auth("n2")).status_code == 404
    assert len(client.get("/api/v1/notifications", headers=h).json()["items"]) == 1
    assert client.delete(f"/api/v1/notifications/{nid}", headers=h).status_code == 204


# ---- voice --------------------------------------------------------------------------------------


def test_voice_is_a_text_foundation_with_typed_unavailable_audio() -> None:
    client, _ = _app([GOOD])
    with client:
        caps = client.get("/api/v1/voice/capabilities", headers=auth("v")).json()
        assert (
            caps["speech_to_text"]["available"] is False and caps["text_turns"]["available"] is True
        )
        sid = client.post(
            "/api/v1/voice/sessions", json={"language": "HI"}, headers=auth("v")
        ).json()["id"]
        pid = create_profile(client, "v")["id"]
        turn = client.post(
            f"/api/v1/voice/sessions/{sid}/turns",
            json={"message": "Tell me about my career", "profile_id": pid},
            headers=auth("v"),
        )
        assert turn.status_code == 200 and turn.json()["audio"]["available"] is False
        assert (
            client.post(
                f"/api/v1/voice/sessions/{sid}/turns",
                json={"message": "x", "profile_id": pid},
                headers=auth("other"),
            ).status_code
            == 404
        )
        assert client.post("/api/v1/voice/audio", headers=auth("v")).status_code == 501
        assert client.delete(f"/api/v1/voice/sessions/{sid}", headers=auth("v")).status_code == 204


# ---- WebSocket ----------------------------------------------------------------------------------


def _ws_ready(ws: Any, subject: str = "w") -> None:
    ws.send_json({"type": "auth", "token": make_token(subject)})
    assert ws.receive_json() == {"type": "ready"}


def test_websocket_requires_authentication_and_closes_with_4401() -> None:
    client, _ = _app([GOOD])
    with client:
        for first in ({"type": "auth", "token": "x" * 20}, {"type": "chat"}, {"nope": 1}):
            with pytest.raises(WebSocketDisconnect) as info:
                with client.websocket_connect("/api/v1/ws/chat") as ws:
                    ws.send_json(first)
                    ws.receive_json()
            assert info.value.code == 4401


def test_websocket_chat_streams_status_then_a_verified_result_and_isolates_users() -> None:
    client, _ = _app([GOOD, GOOD])
    with client:
        pid = create_profile(client, "w")["id"]
        with client.websocket_connect("/api/v1/ws/chat") as ws:
            _ws_ready(ws, "w")
            ws.send_json(
                {
                    "type": "chat",
                    "id": "m1",
                    "message": "Tell me about my career",
                    "profile_id": pid,
                }
            )
            assert ws.receive_json() == {"type": "status", "id": "m1", "state": "started"}
            result = ws.receive_json()
            assert result["type"] == "result" and [
                c["text"] for c in result["payload"]["claims"]
            ] == [GOOD_TEXT]
        with client.websocket_connect(
            "/api/v1/ws/chat"
        ) as ws:  # another user, someone else's profile
            _ws_ready(ws, "intruder")
            ws.send_json({"type": "chat", "id": "m2", "message": "career", "profile_id": pid})
            ws.receive_json()
            err = ws.receive_json()
            assert err["type"] == "error" and err["code"] == "not_found"


def test_websocket_validates_messages_and_rate_limits_and_rejects_foreign_origins() -> None:
    client, _ = _app([GOOD] * 5, RATE_LIMIT_EXPENSIVE=1)
    with client:
        pid = create_profile(client, "w")["id"]
        with client.websocket_connect("/api/v1/ws/chat") as ws:
            _ws_ready(ws)
            ws.send_json({"type": "chat", "id": "bad", "message": ""})
            assert ws.receive_json()["code"] == "validation_error"  # the connection stays open
            ws.send_text("not json")
            assert ws.receive_json()["code"] == "validation_error"
            ws.send_json(
                {"type": "chat", "id": "1", "message": "Tell me about my career", "profile_id": pid}
            )
            ws.receive_json()
            ws.receive_json()
            ws.send_json(
                {"type": "chat", "id": "2", "message": "Tell me about my career", "profile_id": pid}
            )
            assert ws.receive_json()["code"] == "rate_limited"
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                "/api/v1/ws/chat", headers={"origin": "https://evil.example"}
            ) as ws:
                ws.receive_json()
        with client.websocket_connect(
            "/api/v1/ws/chat", headers={"origin": "https://app.example"}
        ) as ws:
            _ws_ready(ws)


def test_websocket_oversize_frames_are_refused() -> None:
    client, _ = _app([GOOD], MAX_REQUEST_BYTES=2000)
    with client:
        with client.websocket_connect("/api/v1/ws/chat") as ws:
            _ws_ready(ws)
            ws.send_text("x" * 5000)
            with pytest.raises(WebSocketDisconnect) as info:
                ws.receive_json()
            assert info.value.code == 1009


# ---- health, readiness, metrics -----------------------------------------------------------------


def test_readiness_reflects_the_critical_dependencies(client: TestClient) -> None:
    body = client.get("/readyz").json()
    deps = {d["component"]: d["state"] for d in body["dependencies"]}
    assert deps["postgresql"] == "ok" and deps["valkey"] == "ok"
    assert {c["component"] for c in body["capabilities"]} == {"llm"}
    assert body["status"] in {"ready", "not_ready"}


def test_readiness_goes_not_ready_when_the_database_is_down(
    client: TestClient, container, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(container.db, "ping", lambda: False)
    body = client.get("/readyz").json()
    assert body["status"] == "not_ready"
    assert {d["component"]: d["state"] for d in body["dependencies"]}["postgresql"] == "unavailable"
    assert client.get("/healthz").json() == {"status": "alive"}  # liveness never depends on it


def test_metrics_are_token_protected_and_hold_no_personal_data(container) -> None:  # type: ignore[no-untyped-def]
    container.settings.metrics_token = "tok-123456"
    with TestClient(create_app(container.settings, container)) as client:
        create_profile(client, "metuser-secret")
        assert client.get("/metrics").status_code == 404
        text = client.get("/metrics", headers={"X-Metrics-Token": "tok-123456"}).text
    assert 'route="/birth-profiles"' in text and "http_requests_total" in text
    for forbidden in ("Delhi", "1990-06-15", "metuser-secret", "Bearer"):
        assert forbidden not in text


def test_security_headers_request_id_and_cors(client: TestClient) -> None:
    r = client.get("/healthz", headers={"Origin": "https://app.example"})
    assert (
        r.headers["X-Content-Type-Options"] == "nosniff"
        and r.headers["Cache-Control"] == "no-store"
    )
    assert r.headers["access-control-allow-origin"] == "https://app.example"
    foreign = client.get("/healthz", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in foreign.headers
    assert (
        client.get("/healthz", headers={"X-Request-ID": "abc-123"}).headers["X-Request-ID"]
        == "abc-123"
    )


def test_internal_errors_never_leak_details(container) -> None:  # type: ignore[no-untyped-def]
    app = create_app(container.settings, container)

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("password=hunter2 select * from users")

    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.get("/boom")
    assert r.status_code == 500 and r.json()["error"]["code"] == "internal_error"
    assert "hunter2" not in r.text and "select" not in r.text


def test_public_endpoints_are_rate_limited_per_ip() -> None:
    client, _ = _app(None, RATE_LIMIT_ANONYMOUS=3)
    with client:
        codes = [client.get("/api/v1/auth/config").status_code for _ in range(6)]
    assert codes[:3] == [200, 200, 200] and 429 in codes[3:]
    limited = client.get("/api/v1/auth/config")
    assert limited.status_code == 429 and "Retry-After" in limited.headers


def test_rate_limit_headers_and_independent_users(container) -> None:  # type: ignore[no-untyped-def]
    container.settings.rate_limit_default = 2
    container.limiter = type(container.limiter)(container.store, 60)
    with TestClient(create_app(container.settings, container)) as client:
        first = client.get("/api/v1/users/me", headers=auth("rl1"))
        assert (
            first.headers["X-RateLimit-Limit"] == "2"
            and first.headers["X-RateLimit-Remaining"] == "1"
        )
        client.get("/api/v1/users/me", headers=auth("rl1"))
        assert client.get("/api/v1/users/me", headers=auth("rl1")).status_code == 429
        assert (
            client.get("/api/v1/users/me", headers=auth("rl2")).status_code == 200
        )  # other user unaffected
