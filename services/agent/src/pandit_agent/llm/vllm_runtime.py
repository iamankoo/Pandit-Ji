"""Runtime for a self-hosted vLLM server (``vllm serve`` on a private address).

vLLM runs as its own process behind this interface (``docs/ARCHITECTURE.md`` section 16): the
agent never embeds the model in-process. This module speaks the server's documented HTTP API
(``/health``, ``/version``, ``/v1/models``, ``/v1/completions``, ``/tokenize``) with the standard
library only, and sends the prompt already rendered with the model's pinned chat template, so
the template that is tested is the template that is used.

Boundaries enforced here:

* the endpoint must be on the operator allow-list (``check_endpoint``); there is no default that
  reaches a hosted provider, and redirects and proxy settings are disabled so content cannot be
  forwarded elsewhere;
* the server must serve the model the manifest names; a different model is a failure, never a
  silent switch;
* error messages never echo the response body (a server may echo the prompt).

Status: written to vLLM's documented API and exercised in CI against a protocol fake only. Running
it against a real vLLM server and a real GPU is ``HARDWARE_REQUIRED`` / ``OPTIONAL_LOCAL_TEST``
(``services/agent/llm/README.md``); the vLLM request fields were not verified against a live server.
"""

from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from typing import Any
from urllib.request import Request

from pandit_contracts.llm import FinishReason, LLMErrorCode

from pandit_agent.llm.errors import LLMFailure
from pandit_agent.llm.manifest import ModelManifest
from pandit_agent.llm.runtime import RuntimeCall, RuntimeResult
from pandit_agent.llm.settings import check_endpoint

_MAX_BODY = 8 * 1024 * 1024
_PROBE_TIMEOUT_S = 10.0


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: Any, **kwargs: Any) -> None:  # noqa: D102
        return None


_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


def _is_timeout(exc: object) -> bool:
    return isinstance(exc, TimeoutError | socket.timeout)


class VLLMServerRuntime:
    name = "vllm"
    is_real_model = True

    def __init__(
        self,
        endpoint_url: str,
        allowed_hosts: frozenset[str],
        *,
        served_model_name: str | None = None,
    ) -> None:
        self._base = check_endpoint(endpoint_url, allowed_hosts)
        self._served = served_model_name
        self._version = "unknown"

    @property
    def version(self) -> str:
        return self._version

    # -- transport -------------------------------------------------------------------------

    def _request(
        self, method: str, path: str, body: dict[str, Any] | None, timeout: float, *, probing: bool
    ) -> tuple[int, Any]:
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = Request(  # noqa: S310 - the URL passed check_endpoint (http/https allow-list)
            self._base + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with _OPENER.open(req, timeout=timeout) as resp:
                status, raw = resp.status, resp.read(_MAX_BODY)
        except urllib.error.HTTPError as exc:
            status, raw = exc.code, exc.read(_MAX_BODY)
        except (urllib.error.URLError, OSError) as exc:
            reason = exc.reason if isinstance(exc, urllib.error.URLError) else exc
            if _is_timeout(reason):
                code = (
                    LLMErrorCode.RUNTIME_UNAVAILABLE if probing else LLMErrorCode.GENERATION_TIMEOUT
                )
                raise LLMFailure(code, "the inference server timed out", retryable=True) from exc
            raise LLMFailure(
                LLMErrorCode.RUNTIME_UNAVAILABLE,
                "the inference server is not reachable",
                retryable=True,
            ) from exc
        try:
            return status, json.loads(raw) if raw else None
        except ValueError:
            return status, None

    @staticmethod
    def _map_error(status: int, payload: Any) -> LLMFailure:
        # Classify from the body without ever copying it into the message.
        blob = json.dumps(payload).lower() if payload is not None else ""
        if status == 400 and "context length" in blob:
            return LLMFailure(LLMErrorCode.CONTEXT_TOO_LARGE, "the server rejected the length")
        if status in {408, 504}:
            return LLMFailure(
                LLMErrorCode.GENERATION_TIMEOUT, "the server timed out", retryable=True
            )
        if status == 404:
            return LLMFailure(LLMErrorCode.MODEL_UNAVAILABLE, "the server does not serve the model")
        if "out of memory" in blob:
            return LLMFailure(
                LLMErrorCode.INSUFFICIENT_RESOURCES, "the server ran out of memory", retryable=True
            )
        if "cuda" in blob or "gpu" in blob:
            return LLMFailure(LLMErrorCode.GPU_UNAVAILABLE, "the server reports a GPU problem")
        return LLMFailure(
            LLMErrorCode.GENERATION_FAILURE,
            f"the server returned HTTP {status}",
            retryable=status >= 500,
        )

    # -- LLMRuntime ------------------------------------------------------------------------

    def load(self, manifest: ModelManifest) -> None:
        status, _ = self._request("GET", "/health", None, _PROBE_TIMEOUT_S, probing=True)
        if status != 200:
            raise LLMFailure(LLMErrorCode.RUNTIME_UNAVAILABLE, "the server is not healthy")
        status, models = self._request("GET", "/v1/models", None, _PROBE_TIMEOUT_S, probing=True)
        served = self._served or manifest.model_id
        ids = (
            [m.get("id") for m in models.get("data", []) if isinstance(m, dict)]
            if status == 200 and isinstance(models, dict)
            else []
        )
        if served not in ids:
            raise LLMFailure(
                LLMErrorCode.MODEL_UNAVAILABLE,
                "the server is not serving the manifest's model (no silent model switch)",
            )
        self._served = served
        status, info = self._request("GET", "/version", None, _PROBE_TIMEOUT_S, probing=True)
        if status == 200 and isinstance(info, dict) and isinstance(info.get("version"), str):
            self._version = info["version"]

    def count_tokens(self, text: str) -> int | None:
        if self._served is None:
            return None
        try:
            status, payload = self._request(
                "POST",
                "/tokenize",
                {"model": self._served, "prompt": text, "add_special_tokens": False},
                _PROBE_TIMEOUT_S,
                probing=True,
            )
        except LLMFailure:
            return None
        if status == 200 and isinstance(payload, dict):
            count = payload.get("count")
            if isinstance(count, int):
                return count
            tokens = payload.get("tokens")
            if isinstance(tokens, list):
                return len(tokens)
        return None

    def generate(self, call: RuntimeCall) -> RuntimeResult:
        gen = call.generation
        body: dict[str, Any] = {
            "model": self._served,
            "prompt": call.prompt,
            "max_tokens": gen.max_new_tokens,
            "temperature": gen.temperature,
            "top_p": gen.top_p,
            "add_special_tokens": False,
        }
        if gen.top_k is not None:
            body["top_k"] = gen.top_k
        if gen.repetition_penalty is not None:
            body["repetition_penalty"] = gen.repetition_penalty
        if gen.stop:
            body["stop"] = list(gen.stop)
        if gen.seed is not None:
            body["seed"] = gen.seed
        if call.json_schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "pj_output", "schema": call.json_schema},
            }
        status, payload = self._request(
            "POST", "/v1/completions", body, gen.timeout_s, probing=False
        )
        if status != 200:
            raise self._map_error(status, payload)
        try:
            choice = payload["choices"][0]
            text = choice["text"]
            reason = {"stop": FinishReason.STOP, "length": FinishReason.LENGTH}.get(
                choice.get("finish_reason"), FinishReason.ERROR
            )
            usage = payload.get("usage") or {}
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMFailure(
                LLMErrorCode.GENERATION_FAILURE, "the server response has an unexpected shape"
            ) from exc
        if not isinstance(text, str):
            raise LLMFailure(LLMErrorCode.GENERATION_FAILURE, "the server returned no text")
        return RuntimeResult(
            text=text,
            finish_reason=reason,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            first_token_ms=None,  # non-streaming: first-token latency is not measured
        )
