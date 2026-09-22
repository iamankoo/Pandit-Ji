# Pandit Ji — Project Summary & Session Handoff

Status: verified through **Phase 6 (complete, accepted, CI green)**, the **Phase 5 Nakshatra boundary correction** (commit `091ca1b`, CI run `35500359836`, green), **Phase 7 (Dasha & Timing Engine): implemented, CI green** (§25), **Phase 8 (Transit / Gochar Engine): methodology locked (standards v1.6.0), implemented, committed and pushed, CI green** (§26), and **Phase 9 WP-A1/A2/A3 (Ashtakavarga: Bhinna/Sarva, Trikona/Ekadhipatya Shodhana reductions, Pinda Sadhana): methodology locked (standards v1.7.0/v1.8.0), implemented, committed and pushed, CI green** (§27) -- **the rest of Phase 9 (Jaimini, Drishti, Western, KP, Shadbala, Ayurdaya, scope-undefined systems) is NOT complete**. Sections 1-19 were written at the end of Phase 5 and are kept as history; §15 carries a post-completion addendum, and §20-§27 hold the current state.
This document exists purely for session continuity. A future AI coding
assistant session should be able to read this file and continue exactly
where the project left off, without re-deriving context from memory.

**How to use this file**: read it fully, then verify its claims against the
actual repository (`Phases.md`, `docs/ASTROLOGY_STANDARDS.md`,
`docs/ARCHITECTURE.md`, `TECH_STACK.md`, git log, `gh run list`) before acting
on it. Treat it as an accurate snapshot as of the commits named in §22 (not §17, which is a historical snapshot), not as
a substitute for the authoritative documents it summarizes.

---

## 1. Project Identity

**Pandit Ji** is a self-hosted AI astrology platform (also describable as an
"AI Astrologer"). Its locked product vision (`features.md` §1) combines:

- A deterministic astrology calculation engine
- A comprehensive Vedic/Western astrology knowledge and rule system
- An AI agent that understands natural-language questions and produces
  personalized astrological interpretations

It intentionally goes beyond a generic AI-horoscope chatbot by separating five
concerns: astronomical/astrological calculation, astrology rules/knowledge, AI
reasoning/conversation, evidence/consistency verification, and
personalization/memory.

Locked product facts, verified against the repository:

- **Initial client platforms: Android + iOS**, via a single Flutter/Dart
  codebase (`features.md` §30, `TECH_STACK.md` §Client Stack, `README.md`).
  Web (Next.js) and an internal admin app are also locked (`apps/web`,
  `apps/admin`).
- **Languages**: English, Hindi, and Hinglish are the locked baseline
  conversational languages (`features.md` §28), with the architecture meant
  to be extensible to more languages later.
- **AI Palm Reading is a locked product feature** (`features.md` §34), not
  merely a future idea — its dedicated implementation is `Phases.md` Phase 13
  (Palm Reading & Vision Intelligence). Face reading remains future/out of
  scope.
- The combined **AstroSage + KundliGPT feature baseline** is locked
  (`features.md` §32) — Vedic astrology is the primary foundation; Western,
  KP, Lal Kitab, Nadi, numerology, compatibility, Panchang/Muhurta, and other
  systems are supported as modules.
- Architecture is a five-service pipeline: deterministic astrology
  calculation → astrology rules → knowledge/RAG → AI reasoning → independent
  verification (see §2).

**Unverified item flagged, not invented**: a prior instruction draft for this
document asked that "later WhatsApp and Truecaller integrations" be recorded
here as a locked product decision. This phrase does **not** appear anywhere in
`features.md`, `Phases.md`, `TECH_STACK.md`, `docs/ARCHITECTURE.md`, or any
other repository document as of the commit named in §17 (verified by a
repository-wide search). Per this project's own "do not silently invent or
change locked decisions" discipline, it is recorded here only as an
**unconfirmed possible future direction**, not as a locked decision — a future
session should ask the project owner to confirm it explicitly (and, if
confirmed, add it to `features.md`/`Phases.md` as a real locked decision)
before treating it as authoritative.

---

## 2. Core Product Principle

The project's single non-negotiable invariant, stated identically in
`features.md`, `docs/ARCHITECTURE.md` §1, and `docs/ASTROLOGY_STANDARDS.md`:

> **FACTS FLOW ONE DIRECTION; AI ONLY NARRATES.**

The canonical evidence-to-response flow (`features.md` §24, `Phases.md` Phase
15, `docs/ARCHITECTURE.md` §3):

```
User
  → AI Agent / Planner
  → Astrology Calculation Engine
  → Chart + Dasha + Transit + Yoga + etc.
  → Astrology Rule Engine / Knowledge Base
  → Evidence / Conflict Analysis
  → AI Reasoning
  → Verification
  → Personalized Response
```

The AI must **never** independently calculate or invent:

- Planetary positions, degrees, speed, retrograde, combustion
- Houses, Ascendant/Lagna, Rashi/sign placement
- Nakshatra/Pada
- Dashas (Vimshottari Mahadasha/Antardasha/Pratyantar)
- Transits, Sade Sati windows
- Yogas/Doshas
- Divisional charts (Vargas), dignity, house lordship
- Panchang/Muhurta elements, Ashtakoot/Guna Milan scores, numerology numbers
- Palm-reading facts (lines, mounts, shapes) — same invariant applies to the
  palm pipeline (`features.md` §34, `Phases.md` Phase 13)

Only `astro-engine` and `rule-engine` may originate any of the above
(`docs/ARCHITECTURE.md` §3, ADR-001). The AI Reasoner (in `agent`) may only
read and narrate structured facts it is handed; `verification` checks that
this boundary held before any response reaches a user.

---

## 3. Source-of-Truth / Execution Discipline

`SOURCE_OF_TRUTH.md` locks this authority order (highest first):

1. Explicitly locked project-owner decisions
2. `features.md` — WHAT
3. `Phases.md` — HOW/WHEN; **sole execution roadmap**
4. `docs/ARCHITECTURE.md` — technical structure
5. `docs/ASTROLOGY_STANDARDS.md` — calculation/interpretation standards
6. `TECH_STACK.md` — locked technology choices
7. `PRODUCT_POLICIES.md`
8. `LEGAL_REGULATIONS.md`
9. Research documents (`research/*.md`)
10. Code/configuration

**Conflict rule**: never silently resolve contradictions. Record them,
resolve in the higher-authority document, update dependents, add a changelog
entry.

**`Phases.md` is the sole authoritative execution roadmap.** Before starting
any new phase:

1. Read `Phases.md`.
2. Identify the current phase and current step.
3. Check deliverables.
4. Check dependencies.
5. Check exit criteria.
6. Check exclusions (what that phase must **not** implement).
7. Do not jump ahead.
8. If the authoritative methodology needed is missing or ambiguous in
   `docs/ASTROLOGY_STANDARDS.md` (or any other authoritative document), STOP
   and resolve it explicitly with the project owner before writing
   implementation code — never guess.

Every phase-implementation prompt given to an assistant in this project has,
in practice, opened with a line equivalent to:

> "Cross-check this entire prompt against the authoritative `Phases.md`. If
> anything differs, STOP and report the mismatch before implementation."

This has already surfaced and correctly resolved genuine standards gaps in
Phase 1 (a 13-item scope question), Phase 4 (combustion thresholds, node
convention), and Phase 5 (aspects, dignity, 14 additional Varga formulas,
Chalit deferral) — always via an explicit question to the project owner, never
by silent assumption. Future phases must follow the same discipline.

---

## 4. Locked Git Workflow

Repository: `https://github.com/iamankoo/Pandit-Ji` (default branch `main`).

**Before every phase:**
- Verify current checkpoint (local HEAD matches `origin/main`).
- Commit and push any outstanding state.
- Verify the remote SHA (`git ls-remote`/`gh api`).
- Verify GitHub Actions status for that commit.
- Verify the working tree is clean.
- Only then may the phase begin.

**After every phase:**
- Run the project's real validation (tests/lint/type-check — never claim a
  check passed without actually running it).
- Commit all changes belonging to that phase.
- Push to `main`.
- Verify the remote SHA matches local HEAD.
- Verify GitHub Actions status is **GREEN** for that commit.
- Verify the working tree is clean.
- Only then may the phase be declared complete.

**IMPORTANT, hard-won rule (see §16)**: a successful push (local HEAD ==
`origin/main`) is **not sufficient** on its own. Both the Phase 4 and the
initial Phase 5 checkpoint commits pushed cleanly and matched the remote SHA,
yet GitHub Actions showed a **red/failing** run on both, undetected until the
project owner checked GitHub directly. **GitHub Actions must be explicitly
checked after every future phase checkpoint** — e.g. `gh run list --commit
<sha>` and/or `gh api repos/<owner>/<repo>/commits/<sha>/check-runs` — not
assumed green because the push succeeded.

**Git identity — every commit in this project must use:**

```
iamankoo <aniketraj00384@gmail.com>
```

- No AI-assistant/coding-agent attribution anywhere in this project's new
  content or history: not in commit author/committer, not in commit message
  trailers (no co-authorship trailer or "generated by" line naming any AI
  tool), not in README/docs/code comments/package metadata/release notes, and
  no file named after any AI-assistant tool (e.g. no assistant-specific
  instruction/config file committed).
- Do not rewrite existing legitimate git history to remove historical
  contributors — this rule governs new work going forward, not retroactively.
- Never force-push or rewrite already-pushed history without explicit
  permission for that specific action.
- `.env` (in any variant) must never be committed.

---

## 5. Locked Pricing

**`PRICING.md` is the sole source of pricing figures.** Current locked model:

- **First 1 month of service: free**, no payment required.
- **After the free month: ₹1 activates the service for exactly 12 hours**,
  scoped to **one mobile number**.
- Each ₹1 payment buys exactly one 12-hour access window for that mobile
  number. When the 12 hours end, access ends until the next ₹1 payment.
- **No auto-renewal** — every 12-hour window requires a fresh, explicit ₹1
  payment.
- Access is **per mobile number**, not per account, device, conversation, or
  feature. One mobile number paying once covers all features/usage for that
  number for that 12-hour window — no separate tiers, credit packs, or
  per-report charges on top.

**Explicitly superseded and must never be reintroduced**: ₹99/month
"Starter," ₹249/month "Pro," ₹1,999/year "Annual Pro," credit packs (₹49 /
₹99 / ₹199 / ₹499), per-report pricing bands, or any framing of pricing as
per-account/per-device/per-conversation/per-feature rather than per mobile
number.

Implementation note: access control keys off a **verified mobile number**
(e.g. OTP), not user-account ID alone; this is a consumable, time-boxed
purchase for app-store compliance purposes, not an auto-renewing subscription
(`LEGAL_REGULATIONS.md`).

---

## 6. Important Pre-Phase-1 Locked Decisions

### Swiss Ephemeris licensing

- **Locked decision**: Pandit Ji will use the **Swiss Ephemeris Professional
  License** (not the AGPL option), because Pandit Ji is a proprietary
  commercial product that will run distributed mobile apps and server-side
  calculation services — AGPL's copyleft is incompatible with that.
- **This license has NOT been purchased yet.** Procurement (purchase + signed
  agreement with Astrodienst) is a pre-production/legal task required before
  public/commercial distribution or public-service activation — **not**
  before internal development/testing (`LEGAL_REGULATIONS.md`, `Phases.md`
  Phase 21 gate). Development through Phase 5 has used `pyswisseph`
  (AGPL-3.0-licensed) for development/internal use only, which is permitted
  under this plan.
- Reference pricing (subject to verification at procurement time): first
  Professional License fee CHF 750, each additional license CHF 400, unlimited
  license CHF 1550 (Astrodienst).

### Canonical repository naming

The locked monorepo structure (`docs/ARCHITECTURE.md` §27, `Phases.md` Phase
3):

```
pandit-ji/
├── apps/
│   ├── mobile/
│   ├── web/
│   └── admin/
├── server/                 FastAPI HTTP composition root (ADR-007;
│                            additive — not one of the five canonical services)
├── services/
│   ├── astro-engine/
│   ├── rule-engine/
│   ├── agent/               (includes voice/ and reports/ subpackages)
│   ├── knowledge/
│   └── verification/
├── packages/
│   ├── shared/
│   ├── contracts/
│   └── ui/
├── datasets/
├── tests/
├── docs/
│   └── architecture/ (diagrams.md, adr/ADR-001..ADR-007)
└── infrastructure/
```

**Canonical service names are locked**: `astro-engine`, `rule-engine`, `agent`, `knowledge`, `verification`. Do not use alternative names such as `astrology-engine`, `ai-agent`, or `knowledge-base` anywhere in the codebase or documentation.

This is enforced by an automated CI scan (`.github/workflows/ci.yml`, "Repository integrity" job).

### Astrology standards

The single canonical standards file is `docs/ASTROLOGY_STANDARDS.md` — there
is no separate `docs/calculation-standards.md`; any historical reference to
that filename refers to this one document.

---

## 7. Technology Stack

Locked baseline (`TECH_STACK.md`), by layer:

- **Mobile**: Flutter/Dart, Android + iOS from one codebase (tracking
  Flutter 3.47.x / Dart 3.13.x stable at time of writing)
- **Web/Admin**: Next.js + React + TypeScript (tracking Next.js 16.x)
- **Backend**: Python 3.12+ / FastAPI / Pydantic v2 / SQLAlchemy 2.x (async,
  via `asyncpg`) / Alembic migrations
- **API Gateway**: Traefik
- **Auth**: Keycloak (OIDC/OAuth 2.0), self-hosted
- **Database**: PostgreSQL (tracking 18.x), sole database technology
- **Vector search**: pgvector, in the same PostgreSQL instance
- **Cache/queue**: Redis-wire-protocol layer, default deployment **Valkey**
  (Redis itself an interchangeable alternative — see licensing rationale
  below)
- **Background jobs**: Celery 5.6 (Redis-protocol broker/result backend;
  Celery Beat for scheduling; Kafka explicitly not introduced)
- **Astronomy**: Swiss Ephemeris (Professional License, locked; see §6)
- **Rule engine**: hand-rolled Python forward-chaining evaluator + versioned
  YAML rule definitions (no third-party rule-engine product)
- **AI/ML framework**: PyTorch
- **Vision (palm reading)**: OpenCV + NumPy + MediaPipe Hand Landmarker (hand
  detection/landmarks only — **not** a palmistry tool by itself) + a
  dedicated custom PyTorch palm-line/feature model
- **LLM inference**: self-hosted only, no hosted-API production dependency —
  **Ollama** for development, **vLLM** for staging/production, both behind a
  common `LLMProvider` interface
- **Object storage**: S3-compatible, **MinIO** self-hosted default
- **Observability**: OpenTelemetry (traces/metrics/logs)
- **Containers**: Docker + Docker Compose (Kubernetes/production
  orchestration explicitly not locked — evaluated only on measured need)
- **Testing**: pytest (Python), `flutter test` (Flutter), Vitest +
  React Testing Library (TypeScript), Schemathesis (API contract tests)
- **Code quality**: Ruff + mypy + pre-commit (Python), ESLint + Prettier +
  `tsc` (TypeScript), `dart analyze` + `dart format` (Flutter)

**Explicitly deferred** (not locked, must not be presented as decided):

- Final LLM model checkpoint (Phase 14)
- GPU hardware (make/model/quantity) — sized against the Phase 14 checkpoint
- Cloud provider (or fully on-prem) for staging/production
- Production container orchestrator (Kubernetes or otherwise)
- Exact production topology (instance sizing, replica counts, region layout)
- Observability backend product (the storage/visualization layer behind
  OpenTelemetry)
- API contract-testing tool's exact package (Schemathesis is the current best
  fit, reconfirm at Phase 18)

---

## 8. Product Language Requirement — FUTURE IMPLEMENTATION (NOT YET BUILT)

A new product requirement has been stated for a future phase. It is recorded
here for continuity only — **it must not be implemented now**, and must only
be implemented in whichever phase `Phases.md` assigns it to (this may require
an explicit `Phases.md` update/decision by the project owner first, since the
current `Phases.md` text does not yet name this exact requirement).

**Account → Language** setting:

- Options: **English** (default) and **हिन्दी (Hindi)**.
- New users default to English.
- The selected language persists for that user.
- The entire app UI follows the selected language.
- AI responses/reports should follow the selected language where applicable.
- The UI language must **not** automatically change based on what the user
  types (i.e., no inferring UI locale from conversational input).
- **Hinglish remains a supported AI conversation language** (per `features.md`
  §28), but the UI language selector itself only offers English/Hindi —
  Hinglish is not a UI locale option.

---

## 9. Phase Roadmap

`Phases.md`'s current authoritative roadmap has **21** phases, verified
directly against the file. Its header previously read "20-Phase Master
Development Plan", a stale label left over from before Phase 13 was inserted;
the header was corrected to "21-Phase" during Phase 6 research:

1. Phase 1 — Product & Astrology Standards
2. Phase 2 — System Architecture
3. Phase 3 — Repository & Engineering Foundation
4. Phase 4 — Astronomical Calculation Engine
5. Phase 5 — Birth Chart / Kundli Engine
6. Phase 6 — Vedic Astrology Rule Engine
7. Phase 7 — Dasha & Timing Engine
8. Phase 8 — Transit / Gochar Engine
9. Phase 9 — Advanced Astrology Systems
10. Phase 10 — Panchang, Muhurta & Calendar Engine
11. Phase 11 — Numerology + Compatibility
12. Phase 12 — Astrology Knowledge Base
13. Phase 13 — Palm Reading & Vision Intelligence
14. Phase 14 — Self-Hosted AI Model
15. Phase 15 — Pandit Ji Agent
16. Phase 16 — Evidence & Verification Engine
17. Phase 17 — Life-Domain Intelligence
18. Phase 18 — Backend Platform
19. Phase 19 — Pandit Ji Web + Mobile App
20. Phase 20 — Voice + Personalization
21. Phase 21 — Validation, Backtesting & Production Launch

**Phases 1 through 7 are complete and verified (Phase 6: accepted by the owner, CI green; see §20). Phase 7 (Vimshottari Dasha) is implemented and CI-verified (see §25); its methodology research is §21. Phase 8 (Transit / Gochar) is implemented, pushed and CI-verified (see §26).** (This roadmap list was first written at the end of Phase 5, when it read "Phase 6 has not started"; that statement is now historical.)

---

## 10. Phase 1 — COMPLETED

Established `docs/ASTROLOGY_STANDARDS.md` as the single canonical standards
document (v1.0.0 at Phase 1 completion; v1.3.0 at Phase 5; now v1.4.1, see §15, §20 and §24). It defines
standards/methodology contracts (what a later phase's engine must compute and
how), not implementations. Content locked in Phase 1:

- Core rule (facts-flow invariant) and AI scope boundary
- Default Vedic profile: sidereal zodiac, **Lahiri ayanamsa**, **Vedic
  whole-sign house baseline**
- Full per-system methodology for: Vedic/Jyotish, Western/Tropical, KP,
  Lal Kitab, Nadi (with Lal Kitab and Nadi explicitly marked **provisional,
  pending dedicated source validation** — not fully specified, not
  implemented)
- Divisional-chart (Varga) framework: the locked Shodashvarga set (D1, D2,
  D3, D4, D7, D9, D10, D12, D16, D20, D24, D27, D30, D40, D45, D60) — at
  Phase 1, only D1/D9 had real derivation formulas; the remaining 14 were
  added in Phase 5 (§15)
- Vimshottari Dasha standard, Nakshatra standard, Yoga/Dosha schema,
  Panchang/Muhurta standards, Numerology standards
- Prediction language policy, birth-time uncertainty handling, data/privacy
  principles (cross-referencing `PRODUCT_POLICIES.md`)
- Self-hosted-AI requirement and AI scope boundary

**Do not claim KP sub-lord arithmetic, Lal Kitab, or Nadi methodology were
fully implemented in Phase 1** — they remain explicitly provisional/deferred
to Phase 9, pending dedicated research validation
(`docs/ASTROLOGY_STANDARDS.md`, `docs/ARCHITECTURE.md` §30).

Phase 1 completion commit: `a784ee7786f055e13f844822ebb8c28ecb1cb3e6`
("feat: complete phase 1 - product and astrology standards"). Note: this is
distinct from the earlier pre-Phase-1 initial checkpoint commit
`ae8ea5c5259aff73758614bd6b567e3bf9a56a27` ("chore: initial pre-phase-1
project checkpoint") — the two are sometimes conflated; the checkpoint commit
is not the Phase 1 completion commit.

---

## 11. Phase 2 — COMPLETED

Established `docs/ARCHITECTURE.md` (the technical-structure authority) plus
`docs/architecture/diagrams.md` and ADR-001 through ADR-007. Covers (with
section numbers as they exist in the current document):

API gateway (§4), five-service architecture with explicit "not responsible
for" boundaries (§5), Astrology Engine Architecture (§6), Rule Engine
Architecture (§7), Agent Orchestrator Architecture (§8), Astrology Service
Interfaces (§9), Knowledge Architecture (§10), Verification Architecture
(§11), Database Architecture (§12), Queue/Background Job Architecture (§13),
Caching Architecture (§14), Authentication Architecture (§15), AI
Infrastructure (§16), Memory Architecture (§17), Observability (§18),
Failure Architecture (§19), Security Architecture (§20), Versioning
Architecture (§21), Deployment Topology (§22), Scaling Strategy (§23), Data
Flow Diagrams (§24), the ADR index (§25), API Architecture (§26), Repository
Structure (§27, see §6 above), the Execution Roadmap pointer to `Phases.md`
(§28), Technical Risks (§29), Components Requiring Research (§30), the
explicit Deterministic-vs-AI-Driven split (§31), and Known Contradictions
Between Documents (§34 — all three tracked contradictions are now marked
RESOLVED/LOCKED).

Phase 2 completion commit: `36998f8ba935e399728f8d103e0520e6382602fb`
("docs: complete phase 2 - system architecture").

---

## 12. Pre-Phase-3 Roadmap / Technology Update

Between Phase 2 and Phase 3, two things were locked:

1. **AI Palm Reading became a locked product feature** (`features.md` §34,
   superseding its earlier "Future Expansion" listing). A new **Phase 13 —
   Palm Reading & Vision Intelligence** was inserted into the roadmap, and
   every phase after it was renumbered (the former Phases 13–20 became
   14–21). Face reading remains future/out of scope. The locked palm pipeline
   (`Phases.md` Phase 13):

   ```
   User Palm Image
     → Image Quality Validation
     → Hand Detection/Localization
     → Palm Region Extraction
     → Palm Landmark/Feature Extraction
     → Palm-Line/Palm Feature Analysis
     → Structured Palm Facts
     → Palm-Reading Rules/Knowledge
     → AI Reasoning
     → Verification
     → Final Interpretation
   ```

   Same facts-flow invariant as §2 applies: the AI must never independently
   invent palm-reading facts (lines, mounts, shapes) from an image.

2. `TECH_STACK.md` (the single technology-stack document) was created and
   locked — see §7.

Pre-Phase-3 update commit: `542498892a3bccf73e729919e58ae7af45d7dcc9`
("docs: lock palm reading scope and technology stack").

---

## 13. Phase 3 — COMPLETED

Built the actual repository engineering foundation: the monorepo skeleton
(§6's structure, all directories present and populated with real, installable
package skeletons), Python package foundations for all five services plus
`packages/contracts`/`packages/shared`, the `server/` FastAPI composition
root (ADR-007), CI (`.github/workflows/ci.yml` — the multi-component test
matrix plus Docker build and repository-integrity scan jobs used throughout
this project), Docker Compose infrastructure (PostgreSQL+pgvector, Valkey,
Keycloak, MinIO, Traefik gateway), environment templates (`.env.example`),
Alembic migration foundation (`infrastructure/migrations`, schema-namespace
scaffolding only), test/tooling setup (pytest, Ruff, mypy, ESLint, Prettier,
`dart analyze`/`dart format`, pre-commit hooks), and initial security/forbidden-name
scans. A known limitation from that phase: Docker daemon was not available in
every sandbox used for initial validation, so some Docker-dependent checks
were validated in a later phase/session instead of at Phase 3 completion time
(this has since been fully validated — see §16).

Phase 3 completion commit: `a9f0bac53c8e5e12240180bc09a61d066600112f`
("feat: complete phase 3 - repository engineering foundation").

---

## 14. Phase 4 — COMPLETED

Built the deterministic Astronomical Calculation Engine in
`services/astro-engine` (package `pandit-astro-engine`, reached v0.2.0 at
Phase 4 completion). Architecture:

- `ephemeris.py` — the **sole** Swiss Ephemeris (`pyswisseph`) import
  boundary in the entire codebase; every other module reaches Swiss Ephemeris
  only through this adapter.
- `planets.py` — per-body orchestration for the nine celestial bodies (Sun,
  Moon, Mars, Mercury, Jupiter, Venus, Saturn, Rahu, Ketu): longitude,
  latitude, speed, retrograde, degree components.
- `combustion.py` — derived layer, pure arithmetic, no ephemeris calls of its
  own.
- `timezones.py` — IANA timezone handling (`zoneinfo`/`tzdata`), historical
  offsets, DST ambiguous/nonexistent detection (PEP 495 fold-based).
- `solar_events.py` — sunrise/sunset.
- `service.py` — `AstronomicalCalculationService`, the one public facade.

Locked configuration: **sidereal zodiac + Lahiri ayanamsa** as the Vedic
default (tropical/Western supported as an explicit alternate); **Mean Node**
default for Rahu/Ketu, **True Node** supported as an explicit alternate
config (never silently mixed); reproducibility metadata on every result
(engine version, Swiss Ephemeris version, ephemeris mode, exact calculation
configuration, time resolution).

**Combustion thresholds** (Brihat Parashara Hora Shastra tradition, locked
per explicit project-owner decision):

| Planet | Threshold (direct) | Threshold (retrograde) |
|---|---|---|
| Moon | 12° | — |
| Mars | 17° | — |
| Mercury | 14° | 12° |
| Jupiter | 11° | — |
| Venus | 10° | 8° |
| Saturn | 15° | — |

The Sun is never combust; Rahu/Ketu are not evaluated for combustion under
this standard.

Validation at Phase 4 completion: 72 tests (unit, boundary, golden reference,
2,000-random-instant internal-consistency/determinism testing, performance
benchmarking: ~0.5–0.7 ms per full 9-body calculation). Golden reference
validation used four independently published 2024 equinox/solstice UTC
instants (matched to within 0.0007°, tolerance 0.01°). Documented known
limitations: no bulk (hundreds/thousands-scale) independent reference dataset
was available in the development environment; `rise_trans` searches forward
from the query instant (so "next sunrise" can belong to the following day);
`SolarEvent.local_datetime` is not populated; only Lahiri ayanamsa is
implemented; KP/Lal Kitab/Nadi remain out of scope.

Phase 4 completion commit: `15312a900309af602f2c3348e52f91131029d878`
("feat: complete phase 4 - astronomical calculation engine").

---

## 15. Phase 5 — COMPLETED AND VERIFIED GREEN

**This is the most recent completed phase and the most important section for
resuming work.**

### Standards locked before implementation

`docs/ASTROLOGY_STANDARDS.md` was bumped to **v1.3.0** (Phase 5
pre-implementation lock; later v1.4.0 for Phase 6 and v1.4.1 for the Nakshatra boundary clarification) after a mandatory pre-implementation standards audit
found four genuine gaps, each resolved by explicit project-owner decision
(never guessed):

- **All 14 remaining Shodashvarga formulas** (D2, D3, D4, D7, D10, D12, D16,
  D20, D24, D27, D30, D40, D45, D60) — full classical Parashari derivation
  formulas now recorded, completing the 16-varga set alongside the
  already-locked D1/D9.
  - **D3 (Drekkana) was explicitly locked to the BPHS trine-counting
    convention** (same sign / 5th sign / 9th sign from the D1 sign) — a
    sequential alternate convention some other software uses was explicitly
    considered and rejected.
  - **D60 (Shashtiamsa) is sign/degree placement only** — the classical
    60-named-deity assignment per division is explicitly **not** asserted or
    implemented; this is a documented scope limitation, not an omission.
- **Planetary aspects standard** (Vedic graha drishti, not Western
  degree-based aspects): all nine grahas cast the universal 7th-house/sign
  aspect; **Mars** additionally casts the 4th and 8th; **Jupiter**
  additionally casts the 5th and 9th; **Saturn** additionally casts the 3rd
  and 10th; **Rahu/Ketu cast only the universal 7th aspect** — no special
  extra aspects, unlike some regional conventions that treat them like Mars.
- **Planetary dignity standard**: exact exaltation/debilitation degree per
  planet plus own-sign/neutral states for the seven classical grahas —
  **Mooltrikona explicitly excluded from Phase 5 scope** (documented
  deferral).
- **Sign/House lordship standard**: the traditional 12-sign ruler table
  (non-ambiguous, no tradition fork; recorded as a versioned, citable standard
  rather than left implicit in code).
- **Chalit (Bhava-Chalit)** and **Ashtakvarga** explicitly recorded as
  **out of scope for Phase 5** (deferred, not guessed or silently
  implemented) — `Phases.md` does not list either among Phase 5's
  deliverables.

The methodology-lock process itself: varga formulas were researched,
documented, and presented for explicit approval before any implementation
code was written; medium-confidence modality-anchor rows were retained only
as explicitly approved by the project owner; no formula was guessed.

### Implementation

`services/astro-engine` advanced **v0.2.0 → v0.3.0**, built entirely on top
of Phase 4's `AstronomicalCalculationService` — **no Swiss Ephemeris call was
duplicated outside `ephemeris.py`**; the **Ascendant** was the only new
astronomical primitive Phase 5 needed, and it was added through the existing
`ephemeris.py` adapter (using Swiss Ephemeris's Whole Sign house system,
`hsys=b'W'`, consistent with the locked whole-sign convention).

New modules, one per standard: `rashi.py`, `nakshatra.py`, `lordship.py`,
`dignity.py`, `aspects.py`, `vargas.py`, plus the orchestrator
`kundli_models.py` (typed output contracts) and `kundli.py`
(`KundliCalculationService`, the public facade).

The resulting `Kundli` output includes:

- Lagna (Ascendant): sign + precise degree
- 12 whole-sign houses, each with its Rashi and house lord
- Every requested planet's Rashi, degree-in-sign, house, Nakshatra + Pada,
  dignity (`None` for Rahu/Ketu, which are not evaluated), houses it aspects,
  retrograde/combustion status (inherited from Phase 4), and per-body
  ephemeris mode
- **All 16 divisional charts** (D1, D2, D3, D4, D7, D9, D10, D12, D16, D20,
  D24, D27, D30, D40, D45, D60), each with its own Ascendant, 12 houses, and
  planet placements
- The **Chandra (Moon) chart**: the same whole-sign methodology, but with the
  Moon's own sign as house 1 instead of the Ascendant

### Validation

**191/191 tests passed** (72 Phase 4 regression tests + 119 new Phase 5
tests), `ruff check` clean, `ruff format --check` clean, `mypy --strict`
clean. Includes:

- A genuine external golden case: **India's Independence chart** (15 Aug
  1947, 00:00 IST, New Delhi) — independently published as Taurus Ascendant,
  Moon in Cancer (e.g. astrotheme.com, jyotishgram.com) — matched exactly by
  the engine.
- Boundary tests (sign/Nakshatra/varga-formula boundaries, extreme latitudes,
  the antimeridian).
- Invariant/property tests at scale (300+ randomized cases): every chart's 12
  houses always contain all 12 Rashis exactly once; house lords always match
  the sign-lordship table; the Rahu/Ketu 180° opposition is preserved through
  the **sign-relative** vargas (D1, D3, D4, D7, D9, D10, D12, D60) but is
  **not** asserted for the **absolute-start** vargas (D2, D16, D20, D24, D27,
  D30, D40, D45) — this asymmetry was verified numerically and is a real,
  correct property of the locked classical formulas, not a bug; determinism
  across repeated calculation.

Documented honest limitations (not overclaimed): the Ascendant's own
`ephemeris_mode` is not disclosed (Swiss Ephemeris's `houses_ex` does not
return a mode flag the way `calc_ut` does for planets); D60 has no
deity-name table; Mooltrikona/Chalit/Ashtakvarga remain out of scope; the
Ascendant is astronomically degenerate at true polar latitudes (±90°) — Swiss
Ephemeris still returns a value there with no crash, but the "rising sign"
concept itself breaks down physically.

Initial Phase 5 completion commit: `e7bd5759381824fcaa75446e6de6ad783bd4e5cb`
("feat: complete phase 5 - birth chart kundli engine").

---

### Post-completion correction: Nakshatra/Pada boundary (commit `091ca1b`, CI run `35500359836`, green)

After Phase 5 was accepted, a defect was found in `pandit_astro_engine.nakshatra.nakshatra_position()`: it divided by the float `360.0/27.0`, which is not exactly 13 deg 20 min, so exactly representable boundary longitudes could fall into the lower bucket (40.0 returned Krittika instead of Rohini; 10.0 returned Pada 3 instead of Pada 4). The defect was reproduced in the checkout before the fix. **It is now fixed and closed.**

- Owner-approved convention (a Pandit Ji engineering convention, not a classical source rule): half-open, lower-inclusive and upper-exclusive intervals for Nakshatras and Padas, exact rational classification of the normalized float, 360 = 0.
- Normalization is unchanged (floating-point modulo 360). The public API, names, ordering, Pada numbering and `near_boundary` behaviour are unchanged. Known unchanged behaviour, not approved for change: a negative longitude smaller in magnitude than about 2.8e-14 degrees normalizes to 360.0 and so classifies as 0 (Ashwini).
- Files: `services/astro-engine/src/pandit_astro_engine/nakshatra.py`, `tests/test_nakshatra.py`, `tests/test_kundli.py`. Old versus new code gave 0 classification differences and 0 `near_boundary` differences over 200,000 random longitudes; the new tests fail (80 failures) against the old code and pass against the fix.
- Validation: astro-engine 353 tests passed (previously 191), rule-engine 235 passed, `ruff format --check`, `ruff check` and `mypy` clean; CI 15 of 15 jobs green.
- Recorded in `docs/ASTROLOGY_STANDARDS.md` v1.4.1 (§Nakshatra standards and the change log).
- **Open follow-up**: Phase 5 calculation records still carry `standards_version = 1.3.0` (`kundli.py`, `STANDARDS_VERSION`) although their boundary behaviour now follows v1.4.1. Advancing that constant is a code change and an owner decision; it has not been made.

---

## 16. Phase 5 CI Failure and Corrective Work

This section is retained deliberately as a lesson for every future phase
checkpoint (see §4's new rule).

The initial Phase 5 commit (`e7bd575`) pushed successfully and matched
`origin/main`, but **GitHub Actions showed a red/failing run**. Investigation
(not guessing) found three distinct, confirmed root causes, none of them a
Phase 5 astrology/methodology problem:

1. **`ruff format --check` failure** in the `services/astro-engine` CI job —
   the `README.md` Kundli code example had been edited after the last local
   `ruff format` run and was never re-validated before committing (a process
   gap, reproduced locally with the exact same ruff version CI used, so not a
   version-drift issue).
2. **`server` job `mypy` failure** — genuinely **pre-existing since Phase 4**
   (confirmed by checking the Phase 4 commit's own CI run, which failed the
   same way). `server/src/pandit_server/api/health.py` legitimately imports
   `get_health` from all five domain services for its `/readyz` endpoint, but
   `server/pyproject.toml` never declared them as dependencies and CI never
   installed them for that job.
3. **Docker build failure**, discovered only *after* fixing #2 (adding the
   five services as `server` dependencies meant the Docker image now had to
   compile `pandit-astro-engine`'s `pyswisseph` C-extension dependency, but
   the single-stage `python:3.12-slim`-based Dockerfile had no C compiler).

Corrective commits:

- `e76d78ec21ad8f1dbea669ae6942cd0344a0e0ed` — reformatted `README.md`;
  declared the five domain services in `server/pyproject.toml`; added a
  conditional CI step installing them for the `server` matrix job only.
- `a00fc8497dfd9cec65412ed41eecf8304532bdc4` — rewrote `server/Dockerfile` as
  a two-stage build: a `builder` stage installs `build-essential` and builds
  a virtualenv; the final runtime stage copies only the built venv, so `gcc`
  never ships in the production image. **Verified with a real local `docker
  build` and container run** (not assumed) — `/healthz` returned `200`
  before this fix was committed.

Final verification, cross-checked two independent ways:

- `gh run view <run-id>` showed all 15 jobs green.
- `gh api repos/iamankoo/Pandit-Ji/commits/<sha>/check-runs` independently
  confirmed all 15 check-runs report `"conclusion": "success"`.
- Local HEAD == `origin/main` == `a00fc84`.
- Working tree clean.
- Commit author/committer correctly `iamankoo <aniketraj00384@gmail.com>` on
  every commit; no AI-assistant/coding-agent attribution anywhere in the
  diffs.

**Phase 5 is therefore fully complete and green — not just pushed, but
actually verified green on GitHub Actions.**

---

## 17. Repository State at the End of Phase 5 (historical)

As of this document's creation:

- **Phase 5: COMPLETE and verified green.**
- **Phase 6: NOT STARTED.**
- Current local HEAD: `a00fc8497dfd9cec65412ed41eecf8304532bdc4`
- `origin/main`: `a00fc8497dfd9cec65412ed41eecf8304532bdc4` (matches)
- Working tree: **clean**
- GitHub Actions for the current HEAD: **15/15 checks passing**
  (`Repository integrity`, `Docker — build & compose config`, nine
  `Python — <component>` jobs for `packages/contracts`, `packages/shared`,
  `services/astro-engine`, `services/rule-engine`, `services/agent`,
  `services/knowledge`, `services/verification`, `server`,
  `infrastructure/migrations`, and three `TypeScript`/`Flutter` client jobs)
- `services/astro-engine` package version: `0.3.0`
- `services/rule-engine`, `services/agent`, `services/knowledge`,
  `services/verification` remain at their Phase 3 skeleton version (`0.1.0`)
  — not yet built out beyond the foundation
- `docs/ASTROLOGY_STANDARDS.md` version: `1.3.0`
- Next phase per `Phases.md`: **Phase 6 — Vedic Astrology Rule Engine**

Do not assume this state remains accurate indefinitely — re-verify HEAD,
remote SHA, and GitHub Actions status at the start of the next session (see
§19 and §20).

---

## 18. Deferred / Pending Methodology Decisions (as of the end of Phase 5; see §20-21 for later decisions)

Explicitly deferred items on record across the repository (do not invent
additional ones beyond this list):

- **Chalit / Bhava-Chalit** house-cusp methodology — deferred to a follow-up
  decision (`docs/ASTROLOGY_STANDARDS.md`, locked Phase 5 scope note)
- **Ashtakvarga** — out of scope for Phase 5; not yet scheduled to a specific
  phase beyond being part of `astro-engine`'s eventual full responsibility
  per `docs/ARCHITECTURE.md` §2
- **Mooltrikona** — explicitly deferred, dignity currently limited to
  exalted/debilitated/own-sign/neutral
- **KP sub-lord subdivision arithmetic** — still provisional; must be
  validated against an authoritative KP reference before Phase 9 implements
  it (`docs/ASTROLOGY_STANDARDS.md`, `docs/ARCHITECTURE.md` §30)
- **Lal Kitab methodology** — still provisional, pending dedicated source
  validation before Phase 9
- **Nadi methodology** — still provisional, pending dedicated source
  validation before Phase 9
- **Swiss Ephemeris Professional License procurement** — decision locked,
  purchase/signed Astrodienst agreement not yet completed; required before
  public/commercial distribution, not before internal development
- **Legal counsel sign-off / launch gate** — outstanding; `LEGAL_REGULATIONS.md`
  is an engineering compliance baseline, not a substitute for qualified legal
  review before public launch
- **Final LLM model checkpoint** — deferred to Phase 14
- **GPU hardware** — deferred, sized against the Phase 14 checkpoint
- **Cloud provider** — deferred, a deployment decision
- **Production container orchestrator** — deferred, evaluated only on
  measured scaling need
- **Exact production topology** (instance sizing, replica counts, region
  layout) — deferred to Phase 18/21
- **Observability backend product** (behind OpenTelemetry) — deferred
- **API contract-testing tool's exact package** — Schemathesis is the current
  best fit, to be reconfirmed at Phase 18

---

## 19. Phase 6 Starting Protocol (historical; Phase 6 is complete, see §20)

**Phase 6 must NOT be started merely because Phase 5 is complete.** Required
process for the next session:

1. Read this `SUMMARY.md`.
2. Read the authoritative `Phases.md` directly (do not rely on this
   document's §9 summary alone).
3. Verify the Phase 5 checkpoint: current HEAD, `origin/main`, and GitHub
   Actions status all still match §17's claims (re-check; time may have
   passed).
4. Read all of Phase 6's stated dependencies (it consumes Phase 5's Kundli
   output).
5. Identify Phase 6's exact deliverables from `Phases.md` (planet meanings,
   house meanings, sign meanings, nakshatra meanings, lordships, aspects,
   strength, dignity, planetary relationships, benefic/malefic conditions,
   yogas, doshas — each rule needing a rule ID, system, conditions, evidence,
   interpretation, priority, exceptions, sources/reference, and tests).
6. Identify any methodology gaps against `docs/ASTROLOGY_STANDARDS.md` (e.g.,
   exact yoga/dosha definitions, source citations, conflict-resolution rules
   across schools).
7. **If a methodology is missing or ambiguous, STOP and ask the project owner
   — do not guess.**
8. Prepare a detailed Phase 6 implementation prompt.
9. Cross-check that prompt against `Phases.md` explicitly.
10. Only after project-owner approval, begin implementation.
11. Maintain strict phase boundaries — do not implement Phase 7+ content.
12. Run full validation (tests, ruff, mypy, and any other component's checks
    touched).
13. Commit, using `iamankoo <aniketraj00384@gmail.com>`.
14. Push to `main`.
15. Verify the remote SHA matches local HEAD.
16. **Verify GitHub Actions is GREEN** (not just that the push succeeded —
    see §4/§16).
17. Verify the working tree is clean.
18. Only then mark Phase 6 complete.

---

## 20. Phase 6 — COMPLETED AND ACCEPTED

Phase 6 (Vedic Astrology Rule Engine) is implemented, accepted by the project owner, and CI is green.

- **Commits**: `337e700` (documentation checkpoint: `docs/ASTROLOGY_STANDARDS.md` v1.4.0, `docs/ARCHITECTURE.md` §7, `Phases.md` ownership clarifications, `research/ASTROLOGY_SOURCES.md` §6), `04c17ca` (implementation), `6e8eba4` (a boundary-test fix: the repository's attribution check forbids vendor names in `.py` files, so tests must not contain them). CI run `35461086198`: 15/15 jobs green.
- **Tests**: 235 rule-engine tests; 191 Phase 5 (astro-engine) tests unchanged. Ruff and mypy strict pass.
- **Standards versions**: Phase 5 calculations keep `standards_version = 1.3.0` (`services/astro-engine/src/pandit_astro_engine/kundli.py` was NOT touched); Phase 6 rule evaluation records `1.4.0`. Historical metadata is never upgraded.
- **Where the code is**: `services/rule-engine/src/pandit_rule_engine/` (`schema.py`, `loader.py`, `conditions.py`, `evaluator.py`, `results.py`, `tables.py`, `derived.py`, `bundle.py`, `hashing.py`, `adapters.py`, `facts.py`, `engine.py`, `vocab.py`). Rule and table YAML: `services/knowledge/rules/` (`ruleset.yaml`, `bphs/`, `phaladeepika/`, `jataka_parijata/`; `modern/` reserved and empty).
- **Implemented rule families (51 rules)**: Pancha Mahapurusha (5); Nabhasa (31 defined yogas); Sunapha, Anapha, Duradhara; Vesi, Vosi, Ubhayachari; Adhi (Moon) and Lagnadhi; Dhana (structural count); BPHS Kemadruma; BPHS Gajakesari (canonical, four documented readings); separate Phaladeepika Kesari and Kemadruma profiles; BPHS Mangal/Kuja (two readings) and JP Kuja. Methodology tables: relationships (BPHS Ch. 3 v. 55-58), natural benefic/malefic (v. 11), Moolatrikona (v. 51-54), the 84-cell Ch. 34 functional-nature table.
- **Locked behavior**: source-specific profiles; ambiguity-preserving evaluation (`NOT_EVALUABLE(reading_ambiguous)` when readings disagree, all readings kept); priority is metadata only; structured `NOT_EVALUABLE` reason codes; reproducible EvidenceBundle (no timestamp, canonical ruleset hash). Two implementation choices approved by the owner: (1) `aspected_by` is definitely false where BPHS Ch. 26 gives no aspect at all (`requires_partial_drishti` only from the 3rd/10th, 5th/9th, 4th/8th from the aspecting planet); (2) in Kemadruma the Moon is the reference and is not counted as a surrounding planet.
- **Deferred**: upagraha/Gulika/Mandi/special-Lagna/Pranapada calculations (Phase 10 special-points module); Jaimini, Chara Karakas and longevity methods (Phase 9); partial/degree drishti and Shadbala (Phase 9); Dasha (Phase 7); Nadi/Bhakoot (Phase 11); Sade Sati (Phase 8).
- **Unsupported**: Ardhachandra (no condition in the source), canonical Kaal Sarp (modern tradition only; `MODERN_KAAL_SARP_<SOURCE>` reserved), D27 (status `UNRESOLVED`; Phase 5 formula unchanged), translator-note-only Gajakesari variants, node relationships/dignity/lordship.

## 21. Phase 7 — METHODOLOGY RESEARCH (historical; implemented in §25)

This section is the research record written before implementation. At the time it was written nothing of Phase 7 existed; Phase 7 is now implemented (§25). Two research passes were done; no code, YAML, tests or documentation changed for them. All findings below are PROPOSALS awaiting the owner's decision unless stated.

**Scope (from `Phases.md`, authoritative)**: Vimshottari Dasha, Mahadasha, Antardasha, Pratyantar, start/end, current/future/historical Dasha, transitions, "complete life-period timeline", plus "connect Dasha with Houses, Lords, Planets, Yogas, Career, Marriage, Education, Finance, Relationships". `Phases.md` states no dependencies, exit criteria or exclusions for Phase 7. The owner's locked scope: Vimshottari only, to Pratyantar; NOT Ashtottari/Yogini/Chara/Narayana, Sookshma, Prana, rectification. "Connect" means deterministic temporal facts and references only, not life-domain interpretation (that belongs to Phase 12/17 and the agent). `ARCHITECTURE.md` places dashas in `services/astro-engine` (`dashas/`), with `DashaRequest`/`DashaResponse`.

**What is established (translation level, Tier 2, no Sanskrit-level verification)**
- Sequence and years: BPHS Ch. 46 v. 12-15 (Kapoor, Vol II, printed pp. 505-507, image-checked) and Phaladeepika Adhyaya XIX sl. 2 (printed p. 192, image-checked): Sun 6, Moon 10, Mars 7, Rahu 18, Jupiter 16, Saturn 19, Mercury 17, Ketu 7, Venus 20 (120), counted from Krittika; matches `docs/ASTROLOGY_STANDARDS.md`.
- Antardasha (BPHS Ch. 51 v. 1-2, printed pp. 618-619, image-checked): Mahadasha years x Antardasha lord's years / 120; first Antardasha belongs to the Mahadasha lord, the rest follow the same nine-lord order; same for Pratyantar. Pratyantar (BPHS Ch. 61 v. 1, printed p. 742, image-checked): Antardasha length x lord's years / 120. Kapoor's worked examples and tables count in 30-day months (for example 3 months 18 days = 108 days) - a translator/edition convention (Tier 3), not a verse statement of year length.

**Balance at birth - three methods, no single source method**
- BPHS Ch. 46 v. 16: expired part = years x Moon's expired stay in the nakshatra / its total stay, both as Panchanga TIME (ghatis/palas) - directly stated. Kapoor's note says modern researchers use the Moon's longitude instead.
- Phaladeepika XIX sl. 3 (image-checked): remaining ghatikas x years / 60, remainder x 12/60 for months and x 30/60 for days - divisor 60 (nominal), so whether "ghatikas" is time or an arc measured in 60ths is not stated (inferred only).
- Uttara Kalamrita, Ch. VI, printed p. 142 (P. Subrahmanya Sastri's worked example, Tier 3, OCR): arc-based balance 1y 11m 6d versus Panchanga-time balance 1y 10m 29d, 7 days apart; the translator calls the arc method "the correct balance".
- `docs/ASTROLOGY_STANDARDS.md` v1.4.0: longitude fraction. Proposed classification: SOURCE_CONFLICT between time-based (BPHS verse) and arc-based (standard); keep separate profiles. Proposed CANONICAL SOURCE METHOD = the BPHS time-based profile (needs Moon nakshatra entry/exit instants, not currently computed); proposed PANDIT JI DEFAULT IMPLEMENTATION PROFILE = the already-locked longitude-fraction method, labelled a product default, never as classical truth.

**Year length - no BPHS verse states it**
- Only Tier 2 textual support: Phaladeepika XIX sl. 4 (image-checked, translation level; my Sanskrit reading of the verse is unreviewed): the Sun's return to its birth position is "one solar year, which is also the year taken for the Ududasa system"; days are obtained by sub-dividing it (bhagakrama). Applying it to Vimshottari is inferred from context (Vimshottari is a nakshatra-based dasa).
- Other conventions, kept as separate profiles: mean sidereal year 365.256363 d (Uttara Kalamrita translator's note), 365.25, 365.2425 (software), 360-day savana (Santhanam/Kapoor translator notes and tables; not a Vimshottari statement). Practitioner and software pages are Tier 4-5 and only corroborate.
- Proposed: fixed-duration years in exact seconds (no calendar-year arithmetic), so leap years do not arise; the calendar date is derived from the UTC instant. The default profile is an OWNER DECISION still open (candidates: the Sun-return year of Phaladeepika, or the fixed mean sidereal year as a Pandit Ji default).

**Nakshatra boundary - genuine Phase 5 defect (RESOLVED by commit `091ca1b`; text below is the original finding, kept as history)**
- `pandit_astro_engine.nakshatra.nakshatra_position` uses `normalized // (360.0/27.0)`. At exactly representable boundaries it can assign the lower nakshatra: 39 of 81 exact-boundary tests were wrong (for example 40.0 degrees returns Krittika, not Rohini). The `near_boundary` flag is raised but the side is wrong; the standard's own arithmetic (longitude / 13 degrees 20') gives Rohini.
- No source states interval inclusivity; sources list shared endpoints. Proposed convention (a Pandit Ji standard, not a source): lower-inclusive, upper-exclusive, 360 = 0.
- Minimum correction, classified PHASE 5 PATCH REQUIRED BEFORE PHASE 7 (owner-approved and applied in `091ca1b`; standards note added in v1.4.1): compute index and pada with exact rational arithmetic on the float value (index = floor(Fraction(L) x 27 / 360), pada = floor(Fraction(L) x 108 / 360) mod 4 + 1); keep `near_boundary` unchanged. Checked in-process without writing any file: with this change all 191 existing astro-engine tests still pass, so no existing golden case changes.

**Other proposals**: exact rational arithmetic with no intermediate rounding; canonical boundary = UTC instant (integer microseconds) with Julian Day UT derived; half-open intervals [start, end); display rounding never used for period selection; local timezone is display metadata and DST never alters a computed UTC boundary. Birth-time precision model EXACT / APPROXIMATE / NOT_EVALUABLE: the input model has no precision field today; the Moon moves about 13 degrees a day, so an uncertainty interval that crosses a nakshatra boundary makes the starting lord ambiguous and the result must not be shown as exact. Rule-engine contract: astro-engine calculates and owns `DashaFacts` (system, profile IDs for balance/year-length/sub-period, starting nakshatra/pada/lord, balance and unit, period tree with UTC boundaries, current period, calculation version); the rule engine only consumes them (a later facts-model extension) and never calculates Dasha. Maraka timing: an earlier `Phases.md` Phase 9 line says "Maraka timing is owned by Phase 7" but Phase 7 does not list it; proposed correction is that Maraka timing is a later rule-engine consumer of Dasha facts, not Phase 7 scope (this doc correction is NOT yet applied).

**Verdict: PHASE 7 IMPLEMENTATION READY: NO (pending owner decisions)**. The Phase 5 boundary patch and convention are now approved, applied and recorded (`091ca1b`, standards v1.4.1). Still open: year-length default profile; balance default profile; birth-time precision field and where it lives; UTC-instant representation; leap-year and rounding policy; the Phase 6 to Phase 7 contract; the Maraka ownership correction in `Phases.md`; missing Phase 7 dependencies, exit criteria and exclusions in `Phases.md`; and the Phase 7 standards amendment (likely v1.5.0).

## 22. Repository State (history and current)

- **Current code state**: the latest code commit is `e56be0f` (Phase 7, see §25), CI run `35507588698` green (15 of 15 jobs, each inspected). Commits after it are documentation only; the current HEAD is whatever `git log` shows (verify it equals `origin/main`). Tests at that commit: astro-engine 513, rule-engine 256; standards v1.5.0. **Phase 8 (§26) then added commits `27afb4d`, `6af6112`, `7cd8887` and `f846e7e` (CI run `35639087407` green, 15 of 15 jobs, each inspected): astro-engine 788 and rule-engine 286 tests, standards v1.6.0.** **Phase 9 WP-A1/A2/A3 (§27) then added commits `31aa3b9` (CI run `35697685293` green) and `f1eb0a6` (CI run `35720123705` green, 15 of 15 jobs, each inspected): astro-engine 850 and rule-engine 286 tests, standards v1.7.0/v1.8.0.** (Earlier in this section's history: `091ca1b`, CI run `35500359836`, standards v1.4.1, astro-engine 353 and rule-engine 235 tests, no `dashas` module.)
- Earlier state, kept as history: branch `main`; HEAD `6e8eba4` = `origin/main`; working tree clean; CI green (run `35461086198`); then `81c9b08` (summary update), CI run `35462906836` green.
- Local environment notes: `pyswisseph` and the rule-engine, knowledge, agent, verification and astro-engine packages were pip-installed in editable mode during the session (needed for local test runs); nothing running in the background.
- Private research material (page-image excerpts for Sanskrit review, extraction JSON, OCR text, generators for the rule YAML) lives in the assistant session scratchpad under the OS temp directory and is NOT in the repository; it may not survive. The durable record is `research/ASTROLOGY_SOURCES.md` (Groups 1-8 and §6 source tiers and profile IDs).

## 23. Session Handoff Instructions

# NEXT SESSION — START HERE

Do not assume anything beyond this document, and re-check it against the repository first.

1. Read this `SUMMARY.md`, then verify HEAD, `origin/main`, working tree and GitHub Actions for HEAD; skim `Phases.md`, `docs/ASTROLOGY_STANDARDS.md`, `docs/ARCHITECTURE.md`, `research/ASTROLOGY_SOURCES.md`.
2. Report: repository state, which phases are complete (1-8 fully, plus Phase 9 WP-A1/A2/A3 only -- described in §27; the rest of Phase 9 is open), CI state, and any mismatch with this document.
3. Phases 7 and 8 are implemented and frozen (§25, §26); Phase 9 WP-A1/A2/A3 are implemented and frozen (§27). Do not start another phase, or another Phase 9 work package, without reading `Phases.md` and getting the owner's approval. Sections 25, 26 and 27 hold the handoffs, decisions and limitations.
4. Standing rules: cite sources honestly (image-checked vs OCR vs translation level; no Sanskrit-level claims without a qualified reviewer); never merge traditions silently; commits use the owner's identity `iamankoo <aniketraj00384@gmail.com>` with no AI attribution (CI rejects vendor names in `.md`, `.py`, `.ts`, `.tsx`, `.dart` files); do not modify Phase 5 or Phase 6 without approval.

## 24. Open Blockers Before Phase 7 (historical: documentation closure, 2026-09-20; resolved by §25)

This list was the pre-implementation blocker list. The owner then supplied the defaults and scope in the Phase 7 implementation directive, and §25 records how each item was resolved.

**Methodology decisions (open)**
1. Vimshottari balance-at-birth default profile (BPHS Ch. 46 v. 16 time-based versus longitude-based; separate profiles required).
2. Year-length default profile (no verse read states it; Phaladeepika XIX sl. 4 is an inference; separate profiles required).
3. Leap-year and rounding policy.
4. UTC-instant and Julian-day representation.
5. Birth-time precision model (EXACT, APPROXIMATE, NOT_EVALUABLE) and where the field lives (the input model has none today).
6. Phase 6 to Phase 7 contract (`DashaFacts`, owned by astro-engine, consumed by rule-engine).
7. Phase 7 standards amendment (likely v1.5.0).
8. Whether `kundli.py` `STANDARDS_VERSION` advances (see the §15 addendum).

**Roadmap and documentation mismatches found, reported and NOT fixed (`Phases.md` is the sole roadmap; edits need owner approval)**
- `Phases.md` states "Maraka timing is owned by Phase 7" in the Phase 9 module notes, but Phase 7's own list does not include it.
- `Phases.md` Phase 7 has no stated dependencies, exit criteria or exclusions. The owner's locked scope (Vimshottari only, to Pratyantar; not Ashtottari, Yogini, Chara, Narayana, Sookshma, Prana or rectification; "connect" means deterministic temporal facts and references only) exists only in this file and in the owner's instructions.
- `docs/ASTROLOGY_STANDARDS.md` §Vimshottari Dasha (Hierarchy bullet) says "and, if later required, Sookshma", which is looser than the owner's locked scope.
- `docs/ASTROLOGY_STANDARDS.md` Phase 1 checklist line for Vimshottari reads "implemented Phase 7"; it names the responsible phase (the same wording is used for Phases 9-11) and does not mean Phase 7 exists.
- The Phase 7 deliverable "connect Dasha with Houses, Lords, Planets, Yogas, Career, Marriage, Education, Finance, Relationships" overlaps later phases (Phase 12 knowledge, Phase 17 life-domain intelligence) unless it is read as facts and references only. That is the owner's stated reading, but it is not in `Phases.md`.
- §8 of this file records a language requirement that the project owner's later locked wording refines (the AI natively understands English, Hindi and Hinglish with no AI language mode; only the UI language is a setting, and it never changes because of what the user types). It was not changed here (outside this task's scope) and should be reconciled before Phase 15 and Phase 19 work.

**Source registry status (`research/ASTROLOGY_SOURCES.md`)**
- BPHS Ch. 46 v. 2-16: image-checked (printed pp. 505-507), translation level.
- BPHS Ch. 51 and Ch. 61 sub-period rules: OCR-level in the registry. A prior report says they were image-checked, but no page-image artifact was preserved, so the registry was not upgraded.
- Phaladeepika XIX sl. 2-4 and the Uttara Kalamrita printed p. 142 worked example: matched against the preserved OCR text and recorded at OCR-TRANSLATION level; the earlier image-check claim for Phaladeepika is not preserved and was not repeated. No Sanskrit-level verification exists for any Vimshottari statement.

## 25. Phase 7 — Vimshottari Dasha Engine — Completion and Handoff

### A. Completion status
- Phase 7 is complete within its defined scope: **Vimshottari Mahadasha → Antardasha → Pratyantar**, as deterministic temporal facts with provenance.
- Branch `main`. Starting commit `2437bcc`. Final implementation and summary commit before this handoff: `d51ad91`. (This handoff refresh is a further documentation-only commit; verify the current HEAD with `git log`.)
- Commits:
  - `ebc98d2`: documentation, standards v1.5.0, Phase 7 roadmap fields, architecture note, source-registry profile table.
  - `7eaada5`: astro-engine `dashas` package, version 0.4.0, README and tests.
  - `e56be0f`: rule-engine EvidenceBundle integration, version 0.7.0, fixtures and tests.
  - `d51ad91`: `SUMMARY.md` and handoff refresh.

### B. Implemented functionality
- Birth Nakshatra, Pada and starting Mahadasha lord; birth Mahadasha balance (elapsed and remaining fraction, remaining duration).
- Mahadasha, Antardasha and Pratyantar generation, as a flat ordered period tree (`parent_id`, `path`, stable period IDs, UTC boundaries), with exact containment, no gaps and no overlaps.
- Lookup of the periods owning an instant (historical, current and future; the caller supplies "now": the pure calculator and lookup never read the system clock), transition queries, window queries, queries by planetary lord.
- UTC is the canonical time; exact rational microsecond arithmetic; half-open intervals `[start, end)`.
- Precision contract (EXACT, APPROXIMATE, NOT_EVALUABLE with an uncertainty interval), structured statuses with reason codes, labelled provenance.
- The service facade (`DashaCalculationService`) is the part that calls the existing astronomical service (Moon longitude and time resolution, including the Moon at the ends of an uncertainty interval). The pure calculator (`calculate_vimshottari`) has no ephemeris, clock or I/O.
- EvidenceBundle integration (section G). Code: `services/astro-engine/src/pandit_astro_engine/dashas/` (`constants.py`, `profiles.py`, `models.py`, `vimshottari.py`, `lookup.py`, `service.py`) and `services/rule-engine/src/pandit_rule_engine/dasha_evidence.py` plus the additive `dasha` section in `bundle.py` and `engine.py`.

### C. Methodology decisions (approved engineering decisions, not universal claims about classical astrology)
- Default balance profile `DASHA_STANDARD_V1_BALANCE_LONGITUDE`: the longitude fraction is an **engineering convention**. The source-based alternatives `DASHA_BPHS_KAPOOR_46_16_BALANCE_TIME` and `DASHA_PHALADEEPIKA_SASTRI_XIX_3_BALANCE` are registered but **inactive** (not approximated). The balance method remains a documented source conflict.
- Default year profile `YEAR_365_2425_FIXED_DAY`: 365.2425 mean solar days, exactly 31,556,952 seconds, with no leap-year calendar arithmetic. `YEAR_365_25_FIXED_DAY` and `YEAR_360_FIXED_DAY` are selectable; `YEAR_SIDEREAL_365_256363_FIXED_DAY` and `YEAR_SUN_RETURN_PHALADEEPIKA_XIX_4` are documented and inactive.
- UTC canonical; exact rational microseconds; each boundary floored once to a whole microsecond.
- Intervals are half-open `[start, end)`; the later period owns a shared boundary; the timeline end is exclusive.
- An approximate birth time requires an explicit uncertainty interval. If the interval reaches a Nakshatra boundary the result is `NOT_EVALUABLE(starting_lord_ambiguous)`. No birth-time rectification is performed.
- Nested sub-period formula (profile `DASHA_SUBPERIOD_PROPORTIONAL_FULL_PARENT_V1`): child duration = full nominal parent duration × child lord years ÷ 120.

### D. Birth-balance sub-period decision (approved by the owner)
- Antardasha and Pratyantar of the birth Mahadasha are calculated from the **full, untruncated** Mahadasha; they are not scaled to the remaining birth balance.
- Sub-periods that ended before birth are removed; the sub-period containing birth is truncated at birth, keeps its `nominal_start_utc`, and is marked `truncated_at_birth`.
- This is an **engineering interpretation of the implementation directive**; it is not a claim that all classical traditions subdivide the birth-balance period this way (the sources read do not state it). It has its own profile ID and is explained in standards v1.5.0.

### E. Standards-version decision
- `kundli.py` keeps `STANDARDS_VERSION = "1.3.0"`. The v1.4.1 Nakshatra boundary change corrected an implementation defect against the existing 1.3.0 text (which already said to divide by 13°20′), so the constant was not advanced.
- Phase 7 methodology and results are recorded under standards **v1.5.0**. Do not change the Kundli constant unless a future standards amendment requires it.

### F. Source governance
- Provenance labels recorded in every result: `source_supported`, `translator_note`, `inference`, `engineering_convention`, `derived_calculation`, `unresolved_conflict`.
- No unsupported image-verification claim was added. BPHS Ch. 51 and Ch. 61 stay **OCR-level** in `research/ASTROLOGY_SOURCES.md` (an earlier report of an image check has no preserved page images). Do not upgrade any evidence tier without page-image verification.
- The Uttara Kalamrita p. 142 worked example is an independent **consistency check** only: the engine's balance agrees with it to within about a day under the 360-day profile. That agreement is not proof of classical correctness.

### G. Phase 6 integration
- `RuleEngine.evaluate_kundli(kundli, dasha_facts)` accepts optional astro-engine Dasha facts (JSON form) and records them in an optional `dasha` section of the EvidenceBundle.
- Bundles without Dasha facts serialize and hash exactly as before; the bundle schema version is unchanged.
- `requires_dasha` remains reserved: no shipped rule emits it, and no shipped rule reads Dasha facts.
- No Phase 4, 5 or 6 module was modified in behaviour (`bundle.py` and `engine.py` changed additively).

### H. Testing and performance (as reported at completion; run locally unless stated)
- astro-engine 513 passed (353 existing + 160 new); rule-engine 256 passed (235 existing + 21 new); server 5 passed with `PYTHONPATH=src`.
- `ruff format`, `ruff check` and `mypy` clean for the astro-engine and rule-engine packages; the other domain packages' ruff and tests passed.
- Full three-level timeline about 19 ms (about 885 nodes, about 0.7 MB as JSON); Mahadasha-only about 0.3 ms; 1,000 lookups about 26 ms (one development machine).
- Property-style checks are seeded random loops; no property-testing library was added.
- The skipped rule-engine integration test (section I) was run locally, not in the rule-engine CI job.

### I. CI records
- https://github.com/iamankoo/Pandit-Ji/actions/runs/35507588698 (commit `e56be0f`) and https://github.com/iamankoo/Pandit-Ji/actions/runs/35507771059 (commit `d51ad91`): 15 of 15 jobs success in each; every job and step was inspected individually.
- The conditional "install domain services" step is skipped in every job except `server`, by design.
- `services/rule-engine/tests/test_dasha_integration.py` (real astro-engine facts) is **skipped in the rule-engine CI job** because astro-engine is not installed there; it was run locally.
- A local `mypy` run on `server` (with `PYTHONPATH=src`, package not installed) reported 2 errors in the untouched `health.py`; the CI server mypy step passed.
- The CI run for the handoff-refresh commit that follows `d51ad91` is not recorded here; check it with `gh run list`.

### J. Known limitations and deferred work
- Scope ends at Pratyantar. Not implemented: Sookshma, Prana, other Dasha systems, birth-time rectification.
- Life-domain interpretation and Maraka interpretation are not part of Phase 7 (later rule-engine and life-domain phases consume the facts).
- The source-alternative balance profiles are registered but inactive.
- The approximate-time first-Mahadasha end range is an envelope from the interval endpoints and the nominal instant, not a proven bound; the Moon range for an approximate time uses Julian-day shifts of a few tens of microseconds precision.
- The Independence-chart test is an internal consistency test, not an external golden reference.
- `SUMMARY.md` §8 still predates the locked language rule (English, Hindi and Hinglish understood natively; only the UI language is a setting) and was left out of scope; reconcile it before Phase 15 and Phase 19 work.

### K. Tomorrow's resume instructions
1. Read `Phases.md` first (authoritative roadmap).
2. Read this `SUMMARY.md` completely.
3. Inspect the latest Git commit, `origin/main` and the working tree.
4. Do not restart Phase 7 or rewrite the completed implementation. Treat Phase 7 as **frozen** unless an explicit correction or amendment is requested.
5. Before starting any new phase, follow the established Git workflow: commit and push the existing state, cross-check the relevant section of `Phases.md`, prepare a detailed implementation prompt, and report CI results per job.
6. Make no assumption about the next phase until the user explicitly selects it.

Last session ended after Phase 7 completion, validation, and handoff. Resume from this summary after the user gives the next instruction.

## 26. Phase 8 — Transit / Gochar Engine — Methodology, Implementation and Handoff

**Status: implemented, committed, pushed and CI-verified.** Base commit `db01cc8`. Phase 8 commits, in order: `27afb4d` docs: lock phase 8 methodology (standards v1.6.0) and roadmap; `6af6112` feat: add transit and gochar engine (phase 8) to astro-engine; `7cd8887` feat: record transit facts in the rule-engine evidence bundle; `f846e7e` docs: record phase 8 completion in the project summary. `origin/main` was verified equal to `f846e7e0955050acf45488a7edcfbab16ee995e8` after the push. The owner approved the commit at Approval Gate 2 and authorized the push conditional on a completion audit, which passed (see section I).

### A. Workflow followed
Research (Step 2 and 2B) -> Approval Gate 1 (all nine recommendations approved) -> documentation lock -> implementation -> tests -> validation -> Approval Gate 2. Earlier approvals by the owner: MOON_SIGN default reference; Moon-from-Moon kept as an explicit source conflict; Vedha structural and Phaladeepika-specific; Ashtakavarga scoring excluded; Sade Sati labelled MODERN_TRADITION; events as engineering conventions.

### B. Research summary and source confidence (all translation level; no Sanskrit-level verification)
- **Page-image verified (IMAGE-TRANSLATION)**: Phaladeepika Ch. XXVI sl. 1-8 (printed pp. 286-288) and sl. 22-23 (p. 295); Brihat Jataka Ch. IX sl. 1-7 (pp. 198-202); Brihat Samhita Adhyaya CIV sl. 4-5 (p. 770); BPHS Vol II Ch. 66 v. 20-22 (p. 847) and Ch. 72 v. 29-31 (p. 904).
- **OCR only**: the rest of BPHS Ch. 66 dot lists, Ch. 70 v. 1-14, Ch. 72 v. 1-28, Brihat Samhita CIV sl. 39-61, Uttara Kalamrita (probe), Jataka Parijata XIII v. 60 with its Sanskrit commentary (unreviewed).
- **Not read**: BPHS Ch. 67-69 mechanics and Ch. 71, Brihat Samhita CIV sl. 6-38, any Sanskrit-level review.
- A Tier 5 claim that Brihat Samhita Ch. 9-17 contains Gochara, Vedha and Sade Sati was **not supported** (the transit chapter is Adhyaya CIV and its verses contain neither Vedha nor Sade Sati).

### C. Locked methodology (`docs/ASTROLOGY_STANDARDS.md` v1.6.0, TR-01 to TR-15; evidence labels `source_supported`, `translator_note`, `inference`, `engineering_convention`, `derived_calculation`, `unresolved_conflict`, `modern_tradition`, `engineering_evidence`)
- Facts and provenance only: no interpretation, verdict, remedy, alert, Ashtakavarga scoring, degree or orb contacts, Dhaiya, Ashtama or degree-based Sade Sati (reserved IDs only), HTTP endpoints or database tables.
- **Reference**: `TRANSIT_REF_MOON_SIGN` (source-supported); optional `TRANSIT_REF_LAGNA_SIGN` positional fact (engineering convention).
- **Favourable sets**: four separate readings (Phaladeepika, Brihat Samhita, Brihat Jataka, BPHS-derived as `derived_calculation`). The six non-Moon planets agree; **Moon from the Moon conflicts on houses 5, 6, 9** and returns `NOT_EVALUABLE(reading_ambiguous)` with every reading kept. Rahu and Ketu are single-source (Phaladeepika "like the Sun") and never consolidated (`NOT_EVALUABLE(node_reading_single_source)`).
- **Vedha**: `GOCHARA_VEDHA_PHALADEEPIKA_SASTRI_XXVI_3_8`, structural occupancy of transiting planets in the Vedha sign; exceptions Sun/Saturn and Moon/Mercury; a node alone in the Vedha sign gives `NOT_EVALUABLE(node_participation_unspecified)`; node subjects give `not_specified_by_source`; the Venus sl. 8 wording anomaly is preserved as a warning.
- **Contacts**: sign-based conjunction and Phase 5 graha drishti only. **Events**: sign ingress (with backward re-entry), retrograde and direct stations, opt-in Nakshatra ingress.
- **Sade Sati**: `SADE_SATI_SIGN_BASED_MODERN_V1` (`modern_tradition`), segments and episodes; an episode is flagged `retrograde_reentry_of_previous_episode` when retrograde motion bounds the gap at either end (found necessary during implementation: Saturn's 2029 re-entry into Aries is by retrograde motion after a forward exit).
- **Time and precision**: UTC canonical; half-open `[start, end)`; bisection to 1e-8 day on a scan grid anchored to absolute multiples of the step (so an event's instant does not depend on the window; found necessary when adjacent windows disagreed by 18 ms for a station); scan steps Moon 0.25, Mercury 0.5, Venus 1, Sun and Mars 2, Jupiter, Saturn and nodes 5 days, with a station split so a double crossing inside one step is not missed; limits 200 years and 50,000 events.
- **Versions**: standards 1.6.0 (Phase 8 results record it), astro-engine 0.5.0, rule-engine 0.8.0; the Phase 5 Kundli constant stays 1.3.0 and Phase 7 results keep 1.5.0.

### D. Unresolved source conflicts (preserved; no winner chosen)
Moon from the Moon (Brihat Jataka 5th; Phaladeepika, Brihat Samhita and the BPHS-derived reading 6th; BPHS-derived also 9th); Rahu and Ketu favourable houses (single source, a possible opposite reading in an unreviewed Jataka Parijata commentary quote); Vedha (single verse-level source; Venus wording anomaly); sign-part effectiveness (Phaladeepika thirds versus Brihat Samhita halves, not used); Gochara/Vedha versus Ashtakavarga scoring (BPHS Ch. 72 v. 30-31 treats Ashtakavarga as paramount; not merged, Phase 9). Registry: `research/ASTROLOGY_SOURCES.md` Group 9 additions and section 6.4.

### E. What was implemented
- `services/astro-engine/src/pandit_astro_engine/transits/` (`constants`, `profiles`, `models`, `positions`, `events`, `evaluate`, `sade_sati`, `calculator`, `service`); an additive public `SWE_NODE_ID` constant in `ephemeris.py` (no Phase 4 behaviour changed); `TransitCalculationService` with `calculate`, `snapshot`, `events` and `sade_sati`; `NatalReference.from_kundli`.
- `services/rule-engine`: `transit_evidence.py`, an additive optional `transit` section in `EvidenceBundle` (omitted when absent, so earlier bundles serialize and hash exactly as before), `RuleEngine.evaluate_kundli(kundli, dasha_facts, transit_facts)`.
- Documentation: `Phases.md` Phase 8 block, `docs/ASTROLOGY_STANDARDS.md` v1.6.0, `docs/ARCHITECTURE.md` (transit interface, cache key, section 31 wording), `research/ASTROLOGY_SOURCES.md`, service READMEs, this section.
- Fixtures: `services/astro-engine/tests/fixtures/horizons_transit_reference.json` (42 JPL Horizons samples, retrieved 2026-09-21) and four rule-engine transit fact fixtures.

### F. Validation (run locally before the commits; CI results are in section I)
- astro-engine **788 passed** (513 existing + 275 new); rule-engine **286 passed** (256 existing + 30 new); packages, agent, knowledge, verification and server tests unchanged and passing (server 5 with `PYTHONPATH=src`); `ruff check`, `ruff format --check` and `mypy` clean for every component except the known local server `mypy` result (2 errors in the untouched `health.py`, `psycopg` not installed locally; the CI server job installs it).
- The repository-integrity greps (forbidden service names, vendor names in `.md` and `.py`, no `.env`) were run locally with the CI patterns and found nothing.
- Independent evidence: the Swiss Ephemeris tropical longitude of date compared with JPL Horizons on 42 samples (maximum 0.26 arcsec Sun, 0.19 Mars, 0.15 Mercury and Venus, 0.38 Jupiter, 0.27 Saturn, 4.78 Moon; Moshier mode). Saturn's ingress and station **dates** in 2019-2026 match widely published dates; published ingress **times** disagree by hours between Tier 5 pages, so they are not used.
- Performance (development machine, Moshier): 90 years of Saturn, Jupiter and Rahu sign ingress in about 1 s; 20 years of all nine bodies with ingress and stations in about 9 s; 10 years of the Moon with sign and Nakshatra ingress in about 9 s.

### G. Known limitations and deferred work
- Moshier mode unless Swiss Ephemeris data files are configured; the Lahiri ayanamsa value and the sidereal frame are not independently verified (the ayanamsa implied by the sidereal calculation differs from `get_ayanamsa_degrees` by up to about 15.6 arcsec, about 1.5 hours of Saturn's motion; not investigated); UT1-UTC is not modelled.
- Station instants are limited by the numerical noise of the ephemeris speed near zero (milliseconds), not by the bisection tolerance.
- Vedha and the node readings are single-source; the Moon-from-Moon conflict needs qualified Sanskrit review; nothing is verified at Sanskrit level.
- The rule-engine integration test with real astro-engine facts runs only where both services are installed (skipped in the rule-engine CI job, as for Phase 7).
- Not implemented (by decision): interpretation of any kind, Ashtakavarga scoring (Phase 9), Sarvatobhadra, Latta, degree or orb contacts, Dhaiya, Ashtama, degree-based Sade Sati, HTTP endpoints, database tables and caching (Phase 18).
- Roadmap and documentation mismatches found and handled with the owner's approval: `Phases.md` Phase 8 had no dependencies, inputs, outputs, exclusions or exit criteria (added); `docs/ARCHITECTURE.md` §31 said "transit-to-natal angles" (reworded to sign-based contacts). Still open from before: `SUMMARY.md` §8 predates the locked language rule (English, Hindi and Hinglish understood natively; only the UI language is a setting) and should be reconciled before Phase 15 and Phase 19.

### H. Resume instructions
1. Read `Phases.md`, then this section. 2. Phase 8 is committed, pushed and CI-verified (section I); treat it as frozen unless the owner requests a correction. 3. Do not restart the Phase 8 research or methodology. 4. After any future push, check GitHub Actions for **each job and its steps** individually before saying the jobs passed. 5. Do not start Phase 9 without the owner's selection.

### I. Completion audit and verified CI (2026-09-22)
- **Audit before the push** (owner's conditional authorization): every approved requirement was mapped to implementing code and at least one existing test (snapshot, historical and future instants, Moon-sign default, optional Lagna fact, per-source favourable readings, Vedha table and exceptions, Moon-from-Moon conflict, Rahu and Ketu single-source handling, node-participation handling, sign ingress, backward ingress and re-entry, stations including a double crossing inside one step, opt-in Nakshatra ingress, sign-based graha-drishti contacts, Sade Sati segments, episodes and re-entry flags, half-open and window-boundary behaviour, profile validation, determinism and JSON round trip, provenance labels, accuracy disclosure, the additive bundle section, the 200-year and 50,000-event limits, the Horizons fixture). All were COMPLETE; the exclusions (Ashtakavarga scoring, interpretation, remedies, verdicts, HTTP endpoints, database tables and migrations, Dhaiya, Ashtama, 45-degree Sade Sati, degree or orb contacts, rectification) were checked by a diff and source search and found only in negating text or as reserved profile IDs that return `UNSUPPORTED_PROFILE`.
- **Bundle backward compatibility, verified against the Phase 7 code**: the bundle built by the `db01cc8` rule-engine source and by the current source were compared for a real Kundli, with and without Dasha facts. They were identical once the `rule_engine_version` stamp (0.7.0 versus 0.8.0, which is part of the hash) was excluded. Existing bundles therefore serialize the same and hash differently only through that version stamp, as at Phase 7.
- **Verified CI**: run `35639087407` (event `push`, commit `f846e7e0955050acf45488a7edcfbab16ee995e8`), https://github.com/iamankoo/Pandit-Ji/actions/runs/35639087407 : status completed, conclusion success. All 15 jobs succeeded, each inspected with its steps, and the GitHub check-runs API independently reports 15 check runs, all `success`: Docker build and compose config; Flutter apps/mobile; TypeScript apps/web, apps/admin and packages/ui; Repository integrity; Python packages/contracts, packages/shared, services/astro-engine, services/rule-engine, services/agent, services/knowledge, services/verification, server and infrastructure/migrations.
- **Steps**: no step failed. In `services/astro-engine` and `services/rule-engine` the Ruff lint, Ruff format check, mypy and pytest steps all succeeded, and in Repository integrity the forbidden-service-name, attribution and `.env` checks all succeeded. Skipped steps, all by design and the same pattern as Phase 7: "Install domain services" in every Python job except `server`; Lint, Format check and Test in `packages/ui`; mypy and pytest in `infrastructure/migrations` (no source or tests).
- **Not visible from step conclusions**: the rule-engine integration test that uses real astro-engine facts skips itself inside the rule-engine pytest step (astro-engine is not installed in that job); it ran locally.
- **Environment-dependent items**: the local server `mypy` reports 2 errors in the untouched `health.py` because `psycopg` is not installed on the development machine; the CI server job (with the domain services and its dependencies installed) passed.
- **Documentation wording corrected after the push**: the commit-status statements in this file and the "await Approval Gate 2" wording in the `docs/ASTROLOGY_STANDARDS.md` v1.6.0 change-log entry described the state before the commit and were stale once the commits existed. They are corrected in the documentation commit that follows the CI verification.

## 27. Phase 9 WP-A1/A2/A3 — Ashtakavarga Engine (Bhinna/Sarva, Reductions, Pinda Sadhana) — Completion and Handoff

**Status: implemented, committed, pushed and CI-verified.** This covers three specific work packages of Phase 9 ("Advanced Astrology Systems") only: **WP-A1** (Bhinnashtakavarga and Sarvashtakavarga across four independent source profiles), **WP-A2** (Trikona and Ekadhipatya Shodhana reductions) and **WP-A3** (Pinda Sadhana: Rasi, Graha and Yoga Pinda). **Phase 9 as a whole is not complete** — Jaimini (WP-B), partial/degree Drishti (WP-C), Western (WP-D), KP (WP-E), Shadbala (WP-F), Ayurdaya and the scope-undefined systems (Chinese, Vastu, Feng Shui, Tarot, Lal Kitab, Nadi, generic Horary) all remain open, per the Phase 9 Gate 1 traceability matrix; none of them was implemented or approved by this work.

Base commit before this work: `965c8d6` (Phase 8, §26). Commits, in order: `31aa3b907a0cf820d276d59c3228420e114f52df` (WP-A1) and `f1eb0a600cef98589aed4134e32e3e95a49bbea4` (WP-A2/A3). `origin/main` verified equal to `f1eb0a6` after the second push.

### A. Workflow followed
Two full research-first cycles, each independently gated: **WP-A1** — page-image research (BPHS Ch. 66, Brihat Jataka Ch. IX, Phaladeepika Ch. XXIII) -> a Gate 1 methodology report -> the owner found an internal inconsistency between an early summary figure and the underlying data, requiring a complete independent reconciliation audit of every comparison count before re-approval -> implementation -> tests -> commit approval -> push approval -> CI verification. **WP-A2/A3** — page-image research (BPHS Ch. 67-69) -> a methodology report classifying every formula's verification status -> approval -> implementation -> a focused owner-directed review that found a genuine, unresolved internal contradiction in one source table -> conservative `NOT_EVALUABLE` handling (not a silent choice) -> re-validation -> commit approval -> push approval -> CI verification.

### B. Methodology summary (`docs/ASTROLOGY_STANDARDS.md` v1.7.0 AV-01 to AV-08, v1.8.0 AV-09 to AV-13)
- **Four independent profiles, no default, no unqualified "BPHS"**: `ASHTAKAVARGA_BRIHAT_JATAKA_SASTRI_IX_1_7`, `ASHTAKAVARGA_PHALADEEPIKA_SASTRI_XXIII_3_9`, `ASHTAKAVARGA_BPHS_GRID_KAPOOR_66`, `ASHTAKAVARGA_BPHS_VERSE_KAPOOR_66`. The last two exist separately because BPHS's own printed dot grid and its own printed verse-translation list disagree with each other on 5 of 56 cells inside the same chapter.
- **56-cell cross-source register**: 47 of 56 (chart, contributor) cells agree across all four readings; the remaining 9 are classified and preserved verbatim (`ashtakavarga.constants.CROSS_TABLE_CONFLICTS`), no winner chosen; two carry translator footnotes (Varahamihira, Parasara) kept as `translator_note`.
- **Reductions and Pinda (WP-A2/A3) are BPHS-profile-only**: no source read gives Brihat Jataka or Phaladeepika a reduction procedure at all. Modelled as a fully separate, additive `AshtakavargaReductionRequest`/`AshtakavargaReductionFacts` pair, so WP-A1's own contract is byte-for-byte unchanged (verified: zero `git diff` on `calculator.py`, `profiles.py` and every WP-A1 fixture/test across both commits; WP-A1's 30 tests re-confirmed passing, individually, after WP-A2/A3 landed).
- **Two source conflicts are deliberately left `NOT_EVALUABLE`, never guessed**:
  - Graha Pinda's **Mercury multiplier** (the printed Grahamana Chakra table says 5, the verse says 6; the chapter's own worked example never isolates a Mercury-only nonzero-valued sign to arbitrate) -> `NOT_EVALUABLE(mercury_multiplier_conflict)`. (Sun, Mars, Moon and Saturn's multipliers *are* resolved, by direct arithmetic proof: substituting the verse's "6" into the chapter's own worked example gives a Graha Pinda of 56, not the source's own stated 48 — only "5" reproduces 48 exactly.)
  - Ekadhipatya Shodhana's **"exactly one sign occupied, both Trikona-corrected values equal"** case — BPHS's own printed "abstract illustration" (Ch. 68 p. 876) answers this identical rule shape two different ways in the same table: its Capricorn/Aquarius pair keeps the occupied sign unchanged; its Gemini/Virgo pair, under the same shape, prints as if both were zeroed. This is a genuine, source-internal contradiction, not a translation-quality question page-verification can settle. On the owner's explicit direction, it returns `NOT_EVALUABLE(ekadhipatya_equal_value_conflict)`; both printed readings are preserved verbatim with page citations on a dedicated `EkadhipatyaConflict` record, and because Rasi Pinda sums all 12 signs, the *entire* affected chart's Rasi, Graha and Yoga Pinda are withheld, never a partial total. **Confirmed live, not just hypothetically**: the shipped worked-example fixture's own Ascendant chart genuinely hits this exact case (Scorpio/Aries, both value 2).
- Every resolved formula (Trikona Shodhana: subtract each trine group's minimum from all three; Ekadhipatya's three unambiguous cases; Rasi and the six resolved Graha multipliers; Yoga Pinda = Rasi + Graha) is verified exactly against BPHS's own worked examples (Ch. 67 pp. 868-869, Ch. 68 p. 876, Ch. 69 pp. 879-880), using one natal chart reconstructed by an independent brute-force search against the already-shipped WP-A1 calculator (not invented, not assumed).

### C. What was implemented
- `services/astro-engine/src/pandit_astro_engine/ashtakavarga/`: WP-A1's `constants`, `profiles`, `models`, `calculator`, `service`; WP-A2/A3's additive `reductions.py`, `pinda.py`, and additive models (`ChartReduction`, `PindaResult`, `EkadhipatyaConflict`, `GrahaPindaContribution`, `GrahaPindaStatus`/`Reason`) plus the `calculate_reductions` / `from_kundli_reduction_request` service methods.
- Fixtures (all independently source-derived, none generated by the implementation under test): `ashtakavarga_source_comparison.json` (the full 56-cell register), `ashtakavarga_brihat_jataka_worked_example.json`, `ashtakavarga_bphs_reduction_pinda_worked_example.json`.
- Documentation: `docs/ASTROLOGY_STANDARDS.md` v1.7.0 and v1.8.0 (§Ashtakavarga standards, AV-01 to AV-13); `research/ASTROLOGY_SOURCES.md` Groups 10 and 11 plus §6.5; `services/astro-engine/README.md`.
- **Explicitly not implemented, by decision**: any `EvidenceBundle` integration (deferred to a separate approval gate); Jaimini or any other Phase 9 work package; `Phases.md` was not modified.

### D. Validation
- astro-engine **850 tests passing** (818 pre-existing + 32 new for WP-A1/A2/A3 combined; WP-A1's own 30 tests individually re-confirmed passing after WP-A2/A3 landed). rule-engine **286 tests passing, unchanged** (not touched by this work at all). Ruff lint, Ruff format check and mypy strict all clean for both commits.
- **CI run `35720123705`** (commit `f1eb0a6`, WP-A2/A3): 15 of 15 jobs green, every job's steps individually inspected (no failed step; only the established by-design skips: "Install domain services" outside `server`; `packages/ui` Lint/Format/Test; `infrastructure/migrations` mypy/pytest), independently cross-checked against the GitHub check-runs API (15/15 `success`).
- **CI run `35697685293`** (commit `31aa3b9`, WP-A1 alone): also 15 of 15 green, verified the same way.

### E. Known limitations and deferred work
- Mercury's Graha Pinda multiplier and the Ekadhipatya equal-value case remain genuinely unresolved source conflicts, by design — see §B. Neither blocks the rest of the implementation; they surface as `NOT_EVALUABLE` results with a machine-readable reason and, for the Ekadhipatya case, both printed readings preserved.
- WP-A2 reductions (and Pinda) are **not** yet integrated into the rule-engine `EvidenceBundle`; a research/design proposal exists (delivered to the owner, not yet approved or implemented) but no code change has been made toward it.
- BPHS Ch. 71 (Ashtakavarga-based longevity) is out of scope under the product's Ayurdaya policy (lifespan/death-timing claims); Ch. 70 and Ch. 72 v. 3-5 (interpretive judgments) are out of scope under the project's no-interpretation boundary.
- The rest of Phase 9 (Jaimini WP-B, partial/degree Drishti WP-C, Western WP-D, KP WP-E, Shadbala WP-F, Ayurdaya, and the scope-undefined systems) remains open; a research/design proposal for WP-B exists (delivered to the owner, not yet approved or implemented).

### F. Resume instructions
1. Read `Phases.md`, then this section. 2. WP-A1/A2/A3 are committed, pushed and CI-verified (commits `31aa3b9`, `f1eb0a6`); treat them as frozen unless the owner requests a correction. 3. Do not restart their research or methodology. 4. After any future push, check GitHub Actions for **each job and its steps** individually before saying the jobs passed. 5. Do not begin `EvidenceBundle` integration or WP-B Jaimini implementation without a separate, explicit approval gate for each — research/design proposals for both exist but are not implementation approvals. 6. Do not start any other Phase 9 work package without the owner's selection.

## 28. Phase 9 WP-EB — EvidenceBundle Ashtakavarga Integration — Completion and Handoff

**Status: implemented, committed, pushed and CI-verified.** This integrates the already-locked WP-A1/A2/A3 Ashtakavarga facts (§27) into the rule-engine `EvidenceBundle` as one additive, optional `ashtakavarga` section, following the exact architecture already established for Dasha (Phase 7, §25) and Transit (Phase 8, §26). **It does not implement WP-B Jaimini or any other Phase 9 work package.**

Base commit before this work: `c6be7c3` (§27 documentation commit). Commit: `475c14a0fc316a2b3c59b8bead4b230107729b02`. `origin/main` verified equal to `475c14a` after the push.

### A. Workflow followed
Architecture audit (existing `bundle.py`, `engine.py`, the Dasha/Transit adapter and evidence-bundle pattern, existing fixture/test conventions) -> adapter design following the caller-selected-profile decision (no implicit default, no silent multi-profile merge) -> implementation -> real-JSON inspection against the actual astro-engine output caught and fixed four issues before they became live risks (a field-name mismatch that `extra="ignore"` would have silently swallowed, a missing source-reference field, missing per-contributor cell detail, and nested validation errors that bypassed the intended `FactsError` wrapping) -> one test failure (the adapter's own docstring contained a literal `pandit_astro_engine` substring, which also broke the pre-existing repository-wide source-purity guard test) found and fixed -> full validation -> documentation -> commit -> push -> CI verification, job by job.

### B. Methodology summary (`docs/ASTROLOGY_STANDARDS.md` v1.9.0 AV-14 to AV-18)
- **Transport-only boundary preserved**: the new `pandit_rule_engine.ashtakavarga_evidence` adapter performs no astrology computation; it only re-shapes and validates already-computed astro-engine JSON, exactly like the Dasha and Transit adapters. It does not import `astro-engine` (verified against the existing repository-wide source-purity test, `test_source_never_calls_astronomy_network_or_the_other_services`).
- **No implicit default profile, no silent merge**: unlike Dasha and Transit (one locked profile each), Ashtakavarga has four profiles with no default (§27 AV-02). The caller selects exactly one profile per bundle build and supplies its own already-computed `AshtakavargaFacts`; a caller wanting more than one profile's evidence builds more than one bundle. The static 56-cell `CROSS_TABLE_CONFLICTS` cross-source register is build-time registry data, never copied into a per-Kundli bundle.
- **Conflicts preserved verbatim, never resolved by the adapter**: every WP-A1/A2/A3 `NOT_EVALUABLE` status and reason code (`lagna_unavailable`, `mercury_multiplier_conflict`, `multiple_occupants_unsupported`, `ekadhipatya_equal_value_conflict`) and both `EkadhipatyaConflict` readings with their page-level provenance are copied unchanged. A chart's reduction map or Rasi/Graha/Yoga Pinda is copied only when astro-engine itself marks it resolved — the adapter enforces the same all-or-nothing contract astro-engine does; a malformed "partial success" cannot be constructed (enforced by Pydantic validators on `ChartReductionRecord` and `PindaRecord`).
- **Backward compatibility**: the `ashtakavarga` field is additive and optional; `_omit_absent_sections` drops it when `None`, so a bundle built without Ashtakavarga facts serializes and hashes byte-for-byte identically to before this change (proven by a regression test comparing an explicit `ashtakavarga=None` build against one that omits the parameter entirely). Adding the section changes the canonical JSON and hash deterministically; a success result and a `NOT_EVALUABLE` result never collapse to the same hash (both proven by dedicated tests).

### C. What was implemented
- `services/rule-engine/src/pandit_rule_engine/ashtakavarga_evidence.py` (new): the adapter, its record models (`ProfileRecord`/`SourceReferenceRecord`, `BhinnaChartRecord`/`SignCountRecord`/`ContributorMarkRecord`, `SarvaRecord`, `ChartReductionRecord`/`EkadhipatyaConflictRecord`, `PindaRecord`/`GrahaPindaContributionRecord`, top-level `AshtakavargaEvidence`), and `ashtakavarga_evidence_from_facts(facts, reduction_facts=None)`.
- `bundle.py`: additive optional `ashtakavarga` field on `EvidenceBundle`, wired into `_omit_absent_sections` and `build_bundle`.
- `engine.py`: `RuleEngine.evaluate()` and `evaluate_kundli()` accept optional `ashtakavarga`/`ashtakavarga_facts` and `ashtakavarga_reduction_facts` parameters; the reduction facts are ignored unless the base facts are also supplied.
- 6 fixtures generated from real astro-engine service calls (`services/rule-engine/tests/fixtures/ashtakavarga/`), including genuinely-triggered `NOT_EVALUABLE` cases for all three conflict types (Ekadhipatya equal-value, Mercury multiplier, multi-occupant) — none hand-written or guessed.
- 31 new tests: `test_ashtakavarga_evidence.py` (22 unit tests: per-profile export, validation rejection, conflict preservation, determinism) and `test_ashtakavarga_integration.py` (9 tests: backward compatibility, hash behavior, the transport-boundary check, and 3 real end-to-end astro-engine-to-bundle tests).
- Documentation: `docs/ASTROLOGY_STANDARDS.md` v1.9.0 (AV-14 to AV-18); `services/rule-engine/README.md` (new "Ashtakavarga evidence (Phase 9 WP-EB)" section, matching the existing Dasha/Transit sections); `services/rule-engine` version bumped `0.8.0` -> `0.9.0` (`_version.py`, `pyproject.toml`), matching the precedent set by the Dasha and Transit integrations.
- **Explicitly not implemented, by decision**: any rule reading Ashtakavarga facts; WP-B Jaimini or any other Phase 9 work package; `Phases.md` was not modified.

### D. Validation
- rule-engine **317 tests passing locally** (286 pre-existing + 31 new), astro-engine **850 tests passing, unchanged** (confirmed via an empty `git diff --stat -- services/astro-engine`). Ruff lint, Ruff format check and mypy strict all clean.
- **CI run `35726783964`** (commit `475c14a`): 15 of 15 jobs green, every job's steps individually inspected (no failed step; only the established by-design skips already recorded for prior phases). Independently cross-checked against the GitHub check-runs API (15/15 `success`). The `services/rule-engine` CI job (which does not install astro-engine/Swiss Ephemeris) reported **303 passed, 4 skipped** — the 4th skip is the new `test_ashtakavarga_integration.py`'s module-level `pytest.importorskip("swisseph")` guard for its 3 real end-to-end tests, following the identical precedented pattern already present in `test_dasha_integration.py`, `test_transit_integration.py` and `test_phase5_integration.py` (3 skips before this change, 4 after); this is not a regression, and the same 3 tests were confirmed to actually execute (not skip) in the local run where astro-engine is installed.

### E. Known limitations and deferred work
- No shipped rule reads the new `ashtakavarga` evidence-bundle section yet; it is transport-only until a future Phase 9/rule-content work package consumes it.
- WP-B Jaimini (Rashi Drishti and Chara Karaka) has a research/design proposal delivered to the owner but is not implemented; it remains gated on this section's own CI verification, which is now satisfied.
- The rest of Phase 9 (partial/degree Drishti WP-C, Western WP-D, KP WP-E, Shadbala WP-F, Ayurdaya, and the scope-undefined systems) remains open.

### F. Resume instructions
1. Read `Phases.md`, then §27, then this section. 2. WP-EB is committed, pushed and CI-verified (commit `475c14a`); treat it as frozen unless the owner requests a correction. 3. Do not restart its research or methodology. 4. After any future push, check GitHub Actions for **each job and its steps** individually before saying the jobs passed. 5. WP-B Jaimini (Rashi Drishti, then Chara Karaka) may now begin per the owner's Phase 1/Phase 2 directive, with each work package's own independent research-verification, implementation, test, commit, push and CI-verification cycle — do not skip a gate. 6. Do not start any other Phase 9 work package without the owner's selection.

## 29. Phase 9 WP-B-1 — Jaimini Rashi Drishti — Completion and Handoff

**Status: implemented, committed, pushed and CI-verified.** This covers WP-B-1 only (Rashi Drishti, a static sign-to-sign aspect table). **Chara Karaka (WP-B-2) and every other Jaimini system (Jaimini Dashas, Arudha Pada, Karakamsa, ...) remain unimplemented.**

Base commit before this work: `b138513` (§28 documentation commit). Commit: `0d5787b1dd45d12d1015673db6b46991fd36d8d3`. `origin/main` verified equal to `0d5787b` after the push.

### A. Workflow followed
Re-verified the source from scratch before writing any code, per the owner's explicit "re-verify, not just reuse prior research" instruction: located the same Santhanam-numbered edition via a website mirror (chapter numbering cross-checked against Ch. 32/Ch. 35 already used elsewhere in this project, confirming it is the same translation), then independently confirmed the chapter heading, verses 1-3, the translator's provenance note and the chapter's own complete 12-sign worked table against the actual archive.org page-image scan via the browser (not OCR text) before implementing anything -> implementation, derived from the already-locked Phase 5 sign-modality table rather than hand-transcribed -> tests proving the derivation reproduces BPHS's own printed table exactly, cell by cell -> full validation -> documentation -> commit -> push -> CI verification, job by job.

### B. Methodology summary (`docs/ASTROLOGY_STANDARDS.md` v1.10.0 JN-01 to JN-05; `research/ASTROLOGY_SOURCES.md` Group 12)
- **One profile, one source, no default question**: `RASHI_DRISHTI_BPHS_8_1_3` (BPHS Ch. 8 v. 1-3, Santhanam translation, Vol I, printed pp. 105-107). Unlike Ashtakavarga, no cross-source variant was found for this rule, so a single profile is sufficient.
- **Provenance corrected against the popular misattribution**: BPHS's own translator note (page-image verified, printed pp. 105-106) states this Rasi-aspect system is Parasara's own and only "came to be known as [the] Jaimini system though the original propounder is Parasara." The profile ID and every citation name BPHS Ch. 8, never Jaimini, as the source.
- **Kept strictly separate from graha drishti**: Rashi Drishti (sign-to-sign) is a different system from Phase 5/6's Vedic graha drishti (planet-to-house, `aspects.py`); different module, different rule, a dedicated regression test proves no conflation.
- **Ch. 8 v. 4-5 read and page-image verified but deliberately not implemented**: the chapter extends the identical table to a planet's own placement, which would produce a planet-level aspect disagreeing with the already-locked graha drishti for the same placement — the two systems must never be blended (an existing, pre-this-work standards rule). Recorded as an open item for the owner, not implemented.
- **Verified exactly against the source's own printed table**: the implementation derives the 12-sign table from the already-locked Phase 5 `RASHI_MODALITY` (Chara/Sthira/Dwiswabhava) classification rather than transcribing it sign by sign; a test (`test_matches_bphs_printed_table_exactly`) hardcodes BPHS's own printed table (transcribed independently from the page image, not from the implementation) and confirms all 12 signs match exactly, with zero mismatches.

### C. What was implemented
- `services/astro-engine/src/pandit_astro_engine/jaimini/`: `profiles.py` (the one profile and its source reference) and `rashi_drishti.py` (`rashi_drishti()`, `has_rashi_drishti()`).
- `services/astro-engine/tests/test_rashi_drishti.py`: 65 tests (all 12 signs against the printed table, always-3-targets, no self-aspect, adjacent-sign exclusion for both movable and fixed signs, common-sign coverage, mutual-relation proof for every sign, `has_rashi_drishti` behavior, invalid-sign rejection, determinism, the graha-drishti non-conflation regression, profile provenance).
- Documentation: `docs/ASTROLOGY_STANDARDS.md` v1.10.0 (JN-01 to JN-05); `research/ASTROLOGY_SOURCES.md` Group 12; `services/astro-engine/README.md` (new "Rashi Drishti (Phase 9 WP-B-1)" section); `services/astro-engine/src/pandit_astro_engine/__init__.py` docstring.
- **Explicitly not implemented, by decision**: Ch. 8 v. 4-5 (planet-level Rasi Drishti); Chara Karaka (WP-B-2); any other Jaimini system; any rule reading Rashi Drishti facts; `Phases.md` was not modified.

### D. Validation
- astro-engine **915 tests passing** (850 pre-existing + 65 new). rule-engine **317 tests passing, unchanged** (not touched by this work at all). Ruff lint, Ruff format check and mypy strict all clean.
- **CI run `35730094599`** (commit `0d5787b`): 15 of 15 jobs green, every job's steps individually inspected (no failed step; only the established by-design skips already recorded for prior phases), independently cross-checked against the GitHub check-runs API (0 non-success conclusions). The `services/astro-engine` job's own log confirms **915 passed**, matching the local run exactly.

### E. Known limitations and deferred work
- No shipped rule reads Rashi Drishti facts yet; it is a pure, tested, provenance-carrying static table until a future rule-content work package consumes it.
- BPHS Ch. 8 v. 4-5 (the same table applied to a planet's own placement) remains an open item for the owner: whether to expose it as a separate, clearly-labelled planet-level fact (never merged with graha drishti) is a future decision, not made here.
- Chara Karaka (WP-B-2) has an approved scope (eight-body, Rahu reverse-degree convention, explicit tie handling) but no implementation yet; it is the next approved step, gated on its own source re-verification per the owner's Phase 2 directive.
- Jaimini Dashas, Arudha Pada, Karakamsa and every other Jaimini system remain unresearched-for-implementation and out of scope until separately approved.

### F. Resume instructions
1. Read `Phases.md`, then §28, then this section. 2. WP-B-1 is committed, pushed and CI-verified (commit `0d5787b`); treat it as frozen unless the owner requests a correction. 3. Do not restart its research or methodology. 4. After any future push, check GitHub Actions for **each job and its steps** individually before saying the jobs passed. 5. Chara Karaka (WP-B-2) may now begin per the owner's Phase 2 directive, with its own independent source re-verification (BPHS Ch. 32 v. 3-17), implementation, test, commit, push and CI-verification cycle — do not skip a gate, and do not silently merge, fill or guess tie values. 6. Do not start any other Jaimini or Phase 9 work package without the owner's selection.
