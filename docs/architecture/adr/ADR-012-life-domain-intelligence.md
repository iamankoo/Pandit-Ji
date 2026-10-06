# ADR-012: Life-Domain Intelligence (Phase 17): where it lives and what it may consume

Status: **PROPOSED (research and architecture lock, 2026-10-06). Not owner-approved. Nothing is implemented. Phase 17 has not started.** Every decision below is a recommendation that waits for the owner decisions listed in `research/PHASE_17_LIFE_DOMAIN_RESEARCH.md` section 18.

## Context
`Phases.md` Phase 17 lists 27 domains and a chain (domain, charts, planets, houses, dashas, transits, rules, interpretation) and the deliverable "complete domain reasoning system"; it specifies no contract, service or exit criterion. `docs/ARCHITECTURE.md` section 8 says specialist modes are "prompt templates + evidence-assembly presets... configuration within `agent`, not new architecture". ADR-001 forbids the agent from computing any astrology fact. `docs/ASTROLOGY_STANDARDS.md` defers the domain-to-varga mapping to Phase 17. Research found: 7 of the 27 domains have a source-backed mapping (houses, karakas, vargas), 11 partial, 9 `NOT_EVALUABLE`; the Phase 6 `ChartFacts` is D1-only; the dasha, transit, Ashtakavarga and compatibility evidence sections exist in the `EvidenceBundle` but no shipped rule reads them; the agent has no dasha or transit tool (Phase 15 deferred them to Phase 18); the rules carry a free-form `interpretation_tags.domain` list (44 `general`, 2 `marriage`, 5 `personality`+`status`).

## Options evaluated
- **A. `agent` presets only.** Rejected alone: relevance (which lords, occupants, aspects and vargas hold for this chart) is a deterministic fact-over-facts evaluation; putting it in the agent would make the agent compute chart-derived facts (ADR-001).
- **B. `knowledge` domain methodology.** Accepted for **data** (what is relevant to a domain, with provenance and status). Rejected for evaluation: `knowledge` never evaluates rules.
- **C. `rule-engine` domain metadata.** Accepted for **evaluation**, in a separate ruleset with its own manifest and content hash (the Phase 13 palm precedent, `services/rule-engine/palm_rules/`), so the Phase 6 ruleset hash `8d29a18c…77209` is untouched. Rejected inside `services/knowledge/rules/` (it would move the Phase 6 hash and the Phase 12 knowledge version).
- **D. A new service.** Rejected: no isolation need (no heavy dependency, no model), and a sixth or seventh canonical component needs an explicit owner decision that nothing here justifies.

## Decision (proposed)
1. **No new service.** Phase 17 is distributed across existing components, each change additive.
2. **Domain methodology data** in `services/knowledge/content/` (extending `domains.yaml` or a sibling file; outside `rules/`): the domain registry, house, karaka and varga mappings with source profile, location, level, direct or derived, status and conflicts, and the typed `NOT_EVALUABLE` reasons. Data only; no prose.
3. **Domain relevance evaluation** in the `rule-engine`, in a separate domain ruleset with its own manifest and hash. It needs additive readers for divisional placements, the dasha section and the transit section of the bundle (the evidence modules exist). It computes structural relation facts (owns, occupies, aspects, karaka; trine relations for the transit method). It never interprets and never changes a Phase 6 rule or hash. Where a Phase 6 rule's own source states a matching effect (for example Dhana yoga for wealth), the domain ruleset references it by rule id; it does not copy or retag the Phase 6 file.
4. **Routing and narration** in `services/agent` (`pandit_agent.orchestration`): a mapping from the coarse `Intent` to candidate domains; evidence presets keyed by domain; a narration schema; the existing policy and disclaimers extended only as the owner decides. The agent reads a dasha or transit section only if it is already inside the supplied bundle; fetching facts for a user and date is Phase 18.
5. **Contracts** in `packages/contracts` as a new additive module (the design is in the research record, section 16); the Phase 15 and 16 contracts are unchanged. The domain result is consumed by the agent as evidence records of the existing five classes.
6. **Verification:** Phase 16 verifies domain claims through the existing claim contract. The verifier must be able to resolve the new domain evidence by bundle reference; that is a small additive change to `services/verification`, and it depends on the owner's closure of Phase 16 (decision 13).
7. **Phase 17 does not own:** the Dasha, Transit, Compatibility and Memory APIs; the tools that obtain facts for a user and date; the regenerate loop; persistence; reports (recommended); Vastu (`DEFERRED`); voice; notifications; any model run.

## Source-conflict and policy consequences
Source profiles are never merged (standards LD-18). Domains whose mappings need no source read stay `NOT_EVALUABLE`. Children, fertility, pregnancy, paternity, minors, the subject's sex and derogatory statements are policy gates that this ADR does not decide (standards LD-20).

## Consequences
- Four components are touched additively (knowledge data, rule-engine domain ruleset and readers, agent presets, contracts) plus a small verifier resolution change; every Phase 6 to 16 pin must stay asserted.
- Domain results are honest about gaps: a domain with no source returns `NOT_EVALUABLE` with a reason.
- If the owner chooses "agent presets only" (option A), the cost is that the agent would have to compute relevance, which this ADR advises against.
- The structural layer can be built before the unread chapters are researched; rule combinations for each domain remain `RESEARCH_PENDING`.

## Status of open items
Owner decisions 1 to 13 and the additional items of the research record (sex of the subject, fear statements, the spouse-longevity tag) are open. `OWNER_DECISION_REQUIRED`: this ADR becomes `Locked` only when the owner records them.
