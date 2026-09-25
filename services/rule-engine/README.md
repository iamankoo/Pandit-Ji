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

## Transit evidence (Phase 8)

`RuleEngine.evaluate_kundli(kundli, dasha_facts, transit_facts)` also accepts the JSON form of an `astro-engine` `TransitFacts` and records it in the `EvidenceBundle` as an additive, optional `transit` section (status, profile IDs, boundary convention, accuracy disclosure, every source reading including the unresolved Moon-from-Moon conflict, Vedha facts, events, the Sade Sati segments and episodes with their `modern_tradition` label, labelled provenance and a hash of the facts). Like `dasha`, it is omitted when absent, so bundles built without it serialize and hash exactly as before; the bundle schema version is unchanged. The rule engine never calculates a transit, and no shipped rule reads transit facts yet.

## Ashtakavarga evidence (Phase 9 WP-EB)

`RuleEngine.evaluate_kundli(kundli, dasha_facts, transit_facts, ashtakavarga_facts, ashtakavarga_reduction_facts)` also accepts the JSON form of an `astro-engine` `AshtakavargaFacts` (WP-A1: the caller-selected profile, per-planet Bhinnashtakavarga charts with per-sign counts and per-contributor marks, Sarvashtakavarga, an optional Lagna chart) and, optionally, an `AshtakavargaReductionFacts` for the *same* profile and natal chart (WP-A2/A3: Trikona/Ekadhipatya Shodhana and Rasi/Graha/Yoga Pinda). Both are recorded in the `EvidenceBundle` as one additive, optional `ashtakavarga` section; `ashtakavarga_reduction_facts` is ignored unless `ashtakavarga_facts` is also given. There is no default profile: the caller selects exactly one of the four supported profiles per bundle build, and a caller wanting more than one profile's evidence builds more than one bundle. Every `NOT_EVALUABLE` status, reason code and `EkadhipatyaConflict` reading from WP-A1/A2/A3 is preserved verbatim, never resolved or merged by the adapter, and a chart's reduction map or Pinda is only ever recorded whole, never partially. Like `dasha` and `transit`, the section is omitted when absent, so bundles built without it serialize and hash exactly as before; the bundle schema version is unchanged. The rule engine never calculates an Ashtakavarga, and no shipped rule reads Ashtakavarga facts yet.

## Phase 9 closure evidence (KP, Shadbala, Jaimini, Chinese, Tarot)

`RuleEngine.evaluate_kundli` also accepts `kp_facts`, `shadbala_facts`, `jaimini_facts`, `chinese_facts` and `tarot_layout` -- the JSON forms of an astro-engine KP natal or horary chart, one Shadbala profile's facts (the BPHS verse profile or the Raman profile, never both in one bundle), the WP-G `JaiminiFacts`, a Chinese Four Pillars chart and a Tarot layout. `pandit_rule_engine.phase9_evidence` validates each (status/reason invariants; a Shadbala total cannot be successful while a leaf component is not evaluable; a Tarot layout may carry no interpretation), keeps profile IDs, readings and provenance verbatim and records a `facts_hash` of the whole input. Each section is optional and omitted when absent, so bundles built without them serialize and hash exactly as before (`docs/ASTROLOGY_STANDARDS.md` EV-01 to EV-10). No rule reads these sections yet.

## Local development

```
pip install -e ../../packages/contracts
pip install -e ../../packages/shared
pip install -e ".[dev]"
pytest
ruff check .
mypy src
```
