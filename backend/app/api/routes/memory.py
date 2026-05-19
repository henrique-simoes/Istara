"""Memory API — inspect, search, and manage the project knowledge base."""

from __future__ import annotations

import logging
from typing import Optional

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

        table = store.db.open_table(store.table_name)
        df = table.to_pandas()
        total = len(df)

        start = (page - 1) * page_size
        end = start + page_size
        page_df = df.iloc[start:end]

        chunks = []
        for _, row in page_df.iterrows():
            chunks.append({
                "text": str(row.get("text", ""))[:500],  # Truncate for listing
                "source": str(row.get("source", "")),
                "page": int(row.get("page", 0)) if "page" in row.index else 0,
                "agent_id": str(row.get("agent_id", "")) if "agent_id" in row.index else "",
                "chunk_type": str(row.get("chunk_type", "character")) if "chunk_type" in row.index else "character",
                "created_at": float(row.get("created_at", 0)) if "created_at" in row.index else 0,
                "confidence": float(row.get("confidence", 1.0)) if "confidence" in row.index else 1.0,
            })

        # Source distribution
        sources = {}
        if "source" in df.columns:
            for src in df["source"]:
                sources[src] = sources.get(src, 0) + 1

        return {
            "chunks": chunks,
            "total": total,
            "page": page,
            "page_size": page_size,
            "sources": [{"name": k, "count": v} for k, v in sorted(sources.items())],
        }
    except Exception as e:
        logger.warning(f"Memory list failed: {e}")
        return {"chunks": [], "total": 0, "page": page, "page_size": page_size, "error": str(e)}


@router.get("/memory/{project_id}/search")
async def search_memory(
    project_id: str,
    request: Request,
    query: str = Query("", max_length=500),
    q: str | None = Query(None, max_length=500),
    top_k: int = Query(20, ge=1, le=100),
    source: Optional[str] = Query(None, max_length=1000),
    file_type: Optional[str] = Query(None, max_length=32),
    db: AsyncSession = Depends(get_db),
):
    """Hybrid search across project memory."""
    await get_visible_project_or_404(db, request, project_id, min_role="viewer")

    search_text = (query or q or "").strip()
    if not search_text:
        return {"results": [], "query": search_text, "total": 0}

    source_filter = source.strip() if source and source.strip() else None
    file_type_filter = file_type.strip().lstrip(".").lower() if file_type and file_type.strip() else None

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

    # Get source distribution
    sources = []
    vector_dim = 0
    try:
        if store._ensure_table():
            table = store.db.open_table(store.table_name)
            df = table.to_pandas()
            if "source" in df.columns:
                src_counts = df["source"].value_counts().to_dict()
                sources = [{"name": k, "chunk_count": v} for k, v in src_counts.items()]

            # Get vector dimensions
            if len(df) > 0 and "vector" in df.columns:
                vec = df.iloc[0]["vector"]
                vector_dim = len(vec) if vec is not None else 0
    except Exception:
        pass

    # Embedding model info
    from app.config import settings as s
    embed_model = s.lmstudio_embed_model if s.llm_provider == "lmstudio" else s.ollama_embed_model

    return {
        "vector_chunks": vector_count,
        "keyword_chunks": keyword_count,
        "sources": sources,
        "embedding_model": embed_model,
        "vector_dimensions": vector_dim,
        "chunk_size": s.rag_chunk_size,
        "chunk_overlap": s.rag_chunk_overlap,
        "hybrid_weights": {
            "vector": s.rag_hybrid_vector_weight,
            "keyword": s.rag_hybrid_keyword_weight,
        },
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
