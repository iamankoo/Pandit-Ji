# Pandit Ji — Project Summary & Session Handoff

Status: verified through **Phase 6 (complete, accepted, CI green)**, the **Phase 5 Nakshatra boundary correction** (commit `091ca1b`, CI run `35500359836`, green), **Phase 7 (Dasha & Timing Engine): implemented, CI green** (§25), **Phase 8 (Transit / Gochar Engine): methodology locked (standards v1.6.0), implemented, committed and pushed, CI green** (§26), and, within Phase 9, **WP-A1/A2/A3 Ashtakavarga** (standards v1.7.0/v1.8.0, §27), **WP-EB Ashtakavarga EvidenceBundle integration** (v1.9.0, §28), **WP-B-1 Rashi Drishti** (v1.10.0, §29), **WP-B-2 Chara Karaka and Constant Karaka** (v1.11.0, §30) **WP-C Partial/Degree Drishti** (v1.12.0/v1.13.0, §31; independent audit passed, §32) **WP-D Western** (tropical positions, Placidus, aspects and orbs; v1.14.0, §33), and **WP-E KP foundation, WP-F Shadbala components, WP-G Jaimini extensions, WP-H Chinese Four Pillars and WP-I Tarot** (v1.15.0-v1.19.0) with the **Phase 9 closure record** (v1.20.0) (§34). **Phase 9 is complete as scoped by the owner (2026-09-25), with accepted deferrals** (Lal Kitab, Nadi, general Horary, Vastu, Feng Shui, Jaimini Dashas and Tarot meanings deferred; Ayurdaya excluded by product policy), after the closure and evidence-hardening work of §35 (the modern Raman Shadbala profile with totals, the WP-G facts object, Tarot provenance and evidence-bundle integration). Then the **Shadbala method policy** (v1.22.0) and **Phase 10 (Panchang, Muhurta and Calendar): implemented for its source-verified scope** (v1.23.0; Choghadiya and Gowri not implemented for lack of a primary source; owner decisions open) (§36). Current standards document version: **v1.23.0**. Sections 1-19 were written at the end of Phase 5 and are kept as history; §15 carries a post-completion addendum; §20-§31 are per-phase and per-work-package records; §32 is the WP-C audit and documentation-consistency record; §33 is the WP-D handoff; §34 is the WP-E to WP-I handoff; §35 is the Phase 9 closure; **§36 is the current handoff and continuation point**.
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

**Phases 1 through 7 are complete and verified (Phase 6: accepted by the owner, CI green; see §20). Phase 7 (Vimshottari Dasha) is implemented and CI-verified (see §25); its methodology research is §21. Phase 8 (Transit / Gochar) is implemented, pushed and CI-verified (see §26). Phase 9 is in progress: WP-A1/A2/A3, WP-EB, WP-B-1, WP-B-2 and WP-C are complete and CI-verified (§27-§32); WP-D Western is implemented, pushed and CI-verified (§33); the rest of Phase 9 is open.** (This roadmap list was first written at the end of Phase 5, when it read "Phase 6 has not started"; that statement is now historical.)

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

- **Current code state**: the latest code commit is `e56be0f` (Phase 7, see §25), CI run `35507588698` green (15 of 15 jobs, each inspected). Commits after it are documentation only; the current HEAD is whatever `git log` shows (verify it equals `origin/main`). Tests at that commit: astro-engine 513, rule-engine 256; standards v1.5.0. **Phase 8 (§26) then added commits `27afb4d`, `6af6112`, `7cd8887` and `f846e7e` (CI run `35639087407` green, 15 of 15 jobs, each inspected): astro-engine 788 and rule-engine 286 tests, standards v1.6.0.** **Phase 9 WP-A1/A2/A3 (§27) then added commits `31aa3b9` (CI run `35697685293` green) and `f1eb0a6` (CI run `35720123705` green, 15 of 15 jobs, each inspected): astro-engine 850 and rule-engine 286 tests, standards v1.7.0/v1.8.0.** **Phase 9 then added WP-EB `475c14a` (CI run `35726783964`; rule-engine 317, v1.9.0, §28), WP-B-1 `0d5787b` (CI run `35730094599`; astro-engine 915, v1.10.0, §29), WP-B-2 `befb9ac` (CI run `35739733487`; astro-engine 938, v1.11.0, §30; a duplicate run `35739733116` for the same commit was cancelled by concurrency, not failed) and WP-C `8a532cf`, `76bd540`, `c4059cc` (CI runs `35762446509`, `35763811712`, `35765414113`; astro-engine 1057, rule-engine 317, v1.12.0/v1.13.0, §31). The latest code commit is therefore `c4059cc`; every later commit is documentation only (`8053d93`, `5b10be9`, and the documentation-consistency commit recorded in §32.H). Test counts at that point: astro-engine 1057, rule-engine 317; standards v1.13.0. **Phase 9 WP-D (§33) then added the Western module: astro-engine 1166 (1057 + 109), rule-engine 317 unchanged, standards v1.14.0, astro-engine 0.8.0; its commits and CI runs are in §33.** (Earlier in this section's history: `091ca1b`, CI run `35500359836`, standards v1.4.1, astro-engine 353 and rule-engine 235 tests, no `dashas` module.)
- Earlier state, kept as history: branch `main`; HEAD `6e8eba4` = `origin/main`; working tree clean; CI green (run `35461086198`); then `81c9b08` (summary update), CI run `35462906836` green.
- Local environment notes: `pyswisseph` and the rule-engine, knowledge, agent, verification and astro-engine packages were pip-installed in editable mode during the session (needed for local test runs); nothing running in the background.
- Private research material (page-image excerpts for Sanskrit review, extraction JSON, OCR text, generators for the rule YAML) lives in the assistant session scratchpad under the OS temp directory and is NOT in the repository; it may not survive. The durable record is `research/ASTROLOGY_SOURCES.md` (Groups 1-8 and §6 source tiers and profile IDs).

## 23. Session Handoff Instructions

# NEXT SESSION — START HERE

Do not assume anything beyond this document, and re-check it against the repository first.

1. Read this `SUMMARY.md`, then verify HEAD, `origin/main`, working tree and GitHub Actions for HEAD; skim `Phases.md`, `docs/ASTROLOGY_STANDARDS.md`, `docs/ARCHITECTURE.md`, `research/ASTROLOGY_SOURCES.md`.
2. Report: repository state, which phases are complete (1-9; Phase 9 as scoped by the owner with accepted deferrals -- §27-§31, §33-§35), CI state, and any mismatch with this document.
3. Phases 7 and 8 are implemented and frozen (§25, §26); Phase 9 WP-A1/A2/A3, WP-EB, WP-B-1, WP-B-2, WP-C and WP-D are implemented and frozen (§27-§31, §33). Do not start another phase, or another Phase 9 work package, without reading `Phases.md` and getting the owner's approval. Sections 25-31 and 33 hold the handoffs, decisions and limitations; §35 records the Phase 9 closure; **§36 holds the current continuation point** (Shadbala method policy; Phase 10 implemented for its source-verified scope, with open owner decisions). The next roadmap phase is Phase 11 (Numerology + Compatibility), which needs the owner's go-ahead.
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

## 30. Phase 9 WP-B-2 — Jaimini Chara Karaka and Constant Karaka — Completion and Handoff

**Status: implemented, committed, pushed and CI-verified.** This covers WP-B-2 (Chara Karaka ranking, BPHS Ch. 32 v. 1-17, and Constant Karaka, v. 18-21). **This completes the master prompt's Phase 2 (WP-B Jaimini) scope: Rashi Drishti (§29) and Chara Karaka/Constant Karaka (this section).** Jaimini Dashas, Arudha Pada, Karakamsa and every other Jaimini system remain unimplemented, unresearched-for-implementation and out of scope.

Base commit before this work: `38a9dc1` (§29 documentation commit). Commit: `befb9ac889993945c9c3cb36bd679983b35d4a95`. `origin/main` verified equal to `befb9ac` after the push.

### A. Workflow followed, including two findings reported to and decided by the owner mid-task
Re-verified BPHS Ch. 32 from scratch via the actual archive.org page-image scan (not reusing the earlier, less rigorous Group 5 research pass), per the owner's "verify again before implementation" directive. This surfaced two findings that did not match the master prompt's original assumptions, each reported to the owner before any code was written, with implementation paused until a decision came back:
1. **Body-scope finding**: BPHS Ch. 32 v. 1-2 states three positions on which planets are Chara Karaka candidates ("Some say Rahu will become a Karka when there is a state of similarity in ... longitude ...; yet some say the 8 planets including Rahu will have to be considered irrespective of such a state"), not the single settled "eight-body" position the master prompt assumed. **Owner decision**: ship two profiles, no default (mirroring the Ashtakavarga precedent), skip the underspecified conditional reading.
2. **Tie-handling finding**: the source's own tie treatment differs by rank. v. 13's "deficit of one karaka" for the seven non-Atma roles has a real, source-stated fallback (a separate "constant significator") -- not a synthetic `NOT_EVALUABLE` as the master prompt's uniform tie-profile proposal implied. **Owner decision**: expand WP-B-2 to also implement Ch. 32 v. 18-21 (Constant Karaka) so that real fallback is available as its own fact set.
After both decisions, re-verification continued through v. 3-21 (Atma Karaka definition and tie-break, the other seven roles, the "deficit" worked illustration, and the Constant Karaka table) before any implementation began.

### B. Methodology summary (`docs/ASTROLOGY_STANDARDS.md` v1.11.0 JN-06 to JN-10; `research/ASTROLOGY_SOURCES.md` Group 13)
- **Two Chara Karaka profiles, no default**: `JAIMINI_CHARA_KARAKA_SEVEN_BODY_BPHS_32_1_17` (7 classical planets) and `JAIMINI_CHARA_KARAKA_EIGHT_BODY_BPHS_32_1_17` (7 + Rahu, unconditional -- confirmed by the chapter's own translator's note as what its own worked "standard nativity" example actually uses). Ketu is never a candidate under any of the three stated readings.
- **Ranking rule verified exactly against the source's own worked example**: candidates are ranked by degree traversed within their own sign, Rahu's degree reversed (30 minus his degree in the sign) before comparison; the implementation reproduces BPHS's own printed 8-role table (Atma=Moon, Amatya=Venus, Bhratru=Jupiter, Matru=Rahu, Pitru=Mercury, Putra=Sun, Gnati=Mars, Dara=Saturn) exactly.
- **Tie handling matches the source's own two-tier treatment**: a tie "identical to the second of arc" below the top rank shares that role between the tied candidates and always pushes the resulting shortfall to the *lowest* role in the fixed sequence (`NOT_EVALUABLE(rank_deficit)`) -- the same mechanism that gives the 7-body profile a structural Dara Karaka deficit even without any tie (7 candidates cannot fill 8 roles). A tie at the very top (Atma Karaka itself) instead makes the *whole* result `NOT_EVALUABLE(tie_unresolved)`, since every other Karaka is judged relative to Atma Karaka -- a Pandit Ji reading bridging two verse blocks, documented as such rather than presented as one verse's explicit statement.
- **Constant Karaka is a separate, independent fact set, not auto-wired as a substitute**: five of its eight significations (Mercury, Mars, Jupiter, Venus, Saturn, Ketu) are direct and unambiguous; the other two ("the stronger" of Sun/Venus for father, Moon/Mars for mother) reproduce an already-recorded "stronger undefined" conflict and are `NOT_EVALUABLE(strength_undefined)`. BPHS's own illustration links a Chara Karaka deficit to this table (Dara Karaka substitutes Venus) but demonstrates only that one case, so it is not generalized into an automatic rule.
- **Deliberately not implemented, by decision**: the conditional Rahu-inclusion reading (v. 1-2); the "merge Matru and Putra into 7 significators" alternative (mentioned once, no worked table); Ch. 32 v. 22-24 ("Houses Related", an interpretive-effects layer, out of scope under the project's facts-only boundary).

### C. What was implemented
- `services/astro-engine/src/pandit_astro_engine/jaimini/chara_karaka.py` (new): `CharaKarakaRequest`/`CharaKarakaResult`, `CandidateDegree`, `RoleAssignment`, `calculate_chara_karaka()`.
- `services/astro-engine/src/pandit_astro_engine/jaimini/constant_karaka.py` (new): `ConstantSignificator`, `constant_karakas()`.
- `services/astro-engine/src/pandit_astro_engine/jaimini/profiles.py` (extended): the two Chara Karaka profile definitions and their source references, alongside the existing Rashi Drishti profile.
- 23 new tests (`test_chara_karaka.py`, `test_constant_karaka.py`): the source's own worked example reproduced exactly, Rahu reverse-degree, highest/lowest comparison degree, exact degree/minute/second ties at the top (unresolved) and mid-rank (shared role, bottom deficit), the 7-body profile's structural deficit, Ketu exclusion, profile/input validation (unknown profile, missing/unexpected body, invalid longitude), determinism, result-contract validation, and the Constant Karaka table's resolved and `NOT_EVALUABLE` entries.
- Documentation: `docs/ASTROLOGY_STANDARDS.md` v1.11.0 (JN-06 to JN-10); `research/ASTROLOGY_SOURCES.md` Group 13 (both findings, both owner decisions, the full re-verification record); `services/astro-engine/README.md` (new "Chara Karaka and Constant Karaka" section); `__init__.py` docstring.
- **Explicitly not implemented, by decision**: any rule reading either fact set; Jaimini Dashas, Arudha Pada, Karakamsa or any other Jaimini system; `Phases.md` was not modified.

### D. Validation
- astro-engine **938 tests passing** (915 pre-existing + 23 new). rule-engine **317 tests passing, unchanged** (not touched by this work at all). Ruff lint, Ruff format check and mypy strict all clean.
- **CI run `35739733487`** (commit `befb9ac`): 15 of 15 jobs green, every job's steps individually inspected (no failed step; only the established by-design skips already recorded for prior phases), independently cross-checked against the GitHub check-runs API. (A duplicate concurrency-cancelled run, `35739733116`, was also triggered for the same commit and correctly excluded from this verification -- it was superseded before running, not a failure.) The `services/astro-engine` job's own log confirms **938 passed**, matching the local run exactly.

### E. Known limitations and deferred work
- No shipped rule reads either Chara Karaka or Constant Karaka facts yet; both are transport/computation-ready, not yet consumed.
- The conditional Rahu-inclusion reading and the "merge Matru/Putra" 7-significator alternative remain unimplemented by design (see §B); a future owner decision could add either as a third, explicitly-labelled profile if ever needed.
- Constant Karaka's father/mother slots remain `NOT_EVALUABLE(strength_undefined)` pending a locked "planetary strength comparison" rule (Shadbala territory, out of scope here).
- Ch. 32 v. 22-24 (Houses Related) remains unimplemented as an interpretive-effects layer.
- Jaimini Dashas, Arudha Pada, Karakamsa and every other Jaimini system remain unresearched-for-implementation and out of scope.
- **This completes the master prompt's approved Phase 1 (EvidenceBundle) and Phase 2 (WP-B Jaimini) scope.** The rest of Phase 9 (partial/degree Drishti WP-C, Western WP-D, KP WP-E, Shadbala WP-F, Ayurdaya, and the scope-undefined systems) remains open and requires a separate owner directive before any research or implementation begins.

### F. Resume instructions
1. Read `Phases.md`, then §29, then this section. 2. WP-B-2 is committed, pushed and CI-verified (commit `befb9ac`); treat it as frozen unless the owner requests a correction. 3. Do not restart its research or methodology. 4. After any future push, check GitHub Actions for **each job and its steps** individually before saying the jobs passed. 5. Do not begin any further Phase 9 work package (Jaimini Dashas, Arudha Pada, Karakamsa, WP-C/D/E/F, Ayurdaya, or the scope-undefined systems) without a new, explicit owner directive scoping it, following the same research-verify-document-approve-implement-test-commit-CI cycle used throughout Phases 7-9.

## 31. Phase 9 WP-C — Partial/Degree Drishti (BPHS and Uttara Kalamrita/Sripatipaddhati profiles) — Completion and Handoff

**Status: implemented, committed, pushed and CI-verified.** This covers WP-C: a continuous, degree-based refinement of planet-to-house aspect strength, shipped as two independent, never-merged profiles, `PARTIAL_DEGREE_DRISHTI_BPHS_26` and `PARTIAL_DEGREE_DRISHTI_UTTARAKALAMRITA_SRIPATI`. **WP-C is not a separately-named `Phases.md` line item** -- the roadmap lists only "Shadbala — BPHS Ch. 27-28"; Ch. 26 is Ch. 27's own stated prerequisite (Ch. 27 v.19's Drik Bala aggregates Ch. 26's values), so this is prerequisite groundwork, authorized by the project owner's explicit decision (the highest-authority source under `SOURCE_OF_TRUTH.md`), not by a roadmap line naming Ch. 26 directly. **Shadbala, Drik Bala, EvidenceBundle integration and Phase 6's `requires_partial_drishti` wiring are all explicitly out of scope and untouched.**

Base commit before this work: `de2e625` (§30 documentation commit). Commits, in order: `8a532cf` (methodology lock, docs only), `76bd540` (Profile A), `c4059cc` (Profile B + cross-profile tests). `origin/main` verified equal to `c4059cc` after the final push.

### A. Workflow followed
This work package went through the most extensive research-and-revision cycle of any Phase 9 work so far, across many gated rounds: (1) initial planning/scoping distinguishing WP-C from WP-D and auditing the repository; (2) source-comparison research (Brihat Jataka and Phaladeepika checked and ruled out; Saravali checked with a genuine negative result; Uttara Kalamrita found as a genuinely comparable second source); (3) mathematical reconstruction of BPHS Ch. 26's formula, including a Sanskrit-level dig that reversed an earlier, unverified "12 vs 10" guess in favour of the literal, page-confirmed "10" -- a correction the owner explicitly required be reported, not hidden; (4) a project-level discovery that BPHS's own formula is algebraically identical to linear interpolation between its own stated checkpoints; (5) a focused Rahu/Ketu source check, finding genuine silence in both primary sources and an explicit instruction not to resolve it by inference; (6) a full methodology lock (v1.12.0, then a v1.13.0 addendum for the node question); (7) a design-review round before any code, catching two contract-level details (the interpolation-equivalence framing and special-planet tolerance) that needed re-verification; (8) implementation, in two separate, fully validated, fully CI-verified commits, one per profile.

### B. Methodology summary (`docs/ASTROLOGY_STANDARDS.md` v1.12.0 PD-01 to PD-09/PD-11, v1.13.0 PD-10)
- **Two profiles, no default, never merged**: `PARTIAL_DEGREE_DRISHTI_BPHS_26` (BPHS Ch. 26, Sanskrit-cross-checked) and `PARTIAL_DEGREE_DRISHTI_UTTARAKALAMRITA_SRIPATI` (Uttara Kalamrita Ch. 2, citing Sripatipaddhati-II, unverified attribution). Independent request/result/status/reason types in separate modules; no shared calculation entry point or mergeable result base, verified by a dedicated structural test.
- **A project-level mathematical finding, clearly labelled as such**: BPHS's own five-branch formula (v.6-9) is algebraically identical to linear interpolation between the discrete checkpoints BPHS itself states (v.2-5) -- proven by a test that computes both ways and asserts equality, not merely claimed in a comment, and never presented as either source's own statement.
- **Houses 9 and 10 are a real, permanent, unresolved conflict inside BPHS itself**, Sanskrit-confirmed: the verse's own reduction step reads "10" (the bhūtasaṃkhyā word "dik"), not "12" -- a corrected, evidence-based reversal of an earlier draft's guess. Applied literally, this reproduces house 8's checkpoint correctly but contradicts BPHS's own house-9/house-10 pairing statement. `NOT_EVALUABLE(reduction_rule_conflict)` for non-special planets there, permanently; no winner chosen. Uttara Kalamrita's profile has no such gap, because it reads its checkpoints directly from the stated table rather than deriving them via BPHS's disputed reduction -- the two profiles were shown, by test, to agree exactly at every checkpoint they share.
- **Special-planet handling deliberately differs between the two profiles**: Saturn/Mars/Jupiter's confirmed full-aspect peaks (60, validated independently twice) are `SUCCESS` only at the exact angle in the BPHS profile, `NOT_EVALUABLE(special_formula_interior_unresolved)` elsewhere in that house; the Uttara Kalamrita profile returns that same `NOT_EVALUABLE` reason **unconditionally, including at the exact peak**, since its own source never states how its interpolation applies to the special-planet case at all. No tolerance or blending curve was invented in either profile.
- **Rahu/Ketu, a focused source check, resolved conservatively**: neither BPHS Ch. 26 nor Uttara Kalamrita Ch. 2 names Rahu or Ketu as an aspecting body -- genuine silence in both, not resolved by inference. BPHS Ch. 27's explicit node exclusion governs its own Shadbala-scoring context and was deliberately not extended into a Ch. 26 rule. Both profiles accept `RAHU`/`KETU` as structurally valid inputs (never a validation error, unlike Chara Karaka's definitive Ketu exclusion) and return `NOT_EVALUABLE(aspecting_node_unresolved)` symmetrically.

### C. What was implemented
- `services/astro-engine/src/pandit_astro_engine/partial_degree_drishti/`: `profiles.py` (both profiles' source/provenance metadata), `bphs.py` (Profile A), `uttarakalamrita.py` (Profile B).
- 119 new tests across `test_partial_degree_drishti_bphs.py` (61) and `test_partial_degree_drishti_uttarakalamrita.py` (58, including the cross-profile checkpoint-agreement test and the structural no-shared-base test).
- Documentation: `docs/ASTROLOGY_STANDARDS.md` v1.12.0 (PD-01 to PD-09, PD-11) and v1.13.0 (PD-10); `research/ASTROLOGY_SOURCES.md` Group 14 (the full verification record: BPHS Ch. 26, Brihat Jataka/Phaladeepika ruled out, Saravali's negative result, Uttara Kalamrita/Sripatipaddhati, the Rahu/Ketu finding); `services/astro-engine/README.md` and `__init__.py` docstring, documenting both profiles together and exactly where/why they diverge.
- **Explicitly not implemented, by decision**: Shadbala, Drik Bala, any rule reading either fact set, EvidenceBundle integration, Phase 6 `requires_partial_drishti` wiring; `Phases.md` was not modified.

### D. Validation
- astro-engine **1057 tests passing** (938 pre-existing + 61 Profile A + 58 Profile B). rule-engine **317 tests passing, unchanged** (not touched by this work at all). Ruff lint, Ruff format check and mypy strict all clean throughout.
- **CI run `35762446509`** (commit `8a532cf`, methodology-lock docs): 15/15 green. **CI run `35763811712`** (commit `76bd540`, Profile A): 15/15 green, astro-engine job's own log confirms 999 passed. **CI run `35765414113`** (commit `c4059cc`, Profile B): 15/15 green, astro-engine job's own log confirms 1057 passed. All three independently cross-checked against the GitHub check-runs API (15/15 `success`, 0 non-success, each time).

### E. Known limitations and deferred work
- No shipped rule reads either Partial/Degree Drishti fact set yet; both are computation-ready, not yet consumed.
- Houses 9/10's `reduction_rule_conflict` in the BPHS profile and both profiles' special-planet `special_formula_interior_unresolved` cases are permanent, by design, not "pending" -- resolving either would require new primary-source evidence (a worked example, a Sanskrit-scholar review) and a fresh owner decision, not a code change alone.
- The Sripatipaddhati-II attribution remains unverified; the primary text was unreachable via two independent technical attempts during research. A future retry (a different mirror, a purchased edition) could upgrade this, but nothing currently blocks on it.
- Shadbala (`Phases.md`'s actual named roadmap item, BPHS Ch. 27-28) remains unimplemented; this work is prerequisite groundwork for it, not the item itself.
- The rest of Phase 9 (WP-D/E/F, Ayurdaya, Jaimini Dashas, Arudha Pada, Karakamsa, and the scope-undefined systems) remains open.

### F. Resume instructions
1. Read `Phases.md`, then §30, then this section. 2. WP-C is committed, pushed and CI-verified across three commits (`8a532cf`, `76bd540`, `c4059cc`); treat it as frozen unless the owner requests a correction. 3. Do not restart its research or methodology, and do not attempt to resolve the houses-9/10 conflict or the special-planet interior questions without new primary-source evidence and an explicit fresh owner decision. 4. After any future push, check GitHub Actions for **each job and its steps** individually before saying the jobs passed. 5. Do not begin WP-D or any other Phase 9 work package without a new, explicit owner directive scoping it, following the same research-verify-document-approve-implement-test-commit-CI cycle used throughout Phases 7-9.

## 32. Session Handoff (2026-09-22) — WP-C Independent Audit (passed, no changes needed) and WP-D Status (not started)

**Read this section first if resuming tomorrow.** Nothing was implemented for WP-D this session. WP-C required no corrections. The exact continuation point is §F below.

### A. What happened in this session, in order
1. Completed WP-C implementation across two work packages (§31 above): Profile A (`bphs.py`, commit `76bd540`), Profile B (`uttarakalamrita.py`, commit `c4059cc`), plus the methodology-lock docs commit (`8a532cf`) and the §31 handoff commit (`8053d93`).
2. The owner then requested a **fresh, independent audit** of WP-C (explicitly: "do not blindly trust the report") before any WP-D work began. This audit was performed and is recorded in full in §B below.
3. A large WP-D research-and-implementation prompt was received, covering repository re-verification, a WP-D research phase (zodiac, body set, houses, aspects, orbs, provenance), a pre-lock report, and — only after explicit approval — implementation.
4. **Before any WP-D research was actually carried out**, the owner sent a stop instruction: finalize this handoff, commit and push, and do not begin any WP-D work (research or implementation) today. This section is that handoff. **WP-D research has not started.**

### B. WP-C Independent Audit — Result: PASSED, no corrections needed
Performed fresh, not by re-reading the prior session's own claims:
- **Repository state**: `git branch` = `main`; `git status` = clean; `git log` head = `8053d93 → c4059cc → 76bd540 → 8a532cf → de2e625`, matching the prior report exactly; local `HEAD` and `origin/main` both verified equal to `8053d93af513f287a30a5fdbace9aa3230771c87`.
- **Source files re-read in full, fresh** (not from memory): `services/astro-engine/src/pandit_astro_engine/partial_degree_drishti/bphs.py` and `uttarakalamrita.py`. Confirmed independently: two fully separate modules, no shared calculation function, no shared result base class beyond each module's own private `_Model` (verified: `UkDrishtiResult.__mro__` is `(UkDrishtiResult, _Model, BaseModel, object)` -- no cross-module class in the chain), no default profile, Profile A's `_DISPUTED_HOUSES = (9, 10)` excludes 8, Profile A's special-planet branch checks exact equality (`delta == peak_degrees`) with no tolerance, Profile B's special-planet branch is unconditional (no peak check at all, always `NOT_EVALUABLE`), both modules check `_NODES = (RAHU, KETU)` before any other logic and return `NOT_EVALUABLE(aspecting_node_unresolved)`, both longitude validators reject `[<0 or >=360)`.
- **Full test suites run fresh**: astro-engine **1057 passed** (including a targeted run of just the two WP-C test files: **119 passed**); rule-engine **317 passed, unchanged**. Ruff lint, Ruff format check and mypy strict all clean, run fresh this session.
- **CI independently re-verified via the GitHub check-runs API** (not re-reading the prior report's numbers) for all four WP-C commits: `8a532cf`, `76bd540`, `c4059cc`, `8053d93` -- each returns exactly 15 check-runs, 0 with a non-success conclusion.
- **Conclusion: every claim in the prior §31 handoff was independently confirmed. No gap was found. No code was touched during this audit** -- per the owner's own instruction, WP-C was not modified since it was already clean.

### C. WP-D Status: Not Started
The large WP-D prompt's Section 1-3 (repository re-verification, "do not skip source verification") were being followed when the stop instruction arrived; the actual WP-D research (Section 5 of that prompt: zodiac, body set, house system, aspects, orbs, provenance) **was not performed this session**. This is a correction to avoid any ambiguity: no WP-D source has been checked, no WP-D profile ID has been proposed, and no WP-D file has been touched, in direct response to today's large prompt.

**Prior, separate WP-D research exists from an earlier point in this project's history** (recorded informally in conversation, not yet in `research/ASTROLOGY_SOURCES.md` or `docs/ASTROLOGY_STANDARDS.md` -- carried here in prose so it is not lost, and must be re-verified before being relied on, not assumed correct):
- `docs/ASTROLOGY_STANDARDS.md`'s existing "Western / Tropical" section (written in the Phase 1 v1.1.0 pass, long before this project's page-image-verification discipline existed) states Tropical zodiac + Placidus houses + "tropical orb conventions" with **zero source citation** -- unlike every other locked convention in that document. This was flagged, not resolved: whether to treat it as a starting point to formally source, or discard and re-derive from scratch, is an open owner decision.
- Ptolemy's *Tetrabiblos* (Book I, checked directly via the LacusCurtius/Loeb text) supports the 4 non-conjunction major aspects (opposition/trine/square/sextile -- Ptolemy explicitly does not count conjunction as a formal aspect) at primary-source level, but **contains no orb or per-planet "moiety" values at all**; an editor's footnote attributes even a vague "15 degree maximum" to a later, anonymous commentator, not to Ptolemy. The widely-cited per-planet moiety table (Sun 15 deg, Moon 12 deg, etc.) is a still-later accretion and must never be cited as "Ptolemaic."
- `docs/ARCHITECTURE.md` already reserves a `western/` package location (never built) matching this project's isolation convention.
- No WP-D source registry entries exist in `research/ASTROLOGY_SOURCES.md` yet.

**None of the above is a locked decision.** It is prior-session findings, offered as a starting point for tomorrow's research, not a substitute for it.

### D. Source-of-truth chain re-read before finalizing this handoff
`features.md` (product vision, accuracy principle unchanged), `Phases.md` Phase 9 (Shadbala -- BPHS Ch. 27-28 -- remains the only named Vedic-strength line item; WP-C's Ch. 26 work and any future WP-D work are both, in different ways, not separately named there), `SOURCE_OF_TRUTH.md` (authority order unchanged: explicitly locked owner decisions outrank `Phases.md` itself), `docs/ASTROLOGY_STANDARDS.md` (current version confirmed at **v1.13.0**, PD-01 through PD-11). No inconsistency found between these documents and the current repository state.

### E. Validation Run This Session (all fresh, all passing)
- astro-engine: ruff lint clean, ruff format clean, mypy strict clean (54 source files), **1057 tests passed** (25.37s).
- rule-engine: **317 tests passed** (19.43s), untouched.
- Git: working tree clean before and after this session's only change (this `SUMMARY.md` update); no other file was modified.
- CI: all four prior WP-C commits re-verified green via the API (§B); this handoff commit's own CI is reported in §G below once pushed.

### F. Exact Continuation Point for Tomorrow
**Do not repeat the WP-C audit -- it passed and is closed.** Start WP-D fresh, following the large prompt already on record in this session's transcript (repository re-verification -> structured research across zodiac/body-set/houses/aspects/orbs/provenance -> a research deliverable -> a pre-lock report classifying every claim as `SOURCE_SUPPORTED`/`PROJECT_DERIVED`/`INFERENCE`/`UNRESOLVED_CONFLICT`/`NOT_EVALUABLE` -> **stop at the methodology-approval gate** -> only implement after explicit approval). Begin by re-reading this section and `Phases.md`, then re-verifying `origin/main` is still at the commit recorded in §G before doing anything else. Reuse §C's prior findings only as a lead to re-verify, never as an assumed-correct starting fact.

### G. Files Changed, Commit, CI (this handoff)
- **File changed**: `SUMMARY.md` only (this section).
- **Commit**: `5b10be9203414ba24f46f54f9ea09a87939408cd` ("docs: record WP-C final audit result and WP-D not-started status (session handoff)"), author `iamankoo <aniketraj00384@gmail.com>`, 2026-09-23. (This line was left as a placeholder in that commit and filled in by the documentation-consistency commit in §H, from the verified Git history.)
- **Push/CI**: pushed; `origin/main` was verified equal to `5b10be9` at the start of the 2026-09-24 session. CI run `35767621792` (event `push`): completed, conclusion success; the GitHub check-runs API reports 15 check runs, 0 non-success; every job's steps were inspected, with only the established by-design skips ("Install domain services" outside `server`; `packages/ui` Lint, Format check and Test; `infrastructure/migrations` mypy and pytest).

### H. Documentation Consistency Gate (2026-09-24, documentation only; WP-D still not started)
Before any WP-D work, a status audit found stale or inconsistent documentation. On the owner's instruction, only the following were corrected; no source code, test, locked methodology, profile, rule or `Phases.md` text was changed:
- `docs/ASTROLOGY_STANDARDS.md`: the header read "Version: 1.6.0" although the change log runs to v1.13.0; the header now reads v1.13.0 and states the per-result standards versions (unchanged). The v1.6.0 change-log entry, which had been appended after v1.13.0, was moved to its chronological position (text unchanged). No new standards version was created, because no standard changed.
- This file: the status header (line 3), the §9 roadmap status, §22 current code state and §23 steps 2-3 were brought up to date with §28-§32 (historical text kept); §G above was filled in.
- `research/ASTROLOGY_SOURCES.md` §4: the Vimshottari balance and year-length entries said "no default selected"; they now record the Phase 7 engineering-convention defaults (standards v1.5.0) while keeping both source conflicts open.
- Validation before the commit: astro-engine 1057 and rule-engine 317 tests passing (unchanged; no code touched); no merge markers; only these three files changed. The commit hash and CI result of this change are in `git log` and GitHub Actions (a commit cannot record its own hash); verify them before relying on this section.
- **Remaining known documentation issues, not changed here**: §8 predates the locked multilingual rule (reconcile before Phase 15/19); `research/ASTROLOGY_SOURCES.md` §6 profile-ID tables stop at §6.5 (Jaimini and WP-C profile IDs are recorded only in Groups 12-14); the astro-engine `pyproject.toml` description stops at WP-A (a code-package file, out of scope for a documentation-only change); the Phase 1 Western/Tropical standards section cites no source and says "same aspect-detection mechanism, tropical orb conventions" (to be handled by the WP-D methodology lock, not here); the WP-A to WP-F labels come from a Phase 9 traceability matrix that is not in the repository, and `Phases.md` lists Phase 9 modules without an order.

## 33. Phase 9 WP-D — Western Astrology (tropical, Placidus, aspects, orbs) — Completion and Handoff

**Status: researched, methodology-locked (standards v1.14.0, WD-01 to WD-20), implemented, tested, committed, pushed and CI-verified (§G).** The project owner's WP-D directive authorized research, methodology lock, implementation, validation, commit and push in one continuous execution, with the rule that where sources conflict a defensible engineering default is chosen, documented and the alternatives kept as profiles where practical. That directive is the approval for the v1.14.0 lock; there was no separate approval gate between research and implementation this time.

Base commit before this work: `120c34c` (documentation consistency gate, §32.H).

### A. Workflow followed
Repository and roadmap re-verification (HEAD = `origin/main` = `120c34c`, clean; WP-C committed; no Western code existed; `Phases.md` Phase 9 names "Western Astrology", "Tropical zodiac", "Western aspects", "Placidus"; `features.md` §4 and §9; `docs/ARCHITECTURE.md` reserves `western/`) -> source research (Swiss Ephemeris documentation read directly; Ptolemy's *Tetrabiblos*, Robbins translation, in the LacusCurtius transcription; Lilly's *Christian Astrology* 1647 in archive.org OCR, with the 1659 Wikisource OCR as a cross-check; JPL Horizons as engineering evidence) -> library probing (Placidus polar behaviour, outer-planet and asteroid availability in Moshier mode) -> methodology lock -> implementation -> tests -> full validation -> documentation -> commits.

**Mismatches found and how they were resolved**: (1) the owner's WP-D prompt asked for commits as "Aniket Raj", while `CONTRIBUTING.md` and §4 lock `iamankoo <aniketraj00384@gmail.com>`; this was put to the owner before committing, and the owner chose to keep the locked `iamankoo` identity. (2) The Phase 1 Western/Tropical standards bullet "same aspect-detection mechanism, tropical orb conventions" was uncited and contradicted the sign-based Vedic mechanism; it is marked superseded by WD-09 to WD-14 (text kept). (3) The source registry's verification-level vocabulary had no term for an English original read in OCR, a web transcription, or technical documentation; three explicit levels were added rather than stretching the Sanskrit-oriented ones.

### B. Methodology summary (`docs/ASTROLOGY_STANDARDS.md` v1.14.0; `research/ASTROLOGY_SOURCES.md` Group 15, §4 and §6.6)
- **Tropical zodiac** of date, no ayanamsa (`WESTERN_ZODIAC_TROPICAL_OF_DATE`); half-open signs with exact arithmetic (WD-02).
- **Bodies**: `WESTERN_BODIES_MODERN_10` default (engineering default, `modern_tradition`), `WESTERN_BODIES_CLASSICAL_7` (Lilly), `WESTERN_BODIES_MODERN_10_NODES` (nodes as positions only, explicit node convention, never defaulted). Chiron, asteroids, Part of Fortune excluded (WD-03 to WD-05).
- **Placidus only** (`WESTERN_HOUSES_PLACIDUS_SWISSEPH`); `NOT_EVALUABLE(placidus_polar_circle)` at |latitude| ≥ 90° − true obliquity (matches Swiss Ephemeris's own switch to 1e-9°); `NOT_EVALUABLE(placidus_not_computable)` for any other library failure; the Porphyry substitute is never returned; half-open placement by ecliptic longitude (WD-06 to WD-08).
- **Aspects**: the five Ptolemaic aspects on the shorter arc, inclusive orbs, one per pair; minor aspects unsupported (WD-09, WD-10).
- **Orbs**: `WESTERN_ORB_FIXED_V1` default (8°, sextile 6°; an engineering convention, not a source rule) and `WESTERN_ORB_LILLY_1647_MOIETY` (Lilly's planet-chapter orbs by moiety; outer-planet pairs `NOT_EVALUABLE(orb_not_defined_for_body)`) (WD-11 to WD-13).
- **Applying/separating** from instantaneous speeds (`WESTERN_MOTION_INSTANTANEOUS_V1`; reading Lilly's three ways of application as a closing rate is an inference) (WD-14).
- **Unknown birth time**: houses, angles, placement and aspects `NOT_EVALUABLE(birth_time_unknown)`; positions reported with a warning (WD-15).
- **Recorded conflicts, no winner chosen**: Ptolemy's exclusion of the conjunction (included, following Lilly); Ptolemy gives no orbs, and the Ashmand table in Robbins's note is not Ptolemaic; Lilly's planet-chapter orbs versus his own platick example (Saturn 10/Venus 8), with his printed table illegible in the OCR.

### C. What was implemented
- `services/astro-engine/src/pandit_astro_engine/western/`: `constants.py` (`WesternBody`, `TropicalSign`, `AspectType`, `WESTERN_STANDARDS_VERSION = "1.14.0"`), `profiles.py` (all nine profiles with evidence labels and source references), `models.py` (`WesternChartRequest`, `WesternChartFacts` and parts), `zodiac.py`, `houses.py`, `aspects.py` (pure), `service.py` (`WesternChartService`).
- Additive adapter changes: `ephemeris.py` (`SWE_WESTERN_OUTER_BODY_ID`, `true_obliquity_degrees`, `calculate_placidus_houses`, `RawHouses`), `errors.py` (`HouseSystemUnavailableError`). No existing function changed; `CelestialBody` and `SWE_BODY_ID` are unchanged (tested).
- astro-engine 0.7.0 -> 0.8.0 (`_version.py`, `pyproject.toml`, whose description also caught up with WP-B/WP-C).
- Tests: `test_western_zodiac_aspects.py` (42), `test_western_houses.py` (29, including an independent Placidus implementation and the polar boundary), `test_western_service.py` (38, including JPL Horizons references for all ten bodies and an import scan proving the module uses no Vedic module and no `swisseph`); fixture `tests/fixtures/western_outer_planets_horizons.json` (12 samples, retrieved 2026-09-24).
- Documentation: `docs/ASTROLOGY_STANDARDS.md` v1.14.0; `research/ASTROLOGY_SOURCES.md` (vocabulary, four source entries, §4 conflicts, §6.6); `docs/ARCHITECTURE.md` (§6 tree note, §9 contract row, deterministic list); `services/astro-engine/README.md`; package docstring; this section.
- **Explicitly not implemented, by decision**: interpretation of any kind, Vedic-versus-Western comparison, EvidenceBundle integration, other house systems, minor aspects, Chiron/asteroids/Part of Fortune, node aspects, a table-based Lilly or Ashmand orb profile, HTTP endpoints, database tables; `Phases.md` was not modified.

### D. Validation (run locally before the commits)
- astro-engine **1166 passed** (1057 existing + 109 new); rule-engine **317 passed** (unchanged); agent 2, knowledge 1, verification 1, contracts 2, shared 1, server 5 (with `PYTHONPATH=src`).
- `ruff check`, `ruff format --check` and `mypy src` clean for astro-engine (62 source files) and rule-engine; the README Western example was executed and returns `TropicalSign.LIBRA` with 18 aspects.
- Independent evidence: outer planets vs JPL Horizons at most 0.63″; classical bodies within the Phase 8 tolerances (1″, Moon 6″); Placidus vs an independent implementation better than 0.01″ over 250 random charts; tropical minus sidereal equals the Lahiri ayanamsa to within 20″ (the documented Phase 8 frame difference).

### E. Known limitations and deferred work
- Moshier mode unless Swiss Ephemeris data files are configured; UT1-UTC not modelled.
- Lilly values are `OCR-ORIGINAL-ENGLISH` (no page-image check; Mars from the 1659 OCR only); the Tetrabiblos was read in a web transcription only; no Western source is verified in its original language.
- Future profiles, each needing its own lock: Whole Sign/Equal/Koch/Regiomontanus houses, minor aspects, Chiron (needs licensed asteroid files), Part of Fortune, node aspects, a page-image-verified Lilly table profile, the Ashmand table (as a labelled translator-note profile if ever wanted).
- No rule reads Western facts; EvidenceBundle integration and the `features.md` §9 "Vedic vs Western comparison" / "Western chart interpretation" belong to later gates and phases.

### F. Resume instructions
1. Read `Phases.md`, then this section. 2. WP-D is committed and pushed (§G); treat it as frozen unless the owner requests a correction. 3. Do not restart its research or methodology. 4. After any future push, check GitHub Actions for each job and its steps before saying the jobs passed. 5. The rest of Phase 9 (KP WP-E, Shadbala WP-F, Ayurdaya, other Jaimini systems, scope-undefined systems) needs a new owner directive.

### G. Commits, push and CI
- Commits (author and committer `iamankoo <aniketraj00384@gmail.com>`, no AI attribution): `615947d` docs: lock Phase 9 WP-D Western methodology (standards v1.14.0); `2957a0d` feat: add Western tropical chart facts to astro-engine (Phase 9 WP-D); `e9d68fb` docs: record Phase 9 WP-D Western completion and handoff.
- Push: the first attempt was rejected by GitHub with an HTTP 500 ("Internal Server Error", request ID `EFE5:3E1945:D9BEF:EB0A4:6AB53540`); `git ls-remote` showed the remote still at `120c34c`, and a single retry succeeded (`120c34c..e9d68fb`). `origin/main` was verified equal to `e9d68fbb28342dccc087fa667921bad592ba29a4`.
- CI run `36013948673` (event `push`, commit `e9d68fb`; the three commits were pushed together, so this one run covers them): completed, conclusion success. All 15 jobs succeeded, each inspected with its steps; the only skipped steps are the established by-design ones ("Install domain services" outside `server`; `packages/ui` Lint, Format check and Test; `infrastructure/migrations` mypy and pytest). The check-runs API reports 15 check runs, 0 non-success. The `services/astro-engine` job log shows **1166 passed**, matching the local run. The CI result of this §G record itself is in GitHub Actions for the commit that adds it.

## 34. Phase 9 WP-E to WP-I and Phase 9 Closure — Completion and Handoff

**Status: WP-E KP foundation, WP-F Shadbala components, WP-G Jaimini extensions, WP-H Chinese Four Pillars and WP-I Tarot are researched, methodology-locked (standards v1.15.0-v1.19.0), implemented and tested; the remaining Phase 9 systems are researched and recorded as deferred or excluded (v1.20.0, §Phase 9 closure).** The owner's Phase 9 master directive (2026-09-24) authorized the whole cycle -- research, lock, implementation, validation, commit, push, CI -- in one execution, as for WP-D; that directive is the approval for these locks.

**Phase 9 completion status: implementation scope closed, with documented deferrals -- not "complete" in the full roadmap sense.** Lal Kitab, Nadi, general Horary, Vastu, Feng Shui and Jaimini Dashas are not implemented (reasons below), Ayurdaya is excluded pending an owner product-policy decision, and Shadbala produces no total. Accepting these deferrals, or directing further work on any of them, is an owner decision.

Base commit before this work: `fb65f61` (§33.G).

### A. Scope reconciliation (every Phase 9 item)

| Work item (`Phases.md` Phase 9) | Outcome | Where |
|---|---|---|
| KP Astrology | Implemented as a foundation (positions, cusps, star/sub/sub-sub lords, 249 table, significators a-d, Ruling Planets); no judgment or timing | WP-E, KP-01 to KP-16 |
| KP Horary | Implemented (number 1-249 horary chart, Ruling Planets); no judgment | WP-E, KP-11 |
| Lal Kitab | Research only, deferred (Urdu editions, no qualified reader, presumed in copyright to 2042) | P9-01 |
| Nadi Astrology | Research only; leaf-matching is not a deterministic calculation | P9-02 |
| Horary Astrology (general) | Deferred; tradition (Western/Lilly or Vedic/Prashna) not chosen by the roadmap | P9-03 |
| Western Astrology, Tropical zodiac, Western aspects, Placidus | Done in WP-D | §33 |
| Chinese astrology | Implemented as Four Pillars calendar pillars; luck cycles not produced (need sex, not collected) | WP-H, CN-01 to CN-14 |
| Vastu | Deferred (no building data collected; Phase 17 cross-domain) | P9-04 |
| Feng Shui-related modules | Deferred (needs building data; Eight Mansions needs sex) | P9-05 |
| Tarot | Implemented as deck, spreads and seeded/user-selected layouts; no meanings | WP-I, TA-01 to TA-10 |
| Shadbala (BPHS Ch. 27-28) | Implemented with documented limits: 11 components plus the Moon's Cheshta evaluated; 7 not evaluable; no total; Ch. 28 research only | WP-F, SB-01 to SB-20 |
| Ashtakavarga (BPHS Ch. 66-72) | Done in WP-A1/A2/A3 and WP-EB | §27, §28 |
| Jaimini: Chara Karakas, Rashi Drishti | Done in WP-B; Ch. 8 v. 4-5 planet level added in WP-G | §29, §30, JN-11 |
| Arudha Pada, Karakamsa (owner directive; not named in `Phases.md`) | Implemented; roadmap gap reported, `Phases.md` not edited | WP-G, JN-13 to JN-17, P9-09 |
| Jaimini Dashas | Research only | P9-07 |
| Ayurdaya (BPHS Ch. 43) | Excluded pending owner product-policy decision | P9-06 |

### B. Research performed (what was actually read)
- **KP**: KP Readers I, III, VI in archive.org OCR (`OCR-ORIGINAL-ENGLISH`); Swiss Ephemeris §2.8.6 (`DOCUMENTATION-DIRECT`). No page image.
- **Shadbala**: BPHS Ch. 27 (all 40 verses) and Ch. 28 v. 1-20 in the `BPHSEnglish` OCR (`OCR-TRANSLATION`); Ch. 3 v. 19. No page image.
- **Jaimini WP-G**: BPHS pp. 107, 294, 295, 296 as page images rendered from the archive.org PDF (`IMAGE-TRANSLATION`); Ch. 29 v. 1-3, 6-7 and Ch. 33 v. 1-2 in OCR.
- **Chinese**: Hong Kong Observatory solar-term definition and data (`DOCUMENTATION-DIRECT`); 《三命通會》 卷一-卷三 on Wikisource (`WEB-TRANSCRIPTION-SOURCE-LANGUAGE (unreviewed)`); almanac websites for one day-pillar check (`SECONDARY`, MEDIUM).
- **Tarot**: Waite, *Pictorial Key*, Parts II-III on English Wikisource (`WEB-TRANSCRIPTION-ORIGINAL-ENGLISH`).
- **Not read**: any Lal Kitab edition, any Nadi text, Vastu and Feng Shui texts, Jaimini dasha chapters, Prasna Marga. Nothing is claimed about them beyond identification.

### C. Findings and conflicts (preserved, not resolved silently)
- KP: the Reader's 291 CE zero year and its own table differ by about 1′; the day-lord convention is unstated (no default); the Reader VI example's intermediate cusps differ by 4-9′ (Raphael's tables) and two significator lists differ as a result (recorded in the fixture).
- Shadbala: six verse/note conflicts or gaps make Abda, Masa, Hora, Ayana, Yuddha, Cheshta (Sun, Mars-Saturn) and Drik `NOT_EVALUABLE`; Saptavargaja is not evaluable when D1 places a planet in its Moolatrikona sign outside the Ch. 3 range.
- Jaimini: the translator's Arudha chart omits the 7th-house exception for houses 9 and 10, and the note's Aquarius/Saturn example contradicts the verse; the Ch. 8 example (b) contradicts the verse table; the standard-nativity degrees on p. 294 differ from the Ch. 32 table used by the frozen WP-B-2 fixture (ranking unaffected; not edited).
- Chinese: day boundary and time basis are genuine school differences (no defaults); the late 子 hour under the midnight boundary is not evaluated.

### D. What was implemented
- New astro-engine packages: `kp/` (constants, profiles, subdivision, significators, ruling_planets, models, service), `shadbala/` (constants, profiles, components, models, service), `chinese/` (constants, pillars, profiles, models, service), `tarot/` (deck, draw, service); `jaimini/` gains `planet_rashi_drishti.py`, `arudha.py`, `karakamsa.py` and WP-G profiles.
- Additive adapter functions in `ephemeris.py`: `SWE_KP_AYANAMSA`, `kp_sidereal_mode` (applies a KP mode and restores the previous one), `get_ayanamsa_with_nutation_degrees`, `calculate_sidereal_placidus_houses`, `placidus_houses_from_armc`, `calculate_sidereal_angles`, `equation_of_time_days`; `set_sidereal_mode` now records the applied mode. Additive `dignity.debilitation_point`. No existing function's behaviour changed.
- astro-engine 0.8.0 -> 0.9.0; PyYAML added to astro-engine's dev extras only (the Shadbala drift test reads the locked Phase 6 tables).
- Fixtures (independent, none generated by the code under test): `kp_reader3_sub_table.json`, `kp_reader6_horary_29.json`, `hko_solar_terms_and_year_names.json`.
- Not implemented, by decision: interpretation of any kind, EvidenceBundle integration for WP-E to WP-I (separate gates), rule-engine consumers, HTTP endpoints, database tables; `Phases.md` and `features.md` were not modified.

### E. Validation (local, before the commits)
- astro-engine **1340 passed** (1166 existing + 174 new: KP 70, Shadbala 37, WP-G 15, Chinese 34, Tarot 18); rule-engine 317, agent 2, knowledge 1, verification 1, contracts 2, shared 1, server 5, all passing.
- `ruff check`, `ruff format --check` clean for every Python package; `mypy src` clean for astro-engine (89 source files) and every other package except `server`, whose two errors (`psycopg` not installed locally) are identical on the untouched baseline and do not occur in CI.
- Repository-integrity scans (forbidden service names, attribution) and `git diff --check` clean; no secrets, no logging, no personal data in the new files (test charts are published book examples or synthetic).
- Independent evidence: KP Reader III (202 rows) and Reader VI (example 29); KP Reader I ayanamsa table; BPHS worked examples (Uchcha 50.75; Arudha chart; Navamsa chart; Ch. 8 example); HKO 216 solar terms within 30.2 s and 7 year names; the 1 January 2000 almanac pillars; Waite's trump list and Celtic positions.
- Isolation: a test proves a Vedic Kundli is identical before and after KP calls; import scans prove KP, Chinese and Tarot import no Vedic/Western modules as applicable and Tarot uses no system randomness.

### F. Known limitations and remaining work
- KP: no event judgment, timing, conjunction/aspect significators or node agency; OCR-level sources only.
- Shadbala: no total until the seven not-evaluable components get a source decision (for example a Sanskrit review of Ch. 27 v. 15-25, or an owner-approved modern method as a separately labelled profile); Ch. 28 and Bhava Bala open.
- Chinese: day count confirmed only against secondary sources (Academia Sinica check recommended); luck cycles blocked by the sex-data rule; no hidden stems, ten gods or Na Yin.
- Tarot: no meanings (a knowledge/agent-phase task).
- Deferred systems P9-01 to P9-07 each need owner scoping and sources.
- Phase 10 dependencies: a Hora standard would unblock Shadbala Hora Bala; sunrise-based Panchang elements are already consumed as noted.

### G. Commits, push and CI
- Commits (author and committer `iamankoo <aniketraj00384@gmail.com>`, no AI attribution; the owner's master prompt named "Aniket Raj", and the locked `iamankoo` identity was kept, as the owner decided for the identical question at WP-D, §33.A): `30b2492` docs: lock Phase 9 WP-E to WP-I methodology and Phase 9 closure (standards v1.15.0-v1.20.0); `4c071f4` feat: KP foundation (WP-E); `a97616e` feat: Shadbala components (WP-F); `7136878` feat: planet-level Rashi Drishti, Arudha Pada and Karakamsa (WP-G); `35ae98e` feat: Chinese Four Pillars (WP-H); `1d8c062` feat: Tarot (WP-I); `96426e4` chore: astro-engine 0.9.0 and README; `6ff6505` docs: §34 handoff.
- Push: `fb65f61..6ff6505`, first attempt; `origin/main` and `git ls-remote` verified equal to `6ff6505d4e0ce450956293784d3c143a356483db`.
- CI run `36092711053` (event `push`, commit `6ff6505`; the eight commits were pushed together, so this run covers them): completed, conclusion success. All 15 jobs succeeded, each inspected with its steps (173 steps); the only skipped steps are the established by-design ones ("Install domain services" outside `server`; `packages/ui` Lint, Format check and Test; `infrastructure/migrations` mypy and pytest). The check-runs API reports 15 check runs, all `success`. Job logs: `services/astro-engine` **1340 passed** (matching the local run); `services/rule-engine` 303 passed, 4 skipped (the existing `importorskip("swisseph")` integration modules, unchanged); `server` 5 passed. The CI result of this §34.G record itself is in GitHub Actions for the commit that adds it.

## 35. Phase 9 Closure and Evidence Hardening (2026-09-25) — Completion and Handoff

**Status: Phase 9 is complete as scoped by the owner, with accepted deferrals** (`Phases.md` Phase 9 status block; `docs/ASTROLOGY_STANDARDS.md` P9-10, P9-11). Owner decisions of 2026-09-25: accept the deferrals of Lal Kitab, Nadi, general Horary, Vastu, Feng Shui, Jaimini Dashas and Tarot meanings; keep Ayurdaya excluded (lifespan outputs are prohibited by `PRODUCT_POLICIES.md`); reopen Shadbala with a separately labelled, evidence-backed modern methodology; integrate WP-E to WP-I into the evidence bundle with provenance; update the roadmap documents.

Base commit before this work: `45fd37a` (§34.G).

### A. What was done
- **Shadbala reopened (v1.21.0, SR-01 to SR-24)**: a second, separate profile, `SHADBALA_RAMAN_GRAHA_BHAVA_BALAS`, after B. V. Raman's *Graha and Bhava Balas* (the standard modern Shadbala manual; the archive.org scan was read in OCR and its worked Standard Horoscope and Tables IV-IX were checked as rendered page images). It evaluates all eighteen leaf components and produces Sthana, Kala and Shadbala totals. Two contradictions inside the book (the Drekkana order, text versus worked example; the Moon's benefic rule for Paksha) are required request fields with no default. The BPHS verse profile (SB-01 to SB-20) is unchanged and still produces no total; the two profiles have separate requests, services, component tables and provenance and are never mixed.
- **Evidence for the Raman profile**: every formula was run on Raman's own printed inputs and compared with his printed results (68 tests): Uchcha, Dig, Nathonnatha, Paksha, Tribhaga, the ahargana lords, Hora and Kranti match; 47 of 49 Saptavargaja relation cells match the locked varga schemes; Ayana matches except two of Raman's arithmetic slips; Cheshta mean elements, kendras and values match within 0.02 Virupa; 24 of 29 Drishti cells match exactly and the pindas within 0.6. Raman's condensed ahargana independently reproduces the Santhanam BPHS Ch. 27 note example (1 June 1984). All book slips are recorded (SR-24).
- **WP-G facts object (JN-19)**: `JaiminiFactsService` returns planet-level Rashi Drishti, Bhava and Graha Padas, Karakamsa and the Chara Karaka ranking for one Kundli with provenance and `standards_version = 1.21.0`.
- **Tarot provenance (TA-11)**: every layout records deck, spread and stream provenance (additive).
- **Evidence bundle (EV-01 to EV-10)**: `pandit_rule_engine.phase9_evidence` adds optional `kp`, `shadbala`, `jaimini`, `chinese` and `tarot` sections; transport only; omitted when absent (earlier bundles hash as before); a Shadbala total cannot be recorded as successful while any component is not evaluable; one Shadbala profile per bundle.
- **Roadmap documents**: `Phases.md` Phase 9 gains a status block (original text kept); standards v1.21.0; source registry (Raman entry, `IMAGE-ORIGINAL-ENGLISH` level, Group 22, conflicts, profile table); architecture interface rows; READMEs; versions astro-engine 0.10.0 and rule-engine 0.10.0.

### B. Evidence confidence (owner's scale)
- HIGH (read directly in the cited source at page-image level, numerically reproduced): Raman profile formulas and constants; WP-G Arudha/Karakamsa/planet-level Rashi Drishti; KP sub table (202 rows, OCR-level but exact numeric agreement); Chinese solar terms (HKO).
- MEDIUM: Chinese day count (secondary almanacs agree); KP significator and Ruling Planets rules (OCR-level prose); BPHS Ch. 27 verse profile (OCR-level).
- LOW or open: the book contradictions exposed as readings (SR-06, SR-09); the KP day-lord convention; the Chinese day boundary and time basis -- all no-default choices.

### C. Validation (local, before the commits)
- astro-engine 1410 passed (1340 + 68 Raman + 1 Jaimini facts + 1 Tarot provenance); rule-engine 335 passed (317 + 18 new: 17 fixture-based evidence tests and 1 end-to-end test that is skipped where Swiss Ephemeris is absent, as in the rule-engine CI job); agent 2, knowledge 1, verification 1, contracts 2, shared 1, server 5.
- Ruff lint and format, mypy strict clean (server's two local-only `psycopg` stub errors are identical on the untouched baseline and absent in CI); repository-integrity scans and `git diff --check` clean.

### D. Remaining work (not hidden)
- Not implemented, owner-accepted: Lal Kitab, Nadi, general Horary, Vastu, Feng Shui, Jaimini Dashas, Tarot meanings. Excluded: Ayurdaya. Research only: BPHS Ch. 28 Ishta/Kashta and Bhava Bala.
- No Phase 6 rule reads any Phase 9 evidence section; `requires_shadbala` rules are still `NOT_EVALUABLE` until a rule-content work package consumes a chosen Shadbala profile (a methodology choice for the owner).
- KP remains a foundation (no judgment or timing); Chinese remains the calendar pillars.
- Phase 10 (Panchang, Muhurta & Calendar) is next and needs the owner's go-ahead.

### E. Commits, push and CI
- Commits (author and committer `iamankoo <aniketraj00384@gmail.com>`, no AI attribution): `adcebca` docs: lock Phase 9 closure and evidence hardening (standards v1.21.0); `bee6041` feat: the modern Raman Shadbala profile with totals; `8dac48a` feat: WP-G Jaimini facts object and Tarot layout provenance; `e953e65` feat: Phase 9 WP-E to WP-I facts in the evidence bundle (rule-engine 0.10.0); `a195287` chore: astro-engine 0.10.0 and README; `4f02652` docs: §35 handoff.
- Push: `45fd37a..4f02652`, first attempt; `origin/main` verified equal to `4f0265246fb7a733597af631856918820ac54e21`.
- CI run `36118415625` (event `push`, commit `4f02652`, covering all six commits): completed, conclusion success; 15 of 15 jobs succeeded, each inspected with its steps; the only skipped steps are the established by-design ones ("Install domain services" outside `server`; `packages/ui` Lint, Format check and Test; `infrastructure/migrations` mypy and pytest); the check-runs API reports 15 check runs, all `success`. Job logs: `services/astro-engine` 1410 passed (matching the local run); `services/rule-engine` 320 passed, 5 skipped (the 17 new fixture tests run; the new end-to-end module joins the four existing `importorskip("swisseph")` modules, as CI does not install astro-engine there); `server` 5 passed. The CI result of this §35.E record itself is in GitHub Actions for the commit that adds it.

## 36. Shadbala Method Policy and Phase 10 (Panchang, Muhurta and Calendar) (2026-09-25) — Completion and Handoff

**Status: Phase 10 is implemented for its source-verified scope**, with the items in D not implemented and the owner decisions in E open (`Phases.md` Phase 10 status block; `docs/ASTROLOGY_STANDARDS.md` v1.23.0, PC-01 to PC-31 and MU-01 to MU-14). The Shadbala method policy is in force (v1.22.0, SM-01 to SM-12). Owner directives of 2026-09-25: accept the Phase 9 closure; set the Shadbala method policy; approve Phase 10.

Base commit before this work: `5c3415f` (§35).

### A. Shadbala method policy (v1.22.0)
- `ShadbalaMethodService` selects exactly one method per request: `MODERN_RAMAN` (the default for user-facing Shadbala; the Raman profile) or `BPHS_VERSE_REFERENCE` (the verse profile, still with no total). The two are never combined; the planets of a result equal the chosen profile's own output (tested).
- Every result exposes method, method version (1.0.0), profile, sources and component provenance, source confidence (Raman HIGH, BPHS MEDIUM), assumptions, methodology choices, unresolved choices, not-evaluable components (with reasons) and per-planet complete/partial totals, and says the Raman totals are not universally authoritative.
- Raman's two contradictions (Drekkana order, Moon benefic rule) are caller-configured or reported as not selected: every option is run, components that differ become `NOT_EVALUABLE(methodology_reading_not_selected)`, and the totals under every option are returned (reproducible by configuring them). On Raman's own example only Venus's Drekkana changes.
- Rule use goes only through `pandit_rule_engine.shadbala_gate.shadbala_for_rule`: a total only from a complete `MODERN_RAMAN` result with an exact birth time; otherwise one precise reason. No strength threshold is locked, so no shipped rule calls it and the Phase 6 strength rules keep `requires_shadbala`.

### B. Phase 10 (v1.23.0)
- **Research (Group 23)**: Calendar Reform Committee report (1955; recommendations and two printed months checked as page images), Sewell and Dikshit, *The Indian Calendar* (1896, OCR), *Kalaprakasika* (Iyer 1917; pp. 168 and 175-177 as page images, the rest OCR), Raman, *Muhurtha* (1948, OCR, modern). Surya Siddhanta not read (download failed); Muhurta Chintamani still has no English text read; Brihat Samhita downloaded, not read.
- **Panchang**: the Hindu day from sunrise to next sunrise; every Tithi, Nakshatra, Yoga and Karana with exact instants (kshaya and repeated flagged); CRC sunrise (Sun's centre, 30 minutes of refraction) as default, the Phase 4 upper-limb sunrise as an explicit alternative; moonrise/moonset; amanta and purnimanta months, adhika and kshaya, Saka and Chaitradi Vikrama years under both saura frames with no default; equal horas; Rahu Kalam (translator's note), Yamaganda, Gulika Kalam; Nakshatra Panchaka; Bhadra (Vishti). Golden test: the CRC's printed calendar for 22 March - 21 May 1954, 61 days and 16 phenomena within one minute, one printed slip recorded.
- **Special points**: upagrahas (two BPHS readings, the translator's worked example reproduced), Gulika/Mandi (three readings), Bhava, Hora, Ghatika and Varnada Lagnas, Pranapada (two Sun readings).
- **Muhurta**: Vivaha, Griha Pravesha (= housewarming) and Chaula (= mundan) rule sets from Kalaprakasika plus Raman's Tarabala, Chandrabala and Panchaka; factor facts with sources, no verdict, no statements of effect; `evaluate` at an instant and `search` over up to 31 days; inputs not collected are `NOT_EVALUABLE`.
- **Evidence bundle**: optional `panchang` section (transport only); earlier bundles hash as before.
- **Versions**: standards v1.22.0 then v1.23.0; astro-engine and rule-engine 0.11.0 then 0.12.0.

### C. Validation (local, before the commits)
- astro-engine 1561 passed (1410 + 17 Shadbala method + 134 Phase 10: 81 CRC golden, 23 Panchang, 11 special points, 19 Muhurta); rule-engine 363 passed (335 + 19 Shadbala policy + 8 Panchang evidence + 1 end-to-end test that is skipped where Swiss Ephemeris is absent); contracts 2, shared 1, agent 2, knowledge 1, verification 1, server 5; migrations has no tests.
- Ruff lint and format, mypy strict clean for both engines; repository-integrity scans (forbidden names, attribution) and `git diff --check` clean.

### D. Not implemented (not hidden)
- Choghadiya and Gowri Panchangam (no primary source read); unequal horas; Bhadra residence; regional solar calendars (Tamil, Bengali, Malayalam, Odia); Karttikadi/Ashadhadi Vikrama and current Saka years; Muhurta purposes other than the three; heliacal rising/setting of Venus and Jupiter; Kalaprakasika's month rule for marriage (month system unspecified).
- No Phase 6 rule reads the Panchang, special points or the Shadbala gate yet.

### E. Owner decisions open
1. The saura-frame default (PC-15): the CRC fixed 23 deg 15 min frame (the 1955 recommendation) and the Lahiri frame (what present-day almanacs publish) place adhika months a month apart in many years (2023, 2026).
2. Muhurta rules live in astro-engine data (MU-03), not in the Phase 6 rule YAML; confirm or move.
3. Choghadiya and Gowri: provide or approve a source.
4. Further Muhurta purposes and any strength threshold for Shadbala-based rules.

### F. Commits, push and CI
- Commits (author and committer `iamankoo <aniketraj00384@gmail.com>`, no AI attribution): `7c9cccf` feat: add the Shadbala method policy (MODERN_RAMAN default, BPHS_VERSE_REFERENCE reference); `23eeb01` feat: add Phase 10 Panchang, calendar, special points and Muhurta (standards v1.23.0); plus this documentation commit.
- Push: `5c3415f..23eeb01`, first attempt; `origin/main` verified equal to `23eeb0162cb7185e115795366b9f9363d08df7d0`.
- CI run `36135679187` (event `push`, commit `23eeb01`, covering both commits): completed, conclusion success; 15 of 15 jobs succeeded; all 173 steps inspected individually; the only skipped steps are the by-design ones ("Install domain services" outside `server`; `packages/ui` Lint, Format check and Test; `infrastructure/migrations` mypy and pytest). astro-engine job: 1561 passed. rule-engine job: 347 passed, 6 skipped (module-level `importorskip("swisseph")`, the new end-to-end module included; astro-engine is not installed in that job, as before).
