# ADR-008: The palm-vision component (`services/palm-vision`)

Status: Locked (owner decision A, 2026-10-02; resolves `docs/ARCHITECTURE.md` §34 item 5). The component is approved and documented; no code exists yet (Phase 13 implementation).

## Context
`Phases.md` Phase 13 (Palm Reading & Vision Intelligence) requires a deterministic vision pipeline that turns a palm image into structured palm facts, and `TECH_STACK.md` locks its technologies (OpenCV, NumPy, MediaPipe, PyTorch). `docs/ARCHITECTURE.md` §2 and §27 are a locked structure of five canonical services (`astro-engine`, `rule-engine`, `agent`, `knowledge`, `verification`) plus `server/` (ADR-007), and `CONTRIBUTING.md` locks the service names. No document says where the vision code lives, and the Phase 13 audit found that placing it in an existing service would either break that service's definition or add a component to a locked structure. `SOURCE_OF_TRUTH.md` requires the conflict to be recorded and resolved by an owner decision, not silently.

## Options considered
1. **A dedicated `services/palm-vision`.** Best responsibility fit. It isolates PyTorch, OpenCV and MediaPipe, model weights, GPU or CPU needs, datasets and evaluation, and the privacy boundary for palm images; it can have its own CI job with heavy dependencies; the dependency direction is simple. Cost: a sixth canonical component in a locked structure, so an owner decision, this ADR and edits to §2, §5, §27, `CONTRIBUTING.md` and `TECH_STACK.md`.
2. **`astro-engine`.** Rejected: its responsibility is deterministic astronomical and chart calculation (§5 and §6); adding torch and OpenCV would bloat the ephemeris library, which is tied to the Swiss Ephemeris licence boundary, and its large test suite.
3. **`knowledge`.** Rejected for vision: it stores and retrieves source-backed knowledge and imports no calculation, rule or model code (Phase 12). It is, however, the home of palm *knowledge text*, and that stays there.
4. **`rule-engine` and `packages/contracts` (already authorised homes).** Not for vision (the rule engine's input is a facts object, not an image), but correct for palm rule evaluation and for the palm-fact contracts, which stay there.

## Decision
1. `services/palm-vision` is a canonical service. Name locked: do not use alternatives.
2. It is responsible for image processing, image quality, hand detection, hand-side classification, palm region extraction, landmarks, the palm-line/feature model and the structured `PalmFactSet`. It owns **no** knowledge text, **no** palm rules, **no** narration, **no** storage API and **no** LLM.
3. Contracts live in `packages/contracts`; palm knowledge in `services/knowledge` (a new knowledge version); palm rules in the `rule-engine` under a completely separate palm ruleset root (owner decision C), never inside the Phase 6 `rules/` directory.
4. Dependency direction: `palm-vision` depends on `packages/contracts` and `packages/shared` only; no other service imports it and it imports none of them.
5. Palm images are referenced by id; storage, upload, consent and retention infrastructure are Phase 18; the model is a pinned artifact outside git.

## Consequences
- `docs/ARCHITECTURE.md` §2 (row 14), §5, §9, §12, §27, §30, §34 (items 5 and 6) and the new §35 are updated; `CONTRIBUTING.md` and `TECH_STACK.md` list the component.
- ADR-007 is unchanged in substance: `server/` composes the canonical services, now including `palm-vision` once implemented; this ADR adds the sixth.
- Phase 13 implementation creates the package, its CI job and its tests; none exists today. The Phase 6 rule files and rule-set hash, the evidence-bundle fields and the Phase 12 knowledge snapshot stay unchanged.
