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
