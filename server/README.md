# server

FastAPI HTTP composition layer (`docs/architecture/adr/ADR-007-api-gateway-and-fastapi-composition-root.md`). **Not** one of the five canonical domain services — it composes them.

**Responsible for**: routers, dependency wiring, the auth-token-validation handoff from the API Gateway (Traefik), request-ID propagation, structured errors, API versioning.

**Not responsible for**: business/domain logic — that lives in `services/*` and is only invoked from here.

## Phase 3 status

Foundation only: app factory, `/healthz` (liveness) + `/readyz` (readiness, checks PostgreSQL/Valkey connectivity and each of the five services' health), request-ID middleware, structured error handling, `/api/v1` versioning mount point with no domain routes yet. Domain endpoints (`/charts`, `/dashas`, `/chat`, ...) are added starting the phase that implements each corresponding engine.

## Local development

```
pip install -e ../packages/contracts
pip install -e ../packages/shared
pip install -e ".[dev]"
uvicorn pandit_server.main:app --reload
```

## Tests

```
pytest
```

## Lint / type-check

```
ruff check .
mypy src
```

## Phase 18 backend

Run the unit tests with `pytest` (SQLite, in-memory store, a throw-away RSA key and the scripted language-model double; no services needed). The integration tests run when `SERVER_TEST_DATABASE_URL` (PostgreSQL with pgvector), `SERVER_TEST_VALKEY_URL` and `SERVER_TEST_KEYCLOAK_URL` (a Keycloak started with `infrastructure/keycloak/pandit-ji-realm.json`) are set. Configuration is read from the environment (`config.py`, `.env.example`). Start a worker with `celery -A pandit_server.jobs.celery_app worker`. The API is under `/api/v1`; OpenAPI is served at `/docs`. The language model is the self-hosted Qwen3-8B on vLLM; without it chat answers `503 llm_unavailable` and there is no hosted fallback.
