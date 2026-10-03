"""The ``LLMProvider`` / AI Reasoner interface (ADR-002) that Phase 15 will call.

Phase 15 supplies the task context, structured evidence, the language, the desired response schema
and a generation policy; it receives the generated text, the validated structured output, the
model provenance, the status and the usage. Nothing here plans, remembers, selects tools or
decides: that is the agent's job, and it stays on the other side of this interface.
"""

from __future__ import annotations

from typing import Protocol

from pandit_contracts.llm import LLMHealth, LLMRequest, LLMResponse


class LLMProvider(Protocol):
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Never raises for an expected failure: it returns a FAILED response with a typed error."""

    def health(self) -> LLMHealth: ...
