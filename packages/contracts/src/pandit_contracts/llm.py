"""Self-hosted LLM contracts (Phase 14).

``LLMRequest`` goes in, ``LLMResponse`` comes out; nothing here knows how a future agent plans.
The model is a language-generation layer: it is never the source of a fact, a calculation, a
rule or a verification. The request carries *evidence the caller already produced* (facts, rule
evaluations, source references) as explicit, size-limited, traceable items; the response says
exactly which model, runtime, configuration and prompt version produced it.

Failures are typed (``LLMErrorCode``) and machine-readable. Nothing in this module logs or
stores content; hashes and identifiers stand in for it.
"""

from __future__ import annotations

import hashlib
import json
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pandit_contracts.palm_policy import ProhibitedCategory

LLM_CONTRACT_VERSION = "1.0.0"

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:\-]{0,127}$")


class _Frozen(BaseModel):
    # ``model_id`` is a domain term here, not a pydantic internal.
    model_config = ConfigDict(frozen=True, extra="forbid", protected_namespaces=())


class LLMLanguage(str, Enum):
    EN = "EN"
    HI = "HI"
    HINGLISH = "HINGLISH"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class OutputMode(str, Enum):
    TEXT = "TEXT"
    JSON = "JSON"


class FinishReason(str, Enum):
    STOP = "stop"
    LENGTH = "length"
    ERROR = "error"


class LLMStatus(str, Enum):
    OK = "OK"
    FAILED = "FAILED"


class Readiness(str, Enum):
    SERVICE_STARTED = "SERVICE_STARTED"
    MODEL_LOADING = "MODEL_LOADING"
    MODEL_READY = "MODEL_READY"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    MODEL_ERROR = "MODEL_ERROR"


class LanguageCheck(str, Enum):
    """A script heuristic, not a quality measure (see ``docs/ARCHITECTURE.md`` section 36)."""

    PASS = "PASS"
    FAIL = "FAIL"
    NOT_CHECKED = "NOT_CHECKED"


class LLMErrorCode(str, Enum):
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    MODEL_LOAD_FAILURE = "MODEL_LOAD_FAILURE"
    TOKENIZER_FAILURE = "TOKENIZER_FAILURE"
    INVALID_MANIFEST = "INVALID_MANIFEST"
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"
    INVALID_REQUEST = "INVALID_REQUEST"
    CONTEXT_TOO_LARGE = "CONTEXT_TOO_LARGE"
    GENERATION_TIMEOUT = "GENERATION_TIMEOUT"
    GENERATION_FAILURE = "GENERATION_FAILURE"
    MALFORMED_STRUCTURED_OUTPUT = "MALFORMED_STRUCTURED_OUTPUT"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    UNSUPPORTED_LANGUAGE = "UNSUPPORTED_LANGUAGE"
    UNSUPPORTED_OUTPUT_SCHEMA = "UNSUPPORTED_OUTPUT_SCHEMA"
    RUNTIME_UNAVAILABLE = "RUNTIME_UNAVAILABLE"
    GPU_UNAVAILABLE = "GPU_UNAVAILABLE"
    INSUFFICIENT_RESOURCES = "INSUFFICIENT_RESOURCES"
    ENDPOINT_NOT_PERMITTED = "ENDPOINT_NOT_PERMITTED"


class LLMError(_Frozen):
    code: LLMErrorCode
    message: str
    retryable: bool = False


class LLMMessage(_Frozen):
    role: MessageRole
    content: str = Field(min_length=1)


class EvidenceItem(_Frozen):
    """One piece of upstream evidence. The model reads it; it never changes it."""

    evidence_id: str
    kind: str = Field(min_length=1, max_length=64)
    source_ref: str | None = Field(default=None, max_length=256)
    content: str = Field(min_length=1, max_length=8000)

    @model_validator(mode="after")
    def _check_id(self) -> EvidenceItem:
        if not _ID_RE.match(self.evidence_id):
            raise ValueError("evidence_id must match [A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
        return self


class TaskInstruction(_Frozen):
    """A trusted, versioned task instruction supplied by application code (Phase 15 templates).

    It is the one channel for task instructions that is not the user message. It must never
    contain user-supplied text: the caller (the agent's template module) owns that guarantee.
    """

    task_id: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=6000)


class LLMContext(_Frozen):
    """The only application state allowed into the prompt: explicit, versioned, size-limited."""

    context_version: str = Field(min_length=1, max_length=64)
    items: tuple[EvidenceItem, ...] = Field(default=(), max_length=200)
    restrictions: tuple[ProhibitedCategory, ...] = ()
    # Additive in Phase 15 (backward compatible: absent means no task section and an unchanged
    # request hash).
    task: TaskInstruction | None = None

    @model_validator(mode="after")
    def _unique_ids(self) -> LLMContext:
        ids = [i.evidence_id for i in self.items]
        if len(set(ids)) != len(ids):
            raise ValueError("evidence ids must be unique")
        return self


class GenerationConfig(_Frozen):
    """Per-request sampling controls. Defaults live in one versioned source (agent settings)."""

    config_version: str = Field(min_length=1, max_length=64)
    temperature: float = Field(ge=0.0, le=2.0)
    top_p: float = Field(gt=0.0, le=1.0)
    top_k: int | None = Field(default=None, ge=1)
    max_new_tokens: int = Field(ge=1, le=8192)
    repetition_penalty: float | None = Field(default=None, gt=0.0, le=2.0)
    stop: tuple[str, ...] = Field(default=(), max_length=4)
    seed: int | None = Field(default=None, ge=0)
    # Qwen3-style models can emit a reasoning block; it is off unless asked for.
    enable_thinking: bool = False
    timeout_s: float = Field(default=120.0, gt=0.0, le=3600.0)


class OutputSpec(_Frozen):
    mode: OutputMode = OutputMode.TEXT
    schema_id: str | None = None

    @model_validator(mode="after")
    def _schema_rules(self) -> OutputSpec:
        if self.mode is OutputMode.JSON and not self.schema_id:
            raise ValueError("JSON output needs a registered schema_id")
        if self.mode is OutputMode.TEXT and self.schema_id:
            raise ValueError("TEXT output takes no schema_id")
        return self


def _canonical(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class LLMRequest(_Frozen):
    request_id: str
    model_id: str = Field(min_length=1)
    language: LLMLanguage
    # Conversation turns only. The system block is assembled by the service from the context
    # and policy, never accepted from the caller (no hidden state, no policy override).
    messages: tuple[LLMMessage, ...] = Field(min_length=1, max_length=64)
    context: LLMContext | None = None
    generation: GenerationConfig
    output: OutputSpec = Field(default_factory=OutputSpec)

    @model_validator(mode="after")
    def _check(self) -> LLMRequest:
        if not _ID_RE.match(self.request_id):
            raise ValueError("request_id must match [A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
        if self.messages[-1].role is not MessageRole.USER:
            raise ValueError("the last message must be a user message")
        return self

    def request_hash(self) -> str:
        """SHA-256 over every field that determines the prompt and the sampling.

        ``request_id`` is excluded: two requests that differ only by id are the same request.
        """
        payload = self.model_dump(mode="json", exclude={"request_id"})
        context = payload.get("context")
        if isinstance(context, dict) and context.get("task") is None:
            # Keep every Phase 14 request hash unchanged: the additive field is absent when unset.
            context.pop("task", None)
        return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


class TokenUsage(_Frozen):
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)


class ResponseMetrics(_Frozen):
    latency_ms: float = Field(ge=0.0)
    first_token_ms: float | None = Field(default=None, ge=0.0)
    tokens_per_second: float | None = Field(default=None, ge=0.0)


class ModelProvenance(_Frozen):
    """What exactly produced this response (``runtime`` says whether a real model ran)."""

    manifest_id: str
    model_id: str
    model_revision: str
    artifact_sha256: tuple[str, ...] = ()
    tokenizer_config_sha256: str | None = None
    chat_template_sha256: str | None = None
    runtime: str
    runtime_version: str
    is_real_model: bool
    quantization: str
    dependency_versions: tuple[tuple[str, str], ...] = ()


class LLMResponse(_Frozen):
    request_id: str
    request_hash: str
    status: LLMStatus
    text: str | None = None
    structured: dict[str, Any] | list[Any] | None = None
    finish_reason: FinishReason | None = None
    usage: TokenUsage = Field(default_factory=TokenUsage)
    metrics: ResponseMetrics | None = None
    provenance: ModelProvenance | None = None
    prompt_version: str | None = None
    generation_config_version: str | None = None
    attempts: int = Field(default=0, ge=0)
    language_check: LanguageCheck = LanguageCheck.NOT_CHECKED
    error: LLMError | None = None

    @model_validator(mode="after")
    def _status_rules(self) -> LLMResponse:
        if self.status is LLMStatus.OK:
            if self.error is not None or self.text is None or self.finish_reason is None:
                raise ValueError("an OK response has text, a finish reason and no error")
        elif self.error is None or self.text is not None or self.structured is not None:
            raise ValueError("a FAILED response has an error and no text or structured output")
        return self


class LLMHealth(_Frozen):
    state: Readiness
    runtime: str
    is_real_model: bool
    model_id: str | None = None
    model_load_ms: float | None = Field(default=None, ge=0.0)
    last_error: LLMErrorCode | None = None
    detail: str | None = None
