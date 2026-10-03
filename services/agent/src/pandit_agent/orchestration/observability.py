"""Agent telemetry: content-free structured log events, same convention as Phase 14.

One JSON line per request through the shared logging foundation. Only identifiers, hashes, counts,
codes and versions can be logged; a field outside the allow-list raises, so user text, generated
narration, evidence content, palm facts and images cannot be logged by accident.
"""

from __future__ import annotations

import json
import logging
from typing import Any

LOGGER = logging.getLogger("pandit.agent")

_ALLOWED_FIELDS = frozenset(
    {
        "event",
        "request_id",
        "domain",
        "intent",
        "language",
        "status",
        "error_code",
        "latency_ms",
        "steps",
        "tool_calls",
        "llm_calls",
        "retries",
        "plan_hash",
        "context_hash",
        "llm_request_hash",
        "prompt_version",
        "task_id",
        "schema_id",
        "model_id",
        "model_version",
        "version_refs",
        "bundle_refs",
        "claims",
        "injection_suspected",
        "agent_version",
    }
)


def log_event(**fields: Any) -> None:
    unknown = set(fields) - _ALLOWED_FIELDS
    if unknown:
        raise ValueError(f"not loggable: {sorted(unknown)}")
    LOGGER.info(json.dumps({k: v for k, v in fields.items() if v is not None}, sort_keys=True))
