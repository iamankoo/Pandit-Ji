from __future__ import annotations

import pytest

from pandit_knowledge.content import KnowledgeContent, load_content
from pandit_knowledge.embeddings import HashingEmbeddingProvider
from pandit_knowledge.ingestion import BuildResult, KnowledgeBuilder
from pandit_knowledge.store import InMemoryKnowledgeStore


@pytest.fixture(scope="session")
def content() -> KnowledgeContent:
    return load_content()


@pytest.fixture
def provider() -> HashingEmbeddingProvider:
    return HashingEmbeddingProvider()


@pytest.fixture
def built(
    content: KnowledgeContent, provider: HashingEmbeddingProvider
) -> tuple[InMemoryKnowledgeStore, BuildResult, HashingEmbeddingProvider]:
    store = InMemoryKnowledgeStore()
    result = KnowledgeBuilder(store, provider).build(content)
    return store, result, provider
