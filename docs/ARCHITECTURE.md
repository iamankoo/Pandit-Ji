# Pandit Ji — System Architecture & Implementation Roadmap

Status: DRAFT v1 (derived from `features.md`, the locked baseline)
Scope: This document defines subsystems, dependencies, database/engine/agent architecture, repository layout, technical risks, and the deterministic/AI split. It intentionally contains no application code. **It does not define the implementation sequence** — see §12 below.

Source-of-truth hierarchy for this project: the full, authoritative authority order is maintained in `SOURCE_OF_TRUTH.md` (project root) — read that file directly rather than trusting a copy of it here, since it can change. As of the Pre-Phase-1 Foundation package it is:

```
1. Explicitly locked project-owner decisions
2. features.md            — WHAT Pandit Ji must contain
3. Phases.md               — HOW/WHEN; sole execution roadmap
4. docs/ARCHITECTURE.md    — technical structure (this document)
5. docs/ASTROLOGY_STANDARDS.md — calculation/interpretation standards (locked canonical location)
6. PRODUCT_POLICIES.md
7. LEGAL_REGULATIONS.md
8. Research documents (research/*.md)
9. Code/configuration
```

Conflict rule (from `SOURCE_OF_TRUTH.md`): never silently resolve a contradiction between documents. Record it, resolve it in the higher-authority document, update dependents, and add a changelog entry. §17 of this document tracks contradictions discovered so far that are not yet resolved.

Before starting any phase or implementation work, read `Phases.md` first (and `PRE_PHASE1_CHECKLIST.md`'s "explicit decisions still needed" list, while it remains open) and identify the current phase, current step, required deliverables, dependencies, exit criteria, and explicitly excluded work. Do not start work from memory or from an older roadmap.

---

## 1. Guiding Constraint

Every design decision below exists to enforce one rule from the product spec:

> The AI must never invent planetary positions, dashas, houses, yogas, nakshatras, or other calculated astrological facts.

Concretely, this means the system is built as a **fact pipeline with a narrating layer on top**, not a chatbot with astrology sprinkled in. The Astrology Engine and Rule Engine produce structured, versioned, reproducible facts. The AI Agent is only ever allowed to read those facts and talk about them — it cannot compute or assert them itself. A Verification layer checks that this boundary held on every response before it reaches the user.

---

## 2. Major Subsystems

| # | Subsystem | Responsibility |
|---|-----------|-----------------|
| 1 | **Astrology Calculation Engine** | Deterministic astronomy + Vedic/Western chart math (positions, houses, vargas, ashtakvarga, dashas, transits, panchang, muhurta, compatibility scoring, numerology). |
| 2 | **Rule Engine** | Versioned, testable rules that turn chart facts into yoga/dosha detections and tagged interpretive evidence. |
| 3 | **Knowledge Base** | (a) structured rule source-of-truth, (b) unstructured classical-text/remedy corpus for retrieval-augmented narration. |
| 4 | **AI Agent** | Intent detection, domain routing, evidence assembly, LLM orchestration, conversation memory use, response generation. |
| 5 | **Verification & Evaluation** | Hallucination/unsupported-claim detection, regression suite, backtesting, accuracy benchmarking. |
| 6 | **Memory & Personalization** | Birth profiles, saved family/partner charts, conversation history, preferences, feedback/correction history. |
| 7 | **Voice Subsystem** | STT/TTS, multilingual voice turn-taking, delegates all reasoning to the AI Agent. |
| 8 | **Reports Service** | Deterministic report assembly (chart/dasha/career/marriage/annual/etc.) from Engine + Rule Engine + Agent narration. |
| 9 | **API Layer** | FastAPI service exposing all of the above; auth, rate limiting, streaming chat. |
| 10 | **Web/Mobile Clients** | Next.js web app, Flutter mobile app; presentation only, no astrology logic. |
| 11 | **Privacy/Security/Audit** | Auth, encryption at rest for birth data, audit logging, data deletion, access control. |
| 12 | **Human Ecosystem / Content** (future) | Live astrologer marketplace, articles, festival calendar — explicitly deferred, not in initial baseline builds. |

---

## 3. Subsystem Dependency Graph

```
                       ┌─────────────────────┐
                       │   Knowledge Base     │
                       │ (rules + RAG corpus) │
                       └──────────┬───────────┘
                                  │ rule defs / retrieval
                                  ▼
┌────────────┐   facts   ┌───────────────┐   evidence   ┌───────────────┐
│  Astrology  ├──────────▶│  Rule Engine  ├─────────────▶│   AI Agent     │
│  Engine     │           └───────────────┘              │ (intent→plan→  │
│ (deterministic)                                        │  reason→verify)│
└─────┬───────┘                                          └───────┬────────┘
      │  reused directly (no AI needed)                          │ narrated
      ▼                                                          ▼
┌────────────┐                                           ┌───────────────┐
│  Reports   │◀──────────────────────────────────────────┤ Verification  │
│  Service   │              cross-checked facts           │ & Evaluation  │
└─────┬──────┘                                           └───────────────┘
      │
      ▼
┌───────────────────────────────────────────────────────────────────────┐
│                              API Layer                                │
│  (also fronts Memory/Personalization, Voice, Auth)                    │
└───────────────────────────────────┬───────────────────────────────────┘
                                     ▼
                         ┌───────────────────────┐
                         │  Web / Mobile Clients  │
                         └───────────────────────┘
```

Key dependency rules:

- **Astrology Engine has zero dependencies** on any other subsystem (pure computation over ephemeris + birth data). This is deliberate: it must be independently testable and swappable in isolation.
- **Rule Engine depends only on Astrology Engine outputs + Knowledge Base rule definitions.** It never calls the LLM.
- **AI Agent depends on Rule Engine, Astrology Engine (for raw facts the rules didn't already package), Memory, and Knowledge Base (RAG for phrasing/remedies text)** — never computes facts itself.
- **Verification depends on the same evidence bundle the Agent used**, so it can diff the Agent's output against ground truth already computed upstream.
- **Reports Service can bypass the AI Agent entirely** for the deterministic parts of a report and only calls the Agent for the narrative section — this keeps "just show me my chart" fast and hallucination-free by construction.

---

## 4. Database Architecture

PostgreSQL + pgvector, one database, schema-per-domain for clarity and independent migration ownership.

| Schema | Key Tables | Notes |
|---|---|---|
| `identity` | `users`, `sessions`, `auth_credentials` | Standard auth; supports future multi-tenant if a marketplace module is added. |
| `profiles` | `birth_profiles`, `locations` | `birth_profiles` link to `users` (self/family/partner flag). `locations` cache resolved lat/lon/historical-tz lookups so they're computed once, reproducibly. |
| `calc_config` | `calculation_configs` | Immutable rows: `{ayanamsa, zodiac_type, house_system, ephemeris_version}`. Every computed artifact below references a `calc_config_id` — this is what makes charts reproducible and lets Vedic/Western/KP modes coexist without ambiguity. |
| `charts` | `computed_charts`, `planetary_positions`, `houses`, `divisional_charts`, `ashtakvarga_tables` | All rows keyed by `(birth_profile_id, calc_config_id)`; treated as an immutable cache, recomputed only if inputs or config change — never mutated in place. |
| `dashas` | `dasha_periods` (mahadasha/antardasha/pratyantar via `level` column + `parent_id`), `dasha_config` | Self-referential tree; timeline queries are a single recursive CTE. |
| `transits` | `transit_snapshots`, `transit_events`, `sade_sati_windows` | Snapshots are point-in-time; events are derived (e.g. "Saturn crosses natal Moon on date X"). |
| `panchang` | `daily_panchang`, `muhurta_windows` | Keyed by `(date, location)`, not by user — shared/cacheable across all users in the same location/day. |
| `rules` | `rule_definitions` (versioned, source-controlled YAML mirrored into DB), `rule_sets`, `rule_evaluation_results` | `rule_evaluation_results` is the durable evidence trail: which rule fired, on which facts, for which chart. |
| `knowledge` | `knowledge_chunks`, `embeddings` (pgvector), `sources` | RAG corpus for narrative/remedy phrasing only — never a source of chart facts. |
| `compatibility` | `match_requests`, `guna_scores`, `match_results` | References two `birth_profiles`. |
| `numerology` | `numerology_profiles`, `numerology_reports` | |
| `conversation` | `chat_sessions`, `messages`, `agent_traces` | `agent_traces` stores the full evidence-bundle + verification result per assistant turn — required for both debugging and the explainability feature (§7). |
| `reports` | `generated_reports`, `report_templates` | |
| `feedback` | `user_feedback`, `corrections`, `backtest_outcomes` | Supports §Verification's backtesting requirement without pretending it's launched with real predictive-accuracy numbers. |
| `audit` | `audit_log` | Append-only; covers data access to sensitive birth data per Privacy requirements. |

Design principle: **AI-generated text is never stored as if it were a fact table.** `messages` stores what the assistant said; `agent_traces` stores what it was allowed to say (the evidence), so the two can always be diffed later.

---

## 5. Astrology Engine Architecture

A pure-Python library (no HTTP, no DB) so it can be unit-tested with fixed inputs/outputs and reused by the API, background jobs, and reports.

```
astro_engine/
  ephemeris/        # Swiss Ephemeris binding (planet positions, houses, ayanamsa)
  time_location/    # historical timezone + DST resolution, lat/lon geocoding cache
  charts/           # D1, D9, and other divisional charts, North/South/Chalit rendering data
  strength/         # dignity, exaltation/debilitation, combustion, retrograde, shadbala (later)
  ashtakvarga/
  dashas/           # vimshottari (mahadasha/antardasha/pratyantar), timeline builder
  transits/         # gochar, sade sati, transit-to-natal aspecting
  panchang/         # tithi, vara, nakshatra, yoga, karana, hora, choghadiya, rahu kaal
  muhurta/
  compatibility/    # ashtakoot/guna milan scoring
  numerology/
  western/          # tropical + Placidus module, kept isolated from Vedic assumptions
  config.py         # CalculationConfig value object (ayanamsa, house system, zodiac, ephemeris version)
```

Rules for this layer:
- Every public function is a pure function of `(birth_data, calculation_config)` → structured output (pydantic models). No hidden global state, no network calls.
- Every module ships **golden fixture tests**: known birth data + independently cross-checked expected output (cross-checked against a second trusted ephemeris source, not just against itself).
- KP/Lal Kitab/Nadi/Chinese/Feng Shui modules are added as additional folders **later** (Phases.md Phase 9 — Advanced Astrology Systems) behind the same `CalculationConfig`-driven interface — they are not architected in v1 beyond a placeholder module boundary, because their calculation standards need dedicated research first (§10).

---

## 6. Rule Engine Architecture

```
Chart Facts (from Astrology Engine)
        ↓
Fact Normalization  → canonical "Facts" object (planet-in-house, planet-in-sign,
                       aspect, dasha-lord, dosha-precondition, etc.)
        ↓
Rule Matching  → each rule = { id, version, category, condition (pattern over Facts),
                                conclusion (yoga/dosha/tag), strength, source_reference,
                                known_contradictions[] }
        ↓
Evidence Collection  → list of triggered rules + the exact facts that satisfied them
        ↓
Contradiction/Conflict Analysis → cross-reference triggered rules' known_contradictions;
                                    surface both supporting and conflicting evidence together
        ↓
Evidence Bundle (structured, versioned) → handed to AI Agent
```

Implementation notes:
- Rules are authored as YAML/JSON in the repo (`knowledge_base/rules/*.yaml`), reviewed like code, and loaded into `rules.rule_definitions` with a content hash as the version — this is what "versioned and testable" means concretely.
- The matcher is a small forward-chaining evaluator hand-rolled in Python (a full production-rule engine like `experta`/`durable_rules` is unnecessary complexity here and both have maintenance-status risk — evaluate during Phases.md Phase 6 — Vedic Astrology Rule Engine, don't default to either).
- Rule authoring must cite a source text/tradition per rule, because classical yoga/dosha rules genuinely conflict across schools (Parashari vs Jaimini vs Lal Kitab) — the engine surfaces conflicts rather than silently picking a winner.
- Rule engine output never contains free text meant for the user — only structured tags + facts. Phrasing is the Agent's job.

---

## 7. AI Agent Architecture

```
User message (+ conversation memory)
        ↓
Intent & Domain Classifier → maps to a fixed taxonomy drawn from features.md
                              (career / marriage / education / wealth / transit-timing / …)
        ↓
Astrology Planner → determines which Engine calculations + rule categories
                     are actually needed for this intent (avoid computing everything
                     for every message)
        ↓
Evidence Assembly → calls Astrology Engine (direct facts) + Rule Engine (evidence bundle)
                     + Knowledge Base RAG (remedy/explanatory language, source texts)
        ↓
LLM Reasoning (self-hosted, swappable) → prompted with: user question, conversation
                     memory, and ONLY the assembled evidence bundle — explicitly
                     instructed not to state any fact not present in the bundle
        ↓
Verification Layer → extracts factual claims from the draft response, checks each
                     against the evidence bundle; on mismatch, either strips the
                     claim, regenerates, or (for borderline cases) appends a
                     clarifying caveat
        ↓
Personalized Response (+ stored agent_trace for explainability)
```

- **Model abstraction**: an `LLMProvider` interface (prompt in, text/stream out) so Qwen/Llama/Mistral/etc. can be swapped, and so a hosted-API fallback can exist for development before self-hosted infra is ready, without touching planner/verification logic. No model is picked as final in this document per the product brief.
- **Specialist "modes"** (career, marriage, business-vs-job, etc.) are not separate models — they are prompt templates + evidence-assembly presets keyed off the intent taxonomy. Keeping them as configuration, not separate agents, avoids N-times the maintenance burden and keeps cross-domain consistency (e.g., career and marriage answers referencing the same dasha timeline must agree).
- **Conversation memory** is retrieved (recent turns + relevant saved profile + prior discussed topics) and passed into evidence assembly, not directly into free-form prompting, so memory can't smuggle in unverified "facts" either.

---

## 8. Knowledge Base Architecture

Two clearly separated stores, because conflating them is exactly how AI-invented facts would sneak back in:

1. **Structured knowledge (source of truth for facts/interpretation triggers)** — the Rule Engine's `rule_definitions`. Authored, reviewed, versioned. This is what actually determines *which* yogas/doshas/interpretive tags apply.
2. **Unstructured knowledge (source of truth for language only)** — classical text excerpts, remedy descriptions, articles, festival/panchang glossary content; chunked + embedded (pgvector) for RAG retrieval. This feeds the LLM only phrasing, remedy wording, and background explanation — retrieval results are never treated as facts about the user's chart.

Ingestion pipeline (Phases.md Phase 12 — Astrology Knowledge Base): document loader → chunker → embedder → dedup/quality filter → `knowledge.knowledge_chunks`. Requires sourcing classical references validated against an astrology-literate reviewer, not just general web scraping (see risks, §10).

---

## 9. Verification & Evaluation Architecture

| Layer | What it checks | When it runs |
|---|---|---|
| Engine golden-fixture tests | Ephemeris/chart/dasha/transit/panchang/compatibility outputs match independently cross-checked values | CI, every commit |
| Rule-engine test suite | Given fixed facts, exact expected rule-trigger set fires (no more, no fewer) | CI, every commit |
| Regression suite | Prior confirmed-correct outputs stay correct across engine/rule changes | CI, every commit |
| Claim/hallucination checker | Every factual assertion in an Agent response is traceable to its evidence bundle | Runtime, every chat turn |
| Contradiction detector | Response doesn't state two mutually exclusive facts (e.g. two different dasha lords for the same period) | Runtime, every chat turn |
| Backtesting framework | Long-run comparison of timing-oriented predictions against later user-reported outcomes | Offline, periodic (Phases.md Phase 20 — Validation, Backtesting & Production Launch) |
| Human-expert evaluation | Sample of AI narrations reviewed by an astrology-literate human for traditional correctness (not scientific accuracy) | Periodic, pre-release gate |

The system must be able to report, per response: **which facts were used, which rules fired, what contradicted, and whether verification passed** — this is the same data as the explainability feature (§25 in features.md), so explainability and verification share one implementation (`agent_traces`).

Hard constraint carried into every layer: no accuracy claim ("this will happen") is ever emitted without being framed as an astrological interpretation with a stated basis, and no marketing/UI copy may claim guaranteed real-world prediction accuracy unless backed by the backtesting framework's actual measured results.

---

## 10. API Architecture

FastAPI, versioned `/api/v1/...`, resource groups mirroring subsystems:

```
/auth/*
/profiles/*                birth profiles, family/partner profiles
/charts/*                  D1/D9/vargas/ashtakvarga, planetary positions — direct,
                            deterministic, no LLM involved
/dashas/*
/transits/*, /sade-sati/*
/panchang/*, /muhurta/*
/compatibility/*           kundli matching
/numerology/*
/reports/*                 generate/fetch specialized reports
/chat/*                    conversation endpoints — SSE/WebSocket streaming for the Agent
/voice/*                   STT/TTS turn exchange, delegates to /chat internally
/admin/rules/*              rule authoring/versioning management (internal/admin auth only)
```

Design rule: **every chart/dasha/transit/panchang/compatibility/numerology endpoint is directly callable without going through `/chat`.** The AI Agent is a consumer of these APIs internally, not a gatekeeper in front of them — this is what lets "just show me my dasha timeline" stay instant and hallucination-free, and lets the Reports Service and future clients reuse the same deterministic surface the Agent uses.

---

## 11. Repository Structure

**LOCKED canonical structure** (matches `Phases.md` Phase 3 exactly — see §17 item 2, now resolved):

```
pandit-ji/
  apps/
    mobile/                 Flutter client
    web/                    Next.js web client
    admin/                  internal admin app (rule authoring/versioning, content ops — see note below)
  services/
    astro-engine/           deterministic calculation library (§5)
    rule-engine/            rule DSL + evaluator (§6)
    agent/                  intent, planner, LLM orchestration, evidence assembly (§7);
                            includes voice/ (STT/TTS integration) and reports/ (report
                            templates + assembly) as subpackages — see note below
    knowledge/              RAG store + ingestion pipelines; rules/*.yaml source-of-truth (§8)
    verification/           claim/hallucination/contradiction checking, regression + backtesting (§9)
  packages/
    shared/                 config, logging, auth utils shared across services
    contracts/              shared pydantic models / OpenAPI-generated client types for web/mobile/admin
    ui/                     shared UI component library across web/mobile/admin
  datasets/                 golden fixtures, rule test fixtures, backtesting data
  tests/
    fixtures/               golden birth-data + independently cross-checked expected outputs
    astro-engine/  rule-engine/  agent/  verification/  integration/
  docs/
    ARCHITECTURE.md          (this document)
    ASTROLOGY_STANDARDS.md   canonical astrology standards document (locked location — see §17 item 1, now resolved)
    rule-authoring-guide.md  (Phases.md Phase 6 — Vedic Astrology Rule Engine)
  infrastructure/
    docker/
    docker-compose.yml
    migrations/             Alembic
  features.md
  Phases.md
  SOURCE_OF_TRUTH.md
  PRODUCT_POLICIES.md
  LEGAL_REGULATIONS.md
  PRICING.md
```

Canonical service names (locked, per project-owner decision): `astro-engine`, `rule-engine`, `agent`, `knowledge`, `verification`. Do not use alternative names such as `astrology-engine`, `ai-agent`, or `knowledge-base` anywhere in the codebase or documentation.

Note on `voice/` and `reports/`: the locked canonical service list has exactly five top-level services and does not list `voice` or `reports` separately. Both still exist as functional subsystems (§2) — they are placed here as subpackages of `services/agent/` (the service that already orchestrates conversation/narration and that both voice and reports call into) rather than as their own top-level `services/` entries. This is an architectural placement choice made during this reconciliation, not something the locked naming decision specified directly; revisit if `voice/` or `reports/` outgrow being subpackages of `agent/`.

Note on `apps/admin`: the locked canonical `apps/` list is `mobile`, `web`, `admin` — it does not include a separate `apps/api`, which is what earlier drafts of this document used to hold the FastAPI HTTP layer (§10). This reconciliation does not silently decide where that FastAPI app now lives; it is flagged as an open item in §17.

Monorepo is deliberate: astro-engine, rule-engine, and agent change together frequently during early phases and a monorepo keeps their interfaces honest without cross-repo version drift. Revisit only if/when a service needs independent scaling or a separate deploy cadence.

---

## 12. Execution Roadmap

The authoritative development roadmap is maintained in:

`Phases.md`

This document defines system architecture and technical boundaries.
`Phases.md` defines the implementation sequence, phases, steps,
deliverables, dependencies, and exit criteria (the locked 20-phase plan).

When the two documents appear to conflict regarding development
sequence, `Phases.md` is authoritative.

The subsystems, engines, and services named throughout this document (Astrology Engine §5, Rule Engine §6, AI Agent §7, Knowledge Base §8, Verification §9, API §10, repository layout §11) are built in the order, and to the deliverables/exit-criteria, that `Phases.md` specifies — this document does not restate or re-derive that sequence. Where a section above cites a specific phase inline (e.g. "Phases.md Phase 6"), that citation is a pointer for convenience, not a duplicate definition; if `Phases.md` is later renumbered or resequenced, those inline pointers are what need updating, not the underlying architecture.

---

## 13. Technical Risks

- **Swiss Ephemeris licensing — decision locked, procurement still open**: the licensing choice itself is locked (Swiss Ephemeris Professional License, not AGPL — see `LEGAL_REGULATIONS.md`). The remaining risk is procurement, not the choice: the Professional License has not yet been purchased, and the signed agreement with Astrodienst must be obtained before public/commercial distribution or public-service activation (Phases.md Phase 20 gate), not before internal development under Phase 4.
- **Historical timezone/DST accuracy**: pre-standardization birth times (especially India pre-1945, and other regions) are genuinely ambiguous in tzdata; wrong resolution silently shifts the whole chart. Needs an explicit historical-tz dataset decision and documented fallback/confidence indication to the user.
- **Ayanamsa/house-system disagreement across traditions**: locking Lahiri + a default house system is necessary but will visibly disagree with some other apps/astrologers; must be configurable and clearly disclosed, not silently "the" answer.
- **Self-hosted LLM quality/latency**: open-weight models may lag hosted frontier models on nuanced Hindi/Hinglish reasoning and on latency under real hardware budgets — may require a hybrid fallback path during early phases (explicitly a stopgap, not the target architecture).
- **Rule completeness and cross-tradition conflict**: classical yoga/dosha rules number in the hundreds and genuinely disagree across Parashari/Jaimini/Lal Kitab/KP; incomplete or poorly-sourced rules propagate incorrect "traditional" claims into every downstream feature.
- **Hallucination verification is imperfect in general**: claim-extraction NLP will have false negatives; treat the verifier as a strong mitigation, not a guarantee, and keep human-expert spot review in the loop.
- **Voice for Hindi/Hinglish code-switching**: open-source STT/TTS support for natural code-switched speech is weaker than for pure English; may need a dedicated Indic-language model rather than a generic multilingual one.
- **KP/Lal Kitab/Nadi/Chinese systems are each their own research project**: attempting them alongside Vedic core work risks diluting rule-quality across the board; explicitly deferred to Phases.md Phase 9 (Advanced Astrology Systems).
- **Sensitive data / regulatory exposure**: birth data + family profiles are sensitive; India's DPDP Act and (for international users) GDPR both apply — needs a privacy/legal review before Phases.md Phase 20 (Production Launch), ideally sketched by Phase 17 (Backend Platform).
- **Backtesting ground truth**: there is no existing dataset of "outcome vs. prediction" for this product; collecting it ethically and usefully (without over-claiming what it proves) is itself a design problem, not just an engineering one.

---

## 14. Components Requiring Research Before Implementation

1. ~~Swiss Ephemeris licensing path~~ **RESOLVED — LOCKED**: Swiss Ephemeris Professional License (see `LEGAL_REGULATIONS.md`). Procurement (purchase + signed agreement) remains an open pre-production/legal task, not a research question.
2. Historical timezone/DST dataset and geocoding source for birthplaces (accuracy + coverage tradeoffs).
3. Rule-engine implementation approach: hand-rolled forward-chaining vs. adopting an existing Python rules library — evaluate maintenance status and fit before committing.
4. Self-hosted LLM + serving stack selection (e.g. vLLM/Ollama/TGI) against realistic hardware/latency budgets, and whether any fine-tuning is feasible given available astrology-labeled data.
5. Claim/hallucination-verification technique: regex/NER-based fact extraction vs. a smaller dedicated verifier model — prototype both against a labeled test set before choosing.
6. Open-weight STT/TTS models with credible Hindi/Hinglish code-switching support.
7. Authoritative sourcing for KP/Lal Kitab/Nadi/Chinese/Vastu rule content — needs a domain-literate reviewer, not general web research, since errors here are indistinguishable from confident hallucination to an end user.
8. Backtesting/outcome-data collection design — what can honestly be measured, and how it's presented to avoid overstating predictive accuracy.

---

## 15. Deterministic vs. AI-Driven — Explicit Split

**Deterministic (Astrology Engine / Rule Engine only — the LLM never computes or asserts these):**
Planetary positions & degrees · Ascendant/houses/cusps · Rashi/Nakshatra/Pada · All divisional charts · Dignity/exaltation/debilitation/combustion/retrograde flags · Ashtakvarga bindus · Vimshottari Mahadasha/Antardasha/Pratyantar dates · Transit positions & transit-to-natal angles · Sade Sati windows · Panchang elements (tithi/vara/nakshatra/yoga/karana/hora/choghadiya/rahu kaal) · Muhurta windows · Ashtakoot/Guna Milan scores · Numerology numbers · Yoga/Dosha trigger set (rule evaluation, not language).

**AI-driven:**
Natural-language intent/domain understanding · Conversational flow & follow-ups · Turning an evidence bundle into coherent, personalized, language-appropriate narrative · Deciding which of many triggered rules matter most to *this* question · Remedy phrasing (content sourced from Knowledge Base, wording generated) · Voice turn-taking.

**Gray zone requiring explicit guardrails:** dosha "severity" framing and "when might X happen" narratives combine a deterministic time window (dasha/transit dates — must always be cited exactly) with an interpretive claim (must always be hedged as traditional interpretation, never stated as certain). The Verification layer's contradiction/claim checks exist specifically to police this boundary.

---

## 16. Getting Started

Do not resume from an earlier version of this section's next-steps list — it duplicated roadmap authority that now belongs solely to `Phases.md`.

To begin or resume work: open `Phases.md`, identify the current phase, its deliverables, dependencies, exit criteria, and explicitly excluded work, and proceed from there. Use §5–§11 of this document as the technical reference for *how* to build whatever that current phase calls for; use `Phases.md` for *what phase comes next* and *when a phase is done*.

---

## 17. Known Contradictions Between Documents (Open Items)

Items 1 and 2 below were resolved by an explicit project-owner decision (see `PRE_PHASE1_CHECKLIST.md` and each document's changelog). They are kept here, marked resolved, so the resolution history isn't lost. Item 3 remains open — it was outside the scope of that reconciliation (features/product-scope decisions, not architecture/repo/standards decisions).

1. **Standards document duplication — RESOLVED, LOCKED.** Canonical standards document is `docs/ASTROLOGY_STANDARDS.md` (moved there from the project root). There is no separate `docs/calculation-standards.md`; the narrow calculation-config fields it would have held (ayanamsa, house system, ephemeris version, timezone/geocoding source) live inside `ASTROLOGY_STANDARDS.md`'s existing "Default Vedic profile" and "Reproducibility" sections instead. §11's repo tree and `Phases.md` Phase 1 both reference this single file.
2. **Repository structure mismatch — RESOLVED, LOCKED.** Canonical structure (matching `Phases.md` Phase 3 exactly): `apps/{mobile, web, admin}`, `services/{astro-engine, rule-engine, agent, knowledge, verification}`, `packages/{shared, contracts, ui}`, `datasets/`, `tests/`, `docs/`, `infrastructure/`. §11 has been rewritten to this exact tree. Two placement details were decided *during* this reconciliation (not dictated by the locked names themselves) and are noted, not hidden: (a) `voice/` and `reports/` are subpackages of `services/agent/` rather than top-level services, since the locked list has exactly five top-level services; (b) the FastAPI HTTP layer, previously `apps/api` in earlier drafts, has no corresponding entry in the locked `apps/` list (`mobile`, `web`, `admin`) — this reconciliation does not invent where it now lives; whoever executes `Phases.md` Phase 3 should settle it explicitly (e.g., as a thin app under one of the existing folders, or as a routing layer inside `services/agent/`) rather than assume this document's placeholder placement.
3. **Palm reading: scope/priority conflict — still open, out of scope for this reconciliation.** `features.md` §33 ("Future Expansion") explicitly lists "Palm reading / Face reading / Image-based palm analysis" as **not required for the initial baseline**. The Pre-Phase-1 Foundation package's `README.md` states the "Locked product baseline" includes "AI palm reading," and `research/PALM_READING.md` designs a full first-class pipeline (vision → landmarks → palmistry rule engine → AI explanation → report) as if it were in-scope now, not deferred. This is a direct contradiction about whether palm reading is baseline or future work. **Not resolved here** — per the conflict rule in `SOURCE_OF_TRUTH.md`, and per explicit instruction not to modify `features.md` product scope during this reconciliation, this needs its own explicit project-owner decision (and, once made, a changelog entry and an update to whichever of `features.md` §33 or the Foundation `README.md` is wrong), not a silent pick by either document.
