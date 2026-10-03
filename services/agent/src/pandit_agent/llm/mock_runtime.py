"""A deterministic, scripted test runtime. It is NOT a language model.

It has no weights and produces no real language: it returns what a test scripts, or a digest of
the prompt when nothing is scripted. It exists so CI can exercise the whole service (manifest,
template, context, structured output, policy, health, errors) without a GPU or weights.
``is_real_model`` is ``False`` and the provenance of every response it serves says
``mock-deterministic``; it must never be presented as the model.
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pandit_contracts.llm import FinishReason, LLMErrorCode

from pandit_agent.llm.errors import LLMFailure
from pandit_agent.llm.manifest import ModelManifest
from pandit_agent.llm.runtime import RuntimeCall, RuntimeResult


@dataclass(frozen=True)
class MockReply:
    text: str
    finish_reason: FinishReason = FinishReason.STOP
    first_token_ms: float | None = None


Scripted = str | MockReply | LLMFailure


class MockRuntime:
    name = "mock-deterministic"
    is_real_model = False
    version = "mock-1"

    def __init__(
        self,
        script: Sequence[Scripted] = (),
        *,
        load_failure: LLMFailure | None = None,
        on_load: Callable[[], None] | None = None,
        token_counter: bool = True,
    ) -> None:
        self._script: deque[Scripted] = deque(script)
        self._load_failure = load_failure
        self._on_load = on_load
        self._token_counter = token_counter
        self._loaded = False
        self.calls: list[RuntimeCall] = []

    def load(self, manifest: ModelManifest) -> None:
        if self._on_load is not None:
            self._on_load()
        if self._load_failure is not None:
            raise self._load_failure
        if not manifest.test_fixture:
            raise LLMFailure(
                LLMErrorCode.INVALID_CONFIGURATION,
                "the scripted runtime serves only test-fixture manifests",
            )
        self._loaded = True

    def count_tokens(self, text: str) -> int | None:
        # A fixed rule (words plus a character term), stable across runs. Not a real tokenizer.
        return len(text.split()) + len(text) // 4 if self._token_counter else None

    def generate(self, call: RuntimeCall) -> RuntimeResult:
        if not self._loaded:
            raise LLMFailure(LLMErrorCode.MODEL_UNAVAILABLE, "the scripted runtime is not loaded")
        self.calls.append(call)
        reply: Scripted = self._script.popleft() if self._script else self._default(call)
        if isinstance(reply, LLMFailure):
            raise reply
        if isinstance(reply, str):
            reply = MockReply(reply)
        return RuntimeResult(
            text=reply.text,
            finish_reason=reply.finish_reason,
            prompt_tokens=self.count_tokens(call.prompt),
            completion_tokens=self.count_tokens(reply.text),
            first_token_ms=reply.first_token_ms,
        )

    @staticmethod
    def _default(call: RuntimeCall) -> str:
        digest = hashlib.sha256(call.prompt.encode("utf-8")).hexdigest()[:16]
        if call.json_schema is not None:
            return json.dumps({"answer": f"mock:{digest}", "evidence_refs": []})
        return f"mock:{digest}"
