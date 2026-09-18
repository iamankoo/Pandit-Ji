"""Structured (JSON) logging foundation.

Stdlib-only by design (no extra dependency) -- emits one JSON object per log
line with timestamp, level, logger/service name, environment, and the
request ID when one is bound via `bind_request_id`.

This is a foundation only (`docs/ARCHITECTURE.md` "Observability"): full
trace/metric export (OpenTelemetry, per `TECH_STACK.md`) is wired up in a
later phase. Callers must never log passwords, tokens, private keys, birth
data, palm images, or other sensitive user content -- pass identifiers
(e.g. a profile ID), not raw sensitive payloads.
"""

from __future__ import annotations

import contextvars
import json
import logging
import sys
from datetime import datetime, timezone

_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "pandit_request_id", default=None
)


def bind_request_id(request_id: str | None) -> None:
    """Bind the current request ID so subsequent log records include it."""
    _request_id.set(request_id)


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str, environment: str) -> None:
        super().__init__()
        self._service = service
        self._environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self._service,
            "environment": self._environment,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = _request_id.get()
        if request_id is not None:
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(service: str, environment: str, level: str = "INFO") -> None:
    """Configure the root logger to emit structured JSON to stdout.

    Idempotent: safe to call once at process startup.
    """
    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers.clear()

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter(service=service, environment=environment))
    root.addHandler(handler)
