"""The agent orchestrator: one bounded, straight-line pass from request to narration.

    request -> screen -> intent/domain -> plan -> collect evidence (allow-listed tools)
            -> assemble context -> sufficiency -> LLM call (Phase 14) -> ground -> response

There is no loop over plans, no recursion, no model-chosen tool and no arbitrary execution: the plan
is a static preset, each tool runs at most once, and the LLM is called at most ``max_llm_calls``
times (a retry happens only for a typed retryable failure, or for a grounding failure when the
generation samples; greedy decoding would repeat itself). Every expected failure is a typed
``NarrationResponse``. The agent never falls back to another model or any hosted API, never
computes a fact, and never marks anything verified (that is Phase 16).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from pandit_contracts.agent import (
    AgentContext,
    AgentErrorCode,
    AgentRequest,
    AgentStatus,
    AgentTrace,
    ClaimType,
    Disclaimer,
    Domain,
    EvidenceCapability,
    EvidenceRecord,
    Intent,
    NarrationClaim,
    NarrationResponse,
    NarrationSection,
    PolicyMetadata,
)
from pandit_contracts.llm import LLMErrorCode, ModelProvenance, Readiness
from pandit_shared.logging import bind_request_id

from pandit_agent._version import __version__
from pandit_agent.llm.provider import LLMProvider
from pandit_agent.llm.settings import generation_profile
from pandit_agent.orchestration import i18n
from pandit_agent.orchestration.context import assemble_context
from pandit_agent.orchestration.errors import AgentFailure
from pandit_agent.orchestration.intent import IntentError, resolve
from pandit_agent.orchestration.memory import ConversationMemory
from pandit_agent.orchestration.narration import ground_narration, limitation_section
from pandit_agent.orchestration.observability import log_event
from pandit_agent.orchestration.planner import build_plan
from pandit_agent.orchestration.policy import (
    POLICY_VERSION,
    DomainPolicy,
    disclaimers_for,
    policy_for,
    screen_request,
)
from pandit_agent.orchestration.prompts import TASK_VERSION, build_llm_request
from pandit_agent.orchestration.tools import ToolRegistry, run_tool

_LLM_ERROR_MAP: dict[LLMErrorCode, AgentErrorCode] = {
    LLMErrorCode.MODEL_UNAVAILABLE: AgentErrorCode.LLM_UNAVAILABLE,
    LLMErrorCode.MODEL_LOAD_FAILURE: AgentErrorCode.LLM_UNAVAILABLE,
    LLMErrorCode.RUNTIME_UNAVAILABLE: AgentErrorCode.LLM_UNAVAILABLE,
    LLMErrorCode.GPU_UNAVAILABLE: AgentErrorCode.LLM_UNAVAILABLE,
    LLMErrorCode.INSUFFICIENT_RESOURCES: AgentErrorCode.LLM_UNAVAILABLE,
    LLMErrorCode.ENDPOINT_NOT_PERMITTED: AgentErrorCode.LLM_UNAVAILABLE,
    LLMErrorCode.GENERATION_TIMEOUT: AgentErrorCode.LLM_TIMEOUT,
    LLMErrorCode.MALFORMED_STRUCTURED_OUTPUT: AgentErrorCode.LLM_STRUCTURED_OUTPUT_FAILURE,
    LLMErrorCode.SCHEMA_MISMATCH: AgentErrorCode.LLM_STRUCTURED_OUTPUT_FAILURE,
    LLMErrorCode.POLICY_VIOLATION: AgentErrorCode.POLICY_REJECTION,
    LLMErrorCode.UNSUPPORTED_LANGUAGE: AgentErrorCode.UNSUPPORTED_LANGUAGE,
    LLMErrorCode.CONTEXT_TOO_LARGE: AgentErrorCode.CONTEXT_TOO_LARGE,
    LLMErrorCode.INVALID_REQUEST: AgentErrorCode.INVALID_REQUEST,
}


_STRUCTURED_FAILURES = frozenset(
    {LLMErrorCode.MALFORMED_STRUCTURED_OUTPUT, LLMErrorCode.SCHEMA_MISMATCH}
)


def _budget_ladder(max_items: int) -> tuple[int, ...]:
    """Evidence budgets to try: the configured one, then half, then a quarter (never below 4)."""
    ladder = (max_items, max(4, max_items // 2), max(4, max_items // 4))
    return tuple(dict.fromkeys(b for b in ladder if b <= max_items))


def map_llm_error(code: LLMErrorCode) -> AgentErrorCode:
    return _LLM_ERROR_MAP.get(code, AgentErrorCode.LLM_FAILURE)


@dataclass(frozen=True)
class AgentConfig:
    config_version: str = "pj-agent-config-1"
    max_llm_calls: int = 2
    max_evidence_items: int = 120

    def __post_init__(self) -> None:
        if not 1 <= self.max_llm_calls <= 3:
            raise ValueError("max_llm_calls must be between 1 and 3")
        if not 1 <= self.max_evidence_items <= 200:
            raise ValueError("max_evidence_items must be between 1 and 200 (the Phase 14 limit)")


@dataclass
class _State:
    domain: Domain | None = None
    intent: Intent | None = None
    plan_hash: str | None = None
    context_hash: str | None = None
    llm_request_hash: str | None = None
    prompt_version: str | None = None
    generation_config_version: str | None = None
    provenance: ModelProvenance | None = None
    language_check: str | None = None
    steps: int = 0
    tool_calls: int = 0
    llm_calls: int = 0
    retries: int = 0
    version_refs: tuple[str, ...] = ()
    bundle_refs: tuple[str, ...] = ()
    injection: bool = False
    policy: DomainPolicy | None = None
    calls_per_tool: dict[str, int] = field(default_factory=dict)


class AgentOrchestrator:
    def __init__(
        self,
        llm: LLMProvider,
        tools: ToolRegistry,
        *,
        memory: ConversationMemory | None = None,
        config: AgentConfig | None = None,
    ) -> None:
        self._llm = llm
        self._tools = tools
        self._memory = memory
        self._config = config or AgentConfig()

    # -- public ----------------------------------------------------------------------------

    def run(self, request: AgentRequest) -> NarrationResponse:
        started = time.perf_counter()
        state = _State()
        bind_request_id(request.request_id)
        try:
            response = self._run(request, state, started)
        except AgentFailure as failure:
            response = self._terminal(request, state, started, failure)
        except Exception:  # contain anything unexpected: never leak a raw error or its content
            response = self._terminal(
                request,
                state,
                started,
                AgentFailure(AgentErrorCode.INTERNAL_ERROR, "an internal error occurred"),
            )
        finally:
            bind_request_id(None)
        self._log(request, response)
        return response

    # -- pipeline --------------------------------------------------------------------------

    def _run(self, request: AgentRequest, state: _State, started: float) -> NarrationResponse:
        snapshot = (
            self._memory.recall(request.conversation_id)
            if self._memory is not None and request.conversation_id
            else None
        )
        try:
            resolved = resolve(request, snapshot)
        except IntentError as exc:
            raise AgentFailure(
                AgentErrorCode.INVALID_REQUEST, "the intent does not fit the domain"
            ) from exc
        state.domain, state.intent = resolved.domain, resolved.intent
        policy = policy_for(resolved.domain)
        state.policy = policy

        screen = screen_request(request.user_text, policy)
        if screen.injection:
            state.injection = True
            raise AgentFailure(
                AgentErrorCode.PROMPT_INJECTION, "the request tries to change the agent's rules"
            )
        if screen.unsafe:
            raise AgentFailure(AgentErrorCode.UNSAFE_REQUEST, "the request is outside policy")

        plan = build_plan(resolved.domain, resolved.intent, self._tools)
        state.plan_hash = plan.plan_hash

        records: list[EvidenceRecord] = []
        provided: set[EvidenceCapability] = set()
        failed_optional: set[EvidenceCapability] = set()
        for step in plan.steps:
            if step.operation != "COLLECT_EVIDENCE":
                continue
            assert step.tool_name is not None
            state.steps += 1
            tool = self._tools.get(step.tool_name)
            used = state.calls_per_tool.get(step.tool_name, 0)
            if used >= tool.spec.max_calls:
                raise AgentFailure(
                    AgentErrorCode.ORCHESTRATION_LIMIT, "a tool call budget was exhausted"
                )
            state.calls_per_tool[step.tool_name] = used + 1
            state.tool_calls += 1
            wanted = frozenset(step.capabilities)
            try:
                result = run_tool(tool, wanted)
            except AgentFailure:
                if wanted & set(plan.required):
                    raise
                failed_optional |= wanted
                continue
            records.extend(result.records)
            provided |= set(wanted & tool.spec.capabilities)

        state.steps += 1  # ASSESS_SUFFICIENCY
        budgets = _budget_ladder(self._config.max_evidence_items)
        context: AgentContext | None = None
        sections: tuple[NarrationSection, ...] = ()
        for index, budget in enumerate(budgets):
            context = assemble_context(
                request_id=request.request_id,
                plan=plan,
                language=request.language,
                policy=policy,
                records=records,
                provided=frozenset(provided),
                max_items=budget,
            )
            state.context_hash = context.context_hash
            state.version_refs, state.bundle_refs = context.version_refs, context.bundle_refs
            if index == 0:
                if not records:
                    raise AgentFailure(AgentErrorCode.MISSING_EVIDENCE, "no evidence was available")
                if any(m.required for m in context.missing):
                    raise AgentFailure(
                        AgentErrorCode.INSUFFICIENT_EVIDENCE, "required evidence is not available"
                    )
                state.steps += 1  # NARRATE
            try:
                sections = self._narrate(request, state, context, policy)
                break
            except AgentFailure as failure:
                # The model's window is smaller than the context: re-assemble with a smaller
                # evidence budget (priority-trimmed and recorded), a bounded number of times.
                if failure.code is AgentErrorCode.CONTEXT_TOO_LARGE and index + 1 < len(budgets):
                    state.retries += 1
                    continue
                raise
        assert context is not None
        extra = limitation_section(
            context, request.language, first_index=sum(len(s.claims) for s in sections)
        )
        all_sections = (*sections, extra) if extra is not None else sections
        not_ready = any(r.bundle_production_ready is False for r in records)
        disclaimers = tuple(
            Disclaimer(code=c, text=i18n.disclaimer_text(c, request.language))
            for c in disclaimers_for(
                policy, resolved.intent, request.user_text, evidence_not_production_ready=not_ready
            )
        )
        degraded = bool(context.missing) or context.trimmed_count > 0
        if self._memory is not None and request.conversation_id:
            self._memory.remember(
                request.conversation_id, resolved.domain, resolved.intent, request.language
            )
        return NarrationResponse(
            request_id=request.request_id,
            language=request.language,
            domain=resolved.domain,
            intent=resolved.intent,
            status=AgentStatus.DEGRADED if degraded else AgentStatus.COMPLETED,
            sections=all_sections,
            missing=context.missing,
            disclaimers=disclaimers,
            policy=self._policy_meta(policy, state),
            trace=self._trace(state, started),
        )

    def _narrate(
        self, request: AgentRequest, state: _State, context: AgentContext, policy: DomainPolicy
    ) -> tuple[NarrationSection, ...]:
        health = self._llm.health()
        if health.state is not Readiness.MODEL_READY or health.model_id is None:
            raise AgentFailure(AgentErrorCode.LLM_UNAVAILABLE, "the language model is not ready")
        generation = generation_profile(request.generation_profile)
        llm_request = build_llm_request(
            request, context, model_id=health.model_id, generation=generation
        )
        state.llm_request_hash = llm_request.request_hash()
        state.prompt_version = TASK_VERSION
        state.generation_config_version = generation.config_version
        sampling = generation.temperature > 0.0
        last: AgentFailure | None = None
        for attempt in range(self._config.max_llm_calls):
            if attempt:
                state.retries += 1
            state.llm_calls += 1
            response = self._llm.generate(llm_request)
            state.provenance = response.provenance
            if response.status.value == "OK":
                state.language_check = response.language_check.value
                state.prompt_version = response.prompt_version or TASK_VERSION
                try:
                    return ground_narration(response.structured, context, policy)
                except AgentFailure as failure:
                    last = failure
                    grounding = failure.code is AgentErrorCode.NARRATION_GROUNDING_FAILURE
                    if grounding and sampling:
                        continue
                    raise
            assert response.error is not None
            last = AgentFailure(
                map_llm_error(response.error.code),
                "the language model did not return a usable result",
                retryable=response.error.retryable,
            )
            # A structured-output failure is retried only when sampling (greedy decoding would
            # repeat itself); availability and timeout failures are retried when typed retryable.
            structured = response.error.code in _STRUCTURED_FAILURES
            if response.error.retryable and (sampling or not structured):
                continue
            raise last
        assert last is not None
        raise last

    # -- responses -------------------------------------------------------------------------

    def _terminal(
        self, request: AgentRequest, state: _State, started: float, failure: AgentFailure
    ) -> NarrationResponse:
        code = failure.code
        refused = code in {AgentErrorCode.UNSAFE_REQUEST, AgentErrorCode.PROMPT_INJECTION}
        degraded = code in {AgentErrorCode.INSUFFICIENT_EVIDENCE, AgentErrorCode.MISSING_EVIDENCE}
        status = (
            AgentStatus.REFUSED
            if refused
            else AgentStatus.DEGRADED
            if degraded
            else AgentStatus.FAILED
        )
        sections: tuple[NarrationSection, ...] = ()
        if degraded and state.domain is not None:
            sections = self._insufficiency_sections(request, state)
        return NarrationResponse(
            request_id=request.request_id,
            language=request.language,
            domain=state.domain,
            intent=state.intent,
            status=status,
            sections=sections,
            policy=self._policy_meta(state.policy, state) if state.policy else None,
            trace=self._trace(state, started),
            error=failure.to_error(),
            user_message=i18n.user_message_for(code, request.language),
        )

    def _insufficiency_sections(
        self, request: AgentRequest, state: _State
    ) -> tuple[NarrationSection, ...]:
        assert state.domain is not None
        claim = NarrationClaim(
            claim_id="C001",
            text=i18n.text(i18n.Message.INSUFFICIENT_EVIDENCE, request.language),
            claim_type=ClaimType.LIMITATION,
            domain=state.domain,
            references=(),
        )
        return (
            NarrationSection(
                heading=i18n.text(i18n.Message.LIMITATIONS_HEADING, request.language),
                claims=(claim,),
            ),
        )

    @staticmethod
    def _policy_meta(policy: DomainPolicy | None, state: _State) -> PolicyMetadata:
        assert policy is not None
        return PolicyMetadata(
            policy_version=POLICY_VERSION,
            domain=policy.domain,
            restricted_categories=tuple(c.value for c in policy.output_restrictions),
            injection_suspected=state.injection,
        )

    def _trace(self, state: _State, started: float) -> AgentTrace:
        provenance = state.provenance
        deterministic = provenance is not None and not provenance.is_real_model
        return AgentTrace(
            agent_version=__version__,
            plan_hash=state.plan_hash,
            context_hash=state.context_hash,
            llm_request_hash=state.llm_request_hash,
            prompt_version=state.prompt_version,
            task_id=TASK_VERSION,
            generation_config_version=state.generation_config_version,
            llm_provenance=provenance,
            steps_executed=state.steps,
            tool_calls=state.tool_calls,
            llm_calls=state.llm_calls,
            retries=state.retries,
            latency_ms=(time.perf_counter() - started) * 1000.0,
            version_refs=state.version_refs,
            bundle_refs=state.bundle_refs,
            generation_deterministic=deterministic,
            language_check=state.language_check,
        )

    def _log(self, request: AgentRequest, response: NarrationResponse) -> None:
        t = response.trace
        prov = t.llm_provenance
        log_event(
            event="agent_request",
            request_id=response.request_id,
            domain=response.domain.value if response.domain else None,
            intent=response.intent.value if response.intent else None,
            language=request.language.value,
            status=response.status.value,
            error_code=response.error.code.value if response.error else None,
            latency_ms=round(t.latency_ms, 3),
            steps=t.steps_executed,
            tool_calls=t.tool_calls,
            llm_calls=t.llm_calls,
            retries=t.retries,
            plan_hash=t.plan_hash,
            context_hash=t.context_hash,
            llm_request_hash=t.llm_request_hash,
            prompt_version=t.prompt_version,
            task_id=t.task_id,
            schema_id=t.schema_id,
            model_id=prov.model_id if prov else None,
            model_version=prov.model_revision if prov else None,
            version_refs=list(t.version_refs) or None,
            bundle_refs=list(t.bundle_refs) or None,
            claims=len(response.claims),
            injection_suspected=response.policy.injection_suspected if response.policy else None,
            agent_version=t.agent_version,
        )
