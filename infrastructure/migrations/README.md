# Database migrations (Alembic)

Centralized Alembic setup for the single shared PostgreSQL database (`docs/ARCHITECTURE.md` §"Database Architecture" — schema-per-domain, one database).

## Phase 3 status

One migration (`0001_initial_schemas`): creates the schema namespaces (`identity`, `profiles`, `calc_config`, `charts`, `dashas`, `transits`, `panchang`, `rules`, `knowledge`, `compatibility`, `numerology`, `conversation`, `reports`, `feedback`, `audit`) and enables the `vector` extension. No domain tables yet — each schema's tables are added by the `Phases.md` phase that owns it.

## Local development

```
pip install -e ".[dev]"
export DATABASE_URL=postgresql+psycopg://pandit:pandit@localhost:5432/pandit
alembic upgrade head
```

## Creating a new migration

```
alembic revision -m "describe the change"
```
