"""Document management API routes — source of truth for all project outputs."""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import get_db
from app.models.document import Document, DocumentSource, DocumentStatus

router = APIRouter()


# --- Request / Response Schemas ---


class DocumentCreate(BaseModel):
    """Create a new document record."""

    project_id: str
    title: str
    description: str = ""
    file_path: str = ""
    file_name: str = ""
    file_type: str = ""
    file_size: int = 0
    source: str = "user_upload"
    task_id: str | None = None
    agent_ids: list[str] = []
    skill_names: list[str] = []
    tags: list[str] = []
    phase: str = "discover"
    atomic_path: dict = {}
    content_preview: str = ""
    content_text: str = ""


class DocumentUpdate(BaseModel):
    """Update a document."""

    title: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    phase: str | None = None
    status: str | None = None
    atomic_path: dict | None = None
    content_preview: str | None = None
    content_text: str | None = None
    version: int | None = None


# --- Endpoints ---


@router.get("/documents")
async def list_documents(
    project_id: str | None = None,
    phase: str | None = None,
    tag: str | None = None,
    source: str | None = None,
    status: str | None = None,
    task_id: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List documents with filtering, search, and pagination."""
    query = select(Document).order_by(Document.updated_at.desc())

    # Filters
    conditions = []
    if project_id:
        conditions.append(Document.project_id == project_id)
    if phase:
        conditions.append(Document.phase == phase)
    if source:
        try:
            conditions.append(Document.source == DocumentSource(source))
        except ValueError:
            pass
    if status:
        try:
            conditions.append(Document.status == DocumentStatus(status))
        except ValueError:
            pass
    if task_id:
        conditions.append(Document.task_id == task_id)
    if tag:
        # Search in JSON tags field
        conditions.append(Document.tags.contains(f'"{tag}"'))

    # Full-text search across title, description, content, tags
    if search:
        search_pattern = f"%{search}%"
        conditions.append(
            or_(
                Document.title.ilike(search_pattern),
                Document.description.ilike(search_pattern),
                Document.content_preview.ilike(search_pattern),
                Document.content_text.ilike(search_pattern),
                Document.tags.ilike(search_pattern),
                Document.file_name.ilike(search_pattern),
            )
        )

    if conditions:
        query = query.where(and_(*conditions))

    # Count total
    count_query = select(func.count(Document.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    docs = result.scalars().all()

    return {
        "documents": [d.to_dict() for d in docs],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }


@router.get("/documents/{document_id}")
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single document with full details."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    data = doc.to_dict()
    # Include full content for single-document view
    data["content_text"] = doc.content_text or ""
    return data


@router.post("/documents", status_code=201)
async def create_document(data: DocumentCreate, db: AsyncSession = Depends(get_db)):
    """Create a new document record."""
    doc_id = str(uuid.uuid4())

    doc = Document(
        id=doc_id,
        project_id=data.project_id,
        title=data.title,
        description=data.description,
        file_path=data.file_path,
        file_name=data.file_name,
        file_type=data.file_type,
        file_size=data.file_size,
        status=DocumentStatus.READY,
        source=DocumentSource(data.source) if data.source else DocumentSource.USER_UPLOAD,
        task_id=data.task_id,
        phase=data.phase,
        content_preview=data.content_preview[:2000] if data.content_preview else "",
        content_text=data.content_text,
    )
    doc.set_agent_ids(data.agent_ids)
    doc.set_skill_names(data.skill_names)
    doc.set_tags(data.tags)
    doc.set_atomic_path(data.atomic_path)

    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # Broadcast to agents via WebSocket
    try:
        from app.api.websocket import broadcast
        await broadcast({
            "type": "document_created",
            "data": {"document_id": doc_id, "title": data.title, "project_id": data.project_id},
        })
    except Exception:
        pass

    return doc.to_dict()


@router.patch("/documents/{document_id}")
async def update_document(
    document_id: str, data: DocumentUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a document."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if data.title is not None:
        doc.title = data.title
    if data.description is not None:
        doc.description = data.description
    if data.phase is not None:
        doc.phase = data.phase
    if data.status is not None:
        try:
            doc.status = DocumentStatus(data.status)
        except ValueError:
            pass
    if data.tags is not None:
        doc.set_tags(data.tags)
    if data.atomic_path is not None:
        doc.set_atomic_path(data.atomic_path)
    if data.content_preview is not None:
        doc.content_preview = data.content_preview[:2000]
    if data.content_text is not None:
        doc.content_text = data.content_text
    if data.version is not None:
        doc.version = data.version

    await db.commit()
    await db.refresh(doc)

    # Broadcast update
    try:
        from app.api.websocket import broadcast
        await broadcast({
            "type": "document_updated",
            "data": {"document_id": document_id, "title": doc.title, "project_id": doc.project_id},
        })
    except Exception:
        pass

    return doc.to_dict()


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a document."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    await db.delete(doc)
    await db.commit()


@router.get("/documents/{document_id}/content")
async def get_document_content(document_id: str, db: AsyncSession = Depends(get_db)):
    """Get full document content for preview."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # If the document has a file_path, try to read directly
    if doc.file_path:
        file_path = Path(doc.file_path)
        if not file_path.is_absolute():
            file_path = Path(settings.upload_dir) / doc.project_id / doc.file_path

        if file_path.exists() and file_path.is_file():
            suffix = file_path.suffix.lower()
            if suffix in {".txt", ".md", ".csv", ".json"}:
                content = file_path.read_text(errors="replace")
                return {
                    "id": doc.id,
                    "file_name": doc.file_name,
                    "type": suffix,
                    "content": content,
                    "size": len(content),
                }
            elif suffix in {".pdf", ".docx"}:
                from app.core.file_processor import process_file
                result = process_file(file_path)
                text = "\n\n".join(c.text for c in result.chunks) if result.chunks else ""
                return {
                    "id": doc.id,
                    "file_name": doc.file_name,
                    "type": suffix,
                    "content": text,
                    "pages": result.pages,
                    "size": len(text),
                }
            elif suffix in {".jpg", ".jpeg", ".png", ".gif"}:
                return {
                    "id": doc.id,
                    "file_name": doc.file_name,
                    "type": suffix,
                    "content": None,
                    "media_url": f"/api/files/{doc.project_id}/serve/{file_path.name}",
                    "size": file_path.stat().st_size,
                }
            elif suffix in {".mp3", ".wav", ".m4a", ".ogg", ".mp4", ".webm", ".mov"}:
                return {
                    "id": doc.id,
                    "file_name": doc.file_name,
                    "type": suffix,
                    "content": None,
                    "media_url": f"/api/files/{doc.project_id}/serve/{file_path.name}",
                    "size": file_path.stat().st_size,
                }

    # Fallback to stored content_text
    return {
        "id": doc.id,
        "file_name": doc.file_name,
        "type": doc.file_type,
        "content": doc.content_text or doc.content_preview or "",
        "size": len(doc.content_text or doc.content_preview or ""),
    }


@router.get("/documents/search/full")
async def search_documents(
    project_id: str,
    q: str,
    phase: str | None = None,
    tag: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Full-text search across document titles, descriptions, content, and tags."""
    search_pattern = f"%{q}%"
    conditions = [
        Document.project_id == project_id,
        or_(
            Document.title.ilike(search_pattern),
            Document.description.ilike(search_pattern),
            Document.content_text.ilike(search_pattern),
            Document.content_preview.ilike(search_pattern),
            Document.tags.ilike(search_pattern),
            Document.file_name.ilike(search_pattern),
        ),
    ]

    if phase:
        conditions.append(Document.phase == phase)
    if tag:
        conditions.append(Document.tags.contains(f'"{tag}"'))

    query = (
        select(Document)
        .where(and_(*conditions))
        .order_by(Document.updated_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    docs = result.scalars().all()

    return {
        "query": q,
        "results": [d.to_dict() for d in docs],
        "total": len(docs),
    }


@router.get("/documents/tags/{project_id}")
async def get_document_tags(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get all unique tags used across documents in a project."""
    result = await db.execute(
        select(Document.tags).where(Document.project_id == project_id)
    )
    all_tags_raw = result.scalars().all()

    tag_counts: dict[str, int] = {}
    for tags_json in all_tags_raw:
        try:
            tags = json.loads(tags_json) if tags_json else []
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "tags": [{"name": t, "count": c} for t, c in sorted(tag_counts.items(), key=lambda x: -x[1])],
    }


@router.post("/documents/sync/{project_id}")
async def sync_project_documents(project_id: str, db: AsyncSession = Depends(get_db)):
    """Scan the project's upload directory and register any untracked files as documents.

    This ensures files placed directly in the project folder instantly appear in the Documents UI.
    """
    upload_dir = Path(settings.upload_dir) / project_id
    if not upload_dir.exists():
        return {"synced": 0, "total": 0}

    from app.core.file_processor import get_supported_extensions

    MEDIA_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".mp4", ".webm", ".mov", ".jpg", ".jpeg", ".png", ".gif"}
    supported = set(get_supported_extensions()) | MEDIA_EXTENSIONS

    # Get existing document file_paths to avoid duplicates
    existing_result = await db.execute(
        select(Document.file_name).where(Document.project_id == project_id)
    )
    existing_files = {r for r in existing_result.scalars().all()}

    synced = 0
    for file_path in sorted(upload_dir.iterdir()):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in supported:
            continue
        if file_path.name in existing_files:
            continue

        stat = file_path.stat()
        suffix = file_path.suffix.lower()

        # Read preview for text-based files
        content_preview = ""
        content_text = ""
        if suffix in {".txt", ".md", ".csv", ".json"}:
            try:
                text = file_path.read_text(errors="replace")
                content_preview = text[:2000]
                content_text = text
            except Exception:
                pass

        # Generate a human-readable title from filename
        title = file_path.stem.replace("-", " ").replace("_", " ").title()

        doc = Document(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title=title,
            description=f"File added to project folder: {file_path.name}",
            file_path=str(file_path),
            file_name=file_path.name,
            file_type=suffix,
            file_size=stat.st_size,
            status=DocumentStatus.READY,
            source=DocumentSource.PROJECT_FILE,
            content_preview=content_preview,
            content_text=content_text,
        )
        doc.set_tags([])

        db.add(doc)
        synced += 1

    if synced > 0:
        await db.commit()

    total_result = await db.execute(
        select(func.count(Document.id)).where(Document.project_id == project_id)
    )
    total = total_result.scalar() or 0

    return {"synced": synced, "total": total}


@router.get("/documents/stats/{project_id}")
async def document_stats(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get document statistics for a project."""
    # Total count
    total_result = await db.execute(
        select(func.count(Document.id)).where(Document.project_id == project_id)
    )
    total = total_result.scalar() or 0

    # By source
    source_result = await db.execute(
        select(Document.source, func.count(Document.id))
        .where(Document.project_id == project_id)
        .group_by(Document.source)
    )
    by_source = {str(r[0].value) if hasattr(r[0], "value") else str(r[0]): r[1] for r in source_result.fetchall()}

    # By phase
    phase_result = await db.execute(
        select(Document.phase, func.count(Document.id))
        .where(Document.project_id == project_id)
        .group_by(Document.phase)
    )
    by_phase = {str(r[0]): r[1] for r in phase_result.fetchall()}

    # By status
    status_result = await db.execute(
        select(Document.status, func.count(Document.id))
        .where(Document.project_id == project_id)
        .group_by(Document.status)
    )
    by_status = {str(r[0].value) if hasattr(r[0], "value") else str(r[0]): r[1] for r in status_result.fetchall()}

    return {
        "total": total,
        "by_source": by_source,
        "by_phase": by_phase,
        "by_status": by_status,
    }
