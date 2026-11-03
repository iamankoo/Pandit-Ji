"""A tiny key-value abstraction over Valkey/Redis (ADR-005) used for revocation, rate limiting and
the result cache. ``MemoryStore`` is the in-process implementation for tests and for degraded
operation when Valkey is down (a limit then applies per process; this is logged, never silent)."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Protocol

_log = logging.getLogger("pandit_server.kv")


class KeyValueStore(Protocol):
    def incr(self, key: str, ttl_seconds: int) -> int: ...

    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str, ttl_seconds: int) -> None: ...

    def delete(self, key: str) -> None: ...

    def ping(self) -> bool: ...


class MemoryStore:
    def __init__(self) -> None:
        self._data: dict[str, tuple[str, float]] = {}
        self._lock = threading.Lock()
        self._offset = 0.0

    def _now(self) -> float:
        return time.monotonic() + self._offset

    def _live(self, key: str) -> str | None:
        item = self._data.get(key)
        if item is None:
            return None
        if item[1] <= self._now():
            del self._data[key]
            return None
        return item[0]

    def incr(self, key: str, ttl_seconds: int) -> int:
        with self._lock:
            current = self._live(key)
            if current is None:
                self._data[key] = ("1", self._now() + ttl_seconds)
                return 1
            value = int(current) + 1
            self._data[key] = (str(value), self._data[key][1])
            return value

    def get(self, key: str) -> str | None:
        with self._lock:
            return self._live(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        with self._lock:
            self._data[key] = (value, self._now() + ttl_seconds)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def ping(self) -> bool:
        return True

    def advance(self, seconds: float) -> None:
        """Test helper: move the store's clock forward."""
        with self._lock:
            self._offset += seconds


class ValkeyStore:
    def __init__(self, url: str) -> None:
        import redis

        self._client: Any = redis.from_url(  # type: ignore[no-untyped-call]
            url, socket_connect_timeout=2, socket_timeout=2, decode_responses=True
        )

    def incr(self, key: str, ttl_seconds: int) -> int:
        pipe = self._client.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl_seconds, nx=True)
        value, _ = pipe.execute()
        return int(value)

    def get(self, key: str) -> str | None:
        value = self._client.get(key)
        return None if value is None else str(value)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._client.set(key, value, ex=ttl_seconds)

    def delete(self, key: str) -> None:
        self._client.delete(key)

    def ping(self) -> bool:
        try:
            return bool(self._client.ping())
        except Exception:  # noqa: BLE001 - readiness must never raise
            return False


class ResilientStore:
    """Valkey first; on a connection failure fall back to a per-process memory store (logged)."""

    def __init__(self, primary: KeyValueStore, fallback: KeyValueStore | None = None) -> None:
        self._primary = primary
        self._fallback: KeyValueStore = fallback or MemoryStore()
        self.degraded = False

    def _call(self, name: str, *args: Any) -> Any:
        try:
            result = getattr(self._primary, name)(*args)
            self.degraded = False
            return result
        except Exception:  # noqa: BLE001
            if not self.degraded:
                _log.warning("valkey_unavailable_using_process_local_fallback")
            self.degraded = True
            return getattr(self._fallback, name)(*args)

    def incr(self, key: str, ttl_seconds: int) -> int:
        return int(self._call("incr", key, ttl_seconds))

    def get(self, key: str) -> str | None:
        value: str | None = self._call("get", key)
        return value

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._call("set", key, value, ttl_seconds)

    def delete(self, key: str) -> None:
        self._call("delete", key)

    def ping(self) -> bool:
        return self._primary.ping()
