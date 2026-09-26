"""A same-dimension embedder swap is detected, never silently mixed into one vector space.

F11 (2026-09-25 map): with the default LM Studio profile the embedding identity is the literal
``"default"`` with dimension 0. If the user loads a different embedding model of the same
dimension, the store manifest still matches, cached vectors from the old model are served, and
query and document vectors come from two spaces without any error. ``vector_health`` only
compared dimensions. The fix fingerprints the model that actually serves: it hashes the
vectors a fixed probe produces (model fingerprinting by behaviour, not by name).
"""

from __future__ import annotations

import hashlib

import pytest

from app.config import settings


def _model(seed: str, dim: int = 8):
    """A deterministic embedder; different seeds are different models of the same dimension."""

    async def _dispatch(texts, **kwargs):
        vectors = []
        for text in texts:
            digest = hashlib.sha256(f"{seed}:{text}".encode()).digest()
            vectors.append([(b - 128) / 128 for b in digest[:dim]])
        return vectors

    return _dispatch


@pytest.fixture
def fresh_embeddings(tmp_path, monkeypatch):
    from app.core import embeddings

    monkeypatch.setattr(settings, "lance_db_path", str(tmp_path / "lance"))
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"))
    monkeypatch.setattr(settings, "keyword_index_dir", None)
    monkeypatch.setattr(embeddings, "_known_embed_dimensions", {})
    store: dict = {}

    async def _get(namespace, text):
        return store.get((namespace, text))

    async def _put(namespace, text, vector):
        store[(namespace, text)] = vector

    monkeypatch.setattr(embeddings.embedding_cache, "get", _get)
    monkeypatch.setattr(embeddings.embedding_cache, "put", _put)
    if hasattr(embeddings, "_known_fingerprints"):
        monkeypatch.setattr(embeddings, "_known_fingerprints", {})
    return embeddings


async def _swap(monkeypatch, embeddings, seed: str):
    monkeypatch.setattr(embeddings, "_dispatch_embed", _model(seed))
    # A restart (or the health probe) re-establishes the serving model's identity.
    monkeypatch.setattr(embeddings, "_known_embed_dimensions", {})
    if hasattr(embeddings, "_known_fingerprints"):
        monkeypatch.setattr(embeddings, "_known_fingerprints", {})


async def test_cached_vectors_from_the_old_model_are_not_served(fresh_embeddings, monkeypatch):
    embeddings = fresh_embeddings
    await _swap(monkeypatch, embeddings, "model-A")
    old = await embeddings.embed_text("receipts at the counter")
    await embeddings.embed_text("warm the dimension")

    await _swap(monkeypatch, embeddings, "model-B")  # same dimension, different model
    # Any first call in the new process re-learns the dimension (8, unchanged). From then on the
    # old identity check trusted every cache hit of that dimension.
    await embeddings.embed_text("a fresh text establishes the dimension")
    new = await embeddings.embed_text("receipts at the counter")
    expected = (await _model("model-B")(["receipts at the counter"]))[0]
    assert new == expected and new != old


async def test_a_store_bound_to_the_old_model_refuses_new_model_queries(
    fresh_embeddings, monkeypatch
):
    from app.core import rag
    from app.core.embeddings import TextChunk

    embeddings = fresh_embeddings
    monkeypatch.setattr(rag, "embed_chunks", embeddings.embed_chunks)
    monkeypatch.setattr(rag, "embed_text", embeddings.embed_text)
    await _swap(monkeypatch, embeddings, "model-A")
    await rag.ingest_chunks(
        "swap-proj", [TextChunk(text="P5 photographs receipts.", source="/u/p5.md")]
    )

    await _swap(monkeypatch, embeddings, "model-B")
    query_vector = await embeddings.embed_text("photographs receipts")
    with pytest.raises(rag.VectorProfileMismatchError):
        await rag.VectorStore("swap-proj").search(query_vector, top_k=3, score_threshold=0.0)


async def test_vector_health_reports_a_same_dimension_swap(fresh_embeddings, monkeypatch):
    from app.core import rag
    from app.core.embeddings import TextChunk
    from app.core.vector_health import check_embedding_dimensions

    embeddings = fresh_embeddings
    monkeypatch.setattr(rag, "embed_chunks", embeddings.embed_chunks)
    await _swap(monkeypatch, embeddings, "model-A")
    await rag.ingest_chunks(
        "health-swap", [TextChunk(text="P5 photographs receipts.", source="/u/p5.md")]
    )

    await _swap(monkeypatch, embeddings, "model-B")
    report = await check_embedding_dimensions("health-swap")
    assert report["status"] in {"profile_mismatch", "fingerprint_mismatch"}, report
    assert report["model_dim"] == 8
