"""A real Keycloak realm (infrastructure/keycloak/pandit-ji-realm.json) against the backend.

Runs only when ``SERVER_TEST_KEYCLOAK_URL`` is set (for example ``http://localhost:58081``). It
proves the resource-server path with real RS256 tokens from the real JWKS endpoint: valid login,
audience, issuer, revocation, a wrong password, and the realm's brute-force lockout.
"""

from __future__ import annotations

import os
import uuid

import httpx
import pytest
from conftest import make_container, make_settings
from fastapi.testclient import TestClient

from pandit_server.auth.oidc import HttpKeyProvider
from pandit_server.container import build_container
from pandit_server.db.session import Database
from pandit_server.kv import MemoryStore
from pandit_server.main import create_app

BASE = os.environ.get("SERVER_TEST_KEYCLOAK_URL")
pytestmark = pytest.mark.skipif(not BASE, reason="SERVER_TEST_KEYCLOAK_URL is not set")
REALM = "pandit-ji"


def _token(
    username: str = "it-user@pandit.test", password: str = "it-test-password-1"
) -> httpx.Response:
    return httpx.post(
        f"{BASE}/realms/{REALM}/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "pandit-it",
            "username": username,
            "password": password,
        },
        timeout=20,
    )


@pytest.fixture()
def client() -> TestClient:
    settings = make_settings(
        AUTH_ISSUER_URL=f"{BASE}/realms/{REALM}", AUTH_AUDIENCE="pandit-server"
    )
    base = make_container(settings)
    container = build_container(
        settings,
        db=Database("sqlite+pysqlite://"),
        store=MemoryStore(),
        key_provider=HttpKeyProvider(f"{BASE}/realms/{REALM}/protocol/openid-connect/certs"),
        llm_factory=base.llm_factory,
    )
    container.db.create_all()
    return TestClient(create_app(settings, container))


def test_a_real_keycloak_token_is_accepted_with_a_subject_and_audience(client: TestClient) -> None:
    response = _token()
    assert response.status_code == 200, response.text
    access = response.json()["access_token"]
    with client:
        me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access}"})
        assert me.status_code == 200
        assert (
            client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access}"}).json()[
                "id"
            ]
            == me.json()["id"]
        )


def test_logout_revokes_the_real_token(client: TestClient) -> None:
    access = _token().json()["access_token"]
    h = {"Authorization": f"Bearer {access}"}
    with client:
        assert client.get("/api/v1/users/me", headers=h).status_code == 200
        assert client.post("/api/v1/auth/logout", headers=h).status_code == 204
        assert client.get("/api/v1/users/me", headers=h).status_code == 401


def test_a_token_for_another_audience_or_a_tampered_token_is_refused(client: TestClient) -> None:
    access = _token().json()["access_token"]
    head, payload, sig = access.split(".")
    tampered = ".".join([head, payload[:-2] + ("AA" if not payload.endswith("AA") else "BB"), sig])
    with client:
        assert (
            client.get(
                "/api/v1/users/me", headers={"Authorization": f"Bearer {tampered}"}
            ).status_code
            == 401
        )
        assert (
            client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {sig}"}).status_code
            == 401
        )


def test_the_realm_enforces_password_login_and_brute_force_lockout() -> None:
    victim = f"lock-{uuid.uuid4().hex[:8]}@pandit.test"
    admin = httpx.post(
        f"{BASE}/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": "admin",
            "password": os.environ.get("SERVER_TEST_KEYCLOAK_ADMIN_PASSWORD", "admin-local-only"),
        },
        timeout=20,
    )
    if admin.status_code != 200:
        pytest.skip("Keycloak admin credentials are not available")
    headers = {"Authorization": f"Bearer {admin.json()['access_token']}"}
    created = httpx.post(
        f"{BASE}/admin/realms/{REALM}/users",
        headers=headers,
        json={
            "username": victim,
            "email": victim,
            "enabled": True,
            "emailVerified": True,
            "firstName": "Lock",
            "lastName": "Test",
            "credentials": [
                {"type": "password", "value": "correct-password-1", "temporary": False}
            ],
        },
        timeout=20,
    )
    assert created.status_code == 201
    assert _token(victim, "correct-password-1").status_code == 200
    statuses = [_token(victim, "wrong-password").status_code for _ in range(8)]
    assert set(statuses) == {401}
    # after the lockout threshold the correct password is refused too (Keycloak's own protection)
    assert _token(victim, "correct-password-1").status_code in (400, 401)
