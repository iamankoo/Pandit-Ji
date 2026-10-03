"""Shared helpers for the Phase 15 agent tests.

The LLM behind every orchestrator built here is the real Phase 14 ``LLMService`` over the scripted
``MockRuntime``: a deterministic test double, not a language model. Nothing in these tests says
anything about real model quality.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from typing import Any

from llm_helpers import MOCK_MODEL_ID, make_service
from pandit_contracts.agent import (
    AgentRequest,
    Domain,
    EvidenceCapability,
    EvidenceClass,
    EvidenceRecord,
    Intent,
)
from pandit_contracts.llm import LLMLanguage

from pandit_agent.llm.mock_runtime import MockRuntime, Scripted
from pandit_agent.llm.service import LLMService
from pandit_agent.orchestration import (
    AgentConfig,
    AgentOrchestrator,
    InMemoryConversationMemory,
    ToolRegistry,
    narration_schema_registry,
)
from pandit_agent.orchestration.tools import ToolResult, ToolSpec

BUNDLE = "b" * 64
KV = "KV-a21c2c040abe9663"
C = EvidenceCapability


def rec(
    evidence_id: str,
    cls: EvidenceClass,
    *,
    domain: Domain = Domain.PALMISTRY,
    kind: str = "K",
    text: str = "t",
    status: str | None = None,
    conf: int | None = None,
    calibrated: bool | None = None,
    profile: str | None = None,
    location: str | None = None,
    version: str | None = None,
    fact_refs: tuple[str, ...] = (),
    conflicts: tuple[str, ...] = (),
    ready: bool | None = None,
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence_id,
        domain=domain,
        evidence_class=cls,
        kind=kind,
        text=text,
        status=status,
        confidence_bp=conf,
        confidence_calibrated=calibrated,
        source_profile=profile,
        source_location=location,
        version_ref=version,
        fact_refs=fact_refs,
        conflict_ids=conflicts,
        bundle_ref=BUNDLE,
        bundle_production_ready=ready,
    )


def palm_records() -> tuple[EvidenceRecord, ...]:
    return (
        rec(
            "bundle.A1",
            EvidenceClass.CONTEXT_STATUS,
            kind="PALM_BUNDLE_STATUS",
            status="NOT_PRODUCTION_READY",
            version=KV,
            ready=False,
        ),
        rec(
            "F_SIDE",
            EvidenceClass.OBSERVED_FACT,
            kind="HAND_SIDE",
            status="CLEAR",
            conf=9000,
            calibrated=False,
            version=KV,
            ready=False,
        ),
        rec(
            "F_PART",
            EvidenceClass.OBSERVED_FACT,
            kind="LINE",
            status="PARTIAL",
            conf=4000,
            calibrated=False,
            version=KV,
            ready=False,
        ),
        rec(
            "F_DERIVED",
            EvidenceClass.DERIVED_FACT,
            kind="RATIO",
            status="CLEAR",
            conf=8000,
            calibrated=False,
            fact_refs=("F_SIDE",),
            version=KV,
            ready=False,
        ),
        rec(
            "R_A",
            EvidenceClass.RULE_EVALUATION,
            kind="PALM_RULE",
            status="TRIGGERED",
            profile="PALM_HA_SIGNS_654_684",
            location="p.654",
            version=KV,
            fact_refs=("F_SIDE",),
            conflicts=("CONFLICT_X",),
            ready=False,
        ),
        rec(
            "R_B",
            EvidenceClass.RULE_EVALUATION,
            kind="PALM_RULE",
            status="TRIGGERED",
            profile="PALM_CHEIRO_FIXTURE",
            location="p.12",
            version=KV,
            conflicts=("CONFLICT_X",),
            ready=False,
        ),
        rec(
            "R_C",
            EvidenceClass.RULE_EVALUATION,
            kind="PALM_RULE",
            status="TRIGGERED",
            profile="PALM_HA_SIGNS_654_684",
            location="p.700",
            version=KV,
            ready=False,
        ),
        rec(
            "R_NE",
            EvidenceClass.RULE_EVALUATION,
            kind="PALM_RULE",
            status="NOT_EVALUABLE",
            profile="PALM_HA_SIGNS_654_684",
            location="p.701",
            version=KV,
            ready=False,
        ),
    )


def astro_records() -> tuple[EvidenceRecord, ...]:
    a = Domain.ASTROLOGY
    ruleset = "PANDIT_JI_VEDIC_PHASE6@1.0.0"
    return (
        rec(
            "astro.config",
            EvidenceClass.CONTEXT_STATUS,
            domain=a,
            status="CONFIGURED",
            version=ruleset,
        ),
        rec(
            "astro.lagna",
            EvidenceClass.CALCULATED_FACT,
            domain=a,
            kind="LAGNA",
            text="lagna_sign=ARIES",
            version=ruleset,
        ),
        rec(
            "astro.planet.sun",
            EvidenceClass.CALCULATED_FACT,
            domain=a,
            kind="PLANET_PLACEMENT",
            text="body=SUN; sign=ARIES; house=1",
            version=ruleset,
        ),
        rec(
            "YOGA_1",
            EvidenceClass.RULE_EVALUATION,
            domain=a,
            kind="ASTRO_RULE",
            status="TRIGGERED",
            profile="BPHS",
            location="ch.36",
            version=ruleset,
        ),
        rec(
            "YOGA_2",
            EvidenceClass.RULE_EVALUATION,
            domain=a,
            kind="ASTRO_RULE",
            status="NOT_TRIGGERED",
            profile="BPHS",
            location="ch.36",
            version=ruleset,
        ),
    )


class StaticTool:
    """A scripted evidence tool for tests (the agent's real adapters have their own tests)."""

    def __init__(
        self,
        name: str,
        domain: Domain,
        capabilities: frozenset[EvidenceCapability],
        records: Sequence[EvidenceRecord],
        *,
        timeout_s: float = 5.0,
        max_calls: int = 1,
        sleep_s: float = 0.0,
        error: Exception | None = None,
    ) -> None:
        self._spec = ToolSpec(name, domain, capabilities, timeout_s, max_calls)
        self._records = tuple(records)
        self._sleep = sleep_s
        self._error = error
        self.calls: list[frozenset[EvidenceCapability]] = []

    @property
    def spec(self) -> ToolSpec:
        return self._spec

    def invoke(self, capabilities: frozenset[EvidenceCapability]) -> ToolResult:
        self.calls.append(capabilities)
        if self._sleep:
            time.sleep(self._sleep)
        if self._error is not None:
            raise self._error
        return ToolResult(self._records)


def palm_tool(**kw: Any) -> StaticTool:
    return StaticTool(
        "palm.static",
        Domain.PALMISTRY,
        frozenset({C.PALM_FACTS, C.PALM_RULES}),
        kw.pop("records", palm_records()),
        **kw,
    )


def astro_tool(**kw: Any) -> StaticTool:
    return StaticTool(
        "astro.static",
        Domain.ASTROLOGY,
        frozenset({C.ASTRO_CHART, C.ASTRO_RULES}),
        kw.pop("records", astro_records()),
        **kw,
    )


def claim(text: str, ctype: str, ids: Sequence[str]) -> dict[str, Any]:
    return {"text": text, "claim_type": ctype, "evidence_ids": list(ids)}


def narration(*sections: tuple[str, Sequence[dict[str, Any]]]) -> str:
    return json.dumps(
        {"sections": [{"heading": h, "claims": list(cs)} for h, cs in sections]},
        ensure_ascii=False,
    )


GOOD_PALM = narration(
    (
        "What was observed",
        [
            claim(
                "The hand side was observed with clear visibility.", "OBSERVED_FEATURE", ["F_SIDE"]
            ),
            claim("A ratio was derived from the hand side.", "DERIVED_FEATURE", ["F_DERIVED"]),
        ],
    ),
    (
        "Traditional reading",
        [
            claim(
                "One tradition reads this sign as a traditional indication.",
                "TRADITIONAL_INTERPRETATION",
                ["R_C", "F_SIDE"],
            ),
            claim("One rule could not be evaluated.", "LIMITATION", ["R_NE"]),
        ],
    ),
)

GOOD_ASTRO = narration(
    (
        "Chart facts",
        [claim("The Sun is placed in Aries.", "CALCULATION_FACT", ["astro.planet.sun"])],
    ),
    (
        "Traditional reading",
        [claim("A traditional yoga is present.", "TRADITIONAL_INTERPRETATION", ["YOGA_1"])],
    ),
)


def request(
    text: str = "What does my hand show?",
    *,
    domain: Domain | None = Domain.PALMISTRY,
    language: LLMLanguage = LLMLanguage.EN,
    request_id: str = "areq-1",
    intent: Intent | None = None,
    conversation_id: str | None = None,
    profile: str = "deterministic",
) -> AgentRequest:
    return AgentRequest(
        request_id=request_id,
        language=language,
        user_text=text,
        domain=domain,
        intent_hint=intent,
        conversation_id=conversation_id,
        generation_profile=profile,  # type: ignore[arg-type]
    )


def make_agent(
    script: Sequence[Scripted] = (),
    *,
    tools: Sequence[Any] | None = None,
    memory: InMemoryConversationMemory | None = None,
    config: AgentConfig | None = None,
    start_llm: bool = True,
    runtime: MockRuntime | None = None,
    llm_factory: Callable[[], Any] | None = None,
    **llm_kwargs: Any,
) -> tuple[AgentOrchestrator, MockRuntime, LLMService]:
    service, rt = make_service(
        script,
        start=start_llm,
        runtime=runtime,
        schemas=narration_schema_registry(),
        **llm_kwargs,
    )
    registry = ToolRegistry(tools if tools is not None else (palm_tool(), astro_tool()))
    llm = llm_factory() if llm_factory else service
    return AgentOrchestrator(llm, registry, memory=memory, config=config), rt, service


__all__ = ["MOCK_MODEL_ID"]
