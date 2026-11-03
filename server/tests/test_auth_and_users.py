"""OIDC resource-server behaviour, user management, privacy and account deletion."""

from __future__ import annotations

import time

import jwt
import pytest
from conftest import (
    ISSUER,
    auth,
    create_profile,
    foreign_key,
    make_container,
    make_settings,
    make_token,
)
from fastapi.testclient import TestClient

from pandit_server.main import create_app

URL = "/api/v1/users/me"


def _status(client: TestClient, headers: dict[str, str] | None) -> int:
    return client.get(URL, headers=headers).status_code


def test_a_valid_token_creates_the_user_on_first_use(client: TestClient) -> None:
    response = client.get(URL, headers=auth("kc-user-a"))
    assert response.status_code == 200
    body = response.json()
    assert body["locale"] == "en" and body["memory_consent"] is False
    assert client.get(URL, headers=auth("kc-user-a")).json()["id"] == body["id"]


def test_missing_and_malformed_credentials_are_401_with_a_typed_body(client: TestClient) -> None:
    for headers in (
        None,
        {"Authorization": "Bearer"},
        {"Authorization": "Basic abc"},
        {"Authorization": "Bearer not.a.jwt"},
    ):
        response = client.get(URL, headers=headers)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "unauthorized"
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert response.json()["error"]["request_id"]


def test_expired_wrong_audience_wrong_issuer_and_foreign_signature_are_refused(
    client: TestClient,
) -> None:
    assert _status(client, auth(expires_in=-600)) == 401
    assert _status(client, auth(audience="someone-else")) == 401
    assert _status(client, auth(issuer="http://evil.test/realms/x")) == 401
    assert _status(client, auth(key=foreign_key())) == 401  # right kid, wrong key
    assert _status(client, auth(kid="unknown-kid")) == 401


def test_the_none_algorithm_and_symmetric_tokens_are_refused(client: TestClient) -> None:
    now = int(time.time())
    claims = {"sub": "x", "iss": ISSUER, "aud": "pandit-server", "exp": now + 300}
    unsigned = jwt.encode(claims, key=None, algorithm="none", headers={"kid": "test-key-1"})
    hs = jwt.encode(claims, "secret" * 8, algorithm="HS256", headers={"kid": "test-key-1"})
    for token in (unsigned, hs):
        assert _status(client, {"Authorization": f"Bearer {token}"}) == 401


def test_a_token_without_exp_is_refused(client: TestClient) -> None:
    token = make_token()
    claims = jwt.decode(token, options={"verify_signature": False})
    claims.pop("exp")
    import conftest

    bad = jwt.encode(
        claims, conftest._PRIVATE_PEM, algorithm="RS256", headers={"kid": "test-key-1"}
    )
    assert _status(client, {"Authorization": f"Bearer {bad}"}) == 401


def test_logout_revokes_only_that_token(client: TestClient) -> None:
    first = auth("u", jti="jti-1")
    other = auth("u", jti="jti-2")
    assert _status(client, first) == 200
    assert client.post("/api/v1/auth/logout", headers=first).status_code == 204
    assert _status(client, first) == 401
    assert _status(client, other) == 200


def test_logout_all_revokes_every_earlier_token_but_not_a_new_login(client: TestClient) -> None:
    old = auth("u", issued_at=int(time.time()) - 5)
    assert _status(client, old) == 200
    assert client.post("/api/v1/auth/logout-all", headers=old).status_code == 204
    assert _status(client, old) == 401
    time.sleep(1.1)
    assert _status(client, auth("u")) == 200


def test_auth_config_is_public_and_holds_no_secret(client: TestClient) -> None:
    body = client.get("/api/v1/auth/config").json()
    assert body["issuer"] == ISSUER and body["flow"] == "authorization_code_pkce"
    assert "secret" not in str(body).lower()


def test_repeated_bad_tokens_from_one_client_are_rate_limited() -> None:
    container = make_container(make_settings(RATE_LIMIT_AUTH=2))
    with TestClient(create_app(container.settings, container)) as client:
        codes = [
            client.get(URL, headers={"Authorization": "Bearer bad.token.here"}).status_code
            for _ in range(10)
        ]
    assert codes[0] == 401 and 429 in codes


def test_users_are_isolated(client: TestClient) -> None:
    created = create_profile(client, "alice")
    assert (
        client.get(f"/api/v1/birth-profiles/{created['id']}", headers=auth("bob")).status_code
        == 404
    )
    assert client.get("/api/v1/birth-profiles", headers=auth("bob")).json()["total"] == 0
    assert (
        client.get(URL, headers=auth("alice")).json()["id"]
        != client.get(URL, headers=auth("bob")).json()["id"]
    )


def test_update_user_and_validation(client: TestClient) -> None:
    ok = client.patch(URL, json={"display_name": "Asha", "locale": "hi"}, headers=auth())
    assert ok.status_code == 200 and ok.json()["display_name"] == "Asha"
    bad = client.patch(URL, json={"locale": "klingon"}, headers=auth())
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "validation_error"
    assert "klingon" not in bad.text  # submitted values are never echoed
    assert client.patch(URL, json={"is_admin": True}, headers=auth()).status_code == 422


def test_privacy_defaults_off_and_withdrawing_memory_consent_erases_memory(
    client: TestClient,
) -> None:
    h = auth("p")
    assert (
        client.put("/api/v1/memory/theme", json={"value": {"a": 1}}, headers=h).status_code == 403
    )
    assert client.put(URL + "/privacy", json={"memory_consent": True}, headers=h).status_code == 200
    assert (
        client.put("/api/v1/memory/theme", json={"value": {"a": 1}}, headers=h).status_code == 200
    )
    assert len(client.get("/api/v1/memory", headers=h).json()["items"]) == 1
    client.put(URL + "/privacy", json={"memory_consent": False}, headers=h)
    client.put(URL + "/privacy", json={"memory_consent": True}, headers=h)
    assert client.get("/api/v1/memory", headers=h).json()["items"] == []


def test_export_returns_only_the_callers_data(client: TestClient) -> None:
    create_profile(client, "e1")
    create_profile(client, "e2", label="Other")
    export = client.get(URL + "/export", headers=auth("e1")).json()
    assert [p["label"] for p in export["birth_profiles"]] == ["Me"]


def test_account_deletion_removes_everything_and_revokes_tokens(
    client: TestClient, container
) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy import func, select

    from pandit_server.db.models import AuditEvent, BirthProfile, User

    token = auth("gone")
    create_profile(client, "gone")
    assert client.delete(URL, headers=token).status_code == 204
    assert client.get(URL, headers=token).status_code == 401  # tokens revoked
    with container.db.session() as s:
        assert s.scalar(select(func.count()).select_from(BirthProfile)) == 0
        assert s.scalar(select(User).where(User.subject == "gone")) is None
        events = s.scalars(select(AuditEvent)).all()
        assert any(e.action == "account.delete" for e in events)
        assert all(
            "gone" not in (e.actor_hash or "") and e.actor_hash for e in events if e.actor_hash
        )


@pytest.mark.parametrize(
    "path", ["/api/v1/birth-profiles", "/api/v1/reports", "/api/v1/memory", "/api/v1/notifications"]
)
def test_every_private_route_needs_authentication(client: TestClient, path: str) -> None:
    assert client.get(path).status_code == 401
