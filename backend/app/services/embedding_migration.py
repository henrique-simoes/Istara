"""Move an install to another embedding model or prompt scheme without mixing vector spaces.

The persisted embedding profile, not settings, decides the model an install embeds with, and every
vector store fails closed when the active identity differs from the one it was built with. Until
now nothing could change it. A migration:

1. checks that the target model embeds (a probe; nothing changes when it does not);
2. activates a new profile version (the old one stays on record, inactive);
3. re-embeds every project's stored chunks, source and derived tables, from the text they already
   hold under the new profile, keeping every other column (provenance, offsets, evidence units);
4. rebinds each store's manifest. The BM25 index does not use vectors and is left alone.

One migration runs at a time. A failure stops it with the reason; running it again resumes with the
tables whose rows are not yet in the new profile version.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from app.config import settings

PROBE_TEXT = "Istara embedding migration probe."
_lock = asyncio.Lock()
_status: dict[str, Any] = {"state": "idle"}


class EmbeddingMigrationError(RuntimeError):
    """The migration was refused before changing anything."""


def migration_status() -> dict[str, Any]:
    return dict(_status)


def is_running() -> bool:
    return _status.get("state") == "running"


async def _probe_embed(texts: list[str], model: str) -> list[list[float]]:
    from app.core.agentic import agentic
    from app.core.agentic.types import TurnParams

    return await agentic.embed(texts=texts, params=TurnParams(model=model))


def _stores() -> list:
    """Every existing vector table, project by project (source first, then derived)."""
    from app.core.rag import DERIVED_TABLE, SOURCE_TABLE, VectorStore

    root = Path(settings.lance_db_path)
    stores = []
    if not root.is_dir():
        return stores
    for project_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for table in (SOURCE_TABLE, DERIVED_TABLE):
            store = VectorStore(project_dir.name, table_name=table)
            if store._ensure_table():
                stores.append(store)
    return stores


def _in_active_version(store) -> bool:
    """Whether every row of the table was embedded under the active profile version."""
    from app.core.pi_runtime.embedding_profile import get_active_embedding_profile

    active = get_active_embedding_profile()
    table = store.db.open_table(store.table_name)
    arrow = table.to_arrow()
    if "embedding_profile_version" not in arrow.column_names:
        return arrow.num_rows == 0
    versions = set(arrow.column("embedding_profile_version").to_pylist())
    namespaces = set(arrow.column("embedding_cache_namespace").to_pylist())
    return versions <= {active.version} and namespaces <= {active.cache_namespace}


async def _reembed_store(store) -> int:
    """Re-embed one table's rows from their text under the active profile; rebind its manifest."""
    from app.core.embeddings import TextChunk, embed_chunks
    from app.core.pi_runtime.embedding_profile import get_active_embedding_profile

    active = get_active_embedding_profile()
    table = store.db.open_table(store.table_name)
    rows = table.to_arrow().to_pylist()
    if rows:
        embedded = await embed_chunks([TextChunk(text=row["text"], source="") for row in rows])
        for row, item in zip(rows, embedded, strict=True):
            row["vector"] = item.vector
            if "embedding_profile_version" in row:
                row["embedding_profile_id"] = active.profile_id
                row["embedding_profile_version"] = active.version
                row["embedding_cache_namespace"] = active.cache_namespace
        store.db.create_table(store.table_name, rows, mode="overwrite")
    store.rebind_to_active_profile()
    return len(rows)


async def _activate(model_id: str, scheme: str, dimension: int) -> None:
    from app.core import embeddings
    from app.core.pi_runtime.embedding_profile import (
        activate_embedding_profile,
        get_active_embedding_profile,
    )
    from app.models.database import async_session

    active = get_active_embedding_profile()
    if (active.model_id, active.prompt_scheme) == (model_id, scheme):
        return  # a resumed migration: the target is already active
    async with async_session() as db:
        await activate_embedding_profile(
            db, model_id=model_id, prompt_scheme=scheme, dimension=dimension
        )
    embeddings._known_fingerprints.clear()


async def prepare_migration(model_id: str, prompt_scheme: str = "auto") -> tuple[str, str, int]:
    """Check the target before anything changes: (model, scheme, dimension), or refuse."""
    from app.core.embedding_prompts import resolve_scheme

    model_id = str(model_id or "").strip()
    if not model_id:
        raise EmbeddingMigrationError("model_id_required")
    try:
        scheme = resolve_scheme(prompt_scheme, model_id)
    except ValueError as exc:
        raise EmbeddingMigrationError(str(exc)) from exc
    if _lock.locked():
        raise EmbeddingMigrationError("migration_already_running")
    try:
        vectors = await _probe_embed([PROBE_TEXT], model_id)
        dimension = len(vectors[0]) if vectors and vectors[0] else 0
    except Exception as exc:
        raise EmbeddingMigrationError(f"embedding_model_unavailable: {exc}") from exc
    if dimension <= 0:
        raise EmbeddingMigrationError("embedding_model_unavailable: empty vector")
    return model_id, scheme, dimension


async def run_migration(*, model_id: str, prompt_scheme: str = "auto") -> dict[str, Any]:
    """Run a migration to completion and return its final status."""
    target = await prepare_migration(model_id, prompt_scheme)
    async with _lock:
        return await _move(*target)


_jobs: set[asyncio.Task] = set()


async def start_migration(*, model_id: str, prompt_scheme: str = "auto") -> dict[str, Any]:
    """Check the target now, then move the install in the background; returns the first status."""
    target = await prepare_migration(model_id, prompt_scheme)

    async def _job() -> None:
        async with _lock:
            await _move(*target)

    _status.clear()
    _status.update({"state": "running", "model_id": target[0], "prompt_scheme": target[1]})
    job = asyncio.create_task(_job())
    _jobs.add(job)
    job.add_done_callback(_jobs.discard)
    return migration_status()


async def _move(model_id: str, scheme: str, dimension: int) -> dict[str, Any]:
    _status.clear()
    _status.update(
        {
            "state": "running",
            "model_id": model_id,
            "prompt_scheme": scheme,
            "dimension": dimension,
            "started_at": time.time(),
            "stores_total": 0,
            "stores_done": 0,
            "stores_skipped": 0,
            "rows_reembedded": 0,
            "error": "",
        }
    )
    try:
        await _activate(model_id, scheme, dimension)
        stores = _stores()
        _status["stores_total"] = len(stores)
        for store in stores:
            if _in_active_version(store):
                _status["stores_skipped"] += 1
                continue
            _status["rows_reembedded"] += await _reembed_store(store)
            _status["stores_done"] += 1
        _status["state"] = "done"
    except Exception as exc:
        _status.update({"state": "failed", "error": f"{type(exc).__name__}: {exc}"[:300]})
    _status["finished_at"] = time.time()
    return dict(_status)
