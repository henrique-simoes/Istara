"""Embedders get the query and document prompts their model cards specify (2026-09-26).

Istara sent raw text to every embedder. Retrieval embedders are trained with instructions:
EmbeddingGemma expects ``task: search result | query: ...`` for queries and ``title: none | text:
...`` for documents, Qwen3-Embedding an ``Instruct: ...\\nQuery:`` prefix on queries, and
nomic-embed-text ``search_query:`` / ``search_document:``. Ollama's /api/embed applies no template,
so the caller must. The scheme is part of the vector-space identity: an index built from raw text is
never queried with prompted vectors, and profiles and stores from before schemes existed stay raw.
"""

from __future__ import annotations

import dataclasses
import hashlib

import pytest

from app.config import settings


def _profile(model_id: str, scheme: str):
    from app.core.pi_runtime.embedding_profile import ActiveEmbeddingProfile

    namespace = model_id if scheme == "raw" else f"{model_id}|prompts:{scheme}"
    return ActiveEmbeddingProfile(
        profile_id="default",
        version=1,
        model_id=model_id,
        endpoint_id="pi-local-ollama",
        transport="pi_http",
        dimension=0,
        dtype="float",
        normalization="provider_native",
        cache_namespace=namespace,
        health_status="unknown",
        migration_source="test",
        prompt_scheme=scheme,
    )


@pytest.fixture
def recorded(tmp_path, monkeypatch):
    """An embedder that records every text it receives; a fresh cache; a given active profile."""
    from app.core import embeddings
    from app.core.pi_runtime import embedding_profile

    monkeypatch.setattr(settings, "lance_db_path", str(tmp_path / "lance"))
    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"))
    monkeypatch.setattr(embeddings, "_known_embed_dimensions", {})
    monkeypatch.setattr(embeddings, "_known_fingerprints", {})
    store: dict = {}

    async def _get(namespace, text):
        return store.get((namespace, text))

    async def _put(namespace, text, vector):
        store[(namespace, text)] = vector

    monkeypatch.setattr(embeddings.embedding_cache, "get", _get)
    monkeypatch.setattr(embeddings.embedding_cache, "put", _put)
    sent: list[str] = []

    async def _dispatch(texts, **kwargs):
        sent.extend(texts)
        return [
            [(b - 128) / 128 for b in hashlib.sha256(text.encode()).digest()[:8]] for text in texts
        ]

    monkeypatch.setattr(embeddings, "_dispatch_embed", _dispatch)

    def use(model_id: str, scheme: str):
        monkeypatch.setattr(embedding_profile, "_active_profile", _profile(model_id, scheme))

    return embeddings, sent, use


def test_each_model_family_gets_its_model_cards_scheme():
    from app.core.embedding_prompts import resolve_scheme, scheme_for_model

    assert scheme_for_model("embeddinggemma") == "embeddinggemma"
    assert scheme_for_model("embeddinggemma:300m") == "embeddinggemma"
    assert scheme_for_model("text-embedding-embeddinggemma-300m") == "embeddinggemma"  # LM Studio
    assert scheme_for_model("qwen3-embedding:0.6b") == "qwen3-embedding"
    assert scheme_for_model("nomic-embed-text") == "nomic"
    assert scheme_for_model("bge-m3") == "raw"  # BGE-M3 dense retrieval takes no instruction
    assert scheme_for_model("default") == "raw"
    assert resolve_scheme("auto", "embeddinggemma") == "embeddinggemma"
    assert resolve_scheme("raw", "embeddinggemma") == "raw"
    with pytest.raises(ValueError):
        resolve_scheme("chatty", "embeddinggemma")


def test_prompts_follow_the_model_cards_and_leave_braces_alone():
    from app.core.embedding_prompts import apply_scheme

    assert apply_scheme("embeddinggemma", "query", "Where are receipts?") == (
        "task: search result | query: Where are receipts?"
    )
    assert apply_scheme("embeddinggemma", "document", "P4: the apron pocket") == (
        "title: none | text: P4: the apron pocket"
    )
    assert apply_scheme("qwen3-embedding", "query", "Why?") == (
        "Instruct: Given a web search query, retrieve relevant passages that answer the query"
        "\nQuery:Why?"
    )
    assert apply_scheme("qwen3-embedding", "document", "Because.") == "Because."
    assert apply_scheme("nomic", "query", "x") == "search_query: x"
    assert apply_scheme("nomic", "document", "x") == "search_document: x"
    assert apply_scheme("raw", "query", "a {b} c") == "a {b} c"
    assert (
        apply_scheme("embeddinggemma", "document", "{json: 1}") == "title: none | text: {json: 1}"
    )


async def test_queries_and_documents_reach_the_model_with_their_prompts(recorded):
    from app.core.embeddings import TextChunk

    embeddings, sent, use = recorded
    use("embeddinggemma", "embeddinggemma")
    await embeddings.embed_text("Where do paper slips end up?")
    await embeddings.embed_chunks(
        [TextChunk(text="The receipt is in my apron pocket.", source="p")]
    )
    prompted = [t for t in sent if "slips" in t or "apron" in t]
    assert prompted == [
        "task: search result | query: Where do paper slips end up?",
        "title: none | text: The receipt is in my apron pocket.",
    ]


async def test_a_raw_profile_still_sends_raw_text(recorded):
    from app.core.embeddings import TextChunk

    embeddings, sent, use = recorded
    use("nomic-embed-text", "raw")
    await embeddings.embed_text("Where do paper slips end up?")
    await embeddings.embed_chunks(
        [TextChunk(text="The receipt is in my apron pocket.", source="p")]
    )
    assert "Where do paper slips end up?" in sent
    assert "The receipt is in my apron pocket." in sent


async def test_the_same_text_as_query_and_as_document_is_two_embeddings(recorded):
    embeddings, sent, use = recorded
    use("embeddinggemma", "embeddinggemma")
    query = await embeddings.embed_text("payroll at midnight")
    document = await embeddings.embed_text("payroll at midnight", role="document")
    assert query != document
    assert sum("payroll at midnight" in t for t in sent) == 2


def test_a_store_built_from_raw_text_refuses_a_prompted_profile(recorded, tmp_path, monkeypatch):
    from app.core import rag
    from app.core.pi_runtime import embedding_profile

    _embeddings, _sent, use = recorded
    use("embeddinggemma", "raw")
    store = rag.VectorStore("scheme-project")
    store._ensure_profile_binding()
    manifest = store._profile_manifest.read_text(encoding="utf-8")
    assert '"prompt_scheme": "raw"' in manifest

    # Same model, prompts switched on: another vector space.
    use("embeddinggemma", "embeddinggemma")
    raw_namespace = dataclasses.replace(
        embedding_profile._active_profile, cache_namespace="embeddinggemma"
    )
    monkeypatch.setattr(embedding_profile, "_active_profile", raw_namespace)
    with pytest.raises(rag.VectorProfileMismatchError):
        rag.VectorStore("scheme-project")._ensure_profile_binding()


def test_a_manifest_from_before_prompt_schemes_is_raw(recorded):
    import json

    from app.core import rag

    _embeddings, _sent, use = recorded
    use("nomic-embed-text", "raw")
    store = rag.VectorStore("legacy-project")
    store._ensure_profile_binding()
    bound = json.loads(store._profile_manifest.read_text(encoding="utf-8"))
    bound.pop("prompt_scheme")
    store._profile_manifest.write_text(json.dumps(bound), encoding="utf-8")
    rag.VectorStore("legacy-project")._ensure_profile_binding()  # still the same space
    rag.VectorStore("legacy-project").check_profile_binding()


def test_a_fresh_install_bootstraps_the_models_scheme_and_an_existing_one_stays_raw(
    tmp_path, monkeypatch
):
    from app.core.pi_runtime import embedding_profile

    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "ollama_embed_model", "embeddinggemma")
    monkeypatch.setattr(settings, "embed_prompt_scheme", "auto")
    monkeypatch.setattr(settings, "lance_db_path", str(tmp_path / "fresh"))
    fresh = embedding_profile._legacy_bootstrap_snapshot()
    assert (fresh.prompt_scheme, fresh.cache_namespace) == (
        "embeddinggemma",
        "embeddinggemma|prompts:embeddinggemma",
    )

    existing = tmp_path / "existing"
    (existing / "some-project" / "chunks.lance").mkdir(parents=True)
    monkeypatch.setattr(settings, "lance_db_path", str(existing))
    kept = embedding_profile._legacy_bootstrap_snapshot()
    assert (kept.prompt_scheme, kept.cache_namespace) == ("raw", "embeddinggemma")


async def test_the_profile_row_persists_its_scheme(tmp_path, monkeypatch):
    from app.core.pi_runtime import embedding_profile
    from app.models.database import async_session, init_db

    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"))
    monkeypatch.setattr(
        embedding_profile, "_active_profile", _profile("embeddinggemma", "embeddinggemma")
    )
    await init_db()
    async with async_session() as db:
        active = await embedding_profile.bootstrap_embedding_profile(db)
    assert active.prompt_scheme in {"embeddinggemma", "raw"}
    embedding_profile.reset_embedding_profile_cache()
    async with async_session() as db:
        reloaded = await embedding_profile.bootstrap_embedding_profile(db)
    assert reloaded.prompt_scheme == active.prompt_scheme
    assert embedding_profile.public_embedding_profile()["prompt_scheme"] == active.prompt_scheme
