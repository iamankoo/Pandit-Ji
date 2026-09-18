# tests (repository-root)

Cross-cutting tests that span more than one component. Unit tests for a single component live inside that component's own `tests/` directory (e.g. `services/astro-engine/tests/`), not here.

- `integration/` — cross-service flows (e.g. the full chat path through `server` → `agent` → `astro-engine`/`rule-engine`/`knowledge` → verification), added as each of those pieces is implemented.
- `contract/` — API contract tests against `server/`'s OpenAPI schema (`TECH_STACK.md` §"Testing" — Schemathesis), added once domain endpoints exist.
- `fixtures/` — shared golden fixtures used by more than one component's tests. Component-specific fixtures stay inside that component.

## Phase 3 status

Directory structure only — no cross-cutting tests exist yet, since no domain logic exists yet to integrate. Each component's own smoke/health test (see `docs/DEVELOPMENT.md` §"Testing") is the current test coverage.
