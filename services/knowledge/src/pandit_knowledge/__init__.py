"""knowledge: structured astrology knowledge (rule source-of-truth) and
unstructured knowledge (classical text/remedy corpus, RAG retrieval).

Phase 3 scope only: package boundary, config, health check. Ingestion
pipeline and retrieval are implemented starting `Phases.md` Phase 12 --
see `docs/ARCHITECTURE.md` §"Knowledge Architecture".

Never a source of chart facts -- retrieval results feed narration/remedy
phrasing only.
"""

from pandit_knowledge._version import __version__
from pandit_knowledge.health import get_health

__all__ = ["get_health", "__version__"]
