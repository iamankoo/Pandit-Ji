# Environments

Conventions for development, staging, and production, per `docs/ARCHITECTURE.md` §"Deployment Topology". No real staging/production infrastructure is provisioned by this repository — this document (and the `.env.example` templates in `environments/`) define what each environment must contain, for the phase that actually provisions it.

## Development

`infrastructure/docker-compose.yml` — everything runs locally via Docker Compose: PostgreSQL+pgvector, Valkey, Keycloak, MinIO, Traefik, `server`. AI inference runs on the host (Ollama) or is skipped entirely for foundation work — the base repository never requires a GPU to start (see `docs/ARCHITECTURE.md` §"Scaling Strategy" / §19 of the Phase 3 prompt).

## Staging

Containerized, mirrors production topology, staging-only data:
- Same five services + `server`, containerized
- Managed or containerized PostgreSQL+pgvector (staging data only, never production data)
- Valkey
- Keycloak (staging realm)
- Staging object-storage bucket
- Self-hosted inference (vLLM) on a smaller/cheaper instance
- Used for `Phases.md` Phase 21 validation/backtesting dry-runs before production

Configuration: `environments/staging.env.example` — copy to a real, secret-filled `.env` outside version control; never commit real staging credentials.

## Production

- Same topology as staging, scaled per `docs/ARCHITECTURE.md` §"Scaling Strategy" (start consolidated, split only on a measured bottleneck)
- Managed PostgreSQL+pgvector with backups
- Valkey
- Keycloak (production realm)
- Production object-storage bucket (encrypted)
- vLLM production inference
- Observability backend (OpenTelemetry collector + a self-hosted or managed backend — product deferred, see `TECH_STACK.md`)
- Secrets via environment/secret-manager configuration, never committed
- **Swiss Ephemeris Professional License must be purchased and the agreement signed before this environment is activated for public/commercial use** (`LEGAL_REGULATIONS.md`, `Phases.md` Phase 21 gate)

Configuration: `environments/production.env.example` — same rule: copy, fill with real secrets outside version control, never commit.

## Health checks expected in every environment

- Liveness (`/healthz`): process is alive, no dependency check.
- Readiness (`/readyz`): PostgreSQL + Valkey connectivity and each of the five services' own health.

Actual cloud provisioning, orchestration, and deployment automation belong to `Phases.md` Phase 18 (Backend Platform) and Phase 21 (Production Launch) — not this Phase 3 foundation.
