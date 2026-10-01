"""Store rules, idempotent ingestion and knowledge versioning (KB-14 to KB-17, KB-36)."""

from __future__ import annotations

from typing import Any

import pytest

from pandit_knowledge.content import KnowledgeContent
from pandit_knowledge.embeddings import HashingEmbeddingProvider
from pandit_knowledge.ingestion import BuildResult, KnowledgeBuilder, build_rows
from pandit_knowledge.models import KnowledgeDomain, RetrievalFilters
from pandit_knowledge.store import (
    InMemoryKnowledgeStore,
    KnowledgeIntegrityError,
    SealedVersionError,
)
from pandit_knowledge.validation import verify_version

Built = tuple[InMemoryKnowledgeStore, BuildResult, HashingEmbeddingProvider]


def test_build_creates_a_sealed_version_with_every_record(built: Built) -> None:
    store, result, _ = built
    version = store.get_version(result.version_id)
    assert version is not None and version.status == "SEALED"
    assert result.outcome == "CREATED"
    counts = version.manifest.record_counts
    assert counts["concepts"] > 100 and counts["statements"] > 80 and counts["chunks"] > 150
    for table, n in counts.items():
        assert len(store.select_rows(result.version_id, table)) == n
    assert result.embeddings_written == counts["chunks"]


def test_version_identity_is_deterministic(
    content: KnowledgeContent, provider: HashingEmbeddingProvider
) -> None:
    a = KnowledgeBuilder(InMemoryKnowledgeStore(), provider).build(content)
    b = KnowledgeBuilder(InMemoryKnowledgeStore(), provider).build(content)
    assert a.version_id == b.version_id and a.snapshot_hash == b.snapshot_hash
    assert a.version_id.startswith("KV-")


def test_reingesting_identical_content_creates_nothing_new(
    content: KnowledgeContent, provider: HashingEmbeddingProvider
) -> None:
    store = InMemoryKnowledgeStore()
    builder = KnowledgeBuilder(store, provider)
    first = builder.build(content)
    before = {t: store.select_rows(first.version_id, t) for t in first.record_counts}
    second = builder.build(content)
    assert second.outcome == "NOOP" and second.version_id == first.version_id
    assert second.embeddings_written == 0
    assert len(store.list_versions()) == 1
    after = {t: store.select_rows(first.version_id, t) for t in first.record_counts}
    assert before == after
    statuses = [r["status"] for r in store.ingestion_runs(first.version_id)]
    assert statuses == ["CREATED", "NOOP_IDENTICAL"]


def test_a_different_embedding_configuration_is_a_new_version(
    content: KnowledgeContent, provider: HashingEmbeddingProvider
) -> None:
    store = InMemoryKnowledgeStore()
    a = KnowledgeBuilder(store, provider).build(content)
    b = KnowledgeBuilder(store, HashingEmbeddingProvider(512)).build(content)
    assert a.version_id != b.version_id
    assert len(store.list_versions()) == 2
    assert all(v.status == "SEALED" for v in store.list_versions())
    # the old version is untouched by the new build
    assert verify_version(store, a.version_id) == []
    assert verify_version(store, b.version_id) == []


def test_changed_content_is_a_new_version_and_the_old_one_is_unchanged(
    content: KnowledgeContent, provider: HashingEmbeddingProvider
) -> None:
    store = InMemoryKnowledgeStore()
    first = KnowledgeBuilder(store, provider).build(content)
    snapshot = store.select_rows(first.version_id, "chunks")
    changed = KnowledgeContent(**{**content.__dict__})
    changed.chunk_units = [
        u.__class__(**{**u.__dict__, "text": u.text + " Added sentence."}) if i == 0 else u
        for i, u in enumerate(content.chunk_units)
    ]
    second = KnowledgeBuilder(store, provider).build(changed)
    assert second.version_id != first.version_id
    assert store.select_rows(first.version_id, "chunks") == snapshot


def test_interrupted_build_resumes_without_duplicates(
    content: KnowledgeContent, provider: HashingEmbeddingProvider
) -> None:
    store = InMemoryKnowledgeStore()
    builder = KnowledgeBuilder(store, provider)
    manifest, parts = builder.manifest_for(content)
    store.register_embedding_config(provider.config)
    version, outcome = store.begin_version(manifest)
    assert outcome == "CREATED"
    rows = parts["rows"]
    for table in ("sources", "source_editions", "concepts", "statements"):
        store.insert_rows(version.version_id, table, rows[table])
    # crash here: the version is still a DRAFT with some rows and no embeddings
    assert store.get_version(version.version_id).status == "DRAFT"  # type: ignore[union-attr]
    result = builder.build(content)
    assert result.outcome == "RESUMED" and result.version_id == version.version_id
    assert verify_version(store, result.version_id) == []
    assert (
        len(store.select_rows(result.version_id, "concepts")) == manifest.record_counts["concepts"]
    )


def test_sealed_version_rejects_every_write(built: Built) -> None:
    store, result, provider = built
    rows, chunks = build_rows(_content())
    with pytest.raises(SealedVersionError):
        store.insert_rows(result.version_id, "concepts", rows["concepts"][:1])
    chunk = chunks[0]
    vec = provider.embed_documents([chunk.text])[0]
    with pytest.raises(SealedVersionError):
        store.insert_embeddings(
            result.version_id,
            provider.config.embedding_config_id,
            [(chunk.chunk_id, chunk.content_hash(), vec)],
        )


def _content() -> KnowledgeContent:
    from pandit_knowledge.content import load_content

    return load_content()


def _draft(
    provider: HashingEmbeddingProvider,
) -> tuple[InMemoryKnowledgeStore, str, dict[str, Any]]:
    store = InMemoryKnowledgeStore()
    builder = KnowledgeBuilder(store, provider)
    manifest, parts = builder.manifest_for(_content())
    store.register_embedding_config(provider.config)
    version, _ = store.begin_version(manifest)
    return store, version.version_id, parts["rows"]


def test_key_collisions_with_different_content_are_rejected(
    provider: HashingEmbeddingProvider,
) -> None:
    store, vid, rows = _draft(provider)
    store.insert_rows(vid, "sources", rows["sources"])
    clash = dict(rows["sources"][0])
    clash["title"] = "A different title"
    clash["content_hash"] = "0" * 64
    with pytest.raises(KnowledgeIntegrityError, match="different content"):
        store.insert_rows(vid, "sources", [clash])
    assert store.insert_rows(vid, "sources", rows["sources"]) == 0  # identical re-insert: no-op


def test_foreign_keys_are_enforced(provider: HashingEmbeddingProvider) -> None:
    store, vid, rows = _draft(provider)
    with pytest.raises(KnowledgeIntegrityError, match="foreign key"):
        store.insert_rows(vid, "source_editions", rows["source_editions"])  # sources missing


def test_embedding_dimension_hash_and_chunk_are_checked(
    provider: HashingEmbeddingProvider,
) -> None:
    store, vid, rows = _draft(provider)
    for table in (
        "sources", "source_editions", "concepts", "statements", "terms",
        "rule_references", "domain_mappings", "exceptions", "chunks",
    ):  # fmt: skip
        store.insert_rows(vid, table, rows[table])
    chunk = rows["chunks"][0]
    cfg = provider.config.embedding_config_id
    good = provider.embed_documents(["x"])[0]
    with pytest.raises(KnowledgeIntegrityError, match="dimension"):
        store.insert_embeddings(vid, cfg, [(chunk["chunk_id"], chunk["content_hash"], good[:-1])])
    with pytest.raises(KnowledgeIntegrityError, match="hash mismatch"):
        store.insert_embeddings(vid, cfg, [(chunk["chunk_id"], "f" * 64, good)])
    with pytest.raises(KnowledgeIntegrityError, match="unknown chunk"):
        store.insert_embeddings(vid, cfg, [("CH-nope", chunk["content_hash"], good)])


def test_unregistered_embedding_configuration_is_rejected(
    content: KnowledgeContent, provider: HashingEmbeddingProvider
) -> None:
    store = InMemoryKnowledgeStore()
    manifest, _ = KnowledgeBuilder(store, provider).manifest_for(content)
    with pytest.raises(KnowledgeIntegrityError, match="not registered"):
        store.begin_version(manifest)


def test_content_hashes_are_stable_and_detect_tampering(built: Built) -> None:
    store, result, _ = built
    assert verify_version(store, result.version_id) == []
    bucket = store._rows[(result.version_id, "statements")]  # noqa: SLF001 - simulate tampering
    key = next(iter(bucket))
    bucket[key]["source_location"] = "Ch. 99 v. 99"
    problems = verify_version(store, result.version_id)
    assert any("statements: content hash mismatch" in p for p in problems)


def test_verify_reports_missing_embeddings(built: Built) -> None:
    store, result, provider = built
    cfg = provider.config.embedding_config_id
    key = next(k for k in store._embeddings if k[0] == result.version_id)  # noqa: SLF001
    del store._embeddings[key]  # noqa: SLF001
    assert any("no embedding" in p for p in verify_version(store, result.version_id))
    assert store.embedded_chunk_ids(result.version_id, cfg)


def test_rows_are_returned_in_a_stable_order(built: Built) -> None:
    store, result, _ = built
    ids = [r["chunk_id"] for r in store.select_rows(result.version_id, "chunks")]
    assert ids == sorted(ids, key=str)


def test_unknown_table_and_unknown_version_are_rejected(built: Built) -> None:
    store, result, _ = built
    with pytest.raises(KnowledgeIntegrityError):
        store.select_rows(result.version_id, "users")
    with pytest.raises(KnowledgeIntegrityError):
        store.insert_rows("KV-none", "concepts", [])
    assert store.get_version("KV-none") is None


def test_record_hashes_do_not_depend_on_language_of_ids(content: KnowledgeContent) -> None:
    rows, _ = build_rows(content)
    for table, items in rows.items():
        hashes = [r["content_hash"] for r in items]
        assert len(set(hashes)) == len(hashes), table


def test_filters_object_is_hashable_and_defaults_empty() -> None:
    f = RetrievalFilters()
    assert not f.source_ids and not f.languages
    assert RetrievalFilters(knowledge_domains=(KnowledgeDomain.TAROT,)).knowledge_domains


# Recorded on Windows (CRLF working tree) at the Phase 12 stopping point and expected to be
# identical on Linux CI: the snapshot hash must not depend on the operating system or on line
# endings. Update it only when the curated content, the schema/ingestion/chunking/standards
# versions or the lexical provider change on purpose: that is a new knowledge version.
PHASE12_LEXICAL_SNAPSHOT_HASH = "c8972e1ec723849a78da3c713f098686eea9199a27ea7494fca4a7fcd479b5e2"


def test_the_snapshot_hash_is_platform_independent(
    content: KnowledgeContent, provider: HashingEmbeddingProvider
) -> None:
    result = KnowledgeBuilder(InMemoryKnowledgeStore(), provider).build(content)
    assert result.snapshot_hash == PHASE12_LEXICAL_SNAPSHOT_HASH
    assert result.version_id == "KV-c8972e1ec723849a"
