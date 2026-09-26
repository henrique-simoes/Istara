"""Memory API — inspect, search, and manage the project knowledge base."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.keyword_index import KeywordIndex
from app.core.permissions import get_visible_project_or_404
from app.core.rag import VectorStore, retrieve_context
from app.models.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/memory/{project_id}")
async def list_memory(
    project_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List all chunks in a project's knowledge base, paginated."""
    await get_visible_project_or_404(db, request, project_id, min_role="viewer")

    store = VectorStore(project_id)
    try:
        if not store._ensure_table():
            return {"chunks": [], "total": 0, "page": page, "page_size": page_size}

        # Page in the query: select the listed columns (never the vectors) with offset/limit.
        # The old code loaded the whole table, vectors included, into pandas per page (F17).
        table = store.db.open_table(store.table_name)
        total = table.count_rows()
        names = set(table.schema.names)
        columns = [
            c
            for c in (
                "text",
                "source",
                "page",
                "agent_id",
                "chunk_type",
                "created_at",
                "confidence",
            )
            if c in names
        ]
        rows = (
            table.search().select(columns).offset((page - 1) * page_size).limit(page_size).to_list()
        )

        chunks = []
        for row in rows:
            chunks.append(
                {
                    "text": str(row.get("text", ""))[:500],  # Truncate for listing
                    "source": str(row.get("source", "")),
                    "page": int(row.get("page") or 0),
                    "agent_id": str(row.get("agent_id") or ""),
                    "chunk_type": str(row.get("chunk_type") or "character"),
                    "created_at": float(row.get("created_at") or 0),
                    "confidence": float(row.get("confidence", 1.0) or 1.0),
                }
            )

        return {
            "chunks": chunks,
            "total": total,
            "page": page,
            "page_size": page_size,
            "sources": [
                {"name": name, "count": count}
                for name, count in sorted(_source_counts(table, total).items())
            ],
        }
    except Exception as e:
        logger.warning(f"Memory list failed: {e}")
        return {"chunks": [], "total": 0, "page": page, "page_size": page_size, "error": str(e)}


def _source_counts(table, total: int) -> dict[str, int]:
    """Chunk count per source from the ``source`` column alone (no vectors, no other columns)."""
    if total <= 0 or "source" not in table.schema.names:
        return {}
    column = table.search().select(["source"]).limit(total).to_arrow().column("source")
    counts: dict[str, int] = {}
    for value in column.to_pylist():
        key = str(value or "")
        counts[key] = counts.get(key, 0) + 1
    return counts


@router.get("/memory/{project_id}/search")
async def search_memory(
    project_id: str,
    request: Request,
    query: str = Query("", max_length=500),
    q: str | None = Query(None, max_length=500),
    top_k: int = Query(20, ge=1, le=100),
    source: str | None = Query(None, max_length=1000),
    file_type: str | None = Query(None, max_length=32),
    db: AsyncSession = Depends(get_db),
):
    """Hybrid search across project memory."""
    await get_visible_project_or_404(db, request, project_id, min_role="viewer")

    search_text = (query or q or "").strip()
    if not search_text:
        return {"results": [], "query": search_text, "total": 0}

    source_filter = source.strip() if source and source.strip() else None
    file_type_filter = (
        file_type.strip().lstrip(".").lower() if file_type and file_type.strip() else None
    )

    context = await retrieve_context(
        project_id,
        search_text,
        top_k=top_k,
        source_filter=source_filter,
        file_type_filter=file_type_filter,
    )

    return {
        "results": [
            {
                "text": r.text,
                "source": r.source,
                "score": round(r.score, 4),
                "page": r.page,
            }
            for r in context.retrieved
        ],
        "query": search_text,
        "total": len(context.retrieved),
        "filters": {
            "source": source_filter,
            "file_type": file_type_filter,
        },
    }


@router.get("/memory/{project_id}/stats")
async def memory_stats(project_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Get memory statistics for a project."""
    await get_visible_project_or_404(db, request, project_id, min_role="viewer")

    store = VectorStore(project_id)
    keyword_idx = KeywordIndex(project_id)

    vector_count = await store.count()
    keyword_count = await keyword_idx.count()

    # Get source distribution (source column only) and the vector dimension from the schema.
    sources = []
    vector_dim = 0
    try:
        if store._ensure_table():
            table = store.db.open_table(store.table_name)
            src_counts = _source_counts(table, vector_count)
            sources = [
                {"name": k, "chunk_count": v}
                for k, v in sorted(src_counts.items(), key=lambda item: -item[1])
            ]
            if vector_count and "vector" in table.schema.names:
                vector_dim = int(getattr(table.schema.field("vector").type, "list_size", 0) or 0)
    except Exception as e:
        logger.debug("Memory stats source/dimension read failed: %s", e)

    # Embedding identity is Pi-owned; classical provider settings are not an
    # authority and must not change what this health response reports.
    from app.config import settings as s
    from app.core.pi_runtime.embedding_profile import public_embedding_profile

    embedding_profile = public_embedding_profile()
    from app.services.retrieval_provenance import provenance_coverage

    return {
        "vector_chunks": vector_count,
        "keyword_chunks": keyword_count,
        "sources": sources,
        "embedding_model": embedding_profile["model_id"],
        "embedding_profile": embedding_profile,
        "vector_dimensions": vector_dim,
        "chunk_size": s.rag_chunk_size,
        "chunk_overlap": s.rag_chunk_overlap,
        "hybrid_weights": {
            "vector": s.rag_hybrid_vector_weight,
            "keyword": s.rag_hybrid_keyword_weight,
        },
        # Health invariant (measurement 5): every source chunk traces to an evidence unit.
        "provenance": await provenance_coverage(project_id),
    }


@router.get("/memory/{project_id}/agent/{agent_id}/notes")
async def agent_notes(
    project_id: str,
    agent_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get an agent's private notes for a project."""
    await get_visible_project_or_404(db, request, project_id, min_role="viewer")

    from app.core.agent_memory import agent_memory

    notes = await agent_memory.get_all_notes(project_id, agent_id)
    return {"agent_id": agent_id, "project_id": project_id, "notes": notes}


@router.delete("/memory/{project_id}/source/{source_name:path}")
async def delete_source(
    project_id: str,
    source_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Delete all chunks from a specific source."""
    await get_visible_project_or_404(db, request, project_id, min_role="researcher")
    source_name = source_name.strip()
    if not source_name:
        raise HTTPException(status_code=400, detail="Source name must not be empty")

    store = VectorStore(project_id)
    keyword_idx = KeywordIndex(project_id)

    await store.delete_by_source(source_name)
    await keyword_idx.delete_by_source(source_name)

    return {"deleted": True, "source": source_name}


@router.post("/memory/{project_id}/sync")
async def sync_project_knowledge(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Index or re-index all project documents and files into LanceDB and BM25 search indices."""
    await get_visible_project_or_404(db, request, project_id, min_role="researcher")
    from app.services.knowledge_sync import KnowledgeSyncService

    service = KnowledgeSyncService()
    result = await service.sync_project(project_id, db)
    return result
