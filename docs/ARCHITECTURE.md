# Pandit Ji — System Architecture

Status: **Phase 2 complete** (System Architecture — see `Phases.md` Phase 2). Derived from `features.md` (the locked baseline) and `docs/ASTROLOGY_STANDARDS.md` (the locked calculation/interpretation standards).

Scope: this document defines the complete technical architecture — subsystems, services, APIs, gateway, queues, databases, caching, authentication, AI infrastructure, memory, observability, security, failure handling, versioning, deployment, and scaling — plus the deterministic/AI split. It intentionally contains no application code. **It does not define the implementation sequence** — see §"Execution Roadmap". Diagrams referenced throughout live in `docs/architecture/diagrams.md`; architecture decision records live in `docs/architecture/adr/`.

Source-of-truth hierarchy for this project: the full, authoritative authority order is maintained in `SOURCE_OF_TRUTH.md` (project root) — read that file directly rather than trusting a copy of it here, since it can change. As of the Pre-Phase-1 Foundation package it is:

```
1. Explicitly locked project-owner decisions
2. features.md            — WHAT Pandit Ji must contain
3. Phases.md               — HOW/WHEN; sole execution roadmap
4. docs/ARCHITECTURE.md    — technical structure (this document)
5. docs/ASTROLOGY_STANDARDS.md — calculation/interpretation standards (locked canonical location)
6. TECH_STACK.md — locked technology-stack choices
7. PRODUCT_POLICIES.md
8. LEGAL_REGULATIONS.md
9. Research documents (research/*.md)
10. Code/configuration
```

Conflict rule (from `SOURCE_OF_TRUTH.md`): never silently resolve a contradiction between documents. Record it, resolve it in the higher-authority document, update dependents, and add a changelog entry. §"Known Contradictions" of this document tracks contradictions discovered so far.

Before starting any phase or implementation work, read `Phases.md` first and identify the current phase, current step, required deliverables, dependencies, exit criteria, and explicitly excluded work. Do not start work from memory or from an older roadmap.

---

## 1. Guiding Constraint

Every design decision below exists to enforce one rule from the product spec:

> The AI must never invent planetary positions, dashas, houses, yogas, nakshatras, or other calculated astrological facts.

Concretely, this means the system is built as a **fact pipeline with a narrating layer on top**, not a chatbot with astrology sprinkled in. The `astro-engine` and `rule-engine` produce structured, versioned, reproducible facts. The `agent` (Agent Orchestrator) is only ever allowed to read those facts and talk about them — it cannot compute or assert them itself. The `verification` service checks that this boundary held on every response before it reaches the user. See ADR-001.

---

## 2. Major Subsystems

| # | Subsystem | Canonical service/location | Responsibility |
|---|-----------|-----------------------------|-----------------|
| 1 | **Astrology Calculation Engine** | `services/astro-engine` | Deterministic astronomy + Vedic/Western chart math (positions, houses, vargas, ashtakvarga, dashas, transits, panchang, muhurta, compatibility scoring, numerology). |
| 2 | **Rule Engine** | `services/rule-engine` | Versioned, testable rules that turn chart facts into yoga/dosha detections and tagged interpretive evidence. |
| 3 | **Knowledge** | `services/knowledge` | (a) structured rule source-of-truth, (b) unstructured classical-text/remedy corpus for retrieval-augmented narration. |
| 4 | **Agent (Agent Orchestrator)** | `services/agent` | Intent detection, planning, tool invocation, evidence assembly, AI Reasoner invocation, conversation memory access, response generation. "Agent Orchestrator" (`Phases.md` diagram terminology) and `services/agent` are the same component — see ADR-003. |
| 5 | **Verification** | `services/verification` | Fact/rule/evidence validation, unsupported-claim detection, contradiction detection, regression suite, backtesting, accuracy benchmarking. See ADR-006. |
| 6 | **Memory & Personalization** | `agent`-owned data, `conversation`/`data.users` schemas | Birth profiles, saved family/partner charts, conversation history, preferences, feedback/correction history. |
| 7 | **Voice** | `services/agent/voice/` (subpackage) | STT/TTS, multilingual voice turn-taking, delegates all reasoning to `agent`. |
| 8 | **Reports** | `services/agent/reports/` (subpackage) | Deterministic report assembly (chart/dasha/career/marriage/annual/etc.) from `astro-engine` + `rule-engine` + `agent` narration. |
| 9 | **API Gateway** | `infrastructure/` (config, not code) | Edge routing, TLS, authN enforcement, rate limiting, request IDs, versioning, abuse protection. See ADR-007. |
| 10 | **FastAPI composition root** | `server/` | Application-level HTTP layer composing the five services into callable endpoints. See ADR-007. |
| 11 | **Web/Mobile/Admin Clients** | `apps/{web, mobile, admin}` | Presentation only, no astrology logic. |
| 12 | **Security/Privacy/Audit** | cross-cutting, see §"Security Architecture" | AuthN/authZ, encryption at rest for birth/palm data, audit logging, data deletion, access control. |
| 13 | **Human Ecosystem / Content** (future) | not yet scheduled | Live astrologer marketplace, articles, festival calendar — explicitly deferred, not in initial baseline builds. |

---

## 3. High-Level Architecture

```
Flutter Mobile / Web / Admin
            ↓
       API Gateway            (edge: routing, TLS, authN, rate limiting — infrastructure, not app code)
            ↓
   FastAPI (server/)          (composition root: routes requests to services, no business logic)
            ↓
   agent (Agent Orchestrator) (plans evidence needs, never computes facts)
     ┌──────┼───────┬────────┐
     ↓      ↓       ↓        ↓
astro-engine rule-engine  knowledge  (memory/user context, via agent)
     └──────┴───────┴────────┘
            ↓
      AI Reasoner (self-hosted model, behind LLMProvider interface)
            ↓
      verification (PASS / REGENERATE)
            ↓
      Final Response
```

Full Mermaid version: `docs/architecture/diagrams.md` ("System overview"). This is the same diagram `Phases.md` Phase 2 specifies, refined with the canonical service names and the Gateway/FastAPI split from ADR-007.

Non-negotiable properties of this diagram (see ADR-001, ADR-003):
- Only `astro-engine` and `rule-engine` may originate a chart/dasha/transit/panchang/yoga/dosha/numerology/compatibility fact.
- Only `agent` may call the AI Reasoner.
- No response for which verification is mandatory reaches a client without passing `verification`.
- Every deterministic endpoint (`/charts`, `/dashas`, etc.) is directly callable by a client without transiting `agent`/`/chat` at all — `agent` is a consumer of these APIs internally, not a gatekeeper in front of them.

---

## 4. API Gateway

Responsibilities (edge, infrastructure-level, not application code — see ADR-007):
- Routing to `server/` (and, later, any additional backend deployment units)
- TLS termination where applicable
- Authentication enforcement: validating the access token/session before a request reaches `server/` (the actual authorization decision — e.g. "does this user own this birth profile" — is `server/`'s and the owning service's job, not the gateway's)
- Request validation (malformed requests rejected before reaching application code)
- Rate limiting (per-user and per-IP; backed by Redis, see §"Caching Architecture")
- Request-ID injection for end-to-end tracing (see §"Observability")
- API versioning at the URL/header level (`/api/v1/...`)
- Abuse protection (basic bot/anomaly filtering)
- Observability-header propagation (trace/request IDs forwarded to `server/` and beyond)

Explicitly **not** the gateway's job: authorization decisions tied to domain data (profile/report/conversation ownership), business logic, or anything astrology-specific. Those live in `server/` and the owning service.

Implementation is deferred (Phase 18, Backend Platform) — this section fixes responsibility boundaries, not a specific gateway product.

---

## 5. Service Architecture

Canonical service names are locked and must not be renamed: `astro-engine`, `rule-engine`, `agent`, `knowledge`, `verification`. Do not introduce alternatives such as `astrology-engine`, `ai-agent`, or `knowledge-base` anywhere in code or documentation.

### astro-engine
**Responsible for**: deterministic astronomical and chart calculations — planetary positions, houses/ascendant, divisional charts, dignity/combustion/retrograde, ashtakvarga, dashas, transits, panchang, muhurta, compatibility scoring, numerology (see §"Astrology Engine Architecture" for module layout).
**Explicitly not responsible for**: interpretation, rule evaluation, narration, or anything involving the AI Reasoner. It has zero dependency on `agent`, `rule-engine`, `knowledge`, or `verification`.

### rule-engine
**Responsible for**: structured astrology rules and deterministic rule evaluation over `astro-engine`'s output — yoga/dosha detection, evidence collection, contradiction/conflict analysis between rules (see §"Rule Engine Architecture").
**Explicitly not responsible for**: computing chart facts itself (it consumes them from `astro-engine`), or producing user-facing natural language (it produces structured tags + facts only).

### agent
**Responsible for**: orchestration — intent/domain detection, planning what evidence is needed, invoking `astro-engine`/`rule-engine`/`knowledge`, assembling the evidence bundle, invoking the AI Reasoner, invoking `verification`, managing conversation/memory access, and the `voice`/`reports` subpackages (see §"Agent Orchestrator Architecture", ADR-003).
**Explicitly not responsible for**: computing any astrology fact, or releasing a response that bypasses mandatory verification.

### knowledge
**Responsible for**: structured astrology knowledge (rule source-of-truth, mirrored from versioned YAML) and unstructured knowledge (classical text/remedy corpus, chunked + embedded for RAG retrieval) — see §"Knowledge Architecture".
**Explicitly not responsible for**: being treated as a source of chart facts. Retrieval results feed narration/remedy phrasing only.

### verification
**Responsible for**: validating calculations, evidence, rules, and generated claims before a response is released — fact validation, rule validation, evidence validation, unsupported-claim detection, contradiction detection (see §"Verification Architecture", ADR-006). Also owns the regression-test and backtesting framework.
**Explicitly not responsible for**: generating narrative content, or being a generic grammar/style checker.

---

## 6. Astrology Engine Architecture

A pure-Python library (no HTTP, no DB) so it can be unit-tested with fixed inputs/outputs and reused by `server/`, background jobs, and reports.

```
astro_engine/
  ephemeris/        # Swiss Ephemeris binding (planet positions, houses, ayanamsa)
  time_location/    # historical timezone + DST resolution, lat/lon geocoding cache
  charts/           # D1, D9, and other divisional charts, North/South/Chalit rendering data
  strength/         # dignity, exaltation/debilitation, combustion, retrograde, shadbala (later)
  ashtakvarga/
  dashas/           # vimshottari (mahadasha/antardasha/pratyantar), timeline builder, period lookup (Phase 7)
  transits/         # gochar states, ingress/station events, sade sati (modern tradition), sign-based transit-to-natal contacts (Phase 8)
  panchang/         # tithi, vara, nakshatra, yoga, karana, hora, choghadiya, rahu kaal
  muhurta/
  compatibility/    # ashtakoot/guna milan scoring
  numerology/
  western/          # tropical + Placidus module, kept isolated from Vedic assumptions (Phase 9 WP-D: built as `pandit_astro_engine/western`, standards WD-01 to WD-20; own body/sign identifiers, no Vedic imports)
  kp/               # KP (Krishnamurti Paddhati) foundation (Phase 9 WP-E, standards KP-01 to KP-16): Krishnamurti ayanamsa applied only for the call, sidereal Placidus cusps, star/sub/sub-sub lords, the derived 249-entry table, four-level significators, Ruling Planets, KP horary charts
  shadbala/         # Shadbala components of BPHS Ch. 27 (Phase 9 WP-F, SB-01 to SB-20); verse-literal, no total while components are not evaluable
  chinese/          # Chinese Four Pillars calendar facts (Phase 9 WP-H, CN-01 to CN-14); solar terms from the tropical Sun, no Vedic imports
  tarot/            # Waite-Smith deck, spreads, seeded deterministic draws (Phase 9 WP-I, TA-01 to TA-10); no ephemeris, no system randomness
  config.py         # CalculationConfig value object (ayanamsa, house system, zodiac, ephemeris version)
```

Rules for this layer:
- Every public function is a pure function of `(birth_data, calculation_config)` → structured output (pydantic models). No hidden global state, no network calls.
- Every module ships **golden fixture tests**: known birth data + independently cross-checked expected output.
- KP/Lal Kitab/Nadi/Chinese/Feng Shui modules are added as additional folders **later** (`Phases.md` Phase 9) behind the same `CalculationConfig`-driven interface — see `docs/ASTROLOGY_STANDARDS.md`'s per-system standards.
- Detailed calculation methodology (ayanamsa, house system, divisional-chart derivation, Vimshottari Dasha, Nakshatra, Panchang/Muhurta, Numerology) is defined in `docs/ASTROLOGY_STANDARDS.md`, not restated here — this section is the code-organization contract, that document is the methodology contract.

---

## 7. Rule Engine Architecture

```
Chart Facts (from astro-engine)
        ↓
Fact Normalization  → canonical "Facts" object (planet-in-house, planet-in-sign,
                       aspect, dasha-lord, dosha-precondition, etc.)
        ↓
Rule Matching  → each rule is a source-specific profile (fields below); each of its
                 readings is evaluated separately against the Facts
        ↓
Evidence Collection  → every rule result (triggered, not triggered, cancelled, partially cancelled,
                       NOT_EVALUABLE) + the exact facts that satisfied or blocked it
        ↓
Contradiction/Conflict Analysis → group results by conflict_group and ambiguity_group and by each
                                    rule's known_contradictions; surface supporting and conflicting
                                    evidence together, never dropping either
        ↓
Evidence Bundle (structured, versioned, reproducible) → handed to agent
```

**Rule schema (reconciled with `docs/ASTROLOGY_STANDARDS.md` v1.4.0 and `Phases.md` Phase 6).** The Yoga/Dosha standard's schema is extended, not replaced. A rule is a source-specific profile with:

- Identity: `rule_id`, `rule_version`, `profile` (profile ID, e.g. `BPHS_SAN_GAJAKESARI_36_3_4`), `category`, `astrology_system`, `school`.
- Provenance: `source`, `source_id`, `source_edition`, `translator`, `source_location`, `source_version`, `standards_version`, `confidence` (translation-level label per `docs/ASTROLOGY_STANDARDS.md` §Source tiers).
- Logic: `conditions` (typed operators over Facts, with an explicit `reference` of LAGNA or MOON where houses are counted), `readings[]` (each with `reading_id`, its own conditions and source), `required_conditions`, `supporting_conditions`, `exceptions`, `cancellations` (separate from detection), `dependencies` (each naming its owner phase and reason code), `applicability` (school, gender or partner-chart requirements).
- Output: `interpretation_tags` (structured tags only), `strength_severity`, `timing_relevance`, `known_contradictions[]`, `conflict_group`, `ambiguity_group`.
- Metadata: `priority` (display and ordering metadata only; never erases conflicting evidence or decides truth), `status` (authoring status).

Rule conditions are declarative data; no arbitrary code is embedded in the rule files. Runtime result statuses are `TRIGGERED`, `NOT_TRIGGERED`, `CANCELLED`, `PARTIALLY_CANCELLED` and `NOT_EVALUABLE(reason)`; the reason codes and the ambiguity-preserving evaluation policy are defined in `docs/ASTROLOGY_STANDARDS.md` §Phase 6 rule-engine methodology.

**Evidence bundle contents.** The bundle preserves, so a result is reproducible: the chart and calculation snapshot; the calculation configuration (ayanamsa, node model, house system, timezone, coordinates); the calculation-engine, standards, rule-engine and ruleset versions; the ruleset content hash; rule IDs, source profiles and reading IDs; triggered, non-triggered and `NOT_EVALUABLE` results; conflicts, unresolved dependencies and provenance. The same input, configuration, ruleset hash and engine version produce the same bundle. Each component keeps the standards version it was produced under: the Phase 5 calculation snapshot records `standards_version` 1.3.0 and Phase 6 rule evaluation records 1.4.0; historical calculation metadata is never upgraded when the standards document advances.

Implementation notes:
- Rules are authored as YAML/JSON in the repo (`services/knowledge/rules/*.yaml` — see §"Knowledge Architecture"), reviewed like code, and loaded with a content hash as the version.
- **Source-profile layout**: rule files live under `services/knowledge/rules/`, grouped by source tradition in subdirectories (for example `bphs/`, `phaladeepika/`, `jataka_parijata/`, `modern/`), one profile per rule; each file declares its schema version, and duplicate rule IDs are a load error. The ruleset content hash covers every rule file and the schema version.
- The matcher is a small forward-chaining evaluator hand-rolled in Python (a full production-rule engine like `experta`/`durable_rules` is unnecessary complexity here and both have maintenance-status risk — evaluate during `Phases.md` Phase 6, don't default to either).
- Rule authoring must cite a source text/tradition per rule, because classical yoga/dosha rules genuinely conflict across schools (Parashari vs Jaimini vs Lal Kitab) — the engine surfaces conflicts rather than silently picking a winner (`docs/ASTROLOGY_STANDARDS.md`'s explicit "do not invent a universal list" rule).
- Rule engine output never contains free text meant for the user — only structured tags + facts. Phrasing is `agent`'s job.

---

## 8. Agent Orchestrator Architecture

See ADR-003 for the service-boundary decision. Full flow:

```
User message (+ conversation memory)
        ↓
Intent & Domain Classifier → maps to a fixed taxonomy drawn from features.md
                              (career / marriage / education / wealth / transit-timing / …)
        ↓
Astrology Planner → determines which astro-engine calculations + rule-engine
                     categories are actually needed for this intent (avoid
                     computing everything for every message)
        ↓
Evidence Assembly → calls astro-engine (direct facts) via ChartRequest/DashaRequest/etc.
                     + rule-engine (evidence bundle) + knowledge (RAG: remedy/
                     explanatory language, source texts)
        ↓
AI Reasoner (self-hosted, swappable) → prompted with: user question, conversation
                     memory, and ONLY the assembled evidence bundle — explicitly
                     instructed not to state any fact not present in the bundle
        ↓
verification → extracts factual claims from the draft response, checks each
                     against the evidence bundle; on mismatch, either strips the
                     claim, regenerates, or (for borderline cases) appends a
                     clarifying caveat
        ↓
Personalized Response (+ stored agent_trace for explainability)
```

Worked example (career question, matching `Phases.md`'s own Phase 15 preview):
```
User: "Will my career improve next year?"
  → Intent = Career
  → Plan: need D1, D10, 10th house, 10th lord, current/upcoming Dasha, next-year transits
  → astro-engine: ChartRequest(D1, D10), DashaRequest, TransitRequest(window=next 12mo)
  → rule-engine: evaluate career-relevant yoga/dosha rules against returned facts
  → knowledge: retrieve any relevant remedy/explanatory phrasing
  → AI Reasoner: narrate from the assembled evidence bundle only
  → verification: check claims against the bundle → PASS/REGENERATE
  → Response
```

- **Model abstraction**: an `LLMProvider`/AI Reasoner interface (prompt in, text/stream out) so Qwen/Llama/Mistral/etc. can be swapped without touching planner/verification logic (ADR-002). No model is picked as final in this document.
- **Specialist "modes"** (career, marriage, business-vs-job, etc.) are not separate models or services — they are prompt templates + evidence-assembly presets keyed off the intent taxonomy, configuration within `agent`, not new architecture.
- **Conversation memory** is retrieved (recent turns + relevant saved profile + prior discussed topics) and passed into evidence assembly, not directly into free-form prompting, so memory can't smuggle in unverified "facts" either (see §"Memory Architecture").

---

## 9. Astrology Service Interfaces

`agent` never calls `astro-engine`/`rule-engine`/`knowledge` through ad hoc internal coupling — every call is one of the following conceptual request/response contracts. Exact schemas are finalized when each engine is implemented; Phase 2 fixes ownership, responsibility, and cross-cutting behavior.

| Contract | Owner | Deterministic? | Notes |
|---|---|---|---|
| `ChartRequest` / `ChartResponse` | `astro-engine` | Yes | Input: birth data + `calculation_config` + requested varga(s). Output: positions/houses/nakshatra/dignity/etc. for D1 and requested divisional charts. |
| `DashaRequest` / `DashaResponse` | `astro-engine` | Yes | Input: birth data + `calculation_config`. Output: Mahadasha/Antardasha/Pratyantar timeline (see `docs/ASTROLOGY_STANDARDS.md` §Phase 7 methodology lock). Phase 7 realizes it as `DashaRequest` (Moon longitude, UTC birth instant, profile IDs, birth-time precision) and `DashaFacts` (status, profile IDs, period tree in UTC, labelled provenance); `rule-engine` records `DashaFacts` in the evidence bundle and never calculates a Dasha. |
| `TransitRequest` / `TransitResponse` | `astro-engine` | Yes | Input: natal chart reference + date/window. Output: transit positions + transit-to-natal aspects + Sade Sati windows where applicable. Phase 8 realises it as `TransitRequest` (a `NatalReference`, a UTC instant and/or window, methodology profile IDs, the Phase 4 calculation configuration) and `TransitFacts` (status, profile IDs, accuracy block, instant snapshot, window events, Sade Sati segments and episodes, labelled provenance); the transit-to-natal relations are the sign-based contacts of `docs/ASTROLOGY_STANDARDS.md` §Transit / Gochar standards TR-07 (no degree angles); `rule-engine` records `TransitFacts` in the evidence bundle and never calculates a transit. No HTTP endpoint or table exists before Phase 18. |
| `WesternChartRequest` / `WesternChartFacts` | `astro-engine` | Yes | Phase 9 WP-D. Input: local birth date-time + IANA timezone, coordinates, an explicit birth-time precision, and body/house/aspect/orb/motion profile IDs (plus a node convention only for the node profile). Output: tropical positions and signs, Placidus cusps and angles (or `NOT_EVALUABLE` with a reason), house placement, aspects with orb and applying/separating state, labelled provenance (`docs/ASTROLOGY_STANDARDS.md` §Western standards). Not part of the Phase 6 evidence bundle; that needs its own approval gate. |
| `KpChartRequest` / `KpChartFacts`, `KpRulingPlanetsRequest` / `KpRulingPlanetsFacts`, `KpHoraryRequest` / `KpHoraryFacts` | `astro-engine` | Yes | Phase 9 WP-E. KP positions under the Krishnamurti ayanamsa, sidereal Placidus cusps, star/sub/sub-sub lords, significators (levels a-d), Ruling Planets, horary chart for a number 1-249; explicit node convention and day-lord convention (no defaults); `NOT_EVALUABLE` for unknown time, polar latitudes and missing sunrise (`docs/ASTROLOGY_STANDARDS.md` §KP standards). No judgment or timing. |
| `ShadbalaRequest` / `ShadbalaFacts` | `astro-engine` | Yes | Phase 9 WP-F. Per-planet Shadbala components with status, reason and provenance under `SHADBALA_BPHS_SANTHANAM_27_VERSE`; no Shadbala total while components are not evaluable (§Shadbala standards). |
| Jaimini WP-G functions (`planet_rashi_drishti`, `bhava_padas`, `graha_padas`, `karakamsa`) | `astro-engine` | Yes | Phase 9 WP-G. Pure functions over signs, Chara Karaka results and longitudes (§Jaimini standards JN-11 to JN-18). |
| `ChineseChartRequest` / `ChineseChartFacts` | `astro-engine` | Yes | Phase 9 WP-H. Year, month, day and hour pillars; explicit time basis and day boundary (no defaults); luck cycles not produced (they need the person's sex, not collected) (§Chinese standards). |
| `TarotDrawRequest` / `TarotSelectionRequest` / `TarotLayout` | `astro-engine` | Yes | Phase 9 WP-I. Card placements only, seeded or user-selected; no meanings (§Tarot standards). |
| `PanchangRequest` / `PanchangResponse` | `astro-engine` | Yes | Input: date + location + regional config. Output: Tithi/Vara/Nakshatra/Yoga/Karana (+ Muhurta windows on request). |
| `CompatibilityRequest` / `CompatibilityResponse` | `astro-engine` | Yes | Input: two birth-profile references. Output: Ashtakoot/Guna Milan scores + component breakdown. |
| `NumerologyRequest` / `NumerologyResponse` | `astro-engine` | Yes | Input: birth date (+ name, if name-numerology requested) + system config. Output: Moolank/Bhagyank/name-number per `docs/ASTROLOGY_STANDARDS.md`. |
| `RuleEvaluationRequest` / `RuleEvaluationResponse` | `rule-engine` | Yes | Input: normalized Facts object (from an `astro-engine` response). Output: evidence bundle (triggered rules + contradictions). |
| `KnowledgeRetrievalRequest` / `KnowledgeRetrievalResponse` | `knowledge` | No (retrieval, not fact) | Input: query/context. Output: narration-only text chunks + sources — never chart facts. |

Every contract above requires, at minimum:
- **Ownership**: exactly one service owns each contract (table above).
- **Input/output responsibility**: the owning service validates its own inputs and is the sole producer of its response shape; callers never construct a response themselves.
- **Versioning**: every response carries the `calculation_config`/rule-set/knowledge version that produced it (see §"Versioning Architecture").
- **Deterministic behavior**: for the `astro-engine`/`rule-engine` rows, identical input + version must reproduce an identical output, always.
- **Error handling**: a contract call either succeeds with a complete response or fails explicitly (see §"Failure Architecture") — it never returns a partial result silently mislabeled as complete.
- **Traceability**: every response is attributable to the exact inputs/version that produced it, for `agent_trace`/explainability and for `verification`.

---

## 10. Knowledge Architecture

```
Knowledge Sources (classical texts, rule definitions, remedy descriptions)
       ↓
Structured Knowledge (versioned YAML rule definitions) ──→ rule-engine (see §7)
       ↓
Unstructured Knowledge (chunked classical text/remedy/glossary content)
       ↓
PostgreSQL + pgvector (embeddings)
       ↓
Knowledge Service (retrieval)
       ↓
agent (evidence assembly — narration/remedy phrasing only)
       ↓
AI Reasoner
```

Two clearly separated stores, because conflating them is exactly how AI-invented facts would sneak back in:
1. **Structured knowledge (source of truth for facts/interpretation triggers)** — the rule engine's `rule_definitions`. Authored, reviewed, versioned. This is what actually determines *which* yogas/doshas/interpretive tags apply.
2. **Unstructured knowledge (source of truth for language only)** — classical text excerpts, remedy descriptions, articles, festival/panchang glossary content; chunked + embedded (pgvector) for RAG retrieval. This feeds the AI Reasoner only phrasing, remedy wording, and background explanation — retrieval results are never treated as facts about the user's chart.

Ingestion pipeline (`Phases.md` Phase 12): document loader → chunker → embedder → dedup/quality filter → `knowledge.knowledge_chunks`. Requires sourcing classical references validated against an astrology-literate reviewer, not just general web scraping (see §"Technical Risks").

---

## 11. Verification Architecture

```
Generated Response
       ↓
verification
       ↓
Fact validation        (does every stated fact match the evidence bundle?)
       ↓
Rule validation         (were the cited rules actually triggered, as claimed?)
       ↓
Evidence validation     (is every claim traceable to evidence the agent was given?)
       ↓
Unsupported-claim detection
       ↓
Contradiction detection (no two mutually exclusive facts stated, e.g. two dasha lords for one period)
       ↓
Approve / Regenerate
```

| Layer | What it checks | When it runs |
|---|---|---|
| Engine golden-fixture tests | Ephemeris/chart/dasha/transit/panchang/compatibility outputs match independently cross-checked values | CI, every commit |
| Rule-engine test suite | Given fixed facts, exact expected rule-trigger set fires (no more, no fewer) | CI, every commit |
| Regression suite | Prior confirmed-correct outputs stay correct across engine/rule changes | CI, every commit |
| Claim/hallucination checker | Every factual assertion in an agent response is traceable to its evidence bundle | Runtime, every chat turn |
| Contradiction detector | Response doesn't state two mutually exclusive facts | Runtime, every chat turn |
| Backtesting framework | Long-run comparison of timing-oriented predictions against later user-reported outcomes | Offline, periodic (`Phases.md` Phase 21) |
| Human-expert evaluation | Sample of AI narrations reviewed by an astrology-literate human for traditional correctness (not scientific accuracy) | Periodic, pre-release gate |

Verification has access to the same structured evidence bundle `agent` used (ADR-006) — it is never a generic spell-checker. The system must be able to report, per response: which facts were used, which rules fired, what contradicted, and whether verification passed — this is the same data as the explainability feature (`features.md` §25), so explainability and verification share one implementation (`agent_traces`).

Hard constraint carried into every layer: no accuracy claim ("this will happen") is ever emitted without being framed as an astrological interpretation with a stated basis, and no marketing/UI copy may claim guaranteed real-world prediction accuracy unless backed by the backtesting framework's actual measured results (`docs/ASTROLOGY_STANDARDS.md`'s Prediction Language Policy).

---

## 12. Database Architecture

PostgreSQL is the sole database technology (ADR-004); pgvector runs inside it for embeddings. Schema-per-domain for clarity and independent migration ownership.

| Schema | Key Tables | Notes |
|---|---|---|
| `identity` | `users`, `sessions`, `auth_credentials` | Standard auth; supports future multi-tenant if a marketplace module is added. |
| `profiles` | `birth_profiles`, `locations` | `birth_profiles` link to `users` (self/family/partner flag). `locations` cache resolved lat/lon/historical-tz lookups so they're computed once, reproducibly. |
| `calc_config` | `calculation_configs` | Immutable rows: `{ayanamsa, zodiac_type, house_system, ephemeris_version}`. Every computed artifact below references a `calc_config_id`. |
| `charts` | `computed_charts`, `planetary_positions`, `houses`, `divisional_charts`, `ashtakvarga_tables` | All rows keyed by `(birth_profile_id, calc_config_id)`; immutable cache, recomputed only if inputs/config change. |
| `dashas` | `dasha_periods` (mahadasha/antardasha/pratyantar via `level` + `parent_id`), `dasha_config` | Self-referential tree; timeline queries are a single recursive CTE. |
| `transits` | `transit_snapshots`, `transit_events`, `sade_sati_windows` | Snapshots are point-in-time; events are derived. |
| `panchang` | `daily_panchang`, `muhurta_windows` | Keyed by `(date, location)`, not by user — shared/cacheable. |
| `rules` | `rule_definitions` (versioned), `rule_sets`, `rule_evaluation_results` | `rule_evaluation_results` is the durable evidence trail. |
| `knowledge` | `knowledge_chunks`, `embeddings` (pgvector), `sources` | RAG corpus for narrative/remedy phrasing only. |
| `compatibility` | `match_requests`, `guna_scores`, `match_results` | References two `birth_profiles`. |
| `numerology` | `numerology_profiles`, `numerology_reports` | |
| `conversation` | `chat_sessions`, `messages`, `agent_traces` | `agent_traces` stores the full evidence-bundle + verification result per assistant turn. |
| `reports` | `generated_reports`, `report_templates` | |
| `feedback` | `user_feedback`, `corrections`, `backtest_outcomes` | Supports backtesting without pretending it's launched with real predictive-accuracy numbers. |
| `audit` | `audit_log` | Append-only; covers data access to sensitive birth/palm data. |

Design principle: **AI-generated text is never stored as if it were a fact table.** `messages` stores what the assistant said; `agent_traces` stores what it was allowed to say (the evidence), so the two can always be diffed later.

Cross-cutting database concerns (Phase 2 requirement):
- **Relational vs. vector data**: relational tables above hold facts/state; only `knowledge.embeddings` is vector data. No fact table stores a vector column.
- **Indexes**: `(birth_profile_id, calc_config_id)` composite indexes on all chart/dasha/transit tables (the standard lookup path); `(date, location)` on `panchang`; an ANN index (e.g. HNSW/IVFFlat, chosen when `knowledge` is implemented) on `knowledge.embeddings`.
- **Versioning**: every computed row carries its producing `calc_config_id`/rule-set version/knowledge version — this is the mechanism behind §"Versioning Architecture".
- **Isolation**: standard read-committed isolation is sufficient for this workload (no cross-row invariants requiring serializable isolation have been identified); revisit if one emerges during implementation.
- **Transactional boundaries**: a single computed artifact (e.g. one `ChartResponse`'s full set of rows) is written in one transaction — partial writes are not acceptable given the "reproducible or absent" requirement.
- **Retention/deletion**: governed by `PRODUCT_POLICIES.md`'s Data & Privacy Principles — per-category retention schedules, honored user-deletion requests, with `audit_log` itself being append-only and exempt from user-triggered deletion (access-log integrity).
- **Backups**: standard PostgreSQL backup/restore (e.g. periodic base backup + WAL archiving); exact tooling deferred to Phase 18/21 deployment work — this section only fixes that backups are mandatory and must cover the single database in full (facts + embeddings + audit).

---

## 13. Queue / Background Job Architecture

Synchronous request/response is used by default; a request only moves to a background job when it cannot complete within a bounded request timeout. Identified asynchronous workloads:

| Workload | Producer | Consumer | Notes |
|---|---|---|---|
| Report generation (long reports) | `server/` (report request) | `agent/reports/` worker | User polls or is notified when ready. |
| Large/batch calculations (e.g. bulk chart recompute after a standards version change) | admin/maintenance trigger | `astro-engine` worker | Idempotent: recomputation of an already-current row is a no-op. |
| Knowledge ingestion | admin/content pipeline | `knowledge` worker | Chunk → embed → store; safe to re-run on the same source (dedup by content hash). |
| Embedding generation | knowledge ingestion job | `knowledge` worker | Same as above; can be a sub-step. |
| Notifications | various (report ready, dasha transition alert, etc.) | notification worker | Fire-and-retry; failure does not lose the underlying result, only the notification. |
| Long-running AI tasks (e.g. batch narration for reports) | `agent/reports/` | `agent` worker | Still passes through `verification` before being marked ready. |
| Backtesting | scheduled/admin trigger | `verification` worker | Reads `feedback.backtest_outcomes`, writes metrics; never blocks a live request. |
| Maintenance jobs (e.g. re-embedding after a knowledge-model upgrade) | scheduled | relevant service worker | |

Architecture (see `docs/architecture/diagrams.md`, diagram D):
- **Queue responsibility**: Redis-backed queue (ADR-005) holds job payloads; a worker process per consuming service pulls and executes.
- **Producer**: the API request handler in `server/` (or an admin/scheduled trigger) enqueues a job and returns immediately (job ID / "processing" status).
- **Consumer**: a worker process owned by the relevant service (`astro-engine`, `knowledge`, `agent`, or `verification`) — workers are part of that service's deployable unit, not a separate "worker service."
- **Retry behavior**: bounded retries with backoff; a job that exhausts retries is marked failed, not silently dropped.
- **Idempotency**: every job is designed so re-running it with the same input produces the same end state (matches the "deterministic or absent" principle used for calculation caching).
- **Failure handling / dead-letter strategy**: jobs that exhaust retries move to a dead-letter queue for manual/alerted inspection rather than being lost; a failed report/ingestion job surfaces as a visible failed state to whoever triggered it, never a silent stall.

No message broker beyond Redis is introduced without a measured, documented bottleneck (ADR-005).

---

## 14. Caching Architecture

Candidates and treatment:

| Cache candidate | Key | TTL/invalidation | Notes |
|---|---|---|---|
| Panchang calculations | `(date, location, config_version)` | Long TTL (Panchang for a past/present date+location+config never changes) | Effectively permanent cache once computed; invalidated only by a config version change. |
| Transit states | `(natal_chart_id, date, config_version)`; Phase 8 adds the methodology profile IDs and engine version to the key (`docs/ASTROLOGY_STANDARDS.md` TR-13) | Short TTL for "current" transit queries (changes daily), long/permanent for past dates | Design only until Phase 18. |
| Repeated chart requests | `(birth_profile_id, calc_config_id, varga_set)` | Effectively permanent (immutable per ADR-004's schema design); cache is a read-through in front of the `charts` schema, not a replacement for it | |
| Knowledge retrieval | `(query_hash, knowledge_version)` | Medium TTL; invalidated on knowledge/embedding version bump | |
| Session/context data | session ID | Session-lifetime TTL | |
| Rate limiting | `(user_id or IP, window)` | Fixed short window (e.g. 1 minute), reset each window | Gateway-level, backed by Redis. |

Rules:
- **Cache is never the ultimate source of truth.** For deterministic astrology: `astro-engine` (and, downstream, the `charts`/`dashas`/`transits`/`panchang` tables) is the authority; Redis is a performance layer only. A cache miss always falls back to computing/reading from the authority, never to a degraded/guessed answer.
- **Stale-data handling**: any cached deterministic result is keyed by its producing `calc_config`/rule-set/knowledge version, so a version bump naturally misses the old cache key rather than requiring active invalidation logic for most cases.
- **Cache-vs-source authority**: explicit — cache keys always include enough version information that "stale" and "wrong" are different things; a stale-but-correct-for-its-version cache entry is fine to serve, an entry for the wrong version must never be served.

---

## 15. Authentication Architecture

```
User
 ↓
Identity (identity.users)
 ↓
Access Token / Session
 ↓
API Gateway (token validated)
 ↓
FastAPI (server/) (authorization: does this token's user own this resource?)
```

- **Authentication**: standard token/session-based auth (exact mechanism — e.g. JWT access + refresh, or session cookies — deferred to Phase 18, since an established authentication direction is not yet locked in an authoritative document; this section fixes the boundary, not the mechanism).
- **Authorization**: resource-ownership checks (birth profile, report, conversation) happen in `server/`/the owning service, not the gateway — the gateway only confirms "this is a valid, unexpired credential."
- **User isolation**: every profile/report/conversation row is scoped to a `user_id`; queries are always scoped, never "fetch by ID alone" without an ownership check.
- **Birth-profile ownership**: a birth profile belongs to exactly one `users` row (with a family/partner flag for profiles a user maintains on behalf of others) — see `profiles.birth_profiles` in §"Database Architecture".
- **Report/conversation ownership**: same pattern — owned by the requesting user, checked on every access.
- **Admin access**: the `admin` app (see §"Service Architecture" / Repository Structure) and `/admin/rules/*` endpoints require a distinct admin-role credential, never the same token scope as a regular user session.
- **Service-to-service authorization**: internal calls between `server/` and the five services are not exposed to the public gateway; they run on an internal network boundary and are not independently user-authenticated per call (the user-auth check happens once, at the gateway/`server/` boundary, and the resulting user/authorization context is passed down explicitly to the services that need it).

---

## 16. AI Infrastructure

```
agent
 ↓
AI Reasoner Interface (LLMProvider — ADR-002)
 ↓
Inference Service
 ↓
Self-hosted Open-Weight Model (Qwen/Llama/Mistral/… — not selected in this document)
 ↓
GPU/CPU infrastructure
```

Agent orchestration (§"Agent Orchestrator Architecture") is strictly separated from model inference — this is what lets the model be replaced without redesigning the agent (ADR-002).

- **Inference boundary**: `agent` sends a single, fully-assembled prompt (evidence bundle + user question + conversation memory, per §8) to the AI Reasoner interface and receives text/stream back — no astrology-specific logic lives on the inference side of that boundary.
- **Model serving**: a dedicated inference service process (candidate stacks: vLLM/Ollama/TGI — selection deferred to Phase 14) sits behind the interface; `agent` never embeds the model in-process.
- **Batching**: the inference service may batch concurrent requests internally; this is invisible to `agent`, which always makes one logical call per response.
- **Context limits**: the evidence-assembly step (§8) is responsible for keeping the evidence bundle + memory within the serving model's context window — if evidence would exceed it, the planner trims to the most relevant evidence rather than silently truncating mid-prompt.
- **Structured output**: where the agent needs machine-parseable output from the model (e.g. a claim list for `verification` to check), the interface supports a structured/JSON-constrained output mode, not free-text parsing.
- **Tool calling**: the interface can expose the astrology service contracts (§"Astrology Service Interfaces") as callable tools if the chosen model supports tool-calling; this is an implementation detail of the planner, not a change to who is allowed to compute facts (the tool boundary is `agent`, invoking `astro-engine`/`rule-engine`, regardless of whether the LLM "calls" it directly or the planner does).
- **Model health**: the inference service exposes a health check; `agent` treats an unhealthy inference service as a failure to be handled per §"Failure Architecture", never as a reason to fall back to guessing an answer itself.
- **Timeout handling**: every inference call has a bounded timeout; a timeout is a failure outcome, not an indefinite wait.
- **Fallback behavior**: a hosted-API fallback may exist for development only (ADR-002) — production fallback on inference failure is a controlled failure response (§"Failure Architecture"), never a silent switch to a different, unreviewed model or provider.

---

## 17. Memory Architecture

Four distinct layers, never merged into one undifferentiated data store:

```
Astrology Facts  (astro-engine/rule-engine output — charts, dashas, evidence)
       ≠
User Memory      (saved profiles, preferences, feedback/correction history)
       ≠
Conversation Context  (recent turns of the current/recent chat sessions)
       ≠
Knowledge Base   (classical texts/rules — shared across all users, not personal)
```

- **Short-term conversation context**: recent messages in `conversation.messages`, scoped to a `chat_session`, retrieved by `agent` for the current turn's evidence assembly.
- **Long-term user memory**: `profiles.birth_profiles`, saved preferences, previously discussed topics, feedback/correction history — persists across sessions, still always scoped to one user.
- **Semantic retrieval**: where memory retrieval benefits from similarity search (e.g. "what did we discuss about this before"), it uses the same `pgvector` mechanism as `knowledge`, but in a separate, user-scoped table/namespace — never mixed into the shared `knowledge.embeddings` corpus.
- **Privacy**: memory is per-user; see `PRODUCT_POLICIES.md`'s Data & Privacy Principles for consent/retention/deletion requirements this layer must satisfy.
- **Deletion**: a user-triggered deletion request removes their `conversation` and long-term memory rows; it never touches shared `knowledge` data (which isn't theirs to delete) or other users' `audit_log` entries.
- **Isolation**: every memory read/write is scoped by `user_id`, enforced the same way as §"Authentication Architecture" describes for any other owned resource.
- **Retention**: per the schedules defined in `PRODUCT_POLICIES.md`.

**Memory must not modify deterministic astrology calculations.** A user's saved preference or past conversation can change how something is phrased or which evidence is prioritized for narration — it can never change a computed chart fact, dasha date, or rule-trigger result.

---

## 18. Observability

```
Client → Gateway → Services (astro-engine / rule-engine / agent / knowledge / verification) → Logs + Metrics + Traces → Monitoring
```

- **Logs**: structured (JSON) logs from every service; every log line carries the request ID injected at the gateway, plus a user/session correlation ID where applicable (never raw sensitive data — birth details/palm images are referenced by ID, not logged in full). Service errors and tool-execution failures are logged with enough context (service, contract, input reference — not raw sensitive payload) to reconstruct what happened.
- **Metrics**: request latency (per endpoint category, §"API Architecture"), error rates, queue depth (§"Queue Architecture"), cache hit/miss (§"Caching Architecture"), database latency, AI inference latency, verification pass/fail rates, tool (service-contract) failure rates.
- **Tracing**: a single trace follows `User request → API Gateway → server/ → agent → astro-engine/rule-engine/knowledge → AI Reasoner → verification`, correlated by the request ID from the gateway — this is the same path as `docs/architecture/diagrams.md` diagram A, and is what lets an engineer reconstruct *why* a specific answer was produced (which evidence, which rule version, which model, whether verification passed) after the fact, using the same `agent_trace` data that also backs the explainability feature.

---

## 19. Failure Architecture

The architecture prioritizes correctness over producing an answer at any cost. Explicit failure modes:

| Failure | Required behavior |
|---|---|
| `astro-engine` unavailable | Do not fabricate results. Return a controlled failure; `agent` must not guess/estimate a chart fact itself. |
| `knowledge` retrieval unavailable | Do not silently invent sourced astrology rules/remedy text. Narration proceeds with reduced supporting language, or fails explicitly if the missing knowledge was required (e.g. a remedy request with no remedy content available). |
| AI Reasoner unavailable | Return a controlled failure or a supported fallback (§"AI Infrastructure") — never silently switch to an unreviewed provider in production. |
| Verification failure | Do not release an unverified response when verification is mandatory for that response type — regenerate, strip the unsupported claim, or add a caveat (ADR-006); as a last resort, return a controlled failure rather than an unverified answer. |
| Database unavailable | Fail safely — reads return a controlled failure, writes are not silently dropped (queued for retry where the workload is asynchronous, per §"Queue Architecture"). |
| Queue failure | Use the retry/idempotency/dead-letter strategy defined in §"Queue Architecture" — never lose a job silently. |
| Timeout | Every external call (DB, cache, inference, inter-service) has a bounded timeout; a timeout is treated as that dependency's failure mode, not an indefinite hang. |
| Partial tool failure | `agent` must know exactly which evidence is missing (not just "something failed") and either replan around it, ask the user for missing critical input, or fail explicitly — it must never narrate as if the missing evidence were present. |

---

## 20. Security Architecture

High-level boundaries (detailed compliance obligations live in `LEGAL_REGULATIONS.md`; product-level principles in `PRODUCT_POLICIES.md`'s Data & Privacy Principles — this section is the technical-architecture statement of those, not a restatement of the legal text):

- **Authentication/authorization**: see §"Authentication Architecture".
- **Secrets**: managed via environment/secret-manager configuration (`infrastructure/`), never committed to the repository (existing `.gitignore` already excludes `.env*`).
- **Encryption**: at rest for all sensitive data categories (birth data, location, palm images, conversations) and in transit (TLS at the gateway, internal-network encryption where the deployment environment requires it).
- **Database isolation**: schema-per-domain (§"Database Architecture") with role-based access control per schema — a service's DB credential only has access to the schemas it owns.
- **API abuse / rate limiting**: enforced at the gateway (§"API Gateway"), backed by Redis (§"Caching Architecture").
- **Sensitive birth data / palm images**: high-privacy handling per `PRODUCT_POLICIES.md` — purpose-limited, minimum retention, access-controlled, never exposed to the AI model beyond what evidence assembly explicitly includes for the current request (i.e. the model never receives a raw dump of a user's full profile/history "just in case" — see §"AI Infrastructure"'s inference boundary).
- **Logs**: never contain raw sensitive payloads (§"Observability").
- **Auditability**: `audit.audit_log` (append-only) covers access to sensitive data.
- **Deletion**: user-triggered deletion honored per §"Memory Architecture" and `PRODUCT_POLICIES.md`.
- **Backups**: covered under §"Database Architecture"; backups inherit the same encryption-at-rest requirement as the live data.
- **Service boundaries**: internal service-to-service calls are not exposed on the public gateway surface (§"Authentication Architecture").

---

## 21. Versioning Architecture

Every one of the following is independently versioned, and every stored/generated artifact records which version(s) produced it, so a result can always be traced back to exactly what produced it:

| Versioned artifact | Where recorded | Consumed by |
|---|---|---|
| Astrology calculation configuration | `calc_config.calculation_configs` | `astro-engine` outputs, cache keys |
| Rule sets | `rules.rule_definitions` (content hash) | `rule-engine` evaluation results |
| Knowledge (structured + embeddings) | `knowledge` schema version field | `knowledge` retrieval, cache keys |
| AI model | recorded per `agent_trace` | verification, explainability |
| Prompt/system policy | recorded per `agent_trace` | verification, explainability |
| Evidence format | schema version on the evidence-bundle contract | `verification`, `agent_trace` |
| API contracts | URL/header version (`/api/v1/...`) | clients, gateway |

A future result must always be able to answer: which calculation standard, which rule version, which knowledge version, which model, which prompt/policy version produced it. Historical calculation behavior must never be silently altered — any change to a versioned artifact is a new, distinct, recorded version, not an in-place mutation (this mirrors `docs/ASTROLOGY_STANDARDS.md`'s own Versioning section, applied system-wide). The complete version registry (a queryable table joining all of the above) is not implemented in Phase 2 — this section defines the architecture it must satisfy.

---

## 22. Deployment Topology

| Environment | Application services | PostgreSQL | Redis | Object storage | AI inference | Notes |
|---|---|---|---|---|---|---|
| Development | Local processes / Docker Compose | Local/containerized instance | Local/containerized instance | Local filesystem or containerized equivalent | Local (small model) or hosted-API stopgap (ADR-002) | Fast iteration; fixtures from `datasets/` seed local DB. |
| Staging | Containerized, mirrors production topology | Managed/containerized instance, staging data only | Containerized instance | Staging bucket | Self-hosted staging inference (smaller/cheaper instance acceptable) | Used for Phase 21 validation/backtesting dry-runs before production. |
| Production | Containerized, scaled per §"Scaling Strategy" | Managed instance with backups (§"Database Architecture") | Managed/containerized instance | Production bucket, encrypted | Self-hosted production inference (ADR-002); Swiss Ephemeris Professional License required before activation (`LEGAL_REGULATIONS.md`) | Monitoring/secrets per §"Observability"/§"Security Architecture". |

Cloud infrastructure is not prematurely provisioned in Phase 2 — this table fixes what each environment must contain, not a specific cloud provider or Terraform layout (deferred to Phase 18/21).

---

## 23. Scaling Strategy

```
Initial architecture (monorepo, five services, one Postgres, one Redis)
       ↓
Measured bottleneck (from §"Observability" metrics)
       ↓
Scale the affected component
       ↓
Only split a service into further services when justified by a measured bottleneck
```

Initial architecture favors simplicity: all five canonical services can run as processes within the same deployable unit(s) during early phases (§"Repository Structure" monorepo rationale already establishes this for the codebase; deployment can start similarly consolidated). Do not introduce additional microservices, a message broker beyond Redis, or a second database technology merely because they "sound scalable" (ADR-004, ADR-005) — each of those is an explicit later decision gated on a measured bottleneck, not a default. The canonical service boundaries (`astro-engine`, `rule-engine`, `agent`, `knowledge`, `verification`) are preserved regardless of how the system scales — scaling changes how many instances of a service run and how they're deployed, never what a service is responsible for.

---

## 24. Data Flow Diagrams

Full Mermaid diagrams: `docs/architecture/diagrams.md`. Summary (ASCII) versions:

**A. Normal astrology question**
```
User → API → agent → required-information planning → astro-engine/rule-engine
     → structured facts/evidence → knowledge (RAG) → evidence bundle
     → AI Reasoner → verification → Response
```

**B. Calculation authority**
```
Input → astro-engine → Deterministic Result → Stored / Passed as Evidence → AI Narration
(AI Narration never writes back into the deterministic-fact tables)
```

**C. Verification**
```
Evidence + Generated Answer → Verifier → PASS | REGENERATE
```

**D. Async job**
```
API → Queue → Worker → Service → Database → Notification/Result
```

**E. Production observability**
```
Client → Gateway → Services → Logs + Metrics + Traces → Monitoring
```

---

## 25. Architecture Decision Records

Full text in `docs/architecture/adr/`:
- **ADR-001**: Deterministic astrology calculation authority
- **ADR-002**: Self-hosted AI inference
- **ADR-003**: Agent/service boundary (Agent Orchestrator = `services/agent`)
- **ADR-004**: PostgreSQL + pgvector as the sole database technology
- **ADR-005**: Redis caching/queue role
- **ADR-006**: Verification as an independent layer
- **ADR-007**: API Gateway vs. FastAPI composition root, and where FastAPI lives (`server/`)

---

## 26. API Architecture

FastAPI (`server/`), versioned `/api/v1/...`, resource groups mirroring subsystems:

```
/auth/*
/users/*
/birth-profiles/*          birth profiles, family/partner profiles
/charts/*                  D1/D9/vargas/ashtakvarga, planetary positions — direct,
                            deterministic, no LLM involved
/dashas/*
/transits/*, /sade-sati/*
/panchang/*, /muhurta/*
/compatibility/*           kundli matching
/numerology/*
/chat/*                    conversation endpoints — SSE/WebSocket streaming for the agent
/reports/*                 generate/fetch specialized reports
/memory/*                  conversation history, saved preferences (user-scoped)
/health                     liveness/readiness, no auth required
/admin/rules/*              rule authoring/versioning management (internal/admin auth only)
```

(`/voice/*` is exposed by `agent`'s `voice/` subpackage and delegates to `/chat` internally — not a separate top-level category.)

For each category:

| Category | Purpose | Caller | Service owner | Sync/Async | AuthN required |
|---|---|---|---|---|---|
| `/auth` | Login/session/token issuance | clients | `identity` (via `server/`) | Sync | No (this is how you get one) |
| `/users` | Profile/account management | clients | `identity` | Sync | Yes |
| `/birth-profiles` | CRUD on birth profiles | clients | `astro-engine` (via `server/`) | Sync | Yes |
| `/charts` | Chart/varga retrieval | clients, `agent`, `reports` | `astro-engine` | Sync | Yes |
| `/dashas` | Dasha timeline retrieval | clients, `agent`, `reports` | `astro-engine` | Sync | Yes |
| `/transits` | Transit/Sade Sati retrieval | clients, `agent`, `reports` | `astro-engine` | Sync | Yes |
| `/panchang`, `/muhurta` | Panchang/Muhurta lookup | clients, `agent` | `astro-engine` | Sync (cached, §"Caching Architecture") | Yes |
| `/compatibility` | Kundli matching | clients, `agent` | `astro-engine` | Sync (may background heavy batch matches) | Yes |
| `/numerology` | Numerology results | clients, `agent` | `astro-engine` | Sync | Yes |
| `/chat` | Conversational Q&A | clients | `agent` | Async-capable (streaming) | Yes |
| `/reports` | Report generation/fetch | clients | `agent/reports` | Async (queue, §"Queue Architecture") | Yes |
| `/memory` | Conversation/preference retrieval | clients, `agent` | `agent`-owned data | Sync | Yes |
| `/health` | Liveness/readiness | gateway, monitoring | each service | Sync | No |
| `/admin/rules` | Rule authoring/versioning | admin app | `knowledge`/`rule-engine` | Sync | Yes (admin role) |

Versioning strategy: URL-prefixed (`/api/v1`), matching §"Versioning Architecture"'s API-contracts row; a breaking change to a category introduces `/api/v2/<category>` rather than mutating `/v1` in place.

Design rule: **every chart/dasha/transit/panchang/compatibility/numerology endpoint is directly callable without going through `/chat`.** `agent` is a consumer of these APIs internally, not a gatekeeper in front of them — this is what lets "just show me my dasha timeline" stay instant and hallucination-free, and lets `reports` and future clients reuse the same deterministic surface `agent` uses.

---

## 27. Repository Structure

**LOCKED canonical structure**, updated per ADR-007 to add `server/`:

```
pandit-ji/
  apps/
    mobile/                 Flutter client
    web/                    Next.js web client
    admin/                  internal admin app (rule authoring/versioning, content ops)
  server/                   FastAPI composition root — routers, dependency wiring,
                            auth-token validation handoff from the gateway; composes
                            the five services below; owns no business logic (ADR-007)
  services/
    astro-engine/           deterministic calculation library (§6)
    rule-engine/            rule DSL + evaluator (§7)
    agent/                  intent, planner, LLM orchestration, evidence assembly (§8);
                            includes voice/ (STT/TTS integration) and reports/ (report
                            templates + assembly) as subpackages
    knowledge/              RAG store + ingestion pipelines; rules/*.yaml source-of-truth (§10)
    verification/           claim/hallucination/contradiction checking, regression + backtesting (§11)
  packages/
    shared/                 config, logging, auth utils shared across services
    contracts/              shared pydantic models / OpenAPI-generated client types for web/mobile/admin
                            (also where the Astrology Service Interface contracts, §9, are defined)
    ui/                     shared UI component library across web/mobile/admin
  datasets/                 golden fixtures, rule test fixtures, backtesting data
  tests/
    fixtures/               golden birth-data + independently cross-checked expected outputs
    astro-engine/  rule-engine/  agent/  verification/  integration/
  docs/
    ARCHITECTURE.md          (this document)
    ASTROLOGY_STANDARDS.md   canonical astrology standards document (locked location)
    architecture/
      diagrams.md            Mermaid diagrams (§24)
      adr/                   architecture decision records (§25)
    rule-authoring-guide.md  (Phases.md Phase 6)
  infrastructure/
    docker/
    docker-compose.yml
    migrations/             Alembic
    gateway/                API Gateway configuration (§4; infra config, not app code)
  features.md
  Phases.md
  SOURCE_OF_TRUTH.md
  TECH_STACK.md
  PRODUCT_POLICIES.md
  LEGAL_REGULATIONS.md
  PRICING.md
```

Canonical service names (locked, per project-owner decision): `astro-engine`, `rule-engine`, `agent`, `knowledge`, `verification`. Do not use alternative names such as `astrology-engine`, `ai-agent`, or `knowledge-base` anywhere in the codebase or documentation.

Note on `voice/` and `reports/`: subpackages of `services/agent/` rather than top-level services, since the locked list has exactly five top-level services (both still exist as functional subsystems, §2).

Note on `server/`: new in Phase 2, resolving the previously-open "where does the FastAPI layer live" item — see ADR-007. It is additive; no locked service or app name was renamed or removed.

Monorepo is deliberate: these components change together frequently during early phases and a monorepo keeps their interfaces honest without cross-repo version drift. Revisit only if/when a service needs independent scaling or a separate deploy cadence (§"Scaling Strategy").

---

## 28. Execution Roadmap

The authoritative development roadmap is maintained in `Phases.md`. This document defines system architecture and technical boundaries; `Phases.md` defines the implementation sequence, phases, steps, deliverables, dependencies, and exit criteria (the locked 21-phase plan). When the two documents appear to conflict regarding development sequence, `Phases.md` is authoritative.

The subsystems, engines, and services named throughout this document are built in the order, and to the deliverables/exit-criteria, that `Phases.md` specifies — this document does not restate or re-derive that sequence. Where a section above cites a specific phase inline, that citation is a pointer for convenience, not a duplicate definition.

---

## 29. Technical Risks

- **Swiss Ephemeris licensing — decision locked, procurement still open**: Professional License chosen (see `LEGAL_REGULATIONS.md`); not yet purchased; signed agreement required before public/commercial distribution (`Phases.md` Phase 21 gate), not before internal development (Phase 4).
- **Historical timezone/DST accuracy**: pre-standardization birth times are genuinely ambiguous in tzdata; wrong resolution silently shifts the whole chart.
- **Ayanamsa/house-system disagreement across traditions**: locking Lahiri + Vedic whole-sign is necessary but will visibly disagree with some other apps/astrologers; must be configurable and clearly disclosed.
- **Self-hosted LLM quality/latency**: open-weight models may lag hosted frontier models on nuanced Hindi/Hinglish reasoning and latency under real hardware budgets.
- **Rule completeness and cross-tradition conflict**: classical yoga/dosha rules number in the hundreds and genuinely disagree across schools.
- **Hallucination verification is imperfect in general**: claim-extraction has false negatives; treat the verifier as strong mitigation, not a guarantee.
- **Voice for Hindi/Hinglish code-switching**: open-source STT/TTS support is weaker than for pure English.
- **KP/Lal Kitab/Nadi/Chinese systems are each their own research project**: explicitly deferred to `Phases.md` Phase 9; `docs/ASTROLOGY_STANDARDS.md` already marks Lal Kitab/Nadi as provisional.
- **Sensitive data / regulatory exposure**: needs a privacy/legal review before `Phases.md` Phase 21, ideally sketched by Phase 18.
- **Backtesting ground truth**: no existing "outcome vs. prediction" dataset; collecting it ethically/usefully is a design problem, not just engineering.
- **Redis-backed queue delivery guarantees** (new, Phase 2): a Redis-backed queue (ADR-005) does not guarantee exactly-once delivery — every job must be designed idempotent from the start, or duplicate processing (e.g. a report generated twice) becomes a real risk.
- **API Gateway product choice** (new, Phase 2): §4/ADR-007 fix responsibilities, not a specific product; a wrong early choice (e.g. one that can't cleanly separate authN-enforcement from authZ) could require rework — evaluate against these responsibilities explicitly before adopting one in Phase 18.

---

## 30. Components Requiring Research Before Implementation

1. ~~Swiss Ephemeris licensing path~~ **RESOLVED — LOCKED**: Professional License (`LEGAL_REGULATIONS.md`). Procurement remains open.
2. Historical timezone/DST dataset and geocoding source for birthplaces.
3. Rule-engine implementation approach: hand-rolled vs. existing Python rules library.
4. Self-hosted LLM + serving stack selection against realistic hardware/latency budgets.
5. Claim/hallucination-verification technique: regex/NER vs. a smaller dedicated verifier model.
6. Open-weight STT/TTS models with credible Hindi/Hinglish code-switching support.
7. Authoritative sourcing for KP/Lal Kitab/Nadi/Chinese/Vastu rule content.
8. Backtesting/outcome-data collection design.
9. Concrete authentication mechanism (JWT vs. session, refresh strategy) — deferred from §"Authentication Architecture" to Phase 18.
10. Concrete API Gateway product — deferred from §4/ADR-007 to Phase 18.

---

## 31. Deterministic vs. AI-Driven — Explicit Split

**Deterministic (`astro-engine`/`rule-engine` only — the AI Reasoner never computes or asserts these):**
Planetary positions & degrees · Ascendant/houses/cusps · Rashi/Nakshatra/Pada · All divisional charts · Dignity/exaltation/debilitation/combustion/retrograde flags · Ashtakvarga bindus · Vimshottari Mahadasha/Antardasha/Pratyantar dates · Transit positions, ingress and station instants & sign-based transit-to-natal contacts (Phase 8; degree angles are not produced) · Sade Sati segments (a `MODERN_TRADITION` profile) · Western tropical positions, Placidus cusps and degree-and-orb aspects (Phase 9 WP-D, a separate system from every Vedic fact) · KP cusps, star/sub lords, significators, Ruling Planets and horary charts (Phase 9 WP-E) · Shadbala component values (Phase 9 WP-F) · planet-level Rashi Drishti, Arudha Padas and Karakamsa (Phase 9 WP-G) · Chinese Four Pillars (Phase 9 WP-H) · Tarot layouts from a caller-supplied seed or selection (Phase 9 WP-I) · Panchang elements · Muhurta windows · Ashtakoot/Guna Milan scores · Numerology numbers · Yoga/Dosha trigger set.

**AI-driven:**
Natural-language intent/domain understanding · Conversational flow & follow-ups · Turning an evidence bundle into coherent, personalized, language-appropriate narrative · Deciding which of many triggered rules matter most to *this* question · Remedy phrasing · Voice turn-taking.

**Gray zone requiring explicit guardrails:** dosha "severity" framing and "when might X happen" narratives combine a deterministic time window (must always be cited exactly) with an interpretive claim (must always be hedged). `verification`'s contradiction/claim checks exist specifically to police this boundary.

---

## 32. Phase 2 Completion / Validation

Validation performed before declaring Phase 2 complete (see final report for results):
- **Documentation**: all required architecture sections present (§4-§27 above cover Services, APIs, Queues, Databases, AI infrastructure, Caching, Authentication, Observability, plus Agent/Astrology-interfaces/Knowledge/Rule/Verification/Memory/Failure/Security/Versioning/Deployment/Scaling/Diagrams/ADRs per Phase 2's required-documentation list); diagrams in `docs/architecture/diagrams.md` are valid Mermaid; no duplicate source-of-truth document was created (single `docs/ARCHITECTURE.md`, single `docs/ASTROLOGY_STANDARDS.md`, unchanged).
- **Architecture**: every Phase 2 requirement (§"Mandatory roadmap cross-check", conversation record) is covered; every one of the five canonical services has a clear responsibility and explicit "not responsible for" boundary (§5); data flow is unambiguous (§3, §24); the AI cannot become calculation authority (ADR-001, §31); verification has a defined place (§11, ADR-006); asynchronous work has defined handling (§13); an authentication boundary exists (§15); observability exists (§18).
- **Repository/consistency**: no forbidden service names (`astrology-engine`, `ai-agent`, `knowledge-base`) introduced; no hosted-AI production dependency introduced (ADR-002 reaffirmed); no unwanted authorship/contributor attribution introduced (per the project's locked identity/attribution rule); no pricing changes; no product-scope changes; no contradiction with `docs/ASTROLOGY_STANDARDS.md`, `features.md`, `SOURCE_OF_TRUTH.md`, `PRODUCT_POLICIES.md`, or `LEGAL_REGULATIONS.md`.

---

## 33. Getting Started

To begin or resume work: open `Phases.md`, identify the current phase, its deliverables, dependencies, exit criteria, and explicitly excluded work, and proceed from there. Use this document as the technical reference for *how* to build whatever that current phase calls for; use `Phases.md` for *what phase comes next* and *when a phase is done*. Phase 2 is now complete; the next phase is Phase 3 (Repository & Engineering Foundation) — do not begin it without explicit authorization.

---

## 34. Known Contradictions Between Documents (Open Items)

1. **Standards document duplication — RESOLVED, LOCKED** (Phase 1 reconciliation). Canonical standards document is `docs/ASTROLOGY_STANDARDS.md`; no separate `docs/calculation-standards.md`.
2. **Repository structure mismatch — RESOLVED, LOCKED** (Phase 1 reconciliation; FastAPI placement sub-item now also resolved in Phase 2). Canonical structure per §27 above, including `server/` for the FastAPI composition root (ADR-007). No remaining sub-item.
3. **Palm reading: scope/priority conflict — RESOLVED, LOCKED** (explicit project-owner decision, pre-Phase-3). AI Palm Reading is now a locked product feature (`features.md` §34), consistent with the Pre-Phase-1 Foundation package's `README.md`/`research/PALM_READING.md`. `features.md` §33 no longer lists palm reading under Future Expansion. Its dedicated implementation phase is `Phases.md` Phase 13 (Palm Reading & Vision Intelligence, inserted pre-Phase-3, shifting the former Phase 13-20 to 14-21) — the product-feature decision and the implementation-phase assignment are deliberately kept distinct, per that decision.
