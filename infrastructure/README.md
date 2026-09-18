# infrastructure

- `docker-compose.yml` — development-oriented Compose foundation (PostgreSQL+pgvector, Valkey, Keycloak, MinIO, Traefik, `server`). See root `README.md`/`docs/DEVELOPMENT.md` for usage.
- `gateway/traefik/` — Traefik dynamic configuration (`docs/ARCHITECTURE.md` §"API Gateway").
- `migrations/` — Alembic migrations for the single shared PostgreSQL database.
- `environments/` — safe `.env` templates for staging/production (no real secrets — see `ENVIRONMENTS.md`).

Production/staging infrastructure is **not** provisioned by this repository (`docs/ARCHITECTURE.md` §"Deployment Topology" and `TECH_STACK.md` §"Deferred Technology Decisions" — cloud provider and orchestrator are explicitly deferred). See `ENVIRONMENTS.md` for what each environment is expected to contain.
