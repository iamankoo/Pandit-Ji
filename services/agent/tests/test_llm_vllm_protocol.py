"""The vLLM runtime against a local PROTOCOL FAKE (a stdlib HTTP server), not a model.

What this proves: the runtime sends the documented request shape, maps responses and errors to
typed failures, refuses a mismatched served model, follows no redirects and echoes no body. What it
does NOT prove: that a real vLLM server, with real weights on a real GPU, accepts these requests
or produces good output. That is ``HARDWARE_REQUIRED`` / ``OPTIONAL_LOCAL_TEST`` and is covered by
``test_real_vllm_server_optional_local`` (skipped unless ``PANDIT_LLM_REAL_VLLM_URL`` is set).
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest
from llm_helpers import QWEN_MANIFEST, QWEN_MODEL_ID, gen, qwen_manifest, request, settings
from pandit_contracts.llm import FinishReason, LLMErrorCode, LLMLanguage, LLMStatus, Readiness

from pandit_agent.llm.errors import LLMFailure
from pandit_agent.llm.runtime import RuntimeCall
from pandit_agent.llm.service import create_service
from pandit_agent.llm.structured import ANSWER_WITH_EVIDENCE_REFS_V1, SchemaRegistry
from pandit_agent.llm.vllm_runtime import VLLMServerRuntime

PROMPT_SENTINEL = "PROMPT-SENTINEL-55e1"


class FakeVLLM:
    """A scripted HTTP stand-in. ``completion`` is a callable (body) -> (status, payload)."""

    def __init__(self) -> None:
        self.models: list[str] = [QWEN_MODEL_ID]
        self.health_status = 200
        self.version: str | None = "0.0.0-fake"
        self.tokenize_count: int | None = 7
        self.completion: Callable[[dict[str, Any]], tuple[int, Any]] = self._ok
        self.completion_delay_s = 0.0
        self.redirect_completions = False
        self.requests: list[tuple[str, str, dict[str, Any] | None]] = []

    @staticmethod
    def _ok(body: dict[str, Any]) -> tuple[int, Any]:
        text = (
            json.dumps({"answer": "fine", "evidence_refs": []})
            if "response_format" in body
            else "Namaste"
        )
        return 200, {
            "choices": [{"text": text, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 3},
        }


@pytest.fixture
def fake() -> Iterator[tuple[FakeVLLM, str]]:
    state = FakeVLLM()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args: Any) -> None:  # silence
            return

        def _send(self, status: int, payload: Any) -> None:
            raw = json.dumps(payload).encode("utf-8") if payload is not None else b""
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self) -> None:
            state.requests.append(("GET", self.path, None))
            if self.path == "/health":
                self._send(state.health_status, None)
            elif self.path == "/version":
                self._send(200, {"version": state.version} if state.version else {})
            elif self.path == "/v1/models":
                self._send(200, {"data": [{"id": m} for m in state.models]})
            else:
                self._send(404, {"error": "nope"})

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length) or b"{}")
            state.requests.append(("POST", self.path, body))
            if self.path == "/tokenize":
                if state.tokenize_count is None:
                    self._send(500, {"error": "no tokenizer"})
                else:
                    self._send(200, {"count": state.tokenize_count})
            elif self.path == "/v1/completions":
                if state.redirect_completions:
                    self.send_response(302)
                    self.send_header("Location", "/elsewhere")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                time.sleep(state.completion_delay_s)
                status, payload = state.completion(body)
                self._send(status, payload)
            else:
                self._send(404, {"error": "nope"})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state, f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


ALLOWED = frozenset({"127.0.0.1", "localhost"})


def _runtime(url: str) -> VLLMServerRuntime:
    return VLLMServerRuntime(url, ALLOWED)


def _loaded(url: str) -> VLLMServerRuntime:
    runtime = _runtime(url)
    runtime.load(qwen_manifest())
    return runtime


def _call(**over: Any) -> RuntimeCall:
    return RuntimeCall(prompt=f"p {PROMPT_SENTINEL}", generation=gen(**over))


# -- loading -----------------------------------------------------------------------------------


def test_load_succeeds_when_the_server_serves_the_manifest_model(
    fake: tuple[FakeVLLM, str],
) -> None:
    state, url = fake
    runtime = _loaded(url)
    assert runtime.version == "0.0.0-fake"
    assert [r[1] for r in state.requests] == ["/health", "/v1/models", "/version"]


def test_a_different_served_model_is_refused_not_switched(fake: tuple[FakeVLLM, str]) -> None:
    state, url = fake
    state.models = ["some-other/model"]
    with pytest.raises(LLMFailure) as caught:
        _runtime(url).load(qwen_manifest())
    assert caught.value.code is LLMErrorCode.MODEL_UNAVAILABLE
    assert "no silent model switch" in caught.value.message


def test_an_unhealthy_server_is_runtime_unavailable(fake: tuple[FakeVLLM, str]) -> None:
    state, url = fake
    state.health_status = 503
    with pytest.raises(LLMFailure) as caught:
        _runtime(url).load(qwen_manifest())
    assert caught.value.code is LLMErrorCode.RUNTIME_UNAVAILABLE


def test_a_missing_version_endpoint_value_degrades_to_unknown(fake: tuple[FakeVLLM, str]) -> None:
    state, url = fake
    state.version = None
    assert _loaded(url).version == "unknown"


def test_the_runtime_refuses_a_host_that_is_not_on_the_allow_list() -> None:
    with pytest.raises(LLMFailure) as caught:
        VLLMServerRuntime("http://203.0.113.9:8000", ALLOWED)
    assert caught.value.code is LLMErrorCode.ENDPOINT_NOT_PERMITTED


# -- the request the server receives -----------------------------------------------------------


def test_the_completion_request_has_the_documented_shape(fake: tuple[FakeVLLM, str]) -> None:
    state, url = fake
    runtime = _loaded(url)
    result = runtime.generate(
        _call(temperature=0.4, top_p=0.9, top_k=5, seed=9, stop=("END",), repetition_penalty=1.1)
    )
    body = next(b for m, p, b in state.requests if p == "/v1/completions" and b)
    assert body["model"] == QWEN_MODEL_ID
    assert body["prompt"] == f"p {PROMPT_SENTINEL}"  # already rendered with the pinned template
    assert (body["temperature"], body["top_p"], body["top_k"], body["seed"]) == (0.4, 0.9, 5, 9)
    assert body["max_tokens"] == 64 and body["stop"] == ["END"]
    assert body["repetition_penalty"] == 1.1 and body["add_special_tokens"] is False
    assert "response_format" not in body
    assert result.text == "Namaste" and result.finish_reason is FinishReason.STOP
    assert (result.prompt_tokens, result.completion_tokens) == (11, 3)
    assert result.first_token_ms is None  # non-streaming: not measured, not invented


def test_a_json_schema_is_sent_as_response_format(fake: tuple[FakeVLLM, str]) -> None:
    state, url = fake
    runtime = _loaded(url)
    schema = SchemaRegistry().get(ANSWER_WITH_EVIDENCE_REFS_V1)
    runtime.generate(RuntimeCall("p", gen(), schema))
    body = next(b for m, p, b in state.requests if p == "/v1/completions" and b)
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["schema"] == schema


def test_token_counting_uses_the_server_and_falls_back_to_none(fake: tuple[FakeVLLM, str]) -> None:
    state, url = fake
    runtime = _loaded(url)
    assert runtime.count_tokens("anything") == 7
    state.tokenize_count = None
    assert runtime.count_tokens("anything") is None  # never a guess


# -- response and error mapping ----------------------------------------------------------------


def test_length_and_unknown_finish_reasons_are_mapped(fake: tuple[FakeVLLM, str]) -> None:
    state, url = fake
    runtime = _loaded(url)
    for raw, expected in (("length", FinishReason.LENGTH), ("abort", FinishReason.ERROR)):
        state.completion = lambda _b, r=raw: (  # type: ignore[misc]
            200,
            {"choices": [{"text": "x", "finish_reason": r}]},
        )
        assert runtime.generate(_call()).finish_reason is expected


@pytest.mark.parametrize(
    ("status", "payload", "code"),
    [
        (
            400,
            {"message": "maximum context length is 32768 tokens"},
            LLMErrorCode.CONTEXT_TOO_LARGE,
        ),
        (504, None, LLMErrorCode.GENERATION_TIMEOUT),
        (500, {"message": "CUDA error: out of memory"}, LLMErrorCode.INSUFFICIENT_RESOURCES),
        (500, {"message": "CUDA driver version is insufficient"}, LLMErrorCode.GPU_UNAVAILABLE),
        (404, {"message": "model not found"}, LLMErrorCode.MODEL_UNAVAILABLE),
        (500, {"message": "boom"}, LLMErrorCode.GENERATION_FAILURE),
        (422, {"message": "bad field"}, LLMErrorCode.GENERATION_FAILURE),
    ],
)
def test_server_errors_map_to_typed_failures(
    fake: tuple[FakeVLLM, str], status: int, payload: Any, code: LLMErrorCode
) -> None:
    state, url = fake
    runtime = _loaded(url)
    state.completion = lambda _b: (status, payload)
    with pytest.raises(LLMFailure) as caught:
        runtime.generate(_call())
    assert caught.value.code is code


def test_error_messages_never_echo_the_server_body(fake: tuple[FakeVLLM, str]) -> None:
    state, url = fake
    runtime = _loaded(url)
    state.completion = lambda b: (500, {"message": f"failed on prompt: {b['prompt']}"})
    with pytest.raises(LLMFailure) as caught:
        runtime.generate(_call())
    assert PROMPT_SENTINEL not in caught.value.message


def test_a_malformed_success_body_is_a_generation_failure(fake: tuple[FakeVLLM, str]) -> None:
    state, url = fake
    runtime = _loaded(url)
    for payload in ({"choices": []}, {"nope": 1}, {"choices": [{"text": 5}]}):
        state.completion = lambda _b, p=payload: (200, p)  # type: ignore[misc]
        with pytest.raises(LLMFailure) as caught:
            runtime.generate(_call())
        assert caught.value.code is LLMErrorCode.GENERATION_FAILURE


def test_a_slow_server_is_a_generation_timeout(fake: tuple[FakeVLLM, str]) -> None:
    state, url = fake
    runtime = _loaded(url)
    state.completion_delay_s = 1.5
    with pytest.raises(LLMFailure) as caught:
        runtime.generate(_call(timeout_s=0.2))
    assert caught.value.code is LLMErrorCode.GENERATION_TIMEOUT and caught.value.retryable


def test_redirects_are_not_followed(fake: tuple[FakeVLLM, str]) -> None:
    state, url = fake
    runtime = _loaded(url)
    state.redirect_completions = True
    with pytest.raises(LLMFailure) as caught:
        runtime.generate(_call())
    assert caught.value.code is LLMErrorCode.GENERATION_FAILURE
    assert [p for m, p, _ in state.requests if p == "/elsewhere"] == []


# -- the whole service over the protocol fake --------------------------------------------------


def test_the_service_runs_end_to_end_over_the_protocol_fake(fake: tuple[FakeVLLM, str]) -> None:
    """Runtime ``vllm`` (a real-model runtime class) talking to a FAKE server: structure only."""
    state, url = fake
    service = create_service(
        settings(manifest_name=QWEN_MANIFEST, endpoint_url=url, allowed_hosts="127.0.0.1")
    )
    health = service.start()
    assert health.state is Readiness.MODEL_READY and health.runtime == "vllm"
    text = service.generate(
        request("Namaste", model_id=QWEN_MODEL_ID, language=LLMLanguage.HINGLISH)
    )
    assert text.status is LLMStatus.OK and text.text == "Namaste"
    assert text.provenance is not None
    assert text.provenance.runtime == "vllm" and text.provenance.runtime_version == "0.0.0-fake"
    assert text.provenance.model_revision == qwen_manifest().model_revision
    assert text.provenance.artifact_sha256 == qwen_manifest().artifact_hashes
    structured = service.generate(
        request("q", model_id=QWEN_MODEL_ID, schema_id=ANSWER_WITH_EVIDENCE_REFS_V1)
    )
    assert structured.status is LLMStatus.OK and structured.structured == {
        "answer": "fine",
        "evidence_refs": [],
    }


def test_a_server_timeout_surfaces_as_a_failed_response_not_a_fallback(
    fake: tuple[FakeVLLM, str],
) -> None:
    state, url = fake
    service = create_service(
        settings(manifest_name=QWEN_MANIFEST, endpoint_url=url, allowed_hosts="127.0.0.1")
    )
    service.start()
    state.completion_delay_s = 1.5
    response = service.generate(request("q", model_id=QWEN_MODEL_ID, generation=gen(timeout_s=0.2)))
    assert response.status is LLMStatus.FAILED
    assert response.error is not None and response.error.code is LLMErrorCode.GENERATION_TIMEOUT
    assert len([p for m, p, _ in state.requests if p == "/v1/completions"]) == 1


# -- optional local test against a real server -------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("PANDIT_LLM_REAL_VLLM_URL"),
    reason=(
        "OPTIONAL_LOCAL_TEST / HARDWARE_REQUIRED: set PANDIT_LLM_REAL_VLLM_URL to a self-hosted "
        "vLLM server serving Qwen/Qwen3-8B (needs a GPU and the downloaded weights)"
    ),
)
def test_real_vllm_server_optional_local() -> None:
    from urllib.parse import urlsplit

    url = os.environ["PANDIT_LLM_REAL_VLLM_URL"]
    host = urlsplit(url).hostname or ""
    service = create_service(
        settings(manifest_name=QWEN_MANIFEST, endpoint_url=url, allowed_hosts=host)
    )
    assert service.start().state is Readiness.MODEL_READY
    for language in LLMLanguage:
        response = service.generate(
            request("Say hello in one short sentence.", model_id=QWEN_MODEL_ID, language=language)
        )
        assert response.status is LLMStatus.OK, response.error
        assert response.provenance is not None and response.provenance.is_real_model
    structured = service.generate(
        request(
            "Answer with one word.", model_id=QWEN_MODEL_ID, schema_id=ANSWER_WITH_EVIDENCE_REFS_V1
        )
    )
    assert structured.status in {LLMStatus.OK, LLMStatus.FAILED}  # may fail: that is a real result
