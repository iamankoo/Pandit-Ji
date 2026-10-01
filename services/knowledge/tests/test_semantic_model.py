"""Optional checks with real local sentence-transformers models (KB-21, KB-25).

Skipped unless the models are already in the local Hugging Face cache (no download is ever
attempted). They record what was *measured*; they do not turn a measurement into a product claim.
See the standards KB-25 for the numbers and their limits.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from pandit_knowledge.content import KnowledgeContent
from pandit_knowledge.ingestion import KnowledgeBuilder
from pandit_knowledge.models import RetrievalQuery
from pandit_knowledge.retrieval import Retriever
from pandit_knowledge.store import InMemoryKnowledgeStore

pytestmark = pytest.mark.semantic_model

ENGLISH_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
MULTILINGUAL_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def _provider(name: str, languages: tuple[str, ...]) -> Any:
    pytest.importorskip("sentence_transformers")
    from pandit_knowledge.embeddings import SentenceTransformerProvider

    try:
        return SentenceTransformerProvider(
            name, model_version="local-cache", languages_declared=languages, local_files_only=True
        )
    except Exception as exc:  # noqa: BLE001 - any load failure means "model not available here"
        pytest.skip(f"{name} is not in the local cache: {exc}")


@pytest.fixture(scope="module")
def english(content: KnowledgeContent) -> Iterator[tuple[Retriever, Any]]:
    p = _provider(ENGLISH_MODEL, ())
    store = InMemoryKnowledgeStore()
    KnowledgeBuilder(store, p).build(content)
    yield Retriever(store, p), p


@pytest.fixture(scope="module")
def multilingual(content: KnowledgeContent) -> Iterator[tuple[Retriever, Any]]:
    p = _provider(MULTILINGUAL_MODEL, ("en", "hi"))
    store = InMemoryKnowledgeStore()
    KnowledgeBuilder(store, p).build(content)
    yield Retriever(store, p), p


def _top(r: Retriever, text: str, k: int = 3) -> list[str]:
    result = r.retrieve(RetrievalQuery(text=text, top_k=k, max_distance=1.0))
    return [h.parent_concept_id for h in result.hits]


def test_semantic_configuration_is_reported_as_semantic(english: tuple[Retriever, Any]) -> None:
    retriever, provider = english
    assert provider.config.is_semantic and provider.config.dimension == 384
    result = retriever.retrieve(RetrievalQuery(text="profession", max_distance=1.0))
    assert result.is_semantic and "LEXICAL_NOT_SEMANTIC" not in result.notes


def test_english_questions_find_the_expected_concepts(english: tuple[Retriever, Any]) -> None:
    r, _ = english
    assert _top(r, "Which house governs profession and livelihood?", 1) == ["HOUSE.10"]
    assert _top(r, "What does the Sun signify?", 1) == ["PLANET.SUN"]
    assert _top(r, "meaning of the Wheel of Fortune card", 1) == ["TAROT.major_10_wheel_of_fortune"]
    assert "HOUSE.04" in _top(r, "Which planet is the significator of the fourth house?", 3)


def test_an_english_only_model_declares_no_hindi_and_says_so(
    english: tuple[Retriever, Any],
) -> None:
    r, provider = english
    assert provider.config.languages_declared == ()
    result = r.retrieve(RetrievalQuery(text="सूर्य किसका कारक है?", max_distance=1.0))
    assert "CROSS_LANGUAGE_RETRIEVAL_NOT_VALIDATED" in result.notes


def test_multilingual_model_hindi_recall_measured_at_top3(
    multilingual: tuple[Retriever, Any],
) -> None:
    """Measured, small sample (4 queries): the expected concept is in the top 3 for Hindi
    queries against English text. It is NOT reliably first, and Hinglish (romanised) queries are
    not reliable at all (measured 1 of 4 in the top 3), so no Hinglish claim is made."""
    r, provider = multilingual
    assert provider.config.languages_declared == ("en", "hi")
    expected = [
        ("कौन सा भाव आजीविका या पेशे से जुड़ा है?", {"HOUSE.10"}),
        ("सूर्य किसका कारक है?", {"PLANET.SUN"}),
        ("चौथे भाव का कारक ग्रह कौन सा है?", {"HOUSE.04", "PLANET.MOON"}),
        ("भाग्य का चक्र कार्ड का अर्थ", {"TAROT.major_10_wheel_of_fortune"}),
    ]
    found = sum(1 for q, want in expected if want & set(_top(r, q, 3)))
    assert found >= 3
    result = r.retrieve(RetrievalQuery(text=expected[0][0], max_distance=1.0))
    assert "CROSS_LANGUAGE_RETRIEVAL_NOT_VALIDATED" not in result.notes  # hi is declared
