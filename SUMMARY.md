# Pandit Ji — Project Summary & Session Handoff

Status: verified through the **completion and green CI validation of Phase 5**.
This document exists purely for session continuity. A future AI coding
assistant session should be able to read this file and continue exactly
where the project left off, without re-deriving context from memory.

**How to use this file**: read it fully, then verify its claims against the
actual repository (`Phases.md`, `docs/ASTROLOGY_STANDARDS.md`,
`docs/ARCHITECTURE.md`, `TECH_STACK.md`, git log, `gh run list`) before acting
on it. Treat it as an accurate snapshot as of the commit named in §17, not as
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

**Phases 1 through 5 are complete and verified. Phase 6 has not started.**

---

## 10. Phase 1 — COMPLETED

Established `docs/ASTROLOGY_STANDARDS.md` as the single canonical standards
document (v1.0.0 at Phase 1 completion; now v1.3.0, see §15). It defines
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
pre-implementation lock) after a mandatory pre-implementation standards audit
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

## 21. Phase 7 — METHODOLOGY RESEARCH ONLY (NOT IMPLEMENTED)

Nothing of Phase 7 exists in the repository. Two research passes were done; no code, YAML, tests or documentation changed for them. All findings below are PROPOSALS awaiting the owner's decision unless stated.

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

**Nakshatra boundary - genuine Phase 5 defect (not fixed)**
- `pandit_astro_engine.nakshatra.nakshatra_position` uses `normalized // (360.0/27.0)`. At exactly representable boundaries it can assign the lower nakshatra: 39 of 81 exact-boundary tests were wrong (for example 40.0 degrees returns Krittika, not Rohini). The `near_boundary` flag is raised but the side is wrong; the standard's own arithmetic (longitude / 13 degrees 20') gives Rohini.
- No source states interval inclusivity; sources list shared endpoints. Proposed convention (a Pandit Ji standard, not a source): lower-inclusive, upper-exclusive, 360 = 0.
- Minimum correction, classified PHASE 5 PATCH REQUIRED BEFORE PHASE 7 (needs owner approval and a standards note): compute index and pada with exact rational arithmetic on the float value (index = floor(Fraction(L) x 27 / 360), pada = floor(Fraction(L) x 108 / 360) mod 4 + 1); keep `near_boundary` unchanged. Checked in-process without writing any file: with this change all 191 existing astro-engine tests still pass, so no existing golden case changes.

**Other proposals**: exact rational arithmetic with no intermediate rounding; canonical boundary = UTC instant (integer microseconds) with Julian Day UT derived; half-open intervals [start, end); display rounding never used for period selection; local timezone is display metadata and DST never alters a computed UTC boundary. Birth-time precision model EXACT / APPROXIMATE / NOT_EVALUABLE: the input model has no precision field today; the Moon moves about 13 degrees a day, so an uncertainty interval that crosses a nakshatra boundary makes the starting lord ambiguous and the result must not be shown as exact. Rule-engine contract: astro-engine calculates and owns `DashaFacts` (system, profile IDs for balance/year-length/sub-period, starting nakshatra/pada/lord, balance and unit, period tree with UTC boundaries, current period, calculation version); the rule engine only consumes them (a later facts-model extension) and never calculates Dasha. Maraka timing: an earlier `Phases.md` Phase 9 line says "Maraka timing is owned by Phase 7" but Phase 7 does not list it; proposed correction is that Maraka timing is a later rule-engine consumer of Dasha facts, not Phase 7 scope (this doc correction is NOT yet applied).

**Verdict at the last report: PHASE 7 IMPLEMENTATION READY: NO (pending owner decisions)**, in particular: year-length default profile; balance default profile; approval of the Phase 5 exact-arithmetic patch and boundary convention; birth-time precision field and where it lives; UTC-instant representation; the Maraka documentation correction; a standards amendment (likely v1.5.0).

## 22. Current Exact Repository State (before this summary commit)

- Branch `main`; HEAD `6e8eba4` = `origin/main`; working tree clean; CI green (run `35461086198`).
- Local environment notes: `pyswisseph` and the rule-engine, knowledge, agent, verification and astro-engine packages were pip-installed in editable mode during the session (needed for local test runs); nothing running in the background.
- Private research material (page-image excerpts for Sanskrit review, extraction JSON, OCR text, generators for the rule YAML) lives in the assistant session scratchpad under the OS temp directory and is NOT in the repository; it may not survive. The durable record is `research/ASTROLOGY_SOURCES.md` (Groups 1-8 and §6 source tiers and profile IDs).

## 23. Session Handoff Instructions

# NEXT SESSION — START HERE

Do not assume anything beyond this document, and re-check it against the repository first.

1. Read this `SUMMARY.md`, then verify HEAD, `origin/main`, working tree and GitHub Actions for HEAD; skim `Phases.md`, `docs/ASTROLOGY_STANDARDS.md`, `docs/ARCHITECTURE.md`, `research/ASTROLOGY_SOURCES.md`.
2. Report: repository state, which phases are complete (1-6), CI state, next phase (7), and any mismatch with this document.
3. **Do not implement Phase 7.** Phase 7 has NO implementation approval. The next step is for the owner to review section 21 and decide the open items; the last request was a focused methodology-closure pass (roadmap: `Phases.md` authoritative; research and reports only; no code, YAML, tests, commits or pushes for Phase 7 until explicitly approved).
4. Standing rules: cite sources honestly (image-checked vs OCR vs translation level; no Sanskrit-level claims without a qualified reviewer); never merge traditions silently; commits use the owner's identity `iamankoo <aniketraj00384@gmail.com>` with no AI attribution (CI rejects vendor names in `.md`, `.py`, `.ts`, `.tsx`, `.dart` files); do not modify Phase 5 or Phase 6 without approval.
