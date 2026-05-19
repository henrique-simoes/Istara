"""Context hierarchy and resource status API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context_hierarchy import ContextDocument, context_hierarchy
from app.core.permissions import require_project_access
from app.core.resource_governor import governor
from app.core.security_middleware import require_admin_from_request
from app.models.database import get_db

router = APIRouter()


async def _require_context_access(
    db: AsyncSession,
    request: Request,
    doc: ContextDocument,
    *,
    min_role: str = "viewer",
) -> None:
    if doc.project_id:
        await require_project_access(db, request, doc.project_id, min_role=min_role)
        return
    require_admin_from_request(request)


class ContextCreateRequest(BaseModel):
    name: str
    level_type: str
    content: str
    project_id: str = ""
    parent_id: str = ""
    priority: int = 0


class ContextUpdateRequest(BaseModel):
    name: str | None = None
    content: str | None = None
    priority: int | None = None
    enabled: bool | None = None


@router.get("/resources")
async def get_resource_status():
    return governor.get_status()


@router.get("/contexts")
async def list_contexts(
    request: Request,
    level_type: str | None = None,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    scoped_project_id = str(project_id or "").strip()
    if scoped_project_id:
        await require_project_access(db, request, scoped_project_id, min_role="viewer")
    else:
        require_admin_from_request(request)

    docs = await context_hierarchy.list_contexts(db, level_type, scoped_project_id)
    return {
        "contexts": [
            {
                "id": d.id,
                "name": d.name,
                "level": d.level,
                "level_type": d.level_type,
                "content_preview": d.content[:200],
                "content_length": len(d.content),
                "priority": d.priority,
                "enabled": d.enabled,
                "project_id": d.project_id,
            }
            for d in docs
        ]
    }


@router.post("/contexts", status_code=201)
async def create_context(
    data: ContextCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    scoped_project_id = data.project_id.strip()
    parent_id = data.parent_id.strip()

    if scoped_project_id:
        await require_project_access(db, request, scoped_project_id, min_role="researcher")
    else:
        require_admin_from_request(request)

    valid_types = {"platform", "company", "product", "project", "task", "agent"}
    if data.level_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid level_type. Must be: {', '.join(valid_types)}",
        )
    doc = await context_hierarchy.create_context(
        db,
        data.name,
        data.level_type,
        data.content,
        scoped_project_id,
        parent_id,
        data.priority,
    )
    return {"id": doc.id, "name": doc.name, "level": doc.level, "level_type": doc.level_type}


@router.get("/contexts/{doc_id}")
async def get_context(doc_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ContextDocument).where(ContextDocument.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Context not found")
    await _require_context_access(db, request, doc, min_role="viewer")
    return {
        "id": doc.id,
        "name": doc.name,
        "level": doc.level,
        "level_type": doc.level_type,
        "content": doc.content,
        "priority": doc.priority,
        "enabled": doc.enabled,
        "project_id": doc.project_id,
        "parent_id": doc.parent_id,
    }


@router.patch("/contexts/{doc_id}")
async def update_context(
    doc_id: str,
    data: ContextUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ContextDocument).where(ContextDocument.id == doc_id))
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Context not found")
    await _require_context_access(db, request, existing, min_role="researcher")

    updates = data.model_dump(exclude_unset=True)
    doc = await context_hierarchy.update_context(db, doc_id, updates)
    if not doc:
        raise HTTPException(status_code=404, detail="Context not found")
    return {"id": doc.id, "name": doc.name, "updated": True}


@router.delete("/contexts/{doc_id}", status_code=204)
async def delete_context(doc_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ContextDocument).where(ContextDocument.id == doc_id))
    existing = result.scalar_one_or_none()
    if not existing:
        raise HTTPException(status_code=404, detail="Context not found")
    await _require_context_access(db, request, existing, min_role="researcher")

    if not await context_hierarchy.delete_context(db, doc_id):
        raise HTTPException(status_code=404, detail="Context not found")


@router.get("/contexts/composed/{project_id}")
async def get_composed_context(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    scoped_project_id = project_id.strip()
    await require_project_access(db, request, scoped_project_id, min_role="viewer")
    composed = await context_hierarchy.compose_context(db, scoped_project_id)
    return {"project_id": scoped_project_id, "composed_context": composed, "length": len(composed)}
