"""ReasoningBank API — inspect and retrieve distilled agent reasoning memory."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.reasoning_bank import reasoning_bank
from app.core.security_middleware import require_admin_from_request
from app.models.database import get_db

router = APIRouter(prefix="/reasoning-bank")


class ReasoningMemoryCreateRequest(BaseModel):
    project_id: str = ""
    agent_id: str = ""
    source_kind: str = "manual"
    source_id: str = ""
    outcome: str = "unknown"
    title: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    content: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)
    domain: str = ""
    evidence_refs: list[dict | str] = Field(default_factory=list)
    judge_score: float | None = Field(default=None, ge=0, le=1)
    confidence: float = Field(default=0.5, ge=0, le=1)


class ReasoningMemoryRetrieveRequest(BaseModel):
    project_id: str = ""
    query: str = Field(..., min_length=1, max_length=2000)
    agent_id: str | None = None
    source_kinds: list[str] | None = None
    limit: int = Field(default=5, ge=1, le=20)


@router.get("/memories")
async def list_memories(
    request: Request,
    project_id: str | None = Query(default=None),
    source_kind: str | None = Query(default=None),
    outcome: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List active reasoning memories. Admin-only because memories can include traces."""
    require_admin_from_request(request)
    memories = await reasoning_bank.list_memories(
        project_id=project_id,
        source_kind=source_kind,
        outcome=outcome,
        limit=limit,
        offset=offset,
        db=db,
    )
    return {"memories": memories, "count": len(memories), "limit": limit, "offset": offset}


@router.post("/memories")
async def create_memory(
    body: ReasoningMemoryCreateRequest,
    request: Request,
):
    """Create a manual reasoning memory item."""
    require_admin_from_request(request)
    item = await reasoning_bank.record_memory(**body.model_dump())
    return {"memory": item.to_dict()}


@router.post("/retrieve")
async def retrieve_memories(
    body: ReasoningMemoryRetrieveRequest,
    request: Request,
):
    """Retrieve reasoning memories and their prompt-ready context."""
    require_admin_from_request(request)
    memories = await reasoning_bank.retrieve(
        project_id=body.project_id,
        query=body.query,
        agent_id=body.agent_id,
        source_kinds=body.source_kinds,
        limit=body.limit,
    )
    context = await reasoning_bank.context_for_query(
        project_id=body.project_id,
        query=body.query,
        agent_id=body.agent_id,
        source_kinds=body.source_kinds,
        limit=body.limit,
    )
    return {"memories": memories, "context": context}


@router.post("/consolidate")
async def consolidate_memories(
    request: Request,
    project_id: str | None = Query(default=None),
):
    """Merge exact duplicate active memories."""
    require_admin_from_request(request)
    return await reasoning_bank.consolidate_duplicates(project_id=project_id)


@router.get("/summary")
async def reasoning_memory_summary(
    request: Request,
    project_id: str | None = Query(default=None),
):
    """Return aggregate ReasoningBank counts for dashboards and meta-agents."""
    require_admin_from_request(request)
    return await reasoning_bank.summary(project_id=project_id)
