"""Inference metadata for logs and performance measurement.

Logging goes through the project's stdlib logging foundation (``pandit_shared.logging``): one JSON
line per event, with the request id bound by the shared context variable. Only identifiers,
hashes, counts and codes can be logged: a field outside the allow-list below is a programming
error. Prompts, evidence, generated text, palm facts and images are never logged.
"""

from __future__ import annotations

import importlib
import json
import logging
import statistics
import sys
from typing import Any

LOGGER = logging.getLogger("pandit.agent.llm")

_ALLOWED_FIELDS = frozenset(
    {
        "event",
        "request_id",
        "request_hash",
        "model_id",
        "model_version",
        "runtime",
        "is_real_model",
        "status",
        "error_code",
        "latency_ms",
        "input_tokens",
        "output_tokens",
        "finish_reason",
        "prompt_version",
        "attempts",
        "language",
        "state",
        "load_ms",
    }
)


def log_event(**fields: Any) -> None:
    unknown = set(fields) - _ALLOWED_FIELDS
    if unknown:
        raise ValueError(f"not loggable: {sorted(unknown)}")
    LOGGER.info(json.dumps({k: v for k, v in fields.items() if v is not None}, sort_keys=True))


def process_memory_bytes() -> int | None:
    """Peak resident memory of this process where the platform reports it, else ``None``."""
    try:
        resource = importlib.import_module("resource")
    except ImportError:
        return None
    peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return peak if sys.platform == "darwin" else peak * 1024


class PerformanceRecorder:
    """Measurements from the environment that actually ran. No target numbers are implied."""

    def __init__(self) -> None:
        self.model_load_ms: float | None = None
        self._latencies: list[float] = []
        self._first_token: list[float] = []
        self._tps: list[float] = []

    def record_load(self, load_ms: float) -> None:
        self.model_load_ms = load_ms

    def record_request(
        self, latency_ms: float, first_token_ms: float | None, tokens_per_second: float | None
    ) -> None:
        self._latencies.append(latency_ms)
        if first_token_ms is not None:
            self._first_token.append(first_token_ms)
        if tokens_per_second is not None:
            self._tps.append(tokens_per_second)

    def snapshot(self) -> dict[str, float | int | None]:
        def mean(values: list[float]) -> float | None:
            return statistics.fmean(values) if values else None

        return {
            "model_load_ms": self.model_load_ms,
            "requests": len(self._latencies),
            "mean_latency_ms": mean(self._latencies),
            "mean_first_token_ms": mean(self._first_token),
            "mean_tokens_per_second": mean(self._tps),
            "process_peak_memory_bytes": process_memory_bytes(),
        }
