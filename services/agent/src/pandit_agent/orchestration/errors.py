"""The one exception type of the orchestration layer. Expected failures are typed, never raw."""

from __future__ import annotations

from pandit_contracts.agent import AgentError, AgentErrorCode


class AgentFailure(Exception):
    """An expected failure. It carries a code and a safe message; never content or internals."""

    def __init__(self, code: AgentErrorCode, message: str, *, retryable: bool = False) -> None:
        super().__init__(f"{code.value}: {message}")
        self.code = code
        self.message = message
        self.retryable = retryable

    def to_error(self) -> AgentError:
        return AgentError(code=self.code, message=self.message, retryable=self.retryable)
