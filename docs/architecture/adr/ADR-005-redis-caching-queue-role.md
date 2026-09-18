# ADR-005: Redis caching/queue role

Status: Locked (Phase 2)

## Context
Several read paths (Panchang for a given date/location, transit state, repeated chart requests, knowledge retrieval, rate-limit counters) are expensive to recompute per-request but are deterministic given the same inputs. Several write paths (report generation, knowledge ingestion, embedding generation, backtesting jobs) are long-running and should not block a request/response cycle. Introducing a dedicated message broker (e.g. Kafka) for this project's current scale is not justified.

## Decision
Redis serves two roles only: (1) a cache in front of deterministic computations and session/rate-limit data, and (2) a lightweight queue for background jobs (e.g. via RQ/Celery-with-Redis-broker or equivalent — exact library choice deferred to the phase that implements it). Redis is never the source of truth for any fact; the calculation engine (or database) always is (see `docs/ARCHITECTURE.md` §"Caching Architecture").

## Consequences
- Cache invalidation is driven by `calculation_config` changes and TTLs, not manual cache management.
- Background jobs must be idempotent (safe to retry) since Redis-backed queues do not guarantee exactly-once delivery.
- If job volume or delivery-guarantee needs later exceed what a Redis-backed queue provides, introducing a dedicated broker is a scaling-strategy decision (`docs/ARCHITECTURE.md` §"Scaling Strategy"), not assumed now.
