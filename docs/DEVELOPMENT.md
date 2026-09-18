# Development Guide

This is the Phase 3 (Repository & Engineering Foundation) developer guide. For architecture, read `docs/ARCHITECTURE.md`; for the roadmap, `Phases.md`; for locked technology choices, `TECH_STACK.md`.

## Prerequisites

- Python 3.12+ (each Python component declares `>=3.10` for portability, but 3.12 matches `TECH_STACK.md`'s policy and the Docker images)
- Node.js 22+ and npm
- Flutter (stable channel) and Dart
- Docker + Docker Compose
- `pre-commit` (`pip install pre-commit`)

## Clone and configure

```
git clone https://github.com/iamankoo/Pandit-Ji.git
cd Pandit-Ji
cp .env.example .env
pre-commit install
```

Never edit `.env.example` with real secrets — copy it to `.env` (gitignored) and edit that instead.

## Start local infrastructure

```
docker compose -f infrastructure/docker-compose.yml up -d postgres valkey keycloak minio
```

This starts PostgreSQL+pgvector, Valkey, Keycloak, and MinIO. The `server` and `gateway` (Traefik) services can be started the same way once you've built the image (`docker compose -f infrastructure/docker-compose.yml up --build`), or you can run `server/` directly on the host against this infrastructure (see below) — both work; running it directly on the host is faster for iterating during Phase 3+.

Apply the database migration foundation:

```
cd infrastructure/migrations
pip install -e ".[dev]"
alembic upgrade head
```

## Run the backend (`server/`) on the host

Each Python component is installed independently (`docs/ARCHITECTURE.md` §"Repository Structure" — clear package boundaries), in this order (foundation packages first):

```
pip install -e packages/contracts
pip install -e packages/shared
pip install -e "services/astro-engine[dev]"
pip install -e "services/rule-engine[dev]"
pip install -e "services/agent[dev]"
pip install -e "services/knowledge[dev]"
pip install -e "services/verification[dev]"
pip install -e "server[dev]"

uvicorn pandit_server.main:app --reload
```

`/healthz` should return `{"status": "alive"}` immediately; `/readyz` reports PostgreSQL/Valkey connectivity plus each service's own health once the infrastructure above is running.

## Run the clients

```
cd apps/web && npm install && npm run dev      # http://localhost:3000
cd apps/admin && npm install && npm run dev     # http://localhost:3001
cd apps/mobile && flutter pub get && flutter run
```

## Testing

| Component | Command |
|---|---|
| Each Python component (`packages/*`, `services/*`, `server`, `infrastructure/migrations`) | `pytest` (run from that component's own directory) |
| `apps/web`, `apps/admin` | `npm test` |
| `apps/mobile` | `flutter test` |

Unit tests live inside each component's own `tests/`. Cross-component integration/contract tests and shared fixtures live in the repository-root `tests/` (see `tests/README.md`) and `datasets/fixtures/`.

## Linting / formatting / type-checking

| Component | Lint | Format check | Type-check |
|---|---|---|---|
| Python components | `ruff check .` | `ruff format --check .` | `mypy src` |
| `apps/web`, `apps/admin` | `npm run lint` | `npm run format` | `npm run typecheck` |
| `apps/mobile` | `flutter analyze` | `dart format --set-exit-if-changed lib test` | (part of `flutter analyze`) |

`pre-commit run --all-files` runs the fast subset of these automatically before every commit (see `.pre-commit-config.yaml`).

## CI

`.github/workflows/ci.yml` runs the same checks (plus `docker build`/`docker compose config` and repository-integrity scans) on every pull request and push to `main`. See that file for the exact job list.

## Contributing

See `CONTRIBUTING.md` at the repository root for the engineering workflow (branching, commit conventions, PR expectations).
