"""Shared fixtures for the backend tests.

The app is built with a SQLite database (schemas translated away), an in-memory key-value store, a
static JWKS signed by a throwaway RSA key (so no Keycloak is needed for unit tests) and eager
Celery. PostgreSQL, Valkey and Keycloak are covered by the opt-in integration tests.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Iterator
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from pandit_server.auth.oidc import StaticKeyProvider, jwks_from_public_key
from pandit_server.config import Settings
from pandit_server.container import Container, build_container
from pandit_server.db.session import Database
from pandit_server.kv import MemoryStore
from pandit_server.main import create_app

ISSUER = "http://keycloak.test/realms/pandit-ji"
AUDIENCE = "pandit-server"
KID = "test-key-1"

_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PRIVATE_PEM = _KEY.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
)
_PUBLIC_PEM = _KEY.public_key().public_bytes(
    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
)
JWKS = jwks_from_public_key(_PUBLIC_PEM, KID)

_OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def make_token(
    subject: str = "user-1",
    *,
    roles: tuple[str, ...] = (),
    expires_in: int = 300,
    audience: str = AUDIENCE,
    issuer: str = ISSUER,
    jti: str | None = None,
    issued_at: int | None = None,
    key: Any = None,
    kid: str = KID,
    algorithm: str = "RS256",
    extra: dict[str, Any] | None = None,
) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        "sub": subject,
        "iss": issuer,
        "aud": audience,
        "iat": issued_at if issued_at is not None else now,
        "exp": now + expires_in,
        "jti": jti or uuid.uuid4().hex,
        "realm_access": {"roles": list(roles)},
    }
    claims.update(extra or {})
    signing = key if key is not None else _PRIVATE_PEM
    return jwt.encode(claims, signing, algorithm=algorithm, headers={"kid": kid})


def foreign_key() -> Any:
    return _OTHER_KEY


def make_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "APP_ENV": "test",
        "DATABASE_URL": "sqlite+pysqlite://",
        "VALKEY_URL": "redis://127.0.0.1:6399/0",
        "AUTH_ISSUER_URL": ISSUER,
        "AUTH_AUDIENCE": AUDIENCE,
        "CELERY_EAGER": True,
        "CORS_ORIGINS": "https://app.example",
        "RATE_LIMIT_DEFAULT": 1000,
        "RATE_LIMIT_EXPENSIVE": 1000,
        "RATE_LIMIT_ANONYMOUS": 1000,
        "RATE_LIMIT_AUTH": 1000,
        "CHAT_MAX_EVIDENCE_ITEMS": 36,
    }
    values.update(overrides)
    return Settings(**values)


def make_container(
    settings: Settings | None = None, llm_factory: Callable[[], Any] | None = None
) -> Container:
    settings = settings or make_settings()
    db = Database("sqlite+pysqlite://")
    db.create_all()

    def no_llm() -> Any:
        raise RuntimeError("no language model in this test")

    return build_container(
        settings,
        db=db,
        store=MemoryStore(),
        key_provider=StaticKeyProvider(JWKS),
        llm_factory=llm_factory or no_llm,
    )


@pytest.fixture()
def container() -> Container:
    return make_container()


@pytest.fixture()
def client(container: Container) -> Iterator[TestClient]:
    from pandit_server import jobs

    app = create_app(container.settings, container)
    jobs.set_container(container)
    with TestClient(app) as test_client:
        yield test_client


def auth(subject: str = "user-1", **kwargs: Any) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(subject, **kwargs)}"}


PROFILE: dict[str, Any] = {
    "label": "Me",
    "birth_date": "1990-06-15",
    "birth_time": "10:00:00",
    "time_precision": "exact",
    "timezone": "Asia/Kolkata",
    "latitude": 28.6139,
    "longitude": 77.2090,
    "place_label": "Delhi",
}


def create_profile(client: TestClient, subject: str = "user-1", **overrides: Any) -> dict[str, Any]:
    response = client.post(
        "/api/v1/birth-profiles", json={**PROFILE, **overrides}, headers=auth(subject)
    )
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body
