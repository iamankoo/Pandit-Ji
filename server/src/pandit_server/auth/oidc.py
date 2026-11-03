"""OIDC resource-server token validation (TECH_STACK.md: self-hosted Keycloak is the identity
provider; this backend never stores or checks passwords).

A bearer access token is accepted only if: its signature verifies against a key of the issuer's
JWKS (asymmetric algorithms only; ``none`` and symmetric algorithms are refused), the issuer and
audience match, it is within its validity (with a small clock skew), and it is not revoked (a
``jti`` deny-list and a per-subject cut-off, both with a TTL tied to the token's life). Errors are
typed and never echo the token.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from typing import Any, Protocol

import jwt
from jwt import PyJWK

from pandit_server.kv import KeyValueStore

ALLOWED_ALGORITHMS = ("RS256", "RS384", "RS512", "ES256", "PS256")


class AuthError(Exception):
    """A failed authentication; ``code`` is a stable machine-readable reason."""

    def __init__(self, code: str, message: str = "Authentication failed.") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: frozenset[str]
    token_id: str | None
    session_id: str | None
    issued_at: int | None
    expires_at: int
    display_name: str | None = None

    def has_role(self, role: str) -> bool:
        return role in self.roles


class KeyProvider(Protocol):
    def signing_key(self, kid: str | None) -> Any: ...


class StaticKeyProvider:
    """A fixed JWKS (tests, or a pinned key set)."""

    def __init__(self, jwks: dict[str, Any]) -> None:
        self._keys = {k.get("kid"): PyJWK(k) for k in jwks.get("keys", [])}

    def signing_key(self, kid: str | None) -> Any:
        key = self._keys.get(kid)
        if key is None:
            raise AuthError("unknown_signing_key")
        return key.key


class HttpKeyProvider:
    """The issuer's JWKS endpoint, cached; an unknown ``kid`` triggers one bounded refresh."""

    def __init__(self, jwks_url: str, cache_seconds: int = 300, timeout: float = 3.0) -> None:
        self._url = jwks_url
        self._ttl = cache_seconds
        self._timeout = timeout
        self._keys: dict[str | None, PyJWK] = {}
        self._fetched_at = 0.0
        self._lock = threading.Lock()

    def _refresh(self) -> None:
        import httpx

        try:
            response = httpx.get(self._url, timeout=self._timeout)
            response.raise_for_status()
            body = response.json()
        except Exception as exc:  # noqa: BLE001
            raise AuthError(
                "identity_provider_unavailable", "Identity provider unavailable."
            ) from exc
        self._keys = {k.get("kid"): PyJWK(k) for k in body.get("keys", []) if k.get("use") != "enc"}
        self._fetched_at = time.monotonic()

    def signing_key(self, kid: str | None) -> Any:
        with self._lock:
            age = time.monotonic() - self._fetched_at
            if age > self._ttl or (kid not in self._keys and age > 5):
                self._refresh()
            key = self._keys.get(kid)
        if key is None:
            raise AuthError("unknown_signing_key")
        return key.key


class TokenVerifier:
    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        keys: KeyProvider,
        store: KeyValueStore,
        algorithms: tuple[str, ...] = ("RS256",),
        leeway_seconds: int = 30,
    ) -> None:
        bad = [a for a in algorithms if a not in ALLOWED_ALGORITHMS]
        if bad:
            raise ValueError(f"algorithm not allowed: {bad}")
        self._issuer = issuer
        self._audience = audience
        self._keys = keys
        self._store = store
        self._algorithms = list(algorithms)
        self._leeway = leeway_seconds

    def verify(self, token: str) -> Principal:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise AuthError("malformed_token") from exc
        if header.get("alg") not in self._algorithms:
            raise AuthError("unsupported_algorithm")
        key = self._keys.signing_key(header.get("kid"))
        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=self._algorithms,
                audience=self._audience,
                issuer=self._issuer,
                leeway=self._leeway,
                options={"require": ["exp", "iss", "sub"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthError("token_expired") from exc
        except jwt.InvalidAudienceError as exc:
            raise AuthError("invalid_audience") from exc
        except jwt.InvalidIssuerError as exc:
            raise AuthError("invalid_issuer") from exc
        except jwt.PyJWTError as exc:
            raise AuthError("invalid_token") from exc
        subject = str(claims["sub"])
        jti = claims.get("jti")
        iat = claims.get("iat")
        if jti and self._store.get(f"revoked:jti:{jti}"):
            raise AuthError("token_revoked")
        cutoff = self._store.get(f"revoked:sub:{subject}")
        if cutoff is not None and (iat is None or int(iat) <= int(cutoff)):
            raise AuthError("session_revoked")
        roles = set(claims.get("realm_access", {}).get("roles", []))
        roles |= set(claims.get("resource_access", {}).get(self._audience, {}).get("roles", []))
        name = claims.get("name")
        return Principal(
            subject=subject,
            roles=frozenset(str(r) for r in roles),
            token_id=str(jti) if jti else None,
            session_id=str(claims["sid"]) if claims.get("sid") else None,
            issued_at=int(iat) if iat is not None else None,
            expires_at=int(claims["exp"]),
            display_name=name if isinstance(name, str) else None,
        )

    def revoke_token(self, principal: Principal) -> None:
        """Deny this access token until it would have expired anyway."""
        if principal.token_id:
            ttl = max(1, principal.expires_at - int(time.time()) + self._leeway)
            self._store.set(f"revoked:jti:{principal.token_id}", "1", ttl)

    def revoke_subject(self, subject: str, *, ttl_seconds: int = 86400) -> None:
        """Deny every token of ``subject`` issued up to now (logout everywhere, deletion)."""
        self._store.set(f"revoked:sub:{subject}", str(int(time.time())), ttl_seconds)


def jwks_from_public_key(public_pem: bytes, kid: str) -> dict[str, Any]:
    """Build a one-key JWKS from a PEM public key (tests and tooling)."""
    from cryptography.hazmat.primitives import serialization
    from jwt.algorithms import RSAAlgorithm

    public_key: Any = serialization.load_pem_public_key(public_pem)
    jwk = json.loads(RSAAlgorithm.to_jwk(public_key))
    jwk.update({"kid": kid, "alg": "RS256", "use": "sig"})
    return {"keys": [jwk]}
