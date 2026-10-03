"""The one exception type of the LLM layer. Every expected failure is typed and machine-readable."""

from __future__ import annotations

from pandit_contracts.llm import LLMError, LLMErrorCode


class LLMFailure(Exception):
    """An expected failure. It carries a code; it never carries user content."""

    def __init__(self, code: LLMErrorCode, message: str, *, retryable: bool = False) -> None:
        super().__init__(f"{code.value}: {message}")
        self.code = code
        self.message = message
        self.retryable = retryable

    def to_error(self) -> LLMError:
        return LLMError(code=self.code, message=self.message, retryable=self.retryable)
