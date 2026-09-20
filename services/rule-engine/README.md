# rule-engine

Structured astrology rules and deterministic rule evaluation. Canonical service name — do not rename to `ai-agent`-style or otherwise.

**Responsible for**: turning `astro-engine` facts into yoga/dosha detections and tagged interpretive evidence, evidence collection, contradiction/conflict analysis between rules (see `docs/ARCHITECTURE.md` §"Rule Engine Architecture", `docs/ASTROLOGY_STANDARDS.md` §"Yoga / Dosha standards").

**Not responsible for**: computing chart facts itself (consumes them from `astro-engine`), or producing user-facing natural language (structured tags + facts only — phrasing is `agent`'s job).

## Phase 6 status

Implemented (`Phases.md` Phase 6, first tranche; methodology in `docs/ASTROLOGY_STANDARDS.md` v1.4.0 §"Phase 6 rule-engine methodology"):

- `schema.py`: typed, declarative rule schema (source-specific profiles, readings, exceptions, cancellations, dependencies); no embedded code.
- `loader.py`: deterministic loading and registration of `services/knowledge/rules/**/*.yaml` (duplicate IDs, duplicate YAML keys, unknown references and dependency cycles are errors).
- `conditions.py` / `evaluator.py`: three-valued (Kleene) evaluation; ambiguity-preserving results (`NOT_EVALUABLE(reading_ambiguous)` when readings disagree, every reading kept); priority orders evaluation only.
- `tables.py` / `derived.py`: BPHS relationships (Ch. 3 v. 55-58), natural benefic/malefic (v. 11), Moolatrikona (v. 51-54) and the 84-cell Ch. 34 functional-nature table, source labels preserved.
- `bundle.py` / `hashing.py`: reproducible `EvidenceBundle` and canonical ruleset content hash.
- `adapters.py`: reads a Phase 5 Kundli's JSON form into normalized facts (no import of `astro-engine`).
- `engine.py`: `RuleEngine.from_directory(...).evaluate_kundli(kundli_json)`.

The rule engine consumes facts only. It never computes astronomy, never calls the network or an AI model, and never resolves a source conflict by picking a winner. Anything owned by a later phase (Shadbala, Dasha, partial drishti, Jaimini, special Lagnas, upagraha calculation, D27 ...) returns a structured `NOT_EVALUABLE` reason.

## Dasha evidence (Phase 7)

`RuleEngine.evaluate_kundli(kundli, dasha_facts)` accepts the JSON form of an `astro-engine` `DashaFacts` and records it in the `EvidenceBundle` as an additive, optional `dasha` section (status, profile IDs, boundary convention, precision, starting Nakshatra/Pada/lord, every period boundary, labelled provenance, and a hash of the facts). The section is omitted when no Dasha facts are given, so bundles built without it serialize and hash exactly as before; the bundle schema version is unchanged. The rule engine never calculates a Dasha, and no shipped rule reads Dasha facts yet, so the reserved `requires_dasha` reason is not emitted by any current rule.

## Local development

```
pip install -e ../../packages/contracts
pip install -e ../../packages/shared
pip install -e ".[dev]"
pytest
ruff check .
mypy src
```
