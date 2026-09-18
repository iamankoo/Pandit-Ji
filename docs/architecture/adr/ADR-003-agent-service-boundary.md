# ADR-003: Agent/service boundary (Agent Orchestrator)

Status: Locked (Phase 2)

## Context
`Phases.md` Phase 2's diagram names an "Agent Orchestrator" sitting between FastAPI and the astrology/knowledge services, branching to Chart/Rules/Dasha/Knowledge, then to an AI Reasoner, then Verification. This must be reconciled with the canonical `services/agent` name (locked prior to Phase 2) and with ADR-001's calculation-authority boundary.

## Decision
"Agent Orchestrator" (as named in `Phases.md`'s Phase 2 diagram) and the canonical `services/agent` are the same component. Its responsibility is strictly orchestration, never calculation:
- Intent/domain detection
- Deciding what evidence is required and in what order (planning)
- Invoking `astro-engine`, `rule-engine`, and `knowledge` through their defined request/response contracts (see `docs/ARCHITECTURE.md` §"Astrology Service Interfaces")
- Assembling the evidence bundle
- Invoking the AI Reasoner (self-hosted model) with that bundle
- Invoking `verification` before releasing a response
- Managing conversation/user memory access (not memory's storage — see `docs/ARCHITECTURE.md` §"Memory Architecture")

It explicitly never: computes a planetary position, house, dasha date, panchang value, yoga/dosha trigger, or numerology number itself; stores those as if agent-owned facts; or bypasses `verification` when verification is mandatory for the response type.

## Consequences
- `agent` is the only service permitted to call the AI Reasoner.
- `agent`'s internal `voice/` and `reports/` subpackages (see Repository Structure) follow the same rule: they call into `agent`'s own orchestration and the deterministic services, never compute facts themselves.
- Adding a new "specialist mode" (e.g., a new life-domain question type) is a change to `agent`'s planning/prompt-template configuration, not a new service.
