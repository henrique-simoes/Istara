"""Context DAG API — inspect, search, and manage the conversation DAG."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context_dag import context_dag
from app.core.permissions import ProjectRole, get_visible_project_or_404
from app.models.database import get_db
from app.models.context_dag import ContextDAGNode
from app.models.session import ChatSession

router = APIRouter()


def _require_project_id(project_id: str | None) -> str:
    """Require project-facing Context DAG routes to carry active project context."""
    if not project_id or not project_id.strip():
        raise HTTPException(status_code=400, detail="project_id is required")
    return project_id.strip()


async def _require_session_access(
    db: AsyncSession,
    request: Request,
    session_id: str,
    project_id: str | None,
    *,
    min_role: ProjectRole = "viewer",
) -> ChatSession:
    scoped_project_id = _require_project_id(project_id)
    await get_visible_project_or_404(
        db,
        request,
        scoped_project_id,
        min_role=min_role,
    )
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.project_id == scoped_project_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


async def _require_dag_node(
    db: AsyncSession,
    session_id: str,
    node_id: str,
) -> ContextDAGNode:
    result = await db.execute(
        select(ContextDAGNode).where(
            ContextDAGNode.id == node_id,
            ContextDAGNode.session_id == session_id,
        )
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="DAG node not found for this session")
    return node


# ---- Request models ----

class ExpandRequest(BaseModel):
    """Request body for expanding a DAG node."""
    node_id: str = Field(..., min_length=1, max_length=36)


class GrepRequest(BaseModel):
    """Request body for searching conversation history."""
    query: str = Field(..., min_length=1, max_length=500)


# ---- Endpoints ----

@router.get("/context-dag/{session_id}")
async def get_dag_structure(
    session_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return the full DAG tree structure and stats for a session."""
    await _require_session_access(db, request, session_id, project_id, min_role="viewer")
    try:
        return await context_dag.get_dag_structure(session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context-dag/{session_id}/health")
async def get_dag_health(
    session_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return context health statistics for a session."""
    await _require_session_access(db, request, session_id, project_id, min_role="viewer")
    try:
        return await context_dag.get_health(session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/context-dag/{session_id}/expand")
async def expand_node(
    session_id: str,
    body: ExpandRequest,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Expand a DAG node to see its original messages or child summaries."""
    await _require_session_access(db, request, session_id, project_id, min_role="viewer")
    node = await _require_dag_node(db, session_id, body.node_id)
    try:
        items = await context_dag.expand_node(body.node_id, session_id=session_id)
        return {"node_id": body.node_id, "depth": node.depth, "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/context-dag/{session_id}/grep")
async def grep_history(
    session_id: str,
    body: GrepRequest,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Search all messages in a session's history (case-insensitive)."""
    await _require_session_access(db, request, session_id, project_id, min_role="viewer")
    if not body.query or not body.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty")
    try:
        results = await context_dag.grep_history(session_id, body.query)
        return {"query": body.query, "count": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/context-dag/{session_id}/node/{node_id}")
async def get_node_details(
    session_id: str,
    node_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return full metadata for a single DAG node."""
    await _require_session_access(db, request, session_id, project_id, min_role="viewer")
    await _require_dag_node(db, session_id, node_id)
    try:
        info = await context_dag.describe_node(node_id, session_id=session_id)
        if "error" in info:
            raise HTTPException(status_code=404, detail=info["error"])
        return info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/context-dag/{session_id}/compact")
async def force_compact(
    session_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Force DAG compaction for a session (creates summary nodes for uncovered messages)."""
    await _require_session_access(db, request, session_id, project_id, min_role="researcher")
    try:
        await context_dag.compact_if_needed(session_id)
        health = await context_dag.get_health(session_id)
        return {"compacted": True, "status": "ok", "health": health}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
