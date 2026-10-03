"""The runtime abstraction: how a rendered prompt becomes text.

``LLMRuntime`` is the seam between this package and an inference engine. The production runtime
talks to a self-hosted vLLM server (``vllm_runtime``); CI uses a deterministic scripted runtime
(``mock_runtime``). Both implement this protocol, so the same service code is exercised by both,
and every response records which one ran (``ModelProvenance.runtime`` / ``is_real_model``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from pandit_contracts.llm import FinishReason, GenerationConfig

from pandit_agent.llm.manifest import ModelManifest


@dataclass(frozen=True)
class RuntimeCall:
    prompt: str
    generation: GenerationConfig
    json_schema: dict[str, Any] | None = None


@dataclass(frozen=True)
class RuntimeResult:
    text: str
    finish_reason: FinishReason
    prompt_tokens: int | None
    completion_tokens: int | None
    first_token_ms: float | None = None


class LLMRuntime(Protocol):
    name: str
    is_real_model: bool

    @property
    def version(self) -> str: ...

    def load(self, manifest: ModelManifest) -> None:
        """Make the model ready or raise ``LLMFailure`` with the reason."""

    def count_tokens(self, text: str) -> int | None:
        """Exact token count if the runtime can give one, else ``None`` (never a guess)."""

    def generate(self, call: RuntimeCall) -> RuntimeResult:
        """One generation. Raises ``LLMFailure`` (timeout, resources, runtime failure)."""
