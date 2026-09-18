# ADR-004: PostgreSQL + pgvector as the sole database technology

Status: Locked (Phase 2)

## Context
Pandit Ji needs both relational, transactional storage (users, profiles, charts, dashas, conversations, audit) and vector similarity search (RAG retrieval over the knowledge corpus). Introducing a second database technology (a dedicated vector DB, a document store, etc.) adds operational surface area without a demonstrated need at this project stage.

## Decision
PostgreSQL is the single system of record, with the `pgvector` extension providing vector storage/search inside the same database (`knowledge.embeddings`). No second database technology is introduced. Redis is used only for caching and lightweight queueing (see ADR-005), never as a system of record for facts.

## Consequences
- One database to back up, secure, and migrate; one connection pool per service.
- Schema-per-domain organization (`docs/ARCHITECTURE.md` §"Database Architecture") keeps ownership clear without needing separate database instances per service.
- If vector search performance or scale ever exceeds what `pgvector` can handle, that would be a measured-bottleneck decision to revisit (see `docs/ARCHITECTURE.md` §"Scaling Strategy"), not a default.
