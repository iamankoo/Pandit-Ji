"""The application container: every long-lived collaborator, built once and injectable in tests."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from pandit_server.auth.oidc import HttpKeyProvider, KeyProvider, TokenVerifier
from pandit_server.config import Settings
from pandit_server.db.session import Database
from pandit_server.kv import KeyValueStore, MemoryStore, ResilientStore, ValkeyStore
from pandit_server.platform_services import Metrics, RateLimiter, ResultCache


def _default_llm_factory(settings: Settings) -> Callable[[], Any]:
    """The locked self-hosted boundary (Qwen3-8B on vLLM, ADR-009). There is no hosted fallback:
    if the model service cannot be built, chat answers with a typed unavailable error."""

    def build() -> Any:
        from pandit_agent.llm.service import create_service
        from pandit_agent.llm.settings import LLMSettings
        from pandit_agent.orchestration import narration_schema_registry

        service = create_service(
            LLMSettings(manifest_name=settings.llm_manifest_name),
            schemas=narration_schema_registry(),
        )
        service.start()
        return service

    return build


@dataclass
class Container:
    settings: Settings
    db: Database
    store: KeyValueStore
    verifier: TokenVerifier
    limiter: RateLimiter
    cache: ResultCache
    metrics: Metrics
    llm_factory: Callable[[], Any]
    _llm: Any = field(default=None, repr=False)
    _llm_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def llm(self) -> Any:
        """The language-model service, built on first use. Raises if it cannot be built."""
        with self._llm_lock:
            if self._llm is None:
                self._llm = self.llm_factory()
            return self._llm


def build_container(
    settings: Settings,
    *,
    db: Database | None = None,
    store: KeyValueStore | None = None,
    key_provider: KeyProvider | None = None,
    llm_factory: Callable[[], Any] | None = None,
) -> Container:
    if store is None:
        store = ResilientStore(ValkeyStore(settings.valkey_url))
    database = db or Database(settings.database_url)
    jwks_url = settings.auth_jwks_url or (
        settings.auth_issuer_url.rstrip("/") + "/protocol/openid-connect/certs"
    )
    keys = key_provider or HttpKeyProvider(jwks_url, settings.auth_jwks_cache_seconds)
    verifier = TokenVerifier(
        issuer=settings.auth_issuer_url,
        audience=settings.auth_audience,
        keys=keys,
        store=store,
        algorithms=tuple(a.strip() for a in settings.auth_algorithms.split(",") if a.strip()),
        leeway_seconds=settings.auth_clock_skew_seconds,
    )
    metrics = Metrics()
    return Container(
        settings=settings,
        db=database,
        store=store,
        verifier=verifier,
        limiter=RateLimiter(store, settings.rate_limit_window_seconds),
        cache=ResultCache(store, settings.cache_ttl_seconds, metrics),
        metrics=metrics,
        llm_factory=llm_factory or _default_llm_factory(settings),
    )


__all__ = ["Container", "MemoryStore", "build_container"]
