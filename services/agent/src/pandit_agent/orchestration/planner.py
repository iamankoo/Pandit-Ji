"""The bounded planner: intent -> a fixed, allow-listed plan.

The plan is a pure function of (domain, intent, the registry's tools). It is built from static
presets, not from model output, so it is deterministic and cannot be steered by user text. Every
step is one of three operations (collect evidence from a registered tool, assess sufficiency,
narrate), the number of steps is capped, each tool is called at most once, and there is no loop and
no recursion: the plan is a straight line.

A preset lists *required* capabilities (without them the agent answers with a structured
insufficiency, no model call) and *desired* ones (without them the narration states the limit).
The presets follow the worked example in ``Phases.md`` Phase 15 and ``docs/ARCHITECTURE.md``
section 8: a career question needs the chart, the rule results, the dasha and the transits.
Capabilities for which no tool exists (dasha, transit, compatibility in Phase 15) are reported as
missing; the agent does not compute them itself.
"""

from __future__ import annotations

import hashlib
import json

from pandit_contracts.agent import (
    AgentErrorCode,
    AgentPlan,
    AgentStep,
    Domain,
    EvidenceCapability,
    Intent,
)

from pandit_agent.orchestration.errors import AgentFailure
from pandit_agent.orchestration.tools import ToolRegistry

PLAN_VERSION = "pj-plan-1"
MAX_STEPS = 8

C = EvidenceCapability
_ASTRO_CORE = (C.ASTRO_CHART, C.ASTRO_RULES)

# intent -> (required, desired)
_PRESETS: dict[Intent, tuple[tuple[EvidenceCapability, ...], tuple[EvidenceCapability, ...]]] = {
    Intent.GENERAL: (_ASTRO_CORE, (C.ASTRO_DASHA,)),
    Intent.LOVE_RELATIONSHIP: (_ASTRO_CORE, (C.ASTRO_DASHA, C.ASTRO_TRANSIT)),
    Intent.MARRIAGE: (_ASTRO_CORE, (C.ASTRO_DASHA, C.ASTRO_TRANSIT)),
    Intent.CAREER: (_ASTRO_CORE, (C.ASTRO_DASHA, C.ASTRO_TRANSIT)),
    Intent.WEALTH: (_ASTRO_CORE, (C.ASTRO_DASHA, C.ASTRO_TRANSIT)),
    Intent.BUSINESS: (_ASTRO_CORE, (C.ASTRO_DASHA, C.ASTRO_TRANSIT)),
    Intent.DAILY_GUIDANCE: (_ASTRO_CORE, (C.ASTRO_TRANSIT,)),
    Intent.EDUCATION: (_ASTRO_CORE, (C.ASTRO_DASHA,)),
    Intent.TRAVEL: (_ASTRO_CORE, (C.ASTRO_DASHA, C.ASTRO_TRANSIT)),
    Intent.LIFE_ANALYSIS: (_ASTRO_CORE, (C.ASTRO_DASHA,)),
    Intent.COMPATIBILITY: ((C.ASTRO_COMPATIBILITY,), _ASTRO_CORE),
    Intent.TRANSIT: ((*_ASTRO_CORE, C.ASTRO_TRANSIT), (C.ASTRO_DASHA,)),
    Intent.DASHA: ((*_ASTRO_CORE, C.ASTRO_DASHA), (C.ASTRO_TRANSIT,)),
    Intent.PALM_OVERVIEW: ((C.PALM_FACTS, C.PALM_RULES), ()),
}


def capabilities_for(
    intent: Intent,
) -> tuple[tuple[EvidenceCapability, ...], tuple[EvidenceCapability, ...]]:
    return _PRESETS[intent]


def build_plan(domain: Domain, intent: Intent, registry: ToolRegistry) -> AgentPlan:
    required, desired = capabilities_for(intent)
    wanted = tuple(dict.fromkeys((*required, *desired)))
    steps: list[AgentStep] = []
    planned: dict[str, set[EvidenceCapability]] = {}
    for capability in wanted:
        for spec in registry.tools_for(capability, domain):
            planned.setdefault(spec.name, set()).add(capability)
            break  # one tool per capability: the first registered, in registry order
    for index, (tool_name, caps) in enumerate(planned.items(), start=1):
        steps.append(
            AgentStep(
                step_id=f"s{index}",
                operation="COLLECT_EVIDENCE",
                tool_name=tool_name,
                capabilities=tuple(sorted(caps, key=lambda c: c.value)),
            )
        )
    steps.append(AgentStep(step_id=f"s{len(steps) + 1}", operation="ASSESS_SUFFICIENCY"))
    steps.append(AgentStep(step_id=f"s{len(steps) + 1}", operation="NARRATE"))
    if len(steps) > MAX_STEPS:
        raise AgentFailure(AgentErrorCode.ORCHESTRATION_LIMIT, "the plan exceeds the step limit")
    body = {
        "plan_version": PLAN_VERSION,
        "domain": domain.value,
        "intent": intent.value,
        "steps": [s.model_dump(mode="json") for s in steps],
        "required": [c.value for c in required],
        "desired": [c.value for c in desired],
    }
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    return AgentPlan(
        plan_version=PLAN_VERSION,
        domain=domain,
        intent=intent,
        steps=tuple(steps),
        required=required,
        desired=desired,
        plan_hash=digest,
    )
