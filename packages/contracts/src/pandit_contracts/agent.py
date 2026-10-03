"""Agent and narration contracts (Phase 15).

The agent plans, collects the deterministic evidence it is handed, asks the self-hosted LLM
(Phase 14) to narrate it, and returns a structured, verification-ready ``NarrationResponse``.

Invariants carried by these types:

* **Facts flow one way.** An ``EvidenceRecord`` keeps the semantic class it was produced with
  (an OBSERVED palm fact stays OBSERVED, a DERIVED fact stays DERIVED, a calculated astrology
  fact stays CALCULATED, a rule evaluation stays a RULE_EVALUATION). Nothing here converts one
  class into another.
* **Domains stay apart.** Every record, reference and claim carries ``Domain``; a palmistry
  record is never an astrology record.
* **Provenance is structured.** Claims cite evidence by id, kind and domain, and the source
  profile, source location, version and uncertainty flags are copied from the evidence record by
  the agent, never written by the model.
* **Generated is not verified.** Phase 15 emits ``VerificationState.UNVERIFIED``. ``VERIFIED``
  exists only for Phase 16 and requires ``verified_by``.
* **No content in telemetry.** ``AgentTrace`` holds identifiers, hashes, counts and versions.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from pandit_contracts.llm import LLMLanguage, ModelProvenance

AGENT_CONTRACT_VERSION = "1.0.0"
NARRATION_SCHEMA_ID = "pj.narration.v1"

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:\-]{0,127}$")


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", protected_namespaces=())


class Domain(str, Enum):
    ASTROLOGY = "ASTROLOGY"
    PALMISTRY = "PALMISTRY"


class Intent(str, Enum):
    """The intent taxonomy, drawn from the specialist modes of ``features.md`` section 2."""

    GENERAL = "GENERAL"
    LOVE_RELATIONSHIP = "LOVE_RELATIONSHIP"
    MARRIAGE = "MARRIAGE"
    CAREER = "CAREER"
    WEALTH = "WEALTH"
    BUSINESS = "BUSINESS"
    DAILY_GUIDANCE = "DAILY_GUIDANCE"
    EDUCATION = "EDUCATION"
    TRAVEL = "TRAVEL"
    LIFE_ANALYSIS = "LIFE_ANALYSIS"
    COMPATIBILITY = "COMPATIBILITY"
    TRANSIT = "TRANSIT"
    DASHA = "DASHA"
    PALM_OVERVIEW = "PALM_OVERVIEW"


class EvidenceClass(str, Enum):
    """The semantic class of a piece of evidence. Never converted from one to another."""

    OBSERVED_FACT = "OBSERVED_FACT"  # Phase 13: seen in the image
    DERIVED_FACT = "DERIVED_FACT"  # Phase 13: computed from other facts
    CALCULATED_FACT = "CALCULATED_FACT"  # astrology: deterministically calculated
    RULE_EVALUATION = "RULE_EVALUATION"  # a rule's outcome (traditional interpretation basis)
    CONTEXT_STATUS = "CONTEXT_STATUS"  # readiness, blockers, conflicts, configuration


class EvidenceCapability(str, Enum):
    """What a tool can contribute. The planner asks for capabilities, never for a vendor tool."""

    ASTRO_CHART = "ASTRO_CHART"
    ASTRO_RULES = "ASTRO_RULES"
    ASTRO_DASHA = "ASTRO_DASHA"
    ASTRO_TRANSIT = "ASTRO_TRANSIT"
    ASTRO_COMPATIBILITY = "ASTRO_COMPATIBILITY"
    PALM_FACTS = "PALM_FACTS"
    PALM_RULES = "PALM_RULES"


class ReferenceKind(str, Enum):
    FACT = "FACT"
    RULE = "RULE"
    STATUS = "STATUS"


class UncertaintyFlag(str, Enum):
    """Why a claim must be read with care. Computed by the agent from the evidence."""

    NOT_EVALUABLE = "NOT_EVALUABLE"
    NOT_TRIGGERED = "NOT_TRIGGERED"
    CONFLICTING_PROFILES = "CONFLICTING_PROFILES"
    UNCALIBRATED_CONFIDENCE = "UNCALIBRATED_CONFIDENCE"
    NOT_VISIBLE = "NOT_VISIBLE"
    BUNDLE_NOT_PRODUCTION_READY = "BUNDLE_NOT_PRODUCTION_READY"
    EVIDENCE_TRIMMED = "EVIDENCE_TRIMMED"


class ClaimType(str, Enum):
    CALCULATION_FACT = "CALCULATION_FACT"  # astrology: a deterministically calculated fact
    OBSERVED_FEATURE = "OBSERVED_FEATURE"  # palmistry: a feature the vision layer observed
    DERIVED_FEATURE = "DERIVED_FEATURE"  # palmistry: computed from other facts, never "observed"
    TRADITIONAL_INTERPRETATION = "TRADITIONAL_INTERPRETATION"  # a named tradition's reading
    LIMITATION = "LIMITATION"  # a stated gap: insufficient, not evaluable, conflicting


class VerificationState(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"  # reserved for Phase 16


class AgentStatus(str, Enum):
    COMPLETED = "COMPLETED"
    DEGRADED = "DEGRADED"  # a structured, honest answer that states what could not be done
    REFUSED = "REFUSED"  # a safe refusal: the request is outside policy
    FAILED = "FAILED"


class AgentErrorCode(str, Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    UNSUPPORTED_LANGUAGE = "UNSUPPORTED_LANGUAGE"
    UNSAFE_REQUEST = "UNSAFE_REQUEST"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    TOOL_NOT_ALLOWED = "TOOL_NOT_ALLOWED"
    TOOL_FAILURE = "TOOL_FAILURE"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    CONTEXT_TOO_LARGE = "CONTEXT_TOO_LARGE"
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_STRUCTURED_OUTPUT_FAILURE = "LLM_STRUCTURED_OUTPUT_FAILURE"
    LLM_FAILURE = "LLM_FAILURE"
    POLICY_REJECTION = "POLICY_REJECTION"
    NARRATION_GROUNDING_FAILURE = "NARRATION_GROUNDING_FAILURE"
    ORCHESTRATION_LIMIT = "ORCHESTRATION_LIMIT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class DisclaimerCode(str, Enum):
    TRADITIONAL_INTERPRETIVE = "TRADITIONAL_INTERPRETIVE"
    NO_GUARANTEED_OUTCOME = "NO_GUARANTEED_OUTCOME"
    NOT_PROFESSIONAL_ADVICE = "NOT_PROFESSIONAL_ADVICE"
    EVIDENCE_NOT_PRODUCTION_READY = "EVIDENCE_NOT_PRODUCTION_READY"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"


class AgentError(_Frozen):
    code: AgentErrorCode
    message: str
    retryable: bool = False


class AgentRequest(_Frozen):
    """A user request. ``user_text`` is untrusted input and only ever reaches the user message."""

    request_id: str
    language: LLMLanguage
    user_text: str = Field(min_length=1, max_length=4000)
    domain: Domain | None = None
    intent_hint: Intent | None = None
    conversation_id: str | None = None
    generation_profile: Literal["deterministic", "model_default"] = "deterministic"

    @model_validator(mode="after")
    def _ids(self) -> AgentRequest:
        for value in (self.request_id, self.conversation_id):
            if value is not None and not _ID_RE.match(value):
                raise ValueError("ids must match [A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
        if not self.user_text.strip():
            raise ValueError("user_text must not be blank")
        return self


class EvidenceReference(_Frozen):
    """A structured pointer into the evidence a claim rests on (Phase 16 resolves it)."""

    evidence_id: str
    domain: Domain
    kind: ReferenceKind
    bundle_ref: str


class EvidenceRecord(_Frozen):
    """One piece of deterministic evidence, exactly as an upstream component produced it."""

    evidence_id: str
    domain: Domain
    evidence_class: EvidenceClass
    kind: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=8000)
    status: str | None = None  # e.g. TRIGGERED, NOT_EVALUABLE, VISIBLE
    # Confidence exactly as the producer defined it (Phase 13: basis points, with a calibrated
    # flag). The agent never creates a confidence value.
    confidence_bp: StrictInt | None = Field(default=None, ge=0, le=10000)
    confidence_calibrated: bool | None = None
    source_profile: str | None = None
    source_location: str | None = None
    version_ref: str | None = None  # palm: knowledge version; astrology: ruleset id@version
    fact_refs: tuple[str, ...] = ()
    conflict_ids: tuple[str, ...] = ()
    bundle_ref: str
    bundle_production_ready: bool | None = None

    @model_validator(mode="after")
    def _id(self) -> EvidenceRecord:
        if not _ID_RE.match(self.evidence_id):
            raise ValueError("evidence_id must match [A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
        return self

    @property
    def reference_kind(self) -> ReferenceKind:
        if self.evidence_class is EvidenceClass.RULE_EVALUATION:
            return ReferenceKind.RULE
        if self.evidence_class is EvidenceClass.CONTEXT_STATUS:
            return ReferenceKind.STATUS
        return ReferenceKind.FACT


class MissingCapability(_Frozen):
    capability: EvidenceCapability
    required: bool
    reason: str


class AgentContext(_Frozen):
    """The deterministic, typed context. The categories stay separate until the LLM request."""

    context_version: str
    request_id: str
    domain: Domain
    intent: Intent
    language: LLMLanguage
    facts: tuple[EvidenceRecord, ...]
    rule_evaluations: tuple[EvidenceRecord, ...]
    statuses: tuple[EvidenceRecord, ...]
    missing: tuple[MissingCapability, ...] = ()
    trimmed_count: int = Field(default=0, ge=0)
    restrictions: tuple[str, ...] = ()  # ProhibitedCategory values applied to this domain
    bundle_refs: tuple[str, ...] = ()
    version_refs: tuple[str, ...] = ()
    context_hash: str


class AgentStep(_Frozen):
    step_id: str
    operation: Literal["COLLECT_EVIDENCE", "ASSESS_SUFFICIENCY", "NARRATE"]
    tool_name: str | None = None
    capabilities: tuple[EvidenceCapability, ...] = ()


class AgentPlan(_Frozen):
    plan_version: str
    domain: Domain
    intent: Intent
    steps: tuple[AgentStep, ...] = Field(max_length=16)
    required: tuple[EvidenceCapability, ...] = ()
    desired: tuple[EvidenceCapability, ...] = ()
    plan_hash: str


class NarrationClaim(_Frozen):
    claim_id: str
    text: str = Field(min_length=1, max_length=2000)
    claim_type: ClaimType
    domain: Domain
    references: tuple[EvidenceReference, ...]
    # Copied from the referenced evidence by the agent, never produced by the model.
    source_profiles: tuple[str, ...] = ()
    source_locations: tuple[str, ...] = ()
    version_refs: tuple[str, ...] = ()
    uncertainty: tuple[UncertaintyFlag, ...] = ()
    min_confidence_bp: StrictInt | None = Field(default=None, ge=0, le=10000)
    verification: VerificationState = VerificationState.UNVERIFIED
    verified_by: str | None = None

    @model_validator(mode="after")
    def _grounded(self) -> NarrationClaim:
        if self.claim_type is not ClaimType.LIMITATION and not self.references:
            raise ValueError("a non-limitation claim needs at least one evidence reference")
        if any(r.domain is not self.domain for r in self.references):
            raise ValueError("a claim may only cite evidence of its own domain")
        if self.verification is VerificationState.VERIFIED and not self.verified_by:
            raise ValueError("VERIFIED requires verified_by (Phase 16 only)")
        return self


class NarrationSection(_Frozen):
    heading: str = Field(min_length=1, max_length=200)
    claims: tuple[NarrationClaim, ...] = Field(min_length=1)


class Disclaimer(_Frozen):
    code: DisclaimerCode
    text: str  # localized for the requested language; the code is the machine-readable part


class PolicyMetadata(_Frozen):
    policy_version: str
    domain: Domain
    restricted_categories: tuple[str, ...] = ()
    request_screened: bool = True
    output_screened: bool = True
    injection_suspected: bool = False


class AgentTrace(_Frozen):
    """Content-free operational metadata: identifiers, hashes, counts, versions."""

    agent_version: str
    plan_hash: str | None = None
    context_hash: str | None = None
    llm_request_hash: str | None = None
    prompt_version: str | None = None
    task_id: str | None = None
    schema_id: str = NARRATION_SCHEMA_ID
    generation_config_version: str | None = None
    llm_provenance: ModelProvenance | None = None
    steps_executed: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    llm_calls: int = Field(default=0, ge=0)
    retries: int = Field(default=0, ge=0)
    latency_ms: float = Field(default=0.0, ge=0.0)
    version_refs: tuple[str, ...] = ()
    bundle_refs: tuple[str, ...] = ()
    # Generation is stochastic unless the runtime guarantees otherwise (Phase 14): say so. It is
    # True only for the scripted test runtime, which is deterministic by construction.
    generation_deterministic: bool = False
    # Phase 14's script heuristic for the requested language (PASS, FAIL, NOT_CHECKED); it is not
    # a quality measure.
    language_check: str | None = None


class NarrationResponse(_Frozen):
    schema_version: str = AGENT_CONTRACT_VERSION
    request_id: str
    language: LLMLanguage
    domain: Domain | None = None
    intent: Intent | None = None
    status: AgentStatus
    sections: tuple[NarrationSection, ...] = ()
    missing: tuple[MissingCapability, ...] = ()
    disclaimers: tuple[Disclaimer, ...] = ()
    policy: PolicyMetadata | None = None
    trace: AgentTrace
    error: AgentError | None = None
    # A localized, deterministic message for the user on a refusal, degradation or failure. It
    # never contains prompts, model internals, policy text or evidence.
    user_message: str | None = None
    verification: VerificationState = VerificationState.UNVERIFIED
    verified_by: str | None = None

    @model_validator(mode="after")
    def _rules(self) -> NarrationResponse:
        ok = self.status in {AgentStatus.COMPLETED, AgentStatus.DEGRADED}
        if ok and self.error is not None and self.status is AgentStatus.COMPLETED:
            raise ValueError("a COMPLETED response has no error")
        if self.status is AgentStatus.FAILED and (self.error is None or self.sections):
            raise ValueError("a FAILED response has an error and no sections")
        if self.status is AgentStatus.REFUSED and self.sections:
            raise ValueError("a REFUSED response has no sections")
        if self.status is AgentStatus.COMPLETED and not self.sections:
            raise ValueError("a COMPLETED response has sections")
        if self.verification is VerificationState.VERIFIED and not self.verified_by:
            raise ValueError("VERIFIED requires verified_by (Phase 16 only)")
        return self

    @property
    def claims(self) -> tuple[NarrationClaim, ...]:
        """Every claim, in order: the verification-ready list Phase 16 consumes."""
        return tuple(c for s in self.sections for c in s.claims)
