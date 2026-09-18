# ADR-007: API Gateway vs. FastAPI composition root, and where the FastAPI app lives

Status: Locked (Phase 2 — new decision, resolves the open item in `docs/ARCHITECTURE.md` §"Known Contradictions" item 2b)

## Context
`Phases.md` Phase 2's diagram distinguishes `API Gateway` from `FastAPI` as two separate boxes. Separately, the repository-structure reconciliation done before Phase 1 locked `apps/{mobile, web, admin}` and `services/{astro-engine, rule-engine, agent, knowledge, verification}`, with no entry for the FastAPI HTTP layer that earlier drafts had called `apps/api`. That gap was explicitly left open rather than silently decided. Phase 2's mandate ("design the complete technical architecture... sufficiently precise that Phase 3+ engineers can implement the system without repeatedly redesigning its foundations") requires resolving it now.

## Decision
1. **API Gateway** is an edge infrastructure component, not application code. It is responsible for routing, TLS termination, authentication-token enforcement, request validation, rate limiting, request-ID injection, coarse-grained API versioning, abuse protection, and observability-header propagation (see `docs/ARCHITECTURE.md` §"API Gateway"). It is configuration/infrastructure (e.g. a reverse proxy or managed gateway), owned under `infrastructure/`, not a Python package under `apps/` or `services/`.
2. **FastAPI** is the application-level HTTP layer that composes the five canonical services into callable endpoints (see `docs/ARCHITECTURE.md` §"API Architecture" for endpoint categories). Because it composes all five services rather than belonging to one, and because `apps/` is reserved for client-facing surfaces a person installs or opens (mobile app, web app, admin app) rather than a server, FastAPI's code does not belong under `apps/` and is not a sixth canonical service. It lives in a new top-level directory, **`server/`**, sibling to `apps/`, `services/`, and `packages/`. `server/` contains routers per API category, dependency wiring (auth, DB sessions, service clients), and no business logic of its own — all business logic stays in the five services.

This is additive to the locked structure: it does not rename or remove any locked service or app name; it adds one new top-level directory whose necessity Phase 2's own gateway/FastAPI distinction makes unavoidable.

## Consequences
- `docs/ARCHITECTURE.md` §"Repository Structure" is updated to include `server/`.
- `docs/ARCHITECTURE.md` §"Known Contradictions" item 2 is marked fully resolved, pointing here.
- Phase 3 (Repository & Engineering Foundation) and Phase 17 (Backend Platform) implement `server/` and the gateway configuration respectively; this ADR only fixes where they go and what they own.
