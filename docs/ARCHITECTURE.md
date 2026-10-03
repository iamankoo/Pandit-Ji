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
| 10 | **FastAPI composition root** | `server/` | Application-level HTTP layer composing the canonical services into callable endpoints (the five of this table today; `palm-vision` joins them when Phase 13 implements it, row 14). See ADR-007. |
| 11 | **Web/Mobile/Admin Clients** | `apps/{web, mobile, admin}` | Presentation only, no astrology logic. |
| 12 | **Security/Privacy/Audit** | cross-cutting, see §"Security Architecture" | AuthN/authZ, encryption at rest for birth/palm data, audit logging, data deletion, access control. |
| 13 | **Human Ecosystem / Content** (future) | not yet scheduled | Live astrologer marketplace, articles, festival calendar — explicitly deferred, not in initial baseline builds. |
| 14 | **Palm Vision** (approved 2026-10-02, Phase 13; implemented 2026-10-03, no trained model) | `services/palm-vision` | Deterministic, versioned palm image analysis: image quality, hand detection, hand-side classification, palm region, landmarks, the palm-line/feature model and the structured `PalmFactSet`. Owns no knowledge text, no palm rules, no narration, no storage API and no LLM. See §35, ADR-008 and `research/PALM_READING.md`. |

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

Canonical service names are locked and must not be renamed: `astro-engine`, `rule-engine`, `agent`, `knowledge`, `verification`, and, from the owner's decision of 2026-10-02 (ADR-008), `palm-vision` (approved for Phase 13; implemented 2026-10-03). Do not introduce alternatives such as `astrology-engine`, `ai-agent`, or `knowledge-base` anywhere in code or documentation.

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

### palm-vision (approved 2026-10-02; Phase 13; not yet implemented)
**Responsible for**: the deterministic, versioned palm image pipeline: image quality validation, hand detection, hand-side classification, palm region extraction, landmarks, the palm-line/feature model and the structured `PalmFactSet` (see §35, ADR-008).
**Explicitly not responsible for**: knowledge text (that is `knowledge`), palmistry rules (the `rule-engine` under a separate palm ruleset root), narration (`agent`, Phase 15), verification (`verification`, Phase 16), any LLM (Phase 14), any storage or upload API (Phase 18). It has zero dependency on `astro-engine`, `rule-engine`, `knowledge`, `agent` and `verification`, and none of them imports it.

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
  panchang/         # Phase 10: tithi, vara, nakshatra, yoga, karana with exact transitions, sunrise/moonrise, lunar months (Lahiri saura frame by default, CRC fixed frame as a labelled alternative, both reported), horas, eighth-day parts, Panchaka, Bhadra, special points (PC-01 to PC-31)
  muhurta/          # Phase 10: purpose-tagged, source-tagged factor evaluation and search (MU-01 to MU-14); rules held as versioned astro-engine data with `export_rules()`, an intentional, owner-approved deviation from the Phase 6 rule format (MU-03)
  compatibility/    # Phase 11: two never-merged profiles (Muhurta Chintamani Ashtakoot,
                    #   Kalaprakasika ten poruthams), minimum-age gate, no gender/role input
  numerology/       # Phase 11: Chaldean (Cheiro, default) and Pythagorean (Balliett) profiles
  western/          # tropical + Placidus module, kept isolated from Vedic assumptions (Phase 9 WP-D: built as `pandit_astro_engine/western`, standards WD-01 to WD-20; own body/sign identifiers, no Vedic imports)
  kp/               # KP (Krishnamurti Paddhati) foundation (Phase 9 WP-E, standards KP-01 to KP-16): Krishnamurti ayanamsa applied only for the call, sidereal Placidus cusps, star/sub/sub-sub lords, the derived 249-entry table, four-level significators, Ruling Planets, KP horary charts
  shadbala/         # Shadbala components of BPHS Ch. 27 (Phase 9 WP-F, SB-01 to SB-20); verse-literal, no total while components are not evaluable; plus the separate modern Raman profile with totals (raman.py, raman_service.py; SR-01 to SR-24), never mixed with the verse profile
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
| `TarotDrawRequest` / `TarotSelectionRequest` / `TarotLayout` | `astro-engine` | Yes | Phase 9 WP-I. Card placements only, seeded or user-selected; no meanings; provenance entries (TA-11) (§Tarot standards). |
| `RamanShadbalaRequest` / `RamanShadbalaFacts` | `astro-engine` | Yes | Phase 9 closure. The modern Shadbala profile after B. V. Raman with totals; two no-default readings; Cheshta in the frame of Raman's tables (SR-01 to SR-24). |
| `ShadbalaMethodRequest` / `ShadbalaMethodResult` | `astro-engine` | Yes | Shadbala method policy (v1.22.0, SM-01 to SM-12): one method per request, `MODERN_RAMAN` (default user-facing) or `BPHS_VERSE_REFERENCE`; never combined; unconfigured Raman readings reported, never defaulted. |
| `shadbala_for_rule` | `rule-engine` | Yes | SM-09 gate: a planet's total only from a complete `MODERN_RAMAN` result, otherwise `NOT_EVALUABLE` with one reason; no shipped rule calls it. |
| `JaiminiFactsRequest` / `JaiminiFacts` | `astro-engine` | Yes | Phase 9 closure. The WP-G facts object with provenance (JN-19). |
| `EvidenceBundle` sections `kp`, `shadbala`, `jaimini`, `chinese`, `tarot` | `rule-engine` | Yes | Phase 9 closure. Optional, transport-only sections (EV-01 to EV-10); omitted when absent; no rule reads them. |
| `PanchangRequest` / `DailyPanchang` | `astro-engine` | Yes | Phase 10. Input: civil date + location + IANA timezone + sunrise convention (default CRC 1955). Output: the five limbs with exact transitions, the selected lunar month (Lahiri saura frame by default) and the months of both frames, horas, day parts, Panchaka, Bhadra; `not_implemented` lists Choghadiya and Gowri (PC-01 to PC-24). |
| `SpecialPointsRequest` / `SpecialPointsFacts` | `astro-engine` | Yes | Phase 10. Upagrahas, Gulika/Mandi, special Lagnas, Pranapada, each with its reading's profile (PC-25 to PC-29). |
| `MuhurtaEvaluateRequest` / `MuhurtaEvaluation`, `MuhurtaSearchRequest` / `MuhurtaSearchResult` | `astro-engine` | Yes | Phase 10. Vivaha, Griha Pravesha, Chaula factor facts and windows; no verdict (MU-01 to MU-14). |
| `EvidenceBundle` section `panchang` | `rule-engine` | Yes | Phase 10. Optional, transport-only (PC-30); no rule reads it. |
| `CompatibilityRequest` / `CompatibilityFacts` | `astro-engine` | Yes | Input (Phase 11, v1.25.0 CM-03): a matching `profile` with no default (`ASHTAKOOT_MUHURTA_CHINTAMANI_VIVAHA_21_37_V1` or `TEN_PORUTHAM_KALAPRAKASIKA_IYER_1917_XIII_V1`), `person_a` and `person_b` (birth date-time, timezone, coordinates, precision; no gender, sex or role), `as_of_date`, `participant_consent_attested`. Output: status (`complete`, `partial`, `not_evaluable`, `blocked_by_policy`, ...), the two birth-Moon placements, per-factor facts with reasons, doshas with exception conditions, the 36-point total only when every kuta is evaluated, ten-porutham counts, methodology metadata and limitations. *(Corrected in Phase 11: the Phase 2 row assumed Ashtakoot scores only.)* |
| `NumerologyRequest` / `NumerologyFacts` | `astro-engine` | Yes | Input (Phase 11, v1.25.0 NU-01 to NU-11): `profile` (Chaldean default), civil `date_of_birth` and/or `name.latin_spelling` (no transliteration), `master_number_policy` (Pythagorean: required). Output: Moolank, Bhagyank, each profile's date numbers, name number with normalisation notes, associated numbers, interpretation references (interpretation deferred), methodology metadata. |
| `RuleEvaluationRequest` / `RuleEvaluationResponse` | `rule-engine` | Yes | Input: normalized Facts object (from an `astro-engine` response). Output: evidence bundle (triggered rules + contradictions). |
| `KnowledgeRetrievalRequest` / `KnowledgeRetrievalResponse` | `knowledge` | No (retrieval, not fact) | Input: query/context. Output: narration-only text chunks + sources — never chart facts. |
| `PalmFactSet` / `PalmFact` | `palm-vision` | Yes, within a documented numerical tolerance (decision K) | Phase 13 (approved, not implemented). Input: an image reference and its bytes. Output: observed and derived palm facts with provenance and artifact identities; never an interpretation. Defined in `packages/contracts`. See §35. |
| `PalmRuleEvaluation` / `PalmEvidenceBundle` | `rule-engine` (palm ruleset) / assembled from the two | Yes | Phase 13 (approved, not implemented). The interpreted layer and the bundle later phases consume; separate from the Phase 6 evidence bundle. See §35. |

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

### Phase 12 implementation (standards v1.26.0, KB-01 to KB-42)

`services/knowledge` (package `pandit_knowledge` 0.2.0) implements the two stores of this section. It is a library with internal service interfaces only; HTTP and the final database API are Phase 18, narration is Phase 15, the final embedding model is Phase 14.

- **Structured store (source-backed knowledge, not rules).** `concepts` (planets, houses, domains, terms, Tarot cards), `statements` (what one source profile says: significations, planetary ranks, house karakas, a strength remark, derived inversions, recorded source variances), `terms`, `rule_references` (pointers to existing rules, tables and astro-engine profiles; the rule logic stays in the rule engine and the rule YAML is untouched), `domain_mappings` (house to Career, Marriage, Finance, Education, each `SOURCE_SUPPORTED`, `PROJECT_DERIVED`, `UNRESOLVED_CONFLICT` or `NOT_EVALUABLE`) and `exceptions`.
- **Explanatory store.** `chunks` (deterministic, one passage and one provenance each; `text_origin` distinguishes verbatim public-domain `SOURCE_TEXT` from `PROJECT_RENDERING` templates) and `embeddings` (an untyped pgvector column keyed by an `embedding_configs` identity, so models of different dimensions coexist).
- **Versioning.** Every row belongs to a `knowledge_versions` row identified by a snapshot hash; a sealed version is immutable (database triggers) and the ingestion is idempotent and resumable. Naming: the tables are schema-qualified (`knowledge.chunks`, `knowledge.sources`, `knowledge.embeddings`); the Phase 2 names `knowledge_chunks` and `embeddings` in §12 became `chunks` and `embeddings`, plus the tables above.
- **Retrieval.** `Retriever` returns bounded, deterministic hits with full provenance and the fixed stamp `KNOWLEDGE_TEXT_NOT_A_CHART_FACT`; it reads sealed versions only, never writes and never stores the query. Search is exact by default; an HNSW partial expression index per embedding configuration is available and opt-in (`APPROXIMATE_INDEX_SEARCH`).
- **Boundaries.** The knowledge package imports no calculation or rule code and no calculation, rule or server code imports it, except the server's `get_health` composition (ADR-007). The evidence bundle gained no knowledge section: knowledge is not a chart fact. Chart calculation never embeds or retrieves.
- **Multilingual.** Identifiers and structured facts are language-neutral; text carries a language tag. Only English knowledge text exists; no Hindi or Hinglish text and no translation was added. Retrieval behaviour for Hindi and Hinglish queries is measured and reported, not claimed (KB-25).
- **Not in this phase.** HTTP endpoints, narration, a final model, verification, remedies, Lal Kitab, numerology interpretation text, Hindi/Sanskrit text, palm knowledge.

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
| `knowledge` | Phase 12 (migration `0002`): `knowledge_versions`, `sources`, `source_editions`, `concepts`, `statements`, `terms`, `rule_references`, `domain_mappings`, `exceptions`, `chunks`, `embedding_configs`, `embeddings` (pgvector), `ingestion_runs` | Source-backed structured knowledge and a retrieval corpus, versioned and sealed (§10). The Phase 2 names `knowledge_chunks` and `embeddings` became `chunks` and `embeddings`. No chart or user data. |
| `compatibility` | `match_requests`, `guna_scores`, `match_results` | References two `birth_profiles`. *(Phase 11 note: results are per-profile factor facts; a `guna_scores` table would hold only Ashtakoot points; the schema is designed in Phase 18. No gender or role column; consent for the second person's data is required.)* |
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
- **Palm data (decided 2026-10-02, §35)**: no palm table exists in this section. Palm image metadata, palm facts and palm evidence bundles are user data whose tables, deletion cascade, consent and retention records are Phase 18 (the `audit` schema covers palm access by id only); the Phase 13 palm-fact contract and rule outputs are defined in `packages/contracts` without a user-data migration. Palmistry knowledge is knowledge (it belongs in the `knowledge` schema as a new knowledge version and needs a forward-only migration at implementation) and holds no user data.
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
- **Service-to-service authorization**: internal calls between `server/` and the canonical services (the five, and `palm-vision` once implemented) are not exposed to the public gateway; they run on an internal network boundary and are not independently user-authenticated per call (the user-auth check happens once, at the gateway/`server/` boundary, and the resulting user/authorization context is passed down explicitly to the services that need it).

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
- **Model serving**: a dedicated inference service process sits behind the interface; `agent` never embeds the model in-process. Phase 14 (2026-10-03) selected vLLM serving `Qwen/Qwen3-8B` and implemented the interface and runtime as `pandit_agent.llm` (§36, ADR-009); the vLLM server itself has not been run by this repository.
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

Initial architecture favors simplicity: all five canonical services (and `palm-vision` once Phase 13 implements it; it may need different hardware and is the likeliest first split) can run as processes within the same deployable unit(s) during early phases (§"Repository Structure" monorepo rationale already establishes this for the codebase; deployment can start similarly consolidated). Do not introduce additional microservices, a message broker beyond Redis, or a second database technology merely because they "sound scalable" (ADR-004, ADR-005) — each of those is an explicit later decision gated on a measured bottleneck, not a default. The canonical service boundaries (`astro-engine`, `rule-engine`, `agent`, `knowledge`, `verification`) are preserved regardless of how the system scales — scaling changes how many instances of a service run and how they're deployed, never what a service is responsible for.

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
- **ADR-008**: The palm-vision component (`services/palm-vision`), approved 2026-10-02

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
                            the canonical services below; owns no business logic (ADR-007)
  services/
    astro-engine/           deterministic calculation library (§6)
    rule-engine/            rule DSL + evaluator (§7)
    agent/                  intent, planner, LLM orchestration, evidence assembly (§8);
                            includes voice/ (STT/TTS integration) and reports/ (report
                            templates + assembly) as subpackages, and (Phase 14, §36, ADR-009)
                            llm/ (the self-hosted LLM capability: LLMProvider interface, model
                            manifest and loader, structured output); data assets (manifests,
                            pinned chat template) in services/agent/llm/; and (Phase 15, §37,
                            ADR-010) orchestration/ (bounded planner, allow-listed evidence
                            tools, context assembly, structured narration, policy; no verification)
    knowledge/              structured knowledge, versioned ingestion, chunking, embedding
                            providers and retrieval (Phase 12, §10); rules/*.yaml source-of-truth;
                            content/ curated Phase 12 records
    verification/           claim/hallucination/contradiction checking, regression + backtesting (§11)
    palm-vision/            (Phase 13; approved 2026-10-02, implemented 2026-10-03) deterministic palm image
                            pipeline: quality, hand detection, side, region, landmarks, line/feature model,
                            PalmFactSet (§35, ADR-008); no knowledge text, rules, narration, storage or LLM
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
11. Palm vision (added 2026-10-02): palmistry sources, the palm-fact taxonomy, image-quality calibration, the line model approach, consented training and evaluation data, and the legal classification of palm images. Researched in `research/PALM_READING.md`; the methodology is locked in `docs/ASTROLOGY_STANDARDS.md` v1.27.0 (PM-01 to PM-24); the dataset, calibration, model and counsel items remain open there.

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

4. **Phase 12 interpretation scope (`Phases.md` "Interpretations" versus §10 "language only") — RESOLVED, LOCKED** (explicit project-owner decision, 2026-10-01). Interpretation content is allowed in the knowledge base when it is source-backed, provenance-tagged, profile-specific where sources differ and distinct from chart facts and AI narration; nothing is generated. §10's "language only" described the explanatory store, not the structured store. Recorded in `docs/ASTROLOGY_STANDARDS.md` KB-03.
5. **Palm vision component versus the five locked services — RESOLVED, LOCKED** (explicit project-owner decision A, 2026-10-02). `docs/ARCHITECTURE.md` §2 and §27 listed five canonical services and the repository has no vision component, while `Phases.md` Phase 13 and `TECH_STACK.md` require a vision pipeline (OpenCV, MediaPipe, PyTorch). The owner approved a sixth canonical component, `services/palm-vision`; `astro-engine` (a calculation library), `knowledge` (no calculation or model code) and the other services were rejected as homes (ADR-008). Dependent documents updated: §2, §5, §9, §27, §30, §35, ADR-008, `CONTRIBUTING.md`, `TECH_STACK.md`. Historical statements of "five services" in the Phase 2 and Phase 3 records of `SUMMARY.md` stay as history.
6. **Phase 13 scope versus Phases 14, 15, 16 and 18 — RESOLVED, LOCKED** (explicit project-owner decision B, 2026-10-02). The Phase 13 text listed "AI narration" and a "verification pass" as its own deliverables while Phases 14 (LLM), 15 (agent and narration), 16 (verification) and 18 (upload and storage) own them. Resolution: Phase 13 builds the deterministic palm facts, the palmistry knowledge and rules, the palm evidence bundle, the evaluation harness and the interfaces; the later phases build the rest. `Phases.md` Phase 13 and §35 record the matrix.

---

## 35. Palm Vision Architecture (approved 2026-10-02; Phase 13; implemented as infrastructure 2026-10-03, see the end of this section)

Decisions and research: `research/PALM_READING.md` (decisions A to M in its section 1; the final owner decisions A to G of 2026-10-02 in its section 1A); methodology locks `docs/ASTROLOGY_STANDARDS.md` v1.27.0 PM-01 to PM-24 and v1.28.0 PM-25 to PM-31; decision record ADR-008. The implementation record is at the end of this section. No owner decision remains open for Phase 13; only the legal launch gates and measured quantities remain.

```
Palm image (by reference)
        ↓
services/palm-vision:  quality → hand detection → side → palm region → landmarks → line/feature model
        ↓
PalmFactSet (OBSERVED + DERIVED facts, provenance, artifact identities)      [packages/contracts]
        ↓
rule-engine (separate palm ruleset root) + knowledge (palm knowledge, new knowledge version)
        ↓
PalmRuleEvaluation (INTERPRETED, cites fact ids) → PalmEvidenceBundle
        ↓
agent (Phase 15, narrates only)  →  verification (Phase 16, checks claims against the bundle)
```

- **Component.** `services/palm-vision` (canonical name, locked). It owns the image pipeline and the palm-line/feature model; it owns no knowledge text, no palm rules, no narration, no storage API and no LLM.
- **Dependency direction.** `palm-vision` depends on `packages/contracts` and `packages/shared` only. `astro-engine`, `rule-engine`, `knowledge`, `agent` and `verification` do not import it; they consume `PalmFactSet`, `PalmRuleEvaluation` and `PalmEvidenceBundle` through `packages/contracts`. `palm-vision` imports none of them (tested at implementation, like the Phase 12 boundary). `server/` composes only its health check until Phase 18.
- **Palm-fact contract.** `PalmFactSet`, `PalmFact` (OBSERVED or DERIVED only), `PalmRuleEvaluation` (INTERPRETED) and `PalmEvidenceBundle`, specified in `research/PALM_READING.md` sections 8 and 15; canonical JSON without floating-point numbers, fixed-point coordinates in a palm-canonical frame, SHA-256 hashes, artifact, preprocessing and runtime identities, a derivation chain. The Phase 6 evidence bundle gains no palm section.
- **Relationship to `knowledge`.** Palm knowledge (sources, concepts, source-profile statements, conflicts, and the source coverage manifest) is a separate, additive, forward-only knowledge version, never a mutation of `KV-06361d7aba28c1ce`; its content lives in `services/knowledge/content/palm/`, a subdirectory the Phase 12 content loader never opens. The vocabulary extension (domain `PALMISTRY`, a palm rule kind) is a forward-only migration at implementation. Palm knowledge references palm rules by id; the existence of every referenced id in `services/rule-engine/palm_rules/` is asserted by a cross-package integration test, so the knowledge package imports no rule code and reads no rule-engine tree. Knowledge text is never a palm fact. **Source coverage is explicit:** a machine-checkable manifest records, for every concept, its status (`SUPPORTED`, `PARTIALLY_SUPPORTED`, `NOT_SUPPORTED`, `NOT_READ`, `EXCLUDED_BY_POLICY`); an unread concept evaluates to `NOT_EVALUABLE` and cannot be used for production interpretation (decision D).
- **Methodology profiles.** `PALM_WESTERN` is the only implemented profile (Heron-Allen, Cheiro and Benham as separate source profiles, never merged, conflicts `UNRESOLVED_CONFLICT`). `PALM_INDIAN_HASTA_SAMUDRIKA` is a reserved extension point, status `RESEARCH_PENDING`, not implemented and producing no interpretation until a primary or authoritative translated source, provenance, a copyright determination and a qualified reviewer exist (decision E).
- **Relationship to `rule-engine`.** Palm rules are evaluated from a completely separate ruleset root with its own manifest. The Phase 6 Vedic ruleset and its hash are unchanged: the knowledge service hashes and the rule-engine loader loads every YAML under the directory they are given, so palm rule files must never be placed under `services/knowledge/rules/`. **The canonical and only root is `services/rule-engine/palm_rules/`** (final owner decision C, 2026-10-02; no alternative is documented): a separate ruleset with its own manifest and version, which does not modify the Phase 6 Vedic ruleset, does not alter `KV-06361d7aba28c1ce` and cannot be included in the Vedic rule hash; it requires dedicated isolation tests (the Phase 6 hash and the Phase 12 snapshot unchanged, disjoint rule-id namespaces, a palm rule never loading into the Vedic engine and the reverse). A palm fact family is a rule-engine extension that changes no Phase 6 rule file, hash or evidence field. Palm rules are limited to a small source-backed fixture set in Phase 13 (decision B); each rule belongs to exactly one source profile and one source location recorded as read in the source coverage manifest, and the permanently prohibited interpretation categories (standards PM-13, PM-25) can never become a rule.
- **Relationship to `astro-engine`.** None: palmistry here has no astronomical input and palm-vision is not part of the calculation engine.
- **Relationship to `agent` and `verification`.** The agent (Phase 15) receives the evidence bundle, never pixels, and narrates only from it. Verification (Phase 16) checks each narrated claim against a `fact_id` or `rule_id` in the bundle; a claim without a matching id is unsupported. Phase 13 defines the interface and builds neither.
- **Object-storage boundary.** Originals and derivatives live in private S3-compatible storage by id; metadata, facts and bundles in PostgreSQL; neither bytes nor pixels in the database or logs. The upload and storage API, signed URLs, consent and retention records are Phase 18; Phase 13 reads an image reference and bytes supplied by tests or fixtures only.
- **Privacy boundary.** Minors are excluded from the initial palm dataset and from the production palm-reading scope until counsel clears the workflow; training on user images is off by default (user or production images are never training or evaluation data without separate explicit authorisation, and the governed consented dataset is separate); images are referenced by id; the model and the agent never receive pixels; no pixels, landmarks or geometry in logs; legal counsel remains a production-launch gate with the ten items of `research/PALM_READING.md` section 12 (none presented as resolved; Phase 13 implementation may proceed on synthetic, fixture or internal appropriately governed data).
- **Safety boundary.** The vision layer is descriptive. No component makes, or turns a palm feature into, a medical diagnosis, disease detection, death or lifespan prediction, or a claim about criminality, mental illness, fertility, paternity, sexual conduct, ethnic or racial ranking, intellectual ranking or moral character (standards PM-13, PM-25); palmistry interpretations are framed as traditional and interpretive, not as scientifically established fact.
- **Model artifact boundary.** Model weights are not committed to git. They live in a separate artifact registry with a SHA-256, version, training manifest hash and licence record; a result records the artifact identity; a missing or mismatched artifact is a failure, never a silent fallback. CI for this component installs its heavy dependencies only in its own job and runs with a small fixture model or none; the optional-model pattern of the Phase 12 tests applies.
- **Reproducibility.** Equivalent structured facts within documented, versioned tolerances given the pinned artifact, preprocessing version, runtime, dependencies, input image and configuration (decisions K and G). The tolerances are `CALIBRATION_REQUIRED` until measured on representative evaluation data; no exact or bit-for-bit claim is made for a learned component unless demonstrated.
- **Phase boundaries.** Phase 13: the pipeline above, the facts, the palmistry knowledge and rules, the evidence bundle, the evaluation harness and the interfaces. Phase 14: the self-hosted LLM only. Phase 15: the agent and AI narration. Phase 16: verification. Phase 18: upload, object storage, persistence, consent and retention infrastructure and the public API. Phase 13 must not implement any of them.

**Implementation record (2026-10-03).**
- **Contracts** (`packages/contracts` 0.2.0): `palm_canonical` (canonical JSON, integer-only, fixed-point geometry at 10^-4 palm unit in PCF-1, scores in basis points, SHA-256 identities; timestamps never enter a fact identity), `palm` (`PalmFact` with class `OBSERVED` or `DERIVED` only, `PalmFactSet`, `PalmRuleEvaluation`, `PalmEvidenceBundle`), `palm_policy` (the prohibited-interpretation filter), `palm_coverage` (SUPPORTED, PARTIALLY_SUPPORTED, NOT_READ, NOT_EVALUABLE, RESEARCH_PENDING, EXCLUDED).
- **`services/palm-vision` 0.1.0**: stages `image_input`, `quality` (ACCEPT, RETRY, REJECT with reason codes; versioned `config`), `hand` and `side` (a replaceable detector abstraction with a MediaPipe adapter that is optional in CI; the side is `UNDETERMINED` when it cannot be established and is never guessed; mirroring is explicit), `frame` (the deterministic PCF-1 palm region and landmark transform), `lines` (the line/feature interface; `MODEL_UNAVAILABLE` without a pinned model; the classical baseline is marked EXPERIMENTAL), `pipeline` (facts with a derivation chain and provenance), `artifacts` (artifact policy: id, version, SHA-256, source, licence), `reproducibility` and `evaluation` (metrics, harness, synthetic plumbing set). The package imports only `packages/contracts` and `packages/shared` and owns no rules, knowledge text, narration, upload or storage.
- **Knowledge**: migration `0003_palm_knowledge_vocabulary` (additive, forward-only); `services/knowledge/content/palm/` loaded by `palm_content` into the separate version `KV-a21c2c040abe9663`; the Phase 12 version `KV-06361d7aba28c1ce` is asserted unchanged. `source_coverage.yaml` is validated so an unread concept cannot back a rule.
- **Rules**: `services/rule-engine/palm_rules/` (own manifest `PANDIT_JI_PALM_WESTERN_PHASE13`, schema, tag vocabulary, conflicts file, six fixture rules) with `pandit_rule_engine.palm` (loader, evaluator). Isolation is asserted: the Phase 6 ruleset hash `8d29a18c…77209` is pinned, the namespaces are disjoint, and a palm file cannot load into the Vedic engine.
- **Evidence**: the `PalmEvidenceBundle` links the image reference and hash, the quality, hand and region results, the facts, the rule evaluations, the knowledge and model versions and an uncertainty summary under one bundle hash; a later phase needs no pixels.
- **CI**: `services/palm-vision` joined the Python matrix; the `palm-integration` job runs the image-to-evidence test with no GPU, no weights and no user data; the knowledge PostgreSQL job covers migration 0003 and the palm parity test.
- **Not built (by design)**: a trained palm-line model, a dataset, calibrated thresholds and tolerances, the Indian profile, and everything owned by Phases 14, 15, 16 and 18.

## 36. Self-Hosted LLM Capability (Phase 14; implemented 2026-10-03)

Decision record: ADR-009. Evidence and candidates: `research/AI_MODELS.md` ("Phase 14 verification record"). Contracts: `packages/contracts` `pandit_contracts.llm`. Code: `services/agent/src/pandit_agent/llm/`. Assets: `services/agent/llm/` (manifests, the pinned chat template, `README.md` with the acquisition steps).

```
STRUCTURED FACTS -> RULES / KNOWLEDGE -> EVIDENCE -> LLMProvider -> LLMService -> LLMRuntime -> vLLM server (self-hosted)
                                                       (interface)   (this layer)   (HTTP)         (separate process, GPU)
```

**What it is.** The language-generation layer. It receives an `LLMRequest` (conversation turns, an explicit size-limited `LLMContext` of evidence items and restricted categories, the language `EN`/`HI`/`HINGLISH`, versioned generation settings, an output mode) and returns an `LLMResponse` (text, validated structured output, finish reason, token usage, latency, and a provenance block). It is not a fact generator, a calculation engine, a palm vision engine, a rule engine or a verifier: the evidence is produced upstream and is never modified here. It has no planner, memory, tool selection or narration orchestration (Phase 15) and no verification (Phase 16).

**Selected model and runtime.** `Qwen/Qwen3-8B`, revision `b968826d9c46dd6066d109eabc6255188de91218`, Apache-2.0, bfloat16 weights (about 16.4 GB), served by vLLM (model card: 0.8.5 or later). Pinned in `services/agent/llm/manifests/qwen3-8b.json`: revision, SHA-256 of 12 artifacts, licence file hash, tokenizer configuration hash, chat-template hash, context figures (32,768 native per the model card, `max_position_embeddings` 40960 in `config.json`, 131,072 with YaRN which is off), runtime, quantization, hardware class, provenance. The manifest says `production_eligible: false` with four named blockers.

**Four things kept apart.** Model *code* (the package); model *configuration* (`settings.py`: service settings and the versioned generation profiles `deterministic` and `model_default`, config version `gen-1`); model *manifest* (JSON, validated on load: pinned revision, hashes, a read licence, a supported runtime, never committed weights, a test fixture can never be production eligible); model *weights* (never in git, ignored by `.gitignore`; acquisition is an explicit operator step; `verify_model_directory` checks presence, size and SHA-256 against the manifest).

**Request flow.** Readiness check -> requested model must be the loaded model (no silent switch) -> language supported -> output schema registered -> prompt assembly -> the model's own chat template -> token budget -> runtime -> strict parse and schema validation (structured output) -> output policy scan -> language-script heuristic -> response with provenance and one structured log event.
- *Prompt assembly* (`context.py`): the system block is built only from fixed versioned text (`PROMPT_VERSION_ID` = `pj-prompt-1+<digest of the fixed text>`) plus the request's evidence, restricted categories, language and schema. The caller cannot send a system message. Content containing a model control token or an evidence delimiter is refused. Over-limit content is refused with `CONTEXT_TOO_LARGE`, never truncated. The same request always gives the same prompt.
- *Chat template* (`chat_template.py`): the template text published with the model at the pinned revision is vendored and its SHA-256 pinned; a different template is refused. Rendering uses the sandboxed Jinja settings of the model's own tooling. Checks: turn-start and end-of-turn token counts, no duplicated special tokens, no BOS, the generation prompt (with the empty reasoning block when thinking is off). Tests assert exact strings for system, user and assistant turns and English, Hindi and Hinglish content. A reasoning block in an output is stripped and never returned.
- *Structured output* (`structured.py`): schemas are registered by id (`pj.answer_with_evidence_refs.v1` is built in; later phases register theirs). vLLM is asked to constrain decoding with `response_format`, but the guarantee is the post-generation check: strict JSON (no fence stripping, no repair, no `NaN`), then JSON Schema validation. Failures are `MALFORMED_STRUCTURED_OUTPUT` or `SCHEMA_MISMATCH`. Retries happen only at non-zero temperature (a greedy retry repeats itself) and are bounded.
- *Safety* (`safety.py`): restricted categories travel as typed `ProhibitedCategory` values from the Phase 13 policy; the prompt names them (first layer) and the generated text, including every string inside structured output, is scanned against the same closed lexicon (second layer); a hit is `POLICY_VIOLATION` and the text is not returned. **Limits**: the lexicon is English only, so Hindi and Hinglish output is not covered; a word list is a safety net, not proof; a prompt instruction does not guarantee compliance. Status: `LEGAL_REVIEW_REQUIRED` and `CALIBRATION_REQUIRED`.
- *Languages* (`language.py`): the interface accepts `EN`, `HI`, `HINGLISH` and the prompt carries a directive for the requested one. A script heuristic (Devanagari versus Latin) is reported as `language_check` and never fails a request. It cannot tell English from romanised Hindi and measures no quality. Real language quality needs an evaluation dataset and human review and is `CALIBRATION_REQUIRED`.

**Health and readiness.** `SERVICE_STARTED` (constructed, nothing loaded), `MODEL_LOADING`, `MODEL_READY`, `MODEL_UNAVAILABLE` (model, runtime, GPU or resources absent: recoverable by an operator), `MODEL_ERROR` (hash, tokenizer, manifest or load failure). A service that could not load never reports ready and refuses requests with a typed failure. When no local model directory was verified, the ready state says the artifact hashes were not verified by this process.

**Errors.** One typed vocabulary (`LLMErrorCode`): model unavailable, model load failure, tokenizer failure, invalid manifest, invalid configuration, invalid request, context too large, generation timeout, generation failure, malformed structured output, schema mismatch, policy violation, unsupported language, unsupported output schema, runtime unavailable, GPU unavailable, insufficient resources, endpoint not permitted. A failure is a `FAILED` response, not an exception. Nothing falls back to another model or to any hosted API.

**Observability.** One JSON log line per load and per request through the shared logging foundation, from a field allow-list (request id, request hash, model id and revision, runtime, status, error code, latency, token counts, finish reason, prompt version, attempts, language, state). A field outside the list raises, so prompts, evidence, generated text, palm facts and images cannot be logged. `PerformanceRecorder` keeps measured load time, latency, tokens per second (completion tokens over total latency) and, where the platform reports it, peak process memory. First-token latency is `null` because the runtime is non-streaming. No target figure is implied.

**Reproducibility.** A response records the manifest id, model id and revision, artifact hashes, tokenizer-configuration and chat-template hashes, runtime and runtime version, quantization, dependency versions, prompt version, generation configuration version and a request hash (SHA-256 over everything that determines the prompt and the sampling, excluding the request id). The prompt is deterministic. Output reproducibility is **not** guaranteed bit for bit: the `deterministic` profile is greedy decoding with a fixed seed, which is the most reproducible setting the runtime offers, but a GPU server may still vary by hardware, batching and library versions. Tolerances are `CALIBRATION_REQUIRED`.

**Self-hosted boundary.** No hosted-model client exists. The HTTP runtime reaches only operator-allow-listed hosts (default loopback), follows no redirects, ignores proxy settings and never echoes a response body; a test scans the agent sources and assets for hosted SDKs and endpoints. The scripted `MockRuntime` (used in CI) serves only a test-fixture manifest, must be passed in explicitly, and labels every response `mock-deterministic` / `is_real_model: false`.

**Phase 13 integration.** `evidence.py` turns the public `PalmEvidenceBundle` into evidence items (one per fact and per rule evaluation plus a readiness item) from identifiers, enumerated values, confidences, statuses and source locations only: no geometry, no image reference or hash. The integration test proves the model can cite real fact and rule ids and cannot change the frozen bundle. The agent imports no other service and no other package imports the agent.

**Interface for Phase 15 and 16.** `LLMProvider.generate(LLMRequest) -> LLMResponse` and `health() -> LLMHealth`. Phase 15 supplies the task context, the structured evidence, the language, the response schema and a generation policy; it receives text, validated structured output, provenance, status and usage. Phase 16 verifies claims against the evidence bundle; Phase 14 does not check that a cited id exists or that a claim is supported.

**Status.** IMPLEMENTED: contracts, manifest and loader, template handling, context assembly, structured output, policy scan, health, errors, observability, the scripted runtime, the vLLM HTTP runtime (against a protocol fake). MODEL_DOWNLOAD_REQUIRED and HARDWARE_REQUIRED: the real model has not been downloaded, served or run here. OPTIONAL_LOCAL_TEST (skipped in CI): a real vLLM server test and a tokenizer cross-check. CALIBRATION_REQUIRED: language quality, structured-output reliability, latency, capacity, tolerances. LEGAL_REVIEW_REQUIRED: the model licence and Hindi and Hinglish prohibited-output coverage. FUTURE_PHASE: planner, narration, tool use, verification, fine-tuning. Not implemented from `TECH_STACK.md`: the Ollama development tier. The vLLM request fields were written to the server's documentation and were not verified against a live server.

## 37. Agent Orchestration and Narration (Phase 15; implemented 2026-10-03)

Decision record: ADR-010. Contracts: `packages/contracts` `pandit_contracts.agent`. Code: `services/agent/src/pandit_agent/orchestration/`. It sits on the Phase 14 `LLMProvider` (section 36) and consumes Phase 13 evidence (section 35) and Phase 6 evidence bundles through public contracts only.

```
AgentRequest -> screen -> intent/domain -> plan -> collect evidence (allow-listed tools) -> AgentContext
             -> sufficiency -> LLMProvider (Phase 14, structured output) -> ground -> NarrationResponse
                                                                                        (claims: UNVERIFIED)
                                                                                              |
                                                                                    Phase 16 verifies
```

**Entry point.** `AgentOrchestrator.run(AgentRequest) -> NarrationResponse`. It never raises for an expected failure; every outcome is a typed response with status `COMPLETED`, `DEGRADED` (an honest answer that states what could not be done), `REFUSED` or `FAILED`.

**Contracts.** `AgentRequest` (language, untrusted `user_text`, optional domain, intent hint, conversation id, generation profile; no evidence, tool or argument fields). `EvidenceRecord` (one deterministic item with its semantic class `OBSERVED_FACT`, `DERIVED_FACT`, `CALCULATED_FACT`, `RULE_EVALUATION` or `CONTEXT_STATUS`, status, confidence as the producer defined it, source profile and location, version reference, fact references, conflict ids, bundle reference). `AgentContext` (facts, rule evaluations and statuses kept in separate tuples; missing capabilities; trim count; restrictions; a deterministic context hash). `AgentPlan` (static steps, plan hash). `NarrationResponse` -> `NarrationSection` -> `NarrationClaim` (claim id, text, claim type, domain, structured `EvidenceReference` list of evidence id, domain, kind FACT/RULE/STATUS and bundle reference; source profiles, source locations, version references, uncertainty flags and minimum confidence copied by the agent from the evidence; verification state). `AgentTrace` (content-free identifiers, hashes, counts and versions). `AgentError` with the typed `AgentErrorCode` vocabulary. The domain is carried on every record, reference and claim, and a claim may cite only evidence of its own domain.

**Domains.** `ASTROLOGY` and `PALMISTRY` are separate: a request has one domain, a tool serves one domain, the context refuses evidence of another domain and a duplicate evidence id, and a palmistry rule is never presented as an astrology rule or the reverse. Combining both domains in one request is not implemented (`FUTURE_PHASE`); the contract keeps the domain on every item so it can be.

**Planning and tools.** The intent classifier is deterministic (English, Hinglish and Devanagari keywords, a fixed tie-break, an explicit hint wins, unknown becomes `GENERAL`); its accuracy is not measured (`CALIBRATION_REQUIRED`). The planner is a pure function of (domain, intent, registered tools) over static presets (for example `CAREER` needs the chart and rule results and would like the dasha and transits, following the example in `Phases.md` Phase 15). A plan is a straight line of at most 8 steps drawn from three operations (`COLLECT_EVIDENCE`, `ASSESS_SUFFICIENCY`, `NARRATE`); there is no loop, no recursion, no model-chosen tool and no arbitrary execution. A tool is an allow-listed `EvidenceTool` that takes only the set of capabilities the plan asked for (no free-form arguments), declares a timeout and a call budget, runs on a worker thread and returns typed records; its exceptions are contained and never leaked. Adapters: `PalmBundleTool` (the public `PalmEvidenceBundle` contract) and `AstrologyBundleTool` (the Phase 6 `EvidenceBundle`, read structurally so the agent does not depend on the calculation packages). They pass identifiers, enumerations, confidences, statuses and source locations; they never pass pixels, geometry, image references or hashes, or birth date, time and coordinates. **Not built**: adapters for dasha, transit, compatibility and knowledge-retrieval evidence (`FUTURE_PHASE`). The planner reports those capabilities as missing; the agent never computes them. A required capability that is missing yields a structured `DEGRADED` result without a model call (`INSUFFICIENT_EVIDENCE`, or `MISSING_EVIDENCE` when nothing was collected); a missing desired capability is stated as a limitation claim.

**Context assembly.** Deterministic and order-independent. Over budget, evidence is trimmed by priority (all statuses; then triggered rules together with the facts they cite; remaining facts and rules share what is left so neither starves the other) and the trim is recorded (`trimmed_count`, an `EVIDENCE_TRIMMED` flag and a stated limitation), never silent. If the model's window is smaller than the context, the agent re-assembles with half and then a quarter of the budget (at most two retries) before failing with `CONTEXT_TOO_LARGE`.

**LLM orchestration.** The agent builds an explicit Phase 14 `LLMRequest`: the trusted task instruction in the additive `LLMContext.task` channel (templates in `prompts.py`, version `pj-narration-task-1+<digest>`, no user text), the typed evidence items, the typed restricted categories, the requested language, the `pj.narration.v1` JSON schema, and the user text only as the user message. System policy, task, evidence and user request stay separate. Structured output is validated by Phase 14. Retries are bounded (`max_llm_calls`, default 2): a typed retryable availability or timeout failure is retried; a structured-output or grounding failure is retried only when the generation samples (greedy decoding would repeat itself); there is no "ask the model to fix itself" loop. There is no fallback model and no hosted API; the agent uses `health()` and `generate()` only.

**Narration and grounding** (`narration.py`). The model supplies, per claim, text, claim type and evidence ids. The agent then enforces *referential and structural* grounding and fails the whole narration (typed, no partial text) on any violation: a cited id must exist in this context; an `OBSERVED_FEATURE` may cite only `OBSERVED_FACT`, a `DERIVED_FEATURE` only `DERIVED_FACT` (a derived fact is never labelled observed), a `CALCULATION_FACT` only calculated astrology facts; a `TRADITIONAL_INTERPRETATION` needs at least one rule evaluation and every cited rule must be `TRIGGERED` (a `NOT_EVALUABLE` or `NOT_TRIGGERED` rule can back only a `LIMITATION`) and may not merge rules of different source profiles that share a conflict id; only a `LIMITATION` may cite nothing. References, profiles, locations, versions, confidence and uncertainty flags (`NOT_EVALUABLE`, `NOT_TRIGGERED`, `CONFLICTING_PROFILES`, `UNCALIBRATED_CONFIDENCE`, `NOT_VISIBLE`, `BUNDLE_NOT_PRODUCTION_READY`, `EVIDENCE_TRIMMED`) are copied or computed from the evidence, never written by the model, and no confidence value is invented. A narration that claims to be verified is rejected. Agent-authored, localized limitation claims state missing capabilities and trimming. **This is not verification**: whether a claim's *text* is supported by the evidence is Phase 16's question.

**Phase 16 interface.** `NarrationResponse.claims` is the verification-ready list: each claim has an id, a type, a domain, structured references with bundle references, copied provenance and flags, and `verification = UNVERIFIED`. `VERIFIED` exists in the contract only with a `verified_by` and is never set by Phase 15 (a test asserts the orchestration package contains no `VERIFIED` assignment and no verifier). The disclaimer `PENDING_VERIFICATION` is always present.

**Safety** (`policy.py`). Palmistry restricts every Phase 13 category (PM-13, PM-25) in requests and output. Astrology follows `PRODUCT_POLICIES.md`: contextual traditional interpretation of high-impact topics is allowed with a professional-advice disclaimer, and lifespan outputs are prohibited (the Ayurdaya exclusion), so lifespan and death-timing requests are refused and lifespan is the restricted output category. **This domain scoping is owner-locked (2026-10-03, ADR-010): palmistry keeps the complete Phase 13 list and is never weakened; astrology keeps lifespan and death-timing refusal and the professional-advice disclaimer and is neither widened nor narrowed for symmetry. The high-impact topics of `PRODUCT_POLICIES.md` (health, finance, legal, relationships, pregnancy, death) are implemented as written.** Controls: (1) request screening before any tool or model call, with the Phase 13 English lexicon plus a small Hindi and Hinglish supplement, refusing with a typed `REFUSED` response and a localized message; (2) typed restrictions into the Phase 14 request and Phase 14's output scan; (3) the agent's own scan of every claim and heading, including the supplement; (4) prompt-injection detection for common override, prompt-extraction, role-marker, control-token, evidence-tampering and "mark it verified" attempts in English, Hinglish and Hindi, refused as `PROMPT_INJECTION`. Following OWASP's guidance on prompt injection (constrain the role, define and validate the output format, filter input and output, segregate untrusted content, least privilege, adversarial testing), the main protections are structural: user text can reach only the user message, control tokens and evidence delimiters in it are refused, evidence is typed, every claim must cite ids that exist in the context, the model has no tool access and the agent's tools take no arguments. **Limits, stated plainly**: word lists and patterns are a safety net, not proof; OWASP itself says prevention cannot be guaranteed; the Hindi and Hinglish supplement is small and partial (`CALIBRATION_REQUIRED`, `LEGAL_REVIEW_REQUIRED`); the evidence-grounding check does not detect a claim whose text overstates its evidence (Phase 16).

**Languages.** `EN`, `HI` and `HINGLISH` are carried unchanged from request to the Phase 14 request and the response; the agent never switches language, never translates ids or machine-readable fields, and returns `UNSUPPORTED_LANGUAGE` if the model layer reports it. Disclaimers and refusals are localized deterministic text (written for this module, not reviewed by a native-speaker editor). No language-quality evaluation exists; the Phase 14 script heuristic result is copied to the trace.

**Memory.** Phase 15 owns in-session conversation context only. `InMemoryConversationMemory` stores labels (domain, intent, language) per conversation, never user text, narration or evidence, in process memory, bounded by turns and conversations, expiring, with `forget`. It can route a short follow-up to the previous intent (same domain) and nothing else; it cannot supply or change a fact. Persistent long-term memory (profiles, journal, feedback) needs user-scoped storage, consent, retention and deletion and is Phase 18 (`FUTURE_PHASE`); a persistent store would implement the `ConversationMemory` protocol.

**Observability.** One JSON log line per request from a field allow-list (request id, domain, intent, language, status, error code, latency, steps, tool calls, LLM calls, retries, plan and context and LLM-request hashes, prompt and task versions, schema id, model id and revision, version and bundle references, claim count, injection flag); a field outside the list raises. User text, narration, evidence content, palm facts and images cannot be logged.

**Reproducibility.** The plan hash, context hash, task version, schema id, Phase 14 request hash, prompt version, generation configuration version and model provenance (manifest, model, revision, runtime, dependency versions) are recorded in the trace. Context assembly and planning are deterministic and tested separately from generation. Generation is stochastic unless the runtime guarantees otherwise: `generation_deterministic` is true only for the scripted test runtime. Nothing claims bit-for-bit reproducibility of a real model.

**Status.** IMPLEMENTED: contracts; deterministic intent, planning, context assembly and trimming; the tool registry and the palm and astrology bundle adapters; narration with structured claims and grounding; policy, injection handling and request and claim screening; localized disclaimers and refusals; bounded in-session memory; typed errors; content-free observability; Phase 16 hand-off. NO ROADMAP ITEM REMAINS PARTIAL (closure 2026-10-03): each Phase 15 roadmap item is IMPLEMENTED or EXPLICITLY DEFERRED (checklist in `Phases.md` Phase 15). The astrology evidence tools beyond chart placements, rule results and conflicts (dasha, transit, compatibility, knowledge retrieval) are deferred to Phase 18, which builds the Dasha, Transit and Compatibility APIs and composes the services; the Hindi and Hinglish safety coverage is a limitation (`CALIBRATION_REQUIRED`, `LEGAL_REVIEW_REQUIRED`), not a roadmap item. **MODEL_DOWNLOAD_REQUIRED / HARDWARE_REQUIRED**: no real model was run; every Phase 15 test ran against the Phase 14 service over the scripted test runtime, so nothing is known about real narration quality, Hindi or Hinglish quality, reasoning quality, latency or real vLLM behaviour. CALIBRATION_REQUIRED: intent accuracy, injection and safety recall, language quality, the evidence and retry budgets. LEGAL_REVIEW_REQUIRED: the domain policy scoping and the Hindi and Hinglish coverage. FUTURE_PHASE: verification (16), persistent memory and upload, storage and consent (18), voice, reports, combined-domain requests, the remaining evidence adapters.

### Phase 15 closure: the locked boundaries (owner decisions of 2026-10-03)

1. **Domain policy scoping.** Palmistry: the complete Phase 13 prohibited-category policy in requests and output (`policy.PALM_POLICY`; only event prediction is allowed as a *request*, and it stays restricted in output). Astrology: lifespan and death-timing requests are refused and lifespan is the restricted output category (`policy.ASTROLOGY_POLICY`); contextual, traditional interpretation of high-impact topics is allowed with the professional-advice disclaimer. The two are not merged. Closure corrections that make the code match the locked wording: English death-timing phrasings ("when will I die") are refused in astrology, as the Hindi and Hinglish forms already were, and death is now among the high-impact topics that carry the disclaimer, as `PRODUCT_POLICIES.md` lists it.
2. **Phase 15 / Phase 16.** Phase 15 validates structure and reference integrity (cited ids exist in the agent context; references point to available fact, rule or status records; semantic classes are preserved; provenance fields are copied from trusted evidence; a non-limitation claim has references; malformed or ungrounded references fail the narration; every claim is `UNVERIFIED`). It does not determine whether the claim text is supported by the referenced evidence, does not judge whether it follows from the facts, and never sets `VERIFIED` or `verified_by`. Only Phase 16, through its own verification process, may set `VERIFIED`. A test shows a claim whose text contradicts its valid, correctly classed evidence still passes Phase 15 as `UNVERIFIED`.
3. **Tools.** Static, deterministic, allow-listed selection by the bounded planner. The model cannot invent a tool name or an argument, execute a function or a shell command, reach the network or the file system, alter evidence or call an unregistered tool: the narration schema has no field for any of these and rejects extra properties; a tool takes only the set of capabilities the plan requested; the orchestration package imports no execution, network, file or persistence module and calls no dynamic-execution builtin (a test scans every source file and a run is executed with file and socket access disabled). Budgets, timeouts and the step limit stay. A later phase that needs richer tools must extend this architecture explicitly.
4. **Memory.** Phase 15 is bounded in-session context (`InMemoryConversationMemory`: enumerated labels, process memory only, bounded, expiring, erasable). Persistent memory, long-term profile storage and any palm-image-derived memory, with their privacy, storage and consent lifecycle, belong to later infrastructure: Phase 18 (Memory API) and Phase 20 (personal memory). No persistent memory table or database was created.

**Real-model status (unchanged).** No real model has been downloaded, served or run. Every Phase 15 test used the Phase 14 service over the scripted test runtime. No multilingual, reasoning, narration quality, latency or real vLLM claim is made, and nothing here is production-ready.
