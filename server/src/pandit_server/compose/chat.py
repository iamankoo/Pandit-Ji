"""The chat pipeline: evidence -> agent (Phase 15) -> verifier (Phase 16) -> bounded regeneration.

Release behaviour is the verifier's, never the model's or this module's:

* ``APPROVE`` / ``RELEASE_VERIFIED_ONLY``: release the verified claims, strip everything else;
* ``REGENERATE`` (a wrong, blocked or invalid claim, or nothing verified): ask the agent again, at
  most ``max_regenerations`` more times; claims the verifier already marked ``VERIFIED`` in any
  attempt are kept (identified by their text hash) and anything not verified is never released;
* ``NOTHING_TO_VERIFY`` (a refusal, a failure, an empty narration): nothing is released.

If the attempts are exhausted with no verified claim the answer is a typed failure. Every attempt
re-applies the agent's policy; only counts and statuses are recorded, never text.
"""

from __future__ import annotations

import datetime as dt
import functools
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pandit_agent.orchestration import (
    AgentConfig,
    AgentOrchestrator,
    AstrologyBundleTool,
    DomainAnalysisTool,
    ToolRegistry,
)
from pandit_agent.orchestration.domain import classify_life_domain
from pandit_contracts.agent import (
    AgentErrorCode,
    AgentRequest,
    AgentStatus,
    Domain,
    NarrationResponse,
)
from pandit_contracts.domain import DomainAnalysisRequest, DomainAnalysisResult, LifeDomain
from pandit_contracts.llm import LLMLanguage
from pandit_contracts.verification import ReleaseAction, VerificationStatus
from pandit_knowledge.content import DEFAULT_RULES_DIR
from pandit_knowledge.domain_content import (
    DEFAULT_DOMAIN_CONTENT_DIR,
    DOMAIN_KNOWLEDGE_STANDARDS_VERSION,
    load_domain_content,
)
from pandit_knowledge.embeddings import HashingEmbeddingProvider
from pandit_knowledge.ingestion import KnowledgeBuilder
from pandit_knowledge.store import InMemoryKnowledgeStore
from pandit_rule_engine.adapters import facts_from_kundli
from pandit_rule_engine.domain import evaluate_domain, load_domain_ruleset, varga_from_kundli
from pandit_rule_engine.engine import RuleEngine
from pandit_verification import TrustedEvidence, Verifier, VerifierConfig, apply_report

from pandit_server.compose.trust import PinnedMethodology, register_domain_result

DOMAIN_RULES_DIR = Path(
    os.environ.get("DOMAIN_RULES_DIR")
    or Path(__file__).resolve().parents[4] / "services" / "rule-engine" / "domain_rules"
)


@functools.lru_cache(maxsize=1)
def rule_engine() -> RuleEngine:
    return RuleEngine.from_directory(DEFAULT_RULES_DIR)


@functools.lru_cache(maxsize=1)
def domain_ruleset() -> Any:
    return load_domain_ruleset(DOMAIN_RULES_DIR)


@functools.lru_cache(maxsize=1)
def domain_knowledge_version() -> str:
    built = KnowledgeBuilder(
        InMemoryKnowledgeStore(), HashingEmbeddingProvider(), DOMAIN_KNOWLEDGE_STANDARDS_VERSION
    ).build(load_domain_content(DEFAULT_DOMAIN_CONTENT_DIR))
    return built.version_id


def pinned_methodology() -> PinnedMethodology:
    return PinnedMethodology(domain_knowledge_version(), domain_ruleset().content_hash)


@dataclass
class Evidence:
    """Everything deterministic that the pipeline needs for one request."""

    bundle: Any
    domain_result: DomainAnalysisResult | None
    trusted: TrustedEvidence
    tools: list[Any]
    life_domain: LifeDomain | None


def build_evidence(
    *,
    kundli_json: dict[str, Any],
    dasha_json: dict[str, Any] | None,
    message: str,
    adult_confirmed: bool | None,
    analysis_id: str,
    now: dt.datetime | None = None,
    forced_domain: LifeDomain | None = None,
) -> Evidence:
    """Run the deterministic layers and register their outputs as trusted evidence."""
    bundle = rule_engine().evaluate_kundli(kundli_json, dasha_facts=dasha_json)
    trusted = TrustedEvidence().add_astrology(bundle)
    tools: list[Any] = [AstrologyBundleTool(bundle)]  # type: ignore[arg-type]
    life_domain = forced_domain or classify_life_domain(message)
    result: DomainAnalysisResult | None = None
    if life_domain is not None:
        instant = (now or dt.datetime.now(dt.timezone.utc)).replace(microsecond=0)
        request = DomainAnalysisRequest(
            analysis_id=analysis_id,
            domain=life_domain,
            subject_adult_confirmed=adult_confirmed,
            as_of_utc=instant.astimezone(dt.timezone.utc).isoformat(),
        )
        result = evaluate_domain(
            domain_ruleset(),
            request,
            facts_from_kundli(kundli_json),
            knowledge_version=domain_knowledge_version(),
            varga=varga_from_kundli(kundli_json),  # only the eight approved charts are read
            dasha=bundle.dasha,
            phase6_results={
                r.rule_id: str(getattr(r.status, "value", r.status)) for r in bundle.results
            },
        )
        register_domain_result(trusted, result, pinned_methodology())
        tools.append(DomainAnalysisTool(result))
    return Evidence(bundle, result, trusted, tools, life_domain)


# ---- the regeneration loop ----------------------------------------------------------------------


@dataclass
class Attempt:
    action: str
    counts: dict[str, int]
    agent_status: str
    error_code: str | None


@dataclass
class ChatOutcome:
    status: str  # "completed" | "degraded" | "refused" | "failed"
    claims: list[dict[str, Any]] = field(default_factory=list)
    disclaimers: list[str] = field(default_factory=list)
    attempts: list[Attempt] = field(default_factory=list)
    final_action: str = "NOTHING_TO_VERIFY"
    error_code: str | None = None
    user_message: str | None = None
    report_hash: str | None = None
    life_domain: str | None = None
    versions: dict[str, Any] = field(default_factory=dict)


_PROVIDER_FAILURES = {
    AgentErrorCode.LLM_UNAVAILABLE,
    AgentErrorCode.LLM_TIMEOUT,
    AgentErrorCode.LLM_FAILURE,
    AgentErrorCode.LLM_STRUCTURED_OUTPUT_FAILURE,
}


def _claim_dict(claim: Any) -> dict[str, Any]:
    return {
        "claim_id": claim.claim_id,
        "text": claim.text,
        "claim_type": claim.claim_type.value,
        "references": [
            {"evidence_id": r.evidence_id, "kind": r.kind.value, "bundle_ref": r.bundle_ref}
            for r in claim.references
        ],
        "verified_by": claim.verified_by,
    }


def run_verified_chat(
    *,
    llm: Any,
    evidence: Evidence,
    request: AgentRequest,
    max_regenerations: int,
    config: AgentConfig | None = None,
) -> ChatOutcome:
    verifier = Verifier(
        evidence.trusted,
        VerifierConfig(
            expected_ruleset_hashes=frozenset(
                {domain_ruleset().content_hash, evidence.bundle.versions.ruleset_content_hash}
            )
        ),
    )
    agent = AgentOrchestrator(llm, ToolRegistry(evidence.tools), config=config or AgentConfig())
    outcome = ChatOutcome(
        status="failed",
        life_domain=evidence.life_domain.value if evidence.life_domain else None,
    )
    if evidence.domain_result is not None:
        outcome.versions = {
            "knowledge_version": evidence.domain_result.versions.knowledge_version,
            "ruleset": evidence.domain_result.versions.ruleset_ref,
            "domain_status": evidence.domain_result.status.value,
        }
    kept: dict[str, dict[str, Any]] = {}  # claim_text_hash -> verified claim (insertion ordered)
    disclaimers: set[str] = set()
    last_report: Any = None
    for attempt_index in range(1 + max(0, max_regenerations)):
        narration: NarrationResponse = agent.run(
            request.model_copy(update={"request_id": f"{request.request_id}-a{attempt_index}"})
        )
        if narration.status is AgentStatus.REFUSED:
            outcome.attempts.append(Attempt("NOTHING_TO_VERIFY", {}, "REFUSED", None))
            outcome.status = "refused"
            outcome.user_message = narration.user_message
            outcome.error_code = narration.error.code.value if narration.error else None
            return outcome
        if narration.error is not None:
            # The agent could not answer (a failure, or an honest insufficiency). Only the
            # verifier's REGENERATE verdict loops; an agent-level result is final.
            code = narration.error.code
            outcome.attempts.append(
                Attempt("NOTHING_TO_VERIFY", {}, narration.status.value, code.value)
            )
            outcome.error_code = code.value
            outcome.user_message = narration.user_message
            if code in {AgentErrorCode.INSUFFICIENT_EVIDENCE, AgentErrorCode.MISSING_EVIDENCE}:
                outcome.status = "insufficient_evidence"
                return outcome
            break
        report = verifier.verify(narration)
        last_report = report
        counts: dict[str, int] = {}
        for item in report.claims:
            counts[item.status.value] = counts.get(item.status.value, 0) + 1
        action = report.release_action
        outcome.attempts.append(Attempt(action.value, counts, narration.status.value, None))
        outcome.final_action = action.value
        disclaimers.update(d.code.value for d in narration.disclaimers)
        verified = apply_report(narration, report)
        by_id = {r.claim_id: r for r in report.claims}
        for section in verified.sections:
            for claim in section.claims:
                result = by_id[claim.claim_id]
                if result.status is VerificationStatus.VERIFIED and result.claim_text_hash:
                    kept.setdefault(result.claim_text_hash, _claim_dict(claim))
        if action in {ReleaseAction.APPROVE, ReleaseAction.RELEASE_VERIFIED_ONLY}:
            break
        if action is ReleaseAction.NOTHING_TO_VERIFY:
            break
        # REGENERATE: loop again (bounded by the range)
    outcome.disclaimers = sorted(disclaimers)
    outcome.report_hash = getattr(last_report, "report_hash", None)
    if kept:
        outcome.claims = list(kept.values())
        outcome.status = (
            "completed" if outcome.final_action == ReleaseAction.APPROVE.value else "degraded"
        )
        outcome.error_code = None
    elif outcome.status == "failed" and outcome.error_code is None:
        outcome.error_code = "no_verified_content"
    return outcome


def language_of(value: str) -> LLMLanguage:
    return LLMLanguage[value]


__all__ = ["ChatOutcome", "Domain", "Evidence", "build_evidence", "run_verified_chat"]
