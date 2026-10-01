# knowledge

Source-backed astrology knowledge: a **structured store** (concepts, statements, terms, rule references, domain mappings, exceptions), an **explanatory store** (chunks and embeddings in PostgreSQL + pgvector), versioned and sealed, with bounded retrieval that always returns provenance. Canonical service name — do not rename to `knowledge-base`.

**Responsible for** (Phase 12, `docs/ASTROLOGY_STANDARDS.md` v1.26.0 KB-01 to KB-42): sources and editions with reading level, copyright status and storage permission; planet and house knowledge as one record per source profile; terminology; references to existing rules; exceptions; house to domain mappings with an explicit support status; deterministic chunking; the embedding-provider abstraction; idempotent, resumable ingestion into immutable knowledge versions; retrieval with source, methodology, language, domain and version filters. `rules/*.yaml` remains the Phase 6 rule source-of-truth (loaded by `rule-engine`); this service never evaluates a rule.

**Not responsible for**: any chart fact, calculation or rule result (retrieval returns knowledge text stamped `KNOWLEDGE_TEXT_NOT_A_CHART_FACT`, never a statement about a user's chart); AI narration (Phase 15); the final model (Phase 14); verification (Phase 16); HTTP endpoints and the public database API (Phase 18).

## Layout

- `src/pandit_knowledge/`: `models` (records and vocabularies), `schema` (table specifications), `store` (interface and in-memory store), `pg_store` (PostgreSQL + pgvector), `content` (loads and validates the curated content), `chunking`, `embeddings`, `ingestion`, `knowledge_base` (structured read access), `retrieval`, `validation`.
- `content/`: the curated Phase 12 records (`sources.yaml`, `planets.yaml`, `houses.yaml`, `terms.yaml`, `domains.yaml`, `references.yaml`) and `corpus/waite_pictorial_key_part3.jsonl` (78 Tarot card entries, public domain). Kept outside `rules/` so the Phase 6 ruleset hash is unaffected.
- `rules/`: the Phase 6 rule YAML (unchanged by Phase 12).
- `tools/build_waite_corpus.py`: maintainer script that fetches and parses the Waite transcription (needs network; not run in CI).
- The schema lives in `infrastructure/migrations/versions/0002_knowledge_schema.py`.

## What is in the knowledge version (current content)

189 chunks (111 template renderings of structured records, labelled `PROJECT_RENDERING`; 78 verbatim public-domain Tarot entries), 110 concepts, 94 statements, 53 terms, 53 rule references, 48 house/domain mappings (6 `SOURCE_SUPPORTED`, 1 `UNRESOLVED_CONFLICT`, 41 `NOT_EVALUABLE`), 10 exceptions. Sources actually used: BPHS (Ch. 3, 11, 32), Phaladeepika (Ch. XV), Brihat Jataka (Ch. II), Waite. Deferred: numerology interpretation, Lal Kitab, remedies, any Hindi, Sanskrit or Hinglish text.

## Embeddings and languages

`HashingEmbeddingProvider` (deterministic, **lexical, not semantic**, no language) is the default for ingestion tests and CI. `SentenceTransformerProvider` loads any local sentence-transformers model (extra `embeddings`). The final model is chosen in Phase 14; a new model is a new embedding configuration and a new knowledge version, with no schema change. Measured behaviour for English, Hindi and Hinglish queries is in KB-25; the package makes no cross-language claim beyond that, and a Devanagari query against a configuration that declares no Hindi returns `CROSS_LANGUAGE_RETRIEVAL_NOT_VALIDATED`.

## Use

```python
from pandit_knowledge.content import load_content
from pandit_knowledge.embeddings import HashingEmbeddingProvider
from pandit_knowledge.ingestion import KnowledgeBuilder
from pandit_knowledge.knowledge_base import KnowledgeBase
from pandit_knowledge.models import RetrievalQuery
from pandit_knowledge.retrieval import Retriever
from pandit_knowledge.store import InMemoryKnowledgeStore  # or PostgresKnowledgeStore(engine)

store, provider = InMemoryKnowledgeStore(), HashingEmbeddingProvider()
result = KnowledgeBuilder(store, provider).build(load_content())  # sealed, idempotent
kb = KnowledgeBase(store, result.version_id)  # structured access
hits = Retriever(store, provider).retrieve(RetrievalQuery(text="profession", top_k=3))
```

## Local development

```
pip install -e ../../packages/contracts
pip install -e ../../packages/shared
pip install -e ".[dev]"
pytest
ruff check .
mypy src
```

The PostgreSQL tests (`tests/test_postgres.py`) run only when `KNOWLEDGE_TEST_DATABASE_URL` is set, for example against the Compose database or a throw-away container (they run the Alembic chain down to base and back, then truncate the knowledge tables, so use a scratch database):

```
docker run -d --name pj-pg -e POSTGRES_USER=pandit -e POSTGRES_PASSWORD=pandit -e POSTGRES_DB=pandit -p 55432:5432 pgvector/pgvector:pg18
export KNOWLEDGE_TEST_DATABASE_URL=postgresql+psycopg://pandit:pandit@localhost:55432/pandit
pytest tests/test_postgres.py
```

The regression tests (`test_integration_regression.py`) need `astro-engine` and `rule-engine` installed; the optional model tests (`test_semantic_model.py`) need `sentence-transformers` and the two models already in the local Hugging Face cache (nothing is downloaded). Both are skipped otherwise.
