# Pandit Ji — Technology Stack

## Status

**LOCKED BASELINE** (foundational categories). A small number of items are explicitly deferred — see §Deferred Technology Decisions. This document does not authorize any implementation; it records technology choices for `Phases.md` Phase 3 onward to build against.

## Purpose

This is the single technology-stack decision document for Pandit Ji. It records *which* technologies are used across the client, backend, data, AI/ML, and vision layers, and *why*, given the architecture already locked in `docs/ARCHITECTURE.md` and the standards locked in `docs/ASTROLOGY_STANDARDS.md`. It does not re-derive architecture (that document is authoritative for responsibility boundaries) and does not implement anything.

There is exactly one technology-stack document. Do not create a competing one.

## Architecture Principles

Every choice below is constrained by principles already locked elsewhere, restated here only as evaluation criteria:
- **Deterministic astrology authority** (`docs/ASTROLOGY_STANDARDS.md`, ADR-001): the astronomy/astrology computation stack must be deterministic and independently testable; no AI/ML technology may sit on the fact-producing side of that boundary.
- **Self-hosted AI** (ADR-002): core AI/ML serving must be self-hostable; no production dependency on a hosted proprietary LLM API.
- **Verification as an independent layer** (ADR-006): the stack must support running verification against the same evidence a response was built from, independent of the generation path.
- **Simplicity before scale** (`docs/ARCHITECTURE.md` §"Scaling Strategy"): prefer the simplest technology that satisfies a real, identified requirement; do not add infrastructure (a broker, an orchestrator, a second database) "because it's common," only on a measured need.
- **Self-hosting and licensing discipline**: prefer technologies whose licenses cleanly support a proprietary, self-hosted, commercial product, and avoid copyleft (AGPL-class) obligations wherever a clean alternative exists — the same reasoning already applied to the Swiss Ephemeris Professional License decision (`LEGAL_REGULATIONS.md`) is applied consistently to every other technology below.

## Technology Decision Summary

Every foundational category (client, backend, database, cache, astronomy, vision framework, containers) is locked. Concrete product choices for background jobs, gateway, authentication, and LLM serving were evaluated against Pandit Ji's actual requirements (not defaulted to the most popular option) and are locked with documented reasoning below. Final LLM model checkpoint, GPU hardware, cloud provider, and production orchestrator remain deferred — see §Deferred Technology Decisions.

## Client Stack

### Mobile
**Flutter (Dart)**, targeting **Android + iOS** from one codebase — matches `features.md`'s locked platform baseline and `docs/ARCHITECTURE.md`'s `apps/mobile`. Version policy: track the current stable Flutter/Dart release line (verified current at the time of writing: Flutter 3.47.x / Dart 3.13.x) rather than pinning an exact patch — see §Versioning Policy.

### Web (and Admin)
**Next.js + React + TypeScript** — matches `docs/ARCHITECTURE.md`'s `apps/web`, per this document's own default (no conflicting authoritative choice exists). Version policy: track the current stable Next.js major line (verified current: Next.js 16). The **`apps/admin`** app (rule authoring/versioning, content ops) uses the same Next.js/React/TypeScript stack rather than a separate framework — it shares `packages/ui` and `packages/contracts` with the public web app, avoiding a second front-end toolchain for a low-traffic internal tool.

## Backend Stack

**Python + FastAPI + Pydantic v2 + SQLAlchemy 2.x (async, via `asyncpg`)** — FastAPI is already established as the HTTP application layer in `docs/ARCHITECTURE.md` §"API Architecture"; this section locks the surrounding language/validation/ORM choices. Pydantic v2 backs every request/response contract, including the Astrology Service Interfaces (`docs/ARCHITECTURE.md` §9). SQLAlchemy 2.x's async engine fits FastAPI's async request handling and the I/O-bound nature of most Pandit Ji endpoints (mostly DB reads/writes, occasional inference calls). **Alembic** handles migrations (already named in `docs/ARCHITECTURE.md`'s `infrastructure/migrations/`).

`server/` remains the FastAPI HTTP composition layer per ADR-007 — it is not one of the five canonical domain services (`astro-engine`, `rule-engine`, `agent`, `knowledge`, `verification`); this technology choice does not change that boundary.

## API Gateway

**Traefik.** Evaluated against Kong, Nginx, and a managed cloud API gateway:
- Traefik provides native Docker/Compose service discovery (labels-based routing), which fits the project's Docker Compose-first development model (§Development Environment) without extra configuration glue.
- Built-in TLS/Let's Encrypt integration and a middleware chain that covers rate limiting, request-header injection (request IDs), and auth-forwarding — directly matching the API Gateway responsibilities already locked in `docs/ARCHITECTURE.md` §4 (routing, TLS termination, authN enforcement, rate limiting, request IDs, versioning, abuse protection, observability propagation) without needing a scripting layer (unlike bare Nginx, which needs Lua/`njs` for equivalent dynamic behavior).
- Lighter operationally than Kong (no separate gateway database/control-plane to run).
- Self-hostable, open-source (MIT), fits the self-hosting principle.
- Local development compatibility: runs as another Compose service in front of `server/`; production compatibility: the same configuration model scales from Compose to a container-orchestrator deployment later, without a rewrite.
- Traefik remains **outside application/domain logic** — it only ever routes to `server/`; no astrology-specific or business-logic-aware routing lives in the gateway (`docs/ARCHITECTURE.md` §4's explicit "not the gateway's job" boundary is unchanged).

## Authentication

**Keycloak (OIDC / OAuth 2.0)**, self-hosted. Evaluated against a custom lightweight JWT auth service and hosted identity providers (e.g. Auth0/Clerk):
- **Self-hosting**: a hosted third-party identity provider would route every user's authentication (and, indirectly, sensitive account/profile linkage) through an external vendor — inconsistent with the project's data-minimization and no-unnecessary-third-party-sharing principles (`PRODUCT_POLICIES.md`), even though the self-hosted-AI requirement is formally scoped to core astrology reasoning, not identity. Keycloak is fully self-hostable.
- **Mobile/web/backend compatibility**: standard OIDC/OAuth2 flows (Authorization Code + PKCE for mobile/web clients, client-credentials for service-to-service where ever needed) are well-supported by mature libraries on Flutter, Next.js, and FastAPI alike.
- **User management / token management**: Keycloak provides account management, password reset, MFA, session/token (access + refresh) lifecycle, and an admin console out of the box — these are exactly the flows a small team should not hand-roll for a product handling sensitive birth data (auth is a classic high-risk "don't build it yourself" surface).
- **Security**: mature, widely audited OIDC implementation, actively maintained.
- **Operational complexity**: the real cost of this choice — Keycloak runs its own JVM process and its own PostgreSQL-backed store (isolated from Pandit Ji's own schemas, per `docs/ARCHITECTURE.md` §"Security Architecture"'s database-isolation rule). This is a one-time infrastructure cost, accepted in exchange for not re-implementing secure auth flows.
- Authorization (resource ownership — does this token's user own this birth profile/report/conversation) remains `server/`'s and the owning service's job per `docs/ARCHITECTURE.md` §"Authentication Architecture" — Keycloak only issues and validates identity/tokens, it does not make domain-authorization decisions.

## Database

**PostgreSQL**, the sole database technology (ADR-004). Version policy: track the current stable major release line (verified current: PostgreSQL 18.x). Schema-per-domain as already defined in `docs/ARCHITECTURE.md` §"Database Architecture."

## Vector Search

**pgvector**, running inside the same PostgreSQL instance (ADR-004) — used only for `knowledge.embeddings` (RAG retrieval) and, separately-namespaced, user-memory semantic retrieval (`docs/ARCHITECTURE.md` §"Memory Architecture"). Relational data (facts, state, evidence, audit) and vector data (embeddings) are stored in the same database but never in the same tables — a fact table never carries a vector column. Indexing approach (HNSW vs IVFFlat) is an implementation detail selected when `knowledge` is built (Phase 12), not fixed here.

## Cache

**Cache/queue layer runs on the Redis wire protocol; default deployment is Valkey (BSD-licensed, Linux Foundation fork), with Redis itself as an interchangeable alternative** — see §Licensing Considerations for why. Used per ADR-005: caching (Panchang/transit/chart-request results, knowledge retrieval, session/rate-limit data) and as the backing broker/result-store for background jobs (§Background Jobs below). **Never the source of truth for astrology calculations** — `astro-engine`/the `charts`/`dashas`/`transits`/`panchang` tables remain authoritative (`docs/ARCHITECTURE.md` §"Caching Architecture").

## Background Jobs

**Celery**, with the Redis-protocol layer above as both broker and result backend. Evaluated against RQ (simpler, but weaker built-in periodic-task support) given Pandit Ji's actual workloads (`docs/ARCHITECTURE.md` §"Queue Architecture"): report generation, knowledge ingestion/embedding, notifications, long-running AI tasks, and — critically — **periodic/scheduled jobs** (daily Panchang precompute, scheduled backtesting runs per `Phases.md` Phase 21, periodic knowledge re-ingestion). Celery Beat's native scheduling covers this without a separate cron/scheduler service; RQ would need an add-on (`rq-scheduler`) for the same coverage. Celery with a Redis-protocol broker avoids introducing a second broker technology (no RabbitMQ) — this is the simplest architecture that satisfies the actual requirement, not a default reach for Celery's full feature surface. **Kafka is explicitly not introduced** — nothing in Pandit Ji's workload list needs a distributed log/streaming platform.

## Astrology Computation

**Swiss Ephemeris** (Professional License, already locked — `LEGAL_REGULATIONS.md`) is the sole astronomical calculation foundation, accessed via `astro-engine` (`docs/ARCHITECTURE.md` §"Astrology Engine Architecture"). Strict separation, restated as a technology-stack constraint:

```
Swiss Ephemeris  →  Astronomical calculations  (astro-engine; deterministic, versioned)
Astrology rules  →  Interpretation              (rule-engine; deterministic rule evaluation)
LLM              →  Narration                   (agent + AI Reasoner; never computes a position)
```

No ML/LLM technology in this stack is permitted to calculate a planetary position, house, dasha date, or any other astronomical/astrological fact — this is the same invariant as ADR-001, stated here so the technology choices themselves can't be misread as blurring it.

## Rule Engine

No third-party rule-engine product is adopted (`docs/ARCHITECTURE.md` §"Rule Engine Architecture" already made this call: a small hand-rolled forward-chaining evaluator in Python, re-evaluated against `experta`/`durable_rules` during Phase 6 if warranted). Rule definitions are authored as versioned YAML (`services/knowledge/rules/*.yaml`), not a proprietary rule-engine DSL — this keeps the rule content plain-text, diffable, and reviewable like code, with no additional runtime dependency.

## Knowledge System

PostgreSQL + pgvector (above) for storage/retrieval; standard Python text-processing tooling (chunking/embedding pipeline, implementation deferred to Phase 12) for ingestion. No separate document database or search engine (e.g. Elasticsearch) is introduced — the retrieval need (RAG over a moderate, curated corpus) does not justify a second search technology at this stage; revisit only on a measured retrieval-quality or scale bottleneck (§"Scaling Strategy").

## AI / ML

**PyTorch** is the ML framework for both the palm-vision models (§Palm Reading / Computer Vision below) and as the underlying framework for self-hosted LLM inference (vLLM and most open-weight model tooling are PyTorch-based). The Hugging Face `transformers`/`accelerate` ecosystem is the expected supporting layer for loading/running open-weight model checkpoints, without being locked as its own top-level decision here.

## LLM Inference

Self-hosted only (ADR-002) — no production dependency on OpenAI/Gemini-style hosted APIs. Two-tier serving, both behind the same `LLMProvider`/AI Reasoner interface (`docs/ARCHITECTURE.md` §"AI Infrastructure"), so switching tiers never touches `agent` code:
- **Development**: **Ollama** — minimal setup, fast local iteration on a developer machine, adequate for functional testing of the agent/planner/verification pipeline without needing production-grade throughput.
- **Staging/Production**: **vLLM** — PagedAttention-based high-throughput serving, concurrent-request batching, broad support for open-weight model families (Qwen/Llama/Mistral and others), and an OpenAI-compatible API mode that keeps the `LLMProvider` interface implementation simple.

**Model framework**: PyTorch (above). **Model checkpoint**: not selected here — see §Deferred Technology Decisions; model benchmarking against Hindi/Hinglish/English/reasoning/tool-calling criteria is `Phases.md` Phase 14's job (`research/AI_MODELS.md`), and each candidate model family's license (Qwen/Llama/Mistral variants carry different, sometimes conditional, license terms) must be checked at that time, not assumed permissive here.

## Palm Reading / Computer Vision

AI Palm Reading is a locked product feature (`features.md` §34); its dedicated implementation phase is `Phases.md` Phase 13. Technology responsibility separation, matching the pipeline already locked there and in `docs/ASTROLOGY_STANDARDS.md`'s Palmistry standard:

```
Palm Image → Image preprocessing → Hand detection → Landmarks/geometry
    → Palm region → Palm-line/feature extraction (vision model) → Structured palm facts
```

- **OpenCV**: image preprocessing and general computer-vision operations (quality validation, normalization, cropping).
- **NumPy**: numerical image/geometry processing underlying the above.
- **MediaPipe**: hand detection, hand landmarks, and left/right localization — Google's pretrained hand-landmark model is a fast, well-tested fit for this specific sub-task.
- **PyTorch**: custom palm-vision model(s) for palm-line/mount/feature extraction and learned palm-feature analysis.

**Important, locked constraint**: MediaPipe's 21-point hand-landmark output is a hand-localization/geometry tool, not a palmistry tool — it does not detect palm lines, mounts, or the features palmistry interpretation actually depends on. A dedicated vision model/pipeline (PyTorch, trained/fine-tuned specifically for palm-line and feature extraction) is required for that step, and the architecture must not claim or imply that generic hand-landmark detection alone provides palmistry interpretation. This is a technology-stack restatement of `docs/ASTROLOGY_STANDARDS.md`'s Palmistry standard and `Phases.md` Phase 13's own explicit warning — not a new decision.

## Object Storage

**S3-compatible object storage**, abstracted the same way regardless of provider — used for palm images, generated report files, and other user uploads. **MinIO** is the self-hosted default for development/on-prem parity (self-hostable, S3 API-compatible, open-source under AGPLv3 for the server — acceptable here specifically because Pandit Ji only *runs* MinIO as infrastructure and does not redistribute or modify its source, which is the boundary AGPL's copyleft actually reaches; this differs from the Swiss Ephemeris case, where Pandit Ji directly links/distributes the library inside its own product). A managed cloud S3-compatible provider is an equally valid production choice behind the same API — provider selection is deferred (§Deferred Technology Decisions), the storage *abstraction* is not.

Documented pattern:
- Binary content lives in object storage, never in PostgreSQL (no large binary files stored directly in the database — avoids DB bloat/backup-size blowup and keeps the relational store fast).
- Metadata (owner, purpose, upload time, retention class, content hash) lives in PostgreSQL, referencing the object storage key.
- **Access control**: objects are private by default; access is via the owning service checking authorization, never a publicly-readable bucket.
- **Signed URLs**: time-limited, single-use-oriented signed URLs are issued for client upload/download rather than proxying large binaries through `server/`.
- **Retention/deletion**: governed by `PRODUCT_POLICIES.md`'s Data & Privacy Principles — palm images in particular follow high-privacy, minimum-retention handling; deleting the metadata row triggers deletion of the underlying object, not just a soft-delete flag.
- **Privacy**: object storage access logging feeds the same `audit.audit_log` as other sensitive-data access (`docs/ARCHITECTURE.md` §"Security Architecture").

## Observability

**OpenTelemetry** for traces, metrics, and logs — vendor-neutral instrumentation so the backend (Grafana/Prometheus/Loki/Tempo, or an equivalent self-hostable stack) can be selected/changed later without re-instrumenting every service. Flow (matching `docs/ARCHITECTURE.md` §"Observability" exactly):

```
Client → Gateway (Traefik) → FastAPI (server/) → agent → astro-engine/rule-engine → knowledge → AI Reasoner → verification
                                    ↓ (every hop emits OTel traces/metrics/logs, correlated by the gateway-issued request ID)
                              Collector → Backend (self-hosted; product selection deferred)
```

Traefik itself supports OTel-compatible metrics/tracing export, keeping the gateway inside the same observability pipeline as the application services rather than a blind spot.

## Containers

**Docker + Docker Compose** for local development and reproducible service environments, matching `docs/ARCHITECTURE.md` §"Deployment Topology." Kubernetes/production orchestration is **not** locked here — premature for the project's current stage; evaluated later against a measured need (§"Scaling Strategy", §Deferred Technology Decisions).

## Testing

| Layer | Technology | Notes |
|---|---|---|
| Python backend/services | **pytest** | Unit + fixture-based tests for `astro-engine`/`rule-engine`/`agent`/`verification`; golden fixtures live in `datasets/`/`tests/fixtures/` (already established in `docs/ARCHITECTURE.md`). |
| Flutter | `flutter test` (widget/unit) + `integration_test` package | Standard Flutter-native tooling; no third-party test framework needed. |
| TypeScript/Next.js | **Vitest** + React Testing Library | Chosen over Jest for faster, ESM-native test runs that fit Next.js's current tooling direction; either is a reasonable choice — Vitest is locked for consistency. |
| API contract tests | **Schemathesis** (or equivalent OpenAPI-driven contract testing) against `server/`'s generated OpenAPI schema | Verifies the Astrology Service Interfaces (`docs/ARCHITECTURE.md` §9) stay contract-compliant. |
| Integration tests | **pytest** + Docker Compose test environment | Cross-service flows (e.g. diagram A's chat path) run against a real (test) Postgres/Redis via Compose, not mocks, for the paths where that matters. |
| Deterministic calculation tests | **pytest** + golden fixtures | Per `docs/ASTROLOGY_STANDARDS.md`'s reproducibility requirement — exact-match assertions, not approximate. |
| Vision tests | Dataset-driven evaluation (precision/recall/detection-rate metrics, not simple assert-equal) | Matches `research/PALM_READING.md`'s own evaluation criteria; implemented when Phase 13 is built. |
| AI evaluation tests | The Verification & Evaluation framework itself (`docs/ARCHITECTURE.md` §"Verification Architecture") | Not a generic off-the-shelf AI-eval tool — claim-fidelity/contradiction/regression testing is purpose-built for this product. |

This is a technology decision, not an implementation — none of the above is built in this task.

## Code Quality

| Ecosystem | Tooling |
|---|---|
| Python | **Ruff** (lint + format — Ruff's formatter covers what Black used to, so a separate Black dependency is not added), **mypy** (type checking, given the heavily-typed Pydantic/SQLAlchemy codebase), **pre-commit** (hook orchestration for both of the above). |
| TypeScript | **ESLint** + **Prettier** + `tsc` (TypeScript compiler, type-check mode in CI). |
| Flutter | `dart analyze` (Dart analyzer) + `dart format` (Dart formatter) — both built into the Dart SDK, no third-party linter added. |

Only tools with a concrete role in this stack are included — nothing added merely to lengthen the list.

## Development Environment

Local processes / Docker Compose (Traefik, `server/`, the five services, PostgreSQL, the Redis-protocol cache/queue layer, MinIO) — matches `docs/ARCHITECTURE.md` §"Deployment Topology"'s Development row exactly. AI inference: Ollama (local, small model) or the development-only hosted-API stopgap (ADR-2's explicitly temporary allowance) when self-hosted infra isn't yet available on a given developer's machine.

## Staging Environment

Containerized, mirrors production topology (Traefik, `server/`, five services, managed/containerized Postgres with staging-only data, Redis-protocol layer, staging object-storage bucket, vLLM on a smaller/cheaper inference instance) — matches `docs/ARCHITECTURE.md` §"Deployment Topology"'s Staging row. Used for Phase 21 validation/backtesting dry-runs before production.

## Production Environment

Containerized, scaled per `docs/ARCHITECTURE.md` §"Scaling Strategy" (start consolidated, split only on a measured bottleneck): Traefik, `server/`, five services, managed PostgreSQL with backups, Redis-protocol layer, production object-storage bucket (encrypted), vLLM production inference, Keycloak, OpenTelemetry backend, secrets management, backups. Swiss Ephemeris Professional License must be purchased/signed before this environment is activated for public/commercial use (`LEGAL_REGULATIONS.md`, `Phases.md` Phase 21 gate). Cloud provider and production orchestrator are explicitly deferred (§Deferred Technology Decisions) — this environment description fixes what must run, not where.

## Licensing Considerations

- **Swiss Ephemeris**: Professional License, locked, not yet purchased — see `LEGAL_REGULATIONS.md` (unchanged by this document).
- **Redis-protocol layer**: as of Redis 8.x, Redis itself ships under a choice of AGPLv3 (OSI-approved copyleft) or the source-available RSALv2/SSPLv1 terms; self-hosting Redis for one's own application (not reselling it as a managed service) is permitted under any of these. To avoid AGPL-copyleft exposure entirely — the same reasoning already applied to the Swiss Ephemeris decision — **Valkey** (Linux Foundation fork, BSD-3, no source-available restrictions at all) is the default, with Redis itself (under RSALv2, which explicitly permits this project's self-hosted-for-its-own-app use) as an interchangeable, license-compatible alternative if a specific Redis-only feature is ever needed.
- **PostgreSQL**: PostgreSQL License (permissive, BSD/MIT-style) — no concerns.
- **pgvector**: PostgreSQL License — no concerns.
- **Traefik**: MIT — no concerns.
- **Keycloak**: Apache 2.0 — no concerns.
- **MinIO**: AGPLv3 for the server. Acceptable here because Pandit Ji only *operates* MinIO as infrastructure (self-hosted object storage) without distributing or modifying its source — this is the boundary AGPL's copyleft actually reaches, unlike Swiss Ephemeris, which Pandit Ji links directly inside its own distributed/served product. Revisit if this distinction is ever unclear for a specific deployment shape.
- **PyTorch, OpenCV, MediaPipe, vLLM, Ollama**: permissively licensed (BSD/Apache-family) as commonly understood — verify the exact current license of the specific version adopted at implementation time, per this document's own "verify before locking" principle.
- **Open-weight LLM checkpoints** (Qwen/Llama/Mistral families): licenses vary by family and sometimes by model size/use-scale, and are **not** evaluated here — model selection is deferred to Phase 14 (`research/AI_MODELS.md`), and license terms must be checked per specific checkpoint at that time, not assumed uniform.
- **Astrology/knowledge source texts**: governed by `research/ASTROLOGY_SOURCES.md`'s and `LEGAL_REGULATIONS.md`'s copyright/licensing requirements — unchanged by this document.

## Security Considerations

Restated from `docs/ARCHITECTURE.md` §"Security Architecture" as technology-specific notes, not a new policy:
- Keycloak is the identity boundary; `server/` and the owning services still perform every resource-ownership authorization check.
- Traefik enforces TLS termination and rate limiting at the edge; internal service-to-service traffic (between `server/` and the five domain services) stays off the public gateway surface.
- Secrets (DB credentials, Keycloak client secrets, object-storage keys, LLM-serving endpoints) are supplied via environment/secret-manager configuration, never committed — the existing `.gitignore` already excludes `.env*`.
- Encryption at rest applies to PostgreSQL data and object-storage content alike (birth data, palm images, conversations); Traefik/TLS covers encryption in transit at the edge.
- OpenTelemetry logs must not carry raw sensitive payloads (birth details, palm images referenced by ID only) — same rule as `docs/ARCHITECTURE.md` §"Observability."

## Technology Selection Principles

1. Prefer the simplest technology that satisfies an actual, identified requirement from `docs/ARCHITECTURE.md` — never adopt something because it is popular or "expected."
2. Prefer self-hostable, license-clean technologies consistent with the project's self-hosting and no-AGPL-in-a-distributed-product stance.
3. Every foundational choice must be independently swappable behind the boundary `docs/ARCHITECTURE.md` already defined for it (e.g. `LLMProvider` for inference, the Astrology Service Interfaces for `astro-engine`/`rule-engine`) — a technology choice never becomes a hidden architectural coupling.
4. Do not lock a decision that legitimately belongs to a later phase (a model checkpoint, GPU hardware, a cloud provider) merely for the sake of a "complete-looking" document — defer it explicitly instead (§Deferred Technology Decisions).
5. Verify current versions/license terms against official sources before locking a technology, rather than relying on assumed/stale knowledge — this document's PostgreSQL/Flutter/Next.js version references and the Redis licensing analysis were verified this way, not asserted from memory.

## Deferred Technology Decisions

Explicitly **not** locked here — belong to a later phase, and must not be presented as decided:
- **Final LLM model checkpoint** — `Phases.md` Phase 14 (Self-Hosted AI Model), per `research/AI_MODELS.md`'s benchmarking criteria.
- **GPU hardware** (make/model/quantity) — sized against the model checkpoint chosen in Phase 14 and real load, not guessed now.
- **Cloud provider** (or fully on-prem) for staging/production hosting — a deployment decision, not a technology-stack decision; `docs/ARCHITECTURE.md` §"Deployment Topology" already declines to fix this.
- **Production container orchestrator** (Kubernetes or otherwise) — evaluated only against a measured scaling need (`docs/ARCHITECTURE.md` §"Scaling Strategy"); Docker Compose is sufficient for the current stage.
- **Exact production topology** (instance sizing, replica counts, region layout) — an operational detail for Phase 18/21, not a technology choice.
- **Observability backend product** (which self-hosted Grafana-stack-equivalent, specifically) — OpenTelemetry (the instrumentation standard) is locked; the storage/visualization backend behind it is not, since it can change without re-instrumenting anything.
- **API contract-testing tool's exact package** (Schemathesis named above as the current best fit) — reconfirm at Phase 18 implementation time against whatever `server/`'s OpenAPI generation looks like by then.

## Versioning Policy

Track supported stable release lines rather than pinning every dependency to one exact patch version — a maintainable technology baseline, not a frozen snapshot. Security patch releases are applied promptly; a major-version upgrade is a deliberate, tested, documented change (matching `docs/ASTROLOGY_STANDARDS.md`'s own versioning discipline, applied here to infrastructure rather than calculation standards).

| Technology | Major/minor baseline | Version policy | Reason |
|---|---|---|---|
| PostgreSQL | 18.x | Track current supported stable major release | Verified current stable line at time of writing. |
| Flutter / Dart | 3.47.x / 3.13.x | Track current stable channel | Verified current at time of writing; Flutter's stable channel moves fairly quickly. |
| Next.js | 16.x | Track current stable major | Verified current at time of writing. |
| Python | 3.12+ | Track a supported CPython minor version | Matches FastAPI/SQLAlchemy 2.x/Pydantic v2 support windows. |
| FastAPI, Pydantic, SQLAlchemy | Latest stable 2.x-compatible releases | Track upstream stable releases | Already locked as libraries in §Backend Stack; patch/minor updates are routine, not re-evaluated per bump. |

## Technology Decision Table

| Layer | Technology | Status | Purpose |
|---|---|---|---|
| Mobile | Flutter/Dart | Locked | Android/iOS client |
| Web/Admin | Next.js/React/TypeScript | Locked | Web app + internal admin app |
| Backend | Python/FastAPI | Locked | HTTP/API composition layer (`server/`) |
| Validation | Pydantic v2 | Locked | Request/response contracts |
| ORM | SQLAlchemy 2.x (async) | Locked | Database access |
| Database | PostgreSQL | Locked | Primary/sole database |
| Vector | pgvector | Locked | Vector retrieval (knowledge, memory) |
| Cache/Queue backend | Valkey (Redis-protocol; Redis interchangeable) | Locked | Cache, transient state, rate limiting, job broker |
| Jobs | Celery | Locked | Async/background/periodic jobs |
| Gateway | Traefik | Locked | Edge routing, TLS, rate limiting |
| Auth | Keycloak (OIDC/OAuth2) | Locked | Identity/access, self-hosted |
| Astronomy | Swiss Ephemeris (Professional License) | Locked | Deterministic astronomy |
| Rule engine | Hand-rolled (Python) + versioned YAML | Locked | Astrology rule evaluation |
| ML framework | PyTorch | Locked | ML/vision, LLM-adjacent tooling |
| Vision | OpenCV + NumPy + MediaPipe + PyTorch | Locked | Palm vision pipeline |
| LLM serving | Ollama (dev) / vLLM (staging/prod) | Locked | Self-hosted AI inference |
| Storage | S3-compatible (MinIO self-hosted default) | Locked | User files (palm images, reports) |
| Observability | OpenTelemetry | Locked | Traces/metrics/logs |
| Containers | Docker + Docker Compose | Locked | Local dev + reproducible environments |
| Testing | pytest / Flutter test / Vitest / Schemathesis | Locked | Per-layer test technology |
| Code quality | Ruff+mypy / ESLint+Prettier+tsc / dart analyze+format | Locked | Per-ecosystem lint/format/type-check |
| LLM checkpoint | — | **Deferred** | Phase 14 |
| GPU hardware | — | **Deferred** | Sized in Phase 14 |
| Cloud provider | — | **Deferred** | Deployment decision |
| Orchestrator | — | **Deferred** | Only on measured scaling need |

## Change Log

- **v1.0.0** (pre-Phase-3): initial technology-stack lock. Established client (Flutter/Next.js), backend (FastAPI/Pydantic v2/SQLAlchemy 2.x), database (PostgreSQL/pgvector), cache/queue (Valkey+Celery), gateway (Traefik), auth (Keycloak), astronomy (Swiss Ephemeris — carried over from `LEGAL_REGULATIONS.md`), ML/vision (PyTorch/OpenCV/MediaPipe), LLM serving (Ollama/vLLM), storage (S3-compatible/MinIO), observability (OpenTelemetry), containers (Docker/Compose), and testing/code-quality tooling per ecosystem. PostgreSQL/Flutter/Next.js version baselines and the Redis-vs-Valkey licensing analysis were verified against current sources at lock time, not assumed. LLM checkpoint, GPU hardware, cloud provider, and production orchestrator remain explicitly deferred.
