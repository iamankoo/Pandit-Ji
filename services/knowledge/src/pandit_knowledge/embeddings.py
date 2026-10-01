"""Embedding-provider abstraction (KB-20 to KB-22).

Phase 14 owns the final self-hosted model choice, so nothing here is built around one model.
A provider exposes an :class:`~pandit_knowledge.models.EmbeddingConfig` (provider, model, model
version, dimension, metric, configuration version); the configuration's identity is part of a
knowledge version, so changing the model is a new version, never a mutation.

Two providers ship:

* :class:`HashingEmbeddingProvider` -- deterministic feature hashing of words and character
  trigrams. It is **lexical, not semantic**: it needs no model download, makes ingestion and
  tests reproducible, and exercises the whole pipeline. It must never be described as semantic
  retrieval, and it declares no languages.
* :class:`SentenceTransformerProvider` -- an optional local ``sentence-transformers`` model.
  Semantic quality and language coverage are whatever the model really has; the declared
  languages are a claim by the operator, not something this package verifies.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence
from typing import Any, Protocol

from pandit_knowledge.models import EmbeddingConfig

_WORD = re.compile(r"\w+", re.UNICODE)
# Function words carry no lexical signal; dropping them keeps the lexical provider from ranking
# on "the" and "of". English only: the provider declares no language and never claims one.
_STOPWORDS = frozenset(
    "a an and are as at be by for from has have in is it its of on or that the this to was were "
    "what when where which who whom with".split()
)


class EmbeddingProvider(Protocol):
    config: EmbeddingConfig

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


def _normalise(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        return vec
    return [v / norm for v in vec]


class HashingEmbeddingProvider:
    """Deterministic lexical feature-hashing embedder (not semantic)."""

    def __init__(self, dimension: int = 256) -> None:
        if dimension < 16:
            raise ValueError("dimension must be at least 16")
        self.config = EmbeddingConfig(
            provider="pandit-lexical-hash",
            model="feature-hashing-words-and-trigrams",
            model_version="2",
            dimension=dimension,
            config_version="1.0.0",
            is_semantic=False,
            languages_declared=(),
        )

    def _features(self, text: str) -> list[str]:
        feats: list[str] = []
        for word in _WORD.findall(text.casefold()):
            if word in _STOPWORDS:
                continue
            feats.append("w:" + word)
            padded = f"^{word}$"
            feats.extend("t:" + padded[i : i + 3] for i in range(len(padded) - 2))
        return feats

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.config.dimension
        for feat in self._features(text):
            digest = hashlib.sha256(feat.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.config.dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            weight = 1.0 if feat.startswith("w:") else 0.5
            vec[index] += sign * weight
        return _normalise(vec)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class SentenceTransformerProvider:
    """A local sentence-transformers model. Imported lazily; optional dependency."""

    def __init__(
        self,
        model_name_or_path: str,
        *,
        model_version: str,
        languages_declared: Sequence[str] = (),
        config_version: str = "1.0.0",
        local_files_only: bool = False,
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - exercised only without the extra
            raise RuntimeError("sentence-transformers is not installed") from exc
        self._model: Any = SentenceTransformer(
            model_name_or_path, local_files_only=local_files_only
        )
        getter = getattr(self._model, "get_embedding_dimension", None)
        dim = getter() if getter else self._model.get_sentence_embedding_dimension()
        if not isinstance(dim, int):  # pragma: no cover - defensive
            raise RuntimeError("model does not report an embedding dimension")
        self.config = EmbeddingConfig(
            provider="sentence-transformers",
            model=model_name_or_path,
            model_version=model_version,
            dimension=dim,
            config_version=config_version,
            is_semantic=True,
            languages_declared=tuple(languages_declared),
        )

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        arr = self._model.encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
        return [[float(x) for x in row] for row in arr]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


def cosine_distance(a: Sequence[float], b: Sequence[float]) -> float:
    """``1 - cosine similarity`` (pgvector's ``<=>`` operator), for the in-memory store."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 1.0
    return 1.0 - dot / (na * nb)
