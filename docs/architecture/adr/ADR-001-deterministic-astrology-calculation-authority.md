# ADR-001: Deterministic astrology calculation authority

Status: Locked (Phase 1/Phase 2)

## Context
Pandit Ji's core product invariant (`docs/ASTROLOGY_STANDARDS.md`, `docs/ARCHITECTURE.md` §1) is that the AI must never invent planetary positions, houses, dashas, nakshatras, yogas, or other calculated astrological facts.

## Decision
All astrological/astronomical facts are produced exclusively by the `astro-engine` service (deterministic, pure computation over ephemeris + birth data + `calculation_config`) and, where interpretive tagging is involved, the `rule-engine` service (deterministic rule evaluation over `astro-engine` facts). The `agent` service and any AI model behind it consume these facts and rule-engine outputs as an **evidence bundle** and may only narrate them — they have no code path that computes or asserts a fact independently.

## Consequences
- `astro-engine` and `rule-engine` must be independently testable with golden fixtures, with zero dependency on the `agent` or any LLM.
- `verification` exists specifically to catch any case where the AI narration states a fact not present in its evidence bundle.
- Every stored fact (chart, dasha, transit, panchang, yoga/dosha, numerology, compatibility result) is queryable and directly API-callable without going through the agent/chat path.
