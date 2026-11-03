"""Cross-cutting backend services: rate limiting, metrics, audit, result cache, idempotency.

All are small and deterministic. They never see request bodies except through explicit, hashed
inputs, and nothing here logs or stores personal data.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from pandit_server.db.models import AuditEvent, IdempotencyKey
from pandit_server.errors import ApiError
from pandit_server.kv import KeyValueStore


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str, ensure_ascii=True)


def sha256_hex(value: Any) -> str:
    text = value if isinstance(value, str) else canonical_json(value)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---- rate limiting ------------------------------------------------------------------------------


@dataclass(frozen=True)
class RateDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int


class RateLimiter:
    """Fixed-window counter per (bucket, identity). The identity is a user-subject hash or an IP;
    only its hash is stored."""

    def __init__(self, store: KeyValueStore, window_seconds: int = 60) -> None:
        self._store = store
        self._window = window_seconds

    def check(self, bucket: str, identity: str, limit: int) -> RateDecision:
        now = int(time.time())
        window = now // self._window
        key = f"rl:{bucket}:{sha256_hex(identity)[:32]}:{window}"
        count = self._store.incr(key, self._window + 1)
        retry_after = self._window - (now % self._window)
        return RateDecision(count <= limit, limit, max(0, limit - count), retry_after)

    def enforce(self, bucket: str, identity: str, limit: int) -> RateDecision:
        decision = self.check(bucket, identity, limit)
        if not decision.allowed:
            raise ApiError(
                429,
                "rate_limited",
                "Too many requests. Please retry later.",
                headers={"Retry-After": str(decision.retry_after)},
            )
        return decision


# ---- metrics ------------------------------------------------------------------------------------


class Metrics:
    """In-process counters and latency sums, rendered in the Prometheus text format."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self._latency: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0.0])

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        with self._lock:
            self._counters[(name, tuple(sorted(labels.items())))] += value

    def observe_request(self, method: str, route: str, status: int, seconds: float) -> None:
        self.inc("http_requests_total", method=method, route=route, status=str(status))
        with self._lock:
            entry = self._latency[(method, route)]
            entry[0] += seconds
            entry[1] += 1

    def value(self, name: str, **labels: str) -> float:
        with self._lock:
            return self._counters.get((name, tuple(sorted(labels.items()))), 0.0)

    def render(self) -> str:
        lines: list[str] = []
        with self._lock:
            for (name, labels), value in sorted(self._counters.items()):
                label_text = ",".join(f'{k}="{v}"' for k, v in labels)
                lines.append(f"{name}{{{label_text}}} {value:g}")
            for (method, route), (total, count) in sorted(self._latency.items()):
                lab = f'method="{method}",route="{route}"'
                lines.append(f"http_request_duration_seconds_sum{{{lab}}} {total:.6f}")
                lines.append(f"http_request_duration_seconds_count{{{lab}}} {count:g}")
        return "\n".join(lines) + "\n"


# ---- audit --------------------------------------------------------------------------------------


def actor_hash(subject: str | None) -> str | None:
    return None if subject is None else sha256_hex("actor:" + subject)


def record_audit(
    session: Session,
    *,
    subject: str | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    request_id: str | None = None,
    outcome: str = "ok",
) -> None:
    session.add(
        AuditEvent(
            actor_hash=actor_hash(subject),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            outcome=outcome,
        )
    )


# ---- result cache -------------------------------------------------------------------------------


class ResultCache:
    """Caches **deterministic** results only. The key covers the namespace, the owner scope, every
    input and every methodology version, so a changed input, version or user never hits another
    entry. ``scope`` is mandatory: pass a user id for private data and the literal ``"public"`` only
    for results that depend on no user data (for example a Panchang for a date and place)."""

    def __init__(self, store: KeyValueStore, ttl_seconds: int, metrics: Metrics | None = None):
        self._store = store
        self._ttl = ttl_seconds
        self._metrics = metrics

    @staticmethod
    def key(namespace: str, scope: str, inputs: Any, versions: Any) -> str:
        return "cache:" + sha256_hex(
            {"ns": namespace, "scope": scope, "inputs": inputs, "versions": versions}
        )

    def get_or_compute(
        self,
        namespace: str,
        scope: str,
        inputs: Any,
        versions: Any,
        compute: Callable[[], dict[str, Any]],
    ) -> tuple[dict[str, Any], bool]:
        key = self.key(namespace, scope, inputs, versions)
        hit = self._store.get(key)
        if hit is not None:
            if self._metrics:
                self._metrics.inc("cache_hits_total", namespace=namespace)
            loaded: dict[str, Any] = json.loads(hit)
            return loaded, True
        value = compute()
        self._store.set(key, canonical_json(value), self._ttl)
        if self._metrics:
            self._metrics.inc("cache_misses_total", namespace=namespace)
        return value, False


# ---- idempotency --------------------------------------------------------------------------------


def run_idempotent(
    session: Session,
    *,
    user_id: Any,
    key: str | None,
    method: str,
    path: str,
    body: Any,
    handler: Callable[[], tuple[int, dict[str, Any]]],
) -> tuple[int, dict[str, Any], bool]:
    """Run ``handler`` once per (user, Idempotency-Key). A replay returns the stored response; the
    same key with a different request is refused."""
    if key is None:
        status, response = handler()
        return status, response, False
    if not 8 <= len(key) <= 128:
        raise ApiError(422, "invalid_idempotency_key", "Idempotency-Key must be 8-128 characters.")
    request_hash = sha256_hex({"m": method, "p": path, "b": body})
    existing = session.scalar(
        select(IdempotencyKey).where(IdempotencyKey.user_id == user_id, IdempotencyKey.key == key)
    )
    if existing is not None:
        if existing.request_hash != request_hash:
            raise ApiError(
                422,
                "idempotency_key_reuse",
                "This Idempotency-Key was used for a different request.",
            )
        return existing.status_code, dict(existing.response), True
    status, response = handler()
    session.add(
        IdempotencyKey(
            user_id=user_id,
            key=key,
            method=method,
            path=path,
            request_hash=request_hash,
            status_code=status,
            response=response,
        )
    )
    session.flush()
    return status, response, False
