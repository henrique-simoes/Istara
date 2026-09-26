"""An install moves to another embedding model without mixing vector spaces (2026-09-26).

Nothing could change the embedding model of an existing install: the persisted profile wins over
settings, and every vector store fails closed when the active identity differs from the one it was
built with. The migration activates a new profile version, re-embeds every project's stored chunks
(source and derived tables) from the text they already hold, keeps every other column, rebinds each
store's manifest, and leaves the BM25 index alone. A target that cannot embed is refused before
anything changes; an interrupted migration resumes from the stores not yet moved.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from app.config import settings


def _model(seed: str, dim: int):
    async def _dispatch(texts, **kwargs):
        return [
            [(b - 128) / 128 for b in hashlib.sha256(f"{seed}:{t}".encode()).digest()[:dim]]
            for t in texts
        ]

    return _dispatch


@pytest.fixture
async def install(tmp_path, monkeypatch):
    """A fresh install on model 'old-embed' (raw, 8 dims) with one project indexed."""
    from app.core import embeddings, rag
    from app.core.embeddings import TextChunk
    from app.core.pi_runtime import embedding_profile
    from app.models.database import async_session, init_db

    monkeypatch.setattr(settings, "data_dir", str(tmp_path / "data"))
    monkeypatch.setattr(settings, "lance_db_path", str(tmp_path / "lance"))
    monkeypatch.setattr(settings, "keyword_index_dir", None)
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "ollama_embed_model", "old-embed")
    monkeypatch.setattr(settings, "embed_prompt_scheme", "raw")
    monkeypatch.setattr(embeddings, "_known_embed_dimensions", {})
    monkeypatch.setattr(embeddings, "_known_fingerprints", {})
    cache: dict = {}

    async def _get(namespace, text):
        return cache.get((namespace, text))

    async def _put(namespace, text, vector):
        cache[(namespace, text)] = vector

    monkeypatch.setattr(embeddings.embedding_cache, "get", _get)
    monkeypatch.setattr(embeddings.embedding_cache, "put", _put)
    models = {"old-embed": _model("old", 8), "new-embed": _model("new", 12)}
    current = {"model": "old-embed"}

    async def _dispatch(texts, **kwargs):
        return await models[embedding_profile.get_active_embedding_profile().model_id](texts)

    async def _probe(texts, model):
        if model not in models:
            raise RuntimeError(f"model {model} not served")
        return await models[model](texts)

    monkeypatch.setattr(embeddings, "_dispatch_embed", _dispatch)
    embedding_profile.reset_embedding_profile_cache()
    await init_db()
    await _clear_profiles()
    async with async_session() as db:
        await embedding_profile.bootstrap_embedding_profile(db)

    texts = ["Receipts end up in the apron pocket.", "Payroll runs Thursday night."]
    for project_id in ("proj-a", "proj-b"):
        store = rag.VectorStore(project_id)
        chunks = [
            TextChunk(
                text=t,
                source=f"{project_id}/notes.md",
                metadata={"evidence_unit_id": f"eu-{i}", "start_offset": i, "end_offset": i + 5},
            )
            for i, t in enumerate(texts)
        ]
        await store.add_chunks(await embeddings.embed_chunks(chunks))
    derived = rag.VectorStore("proj-a", table_name=rag.DERIVED_TABLE)
    await derived.add_chunks(
        await embeddings.embed_chunks([TextChunk(text="An agent note.", source="agent:note")])
    )
    yield {"models": models, "probe": _probe, "texts": texts, "current": current}
    await _clear_profiles()
    embedding_profile.reset_embedding_profile_cache()


async def _clear_profiles() -> None:
    """The test database is shared: profile versions from other tests must not leak in or out."""
    from sqlalchemy import delete

    from app.models.database import async_session
    from app.models.embedding_profile import EmbeddingProfile

    async with async_session() as db:
        await db.execute(delete(EmbeddingProfile))
        await db.commit()


def _rows(project_id: str, table: str = "chunks") -> list[dict]:
    from app.core import rag

    store = rag.VectorStore(project_id, table_name=table)
    return store.db.open_table(table).to_arrow().to_pylist()


async def test_activating_a_new_profile_version_keeps_one_active_row(install):
    from sqlalchemy import select

    from app.core.pi_runtime import embedding_profile
    from app.models.database import async_session
    from app.models.embedding_profile import EmbeddingProfile

    async with async_session() as db:
        active = await embedding_profile.activate_embedding_profile(
            db, model_id="new-embed", prompt_scheme="embeddinggemma", dimension=12
        )
        rows = (await db.execute(select(EmbeddingProfile))).scalars().all()
    assert (active.version, active.model_id, active.prompt_scheme, active.dimension) == (
        2,
        "new-embed",
        "embeddinggemma",
        12,
    )
    assert active.cache_namespace == "new-embed|prompts:embeddinggemma"
    assert sorted((r.version, r.is_active) for r in rows) == [(1, False), (2, True)]
    assert embedding_profile.get_active_embedding_profile() == active


async def test_migration_reembeds_every_store_and_keeps_everything_else(install, monkeypatch):
    from app.core import rag
    from app.core.pi_runtime import embedding_profile
    from app.services import embedding_migration

    before_a = _rows("proj-a")
    before_note = _rows("proj-a", rag.DERIVED_TABLE)
    monkeypatch.setattr(embedding_migration, "_probe_embed", install["probe"])

    status = await embedding_migration.run_migration(model_id="new-embed", prompt_scheme="raw")

    assert status["state"] == "done", status
    assert (status["stores_total"], status["stores_done"], status["rows_reembedded"]) == (3, 3, 5)
    active = embedding_profile.get_active_embedding_profile()
    assert (active.model_id, active.version, active.dimension) == ("new-embed", 2, 12)
    after_a = _rows("proj-a")
    expected = await install["models"]["new-embed"]([r["text"] for r in before_a])
    for old, new, vector in zip(before_a, after_a, expected, strict=True):
        assert [round(x, 5) for x in new["vector"]] == [round(x, 5) for x in vector]
        assert new["embedding_profile_version"] == 2
        assert new["embedding_cache_namespace"] == "new-embed"
        for column in ("text", "source", "evidence_unit_id", "start_offset", "provenance_key"):
            assert new[column] == old[column]
    assert len(_rows("proj-a", rag.DERIVED_TABLE)) == len(before_note)
    manifest = json.loads(rag.VectorStore("proj-b")._profile_manifest.read_text(encoding="utf-8"))
    assert (manifest["model_id"], manifest["version"]) == ("new-embed", 2)
    # Reads work in the new space.
    hits = await rag.VectorStore("proj-b").search(
        (await install["models"]["new-embed"](["Payroll runs Thursday night."]))[0], top_k=1
    )
    assert hits and hits[0].text == "Payroll runs Thursday night."


async def test_a_model_that_cannot_embed_is_refused_before_anything_changes(install, monkeypatch):
    from app.core.pi_runtime import embedding_profile
    from app.services import embedding_migration

    monkeypatch.setattr(embedding_migration, "_probe_embed", install["probe"])
    before = _rows("proj-a")
    with pytest.raises(embedding_migration.EmbeddingMigrationError):
        await embedding_migration.run_migration(model_id="missing-embed", prompt_scheme="auto")
    assert embedding_profile.get_active_embedding_profile().model_id == "old-embed"
    assert _rows("proj-a") == before


async def test_an_interrupted_migration_resumes_with_the_stores_left(install, monkeypatch):
    from app.services import embedding_migration

    monkeypatch.setattr(embedding_migration, "_probe_embed", install["probe"])
    original = embedding_migration._reembed_store
    calls: list[str] = []

    async def _fail_on_b(store):
        calls.append(f"{store.project_id}/{store.table_name}")
        if store.project_id == "proj-b":
            raise RuntimeError("disk full")
        return await original(store)

    monkeypatch.setattr(embedding_migration, "_reembed_store", _fail_on_b)
    first = await embedding_migration.run_migration(model_id="new-embed", prompt_scheme="raw")
    assert first["state"] == "failed" and "disk full" in first["error"]

    monkeypatch.setattr(embedding_migration, "_reembed_store", original)
    second = await embedding_migration.run_migration(model_id="new-embed", prompt_scheme="raw")
    assert second["state"] == "done"
    assert second["stores_skipped"] == 2 and second["stores_done"] == 1


async def _call(method: str, path: str, role: str, json_body: dict | None = None):
    from httpx import ASGITransport, AsyncClient

    from app.core.auth import create_token
    from app.main import app

    if not settings.jwt_secret:
        settings.jwt_secret = "test-secret"
    headers = {"Authorization": f"Bearer {create_token(f'{role}-u', role, role)}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, path, headers=headers, json=json_body)


async def test_only_an_admin_can_see_or_start_a_migration(install, monkeypatch):
    from app.services import embedding_migration

    monkeypatch.setattr(settings, "team_mode", True)
    monkeypatch.setattr(embedding_migration, "_probe_embed", install["probe"])
    for method, body in (("GET", None), ("POST", {"model_id": "new-embed"})):
        response = await _call(method, "/api/settings/embedding-profile", "researcher", body)
        assert response.status_code == 403, (method, response.text)


async def test_an_admin_starts_a_migration_and_reads_its_progress(install, monkeypatch):
    import asyncio

    from app.services import embedding_migration

    monkeypatch.setattr(settings, "team_mode", True)
    monkeypatch.setattr(embedding_migration, "_probe_embed", install["probe"])
    status = await _call("GET", "/api/settings/embedding-profile", "admin")
    assert status.status_code == 200
    assert status.json()["active"]["model_id"] == "old-embed"

    refused = await _call(
        "POST", "/api/settings/embedding-profile", "admin", {"model_id": "missing-embed"}
    )
    assert refused.status_code == 400 and "embedding_model_unavailable" in refused.text

    started = await _call(
        "POST", "/api/settings/embedding-profile", "admin", {"model_id": "new-embed"}
    )
    assert started.status_code == 202, started.text
    assert started.json()["migration"]["state"] == "running"
    for _ in range(100):
        body = (await _call("GET", "/api/settings/embedding-profile", "admin")).json()
        if body["migration"]["state"] != "running":
            break
        await asyncio.sleep(0.05)
    assert body["migration"]["state"] == "done", body
    assert body["active"]["model_id"] == "new-embed" and body["active"]["version"] == 2
