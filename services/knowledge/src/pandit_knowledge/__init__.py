"""knowledge: source-backed astrology knowledge (Phase 12, standards v1.26.0 KB-01 to KB-42).

A structured store (concepts, statements, terms, rule references, domain mappings,
exceptions) and an explanatory store (chunks and embeddings in PostgreSQL + pgvector), both
versioned and sealed, with bounded retrieval that returns provenance. Library and internal
service interfaces only: HTTP is Phase 18, narration Phase 15, the final model Phase 14.

Never a source of chart facts: a retrieved chunk is knowledge text, stamped
``KNOWLEDGE_TEXT_NOT_A_CHART_FACT``; chart facts and rule results come only from the
deterministic pipeline (``astro-engine`` and ``rule-engine``).
"""

from pandit_knowledge._version import __version__
from pandit_knowledge.health import get_health

__all__ = ["get_health", "__version__"]
