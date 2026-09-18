# knowledge

Structured astrology knowledge (rule source-of-truth) and unstructured knowledge (classical text/remedy corpus, RAG retrieval). Canonical service name — do not rename to `knowledge-base`.

**Responsible for**: `rules/*.yaml` source-of-truth, ingestion pipeline, embeddings, retrieval (see `docs/ARCHITECTURE.md` §"Knowledge Architecture").

**Not responsible for**: being treated as a source of chart facts — retrieval feeds narration/remedy phrasing only.

## Phase 3 status

Foundation only: package boundary, config, health check, empty `rules/` directory. No ingestion pipeline or content yet — that begins in `Phases.md` Phase 12.

## Local development

```
pip install -e ../../packages/contracts
pip install -e ../../packages/shared
pip install -e ".[dev]"
pytest
ruff check .
mypy src
```
