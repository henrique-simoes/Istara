"""Document management API routes — source of truth for all project outputs."""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.file_encryption import (
    encrypt_file_in_place,
    protect_document_text,
    read_file_text,
    reveal_document_text,
)
from app.core.permissions import get_visible_project_or_404
from app.models.code_application import CodeApplication
from app.models.database import get_db
from app.models.document import Document, DocumentSource, DocumentStatus
from app.models.finding import Nugget
from app.models.project import Project
from app.services.research_validity_service import (
    document_research_spine_summary,
    document_source_unit_count_map,
    persist_document_source_evidence_units,
    record_source_evidence_unit_telemetry,
)

router = APIRouter()

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg"}
MEDIA_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".ogg",
    ".mp4",
    ".webm",
    ".mov",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
}


def _dedupe_text_list(values: list[str]) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for value in values:
        item = str(value or "").strip()
        if item and item not in seen:
            cleaned.append(item)
            seen.add(item)
    return cleaned


def _project_roots(project, project_id: str) -> list[Path]:
    roots = [Path(settings.upload_dir).expanduser() / project_id]
    watch_path = getattr(project, "watch_folder_path", None) if project else None
    if watch_path:
        watch_root = Path(watch_path).expanduser()
        if watch_root not in roots:
            roots.append(watch_root)
    return roots


def _is_allowed_project_path(path: Path, project, project_id: str) -> bool:
    try:
        resolved = path.expanduser().resolve()
    except OSError:
        return False
    for root in _project_roots(project, project_id):
        try:
            resolved.relative_to(root.expanduser().resolve())
            return True
        except (OSError, ValueError):
            continue
    return False


def _is_managed_upload_path(path: Path) -> bool:
    try:
        path.expanduser().resolve().relative_to(Path(settings.upload_dir).expanduser().resolve())
        return True
    except (OSError, ValueError):
        return False


def _resolve_project_folder(project, project_id: str) -> Path:
    """Resolve the primary folder to scan for project files.

    Returns watch_folder_path if the project has one set, otherwise falls
    back to the internal uploads directory.
    """
    if project and getattr(project, "watch_folder_path", None):
        return Path(project.watch_folder_path)
    return Path(settings.upload_dir) / project_id


def _resolve_document_file_path(doc: Document, project=None) -> Path | None:
    """Resolve a document's stored file path across legacy relative formats."""
    if not doc.file_path:
        return None

    raw_path = Path(doc.file_path)
    if raw_path.is_absolute() and _is_allowed_project_path(raw_path, project, doc.project_id):
        return raw_path

    upload_dir = Path(settings.upload_dir)
    raw_parts = raw_path.parts
    upload_parts = upload_dir.parts[-2:]
    if len(upload_parts) == 2:
        for idx in range(0, len(raw_parts) - 1):
            if raw_parts[idx : idx + 2] == upload_parts:
                candidate = upload_dir / Path(*raw_parts[idx + 2 :])
                if candidate.exists() and _is_allowed_project_path(
                    candidate, project, doc.project_id
                ):
                    return candidate

    candidates = [
        raw_path,
        upload_dir / doc.project_id / raw_path,
    ]
    if raw_path.name != str(raw_path):
        candidates.append(upload_dir.parent / raw_path)
    else:
        candidates.append(upload_dir / doc.project_id / raw_path.name)

    for candidate in candidates:
        if candidate.exists() and _is_allowed_project_path(candidate, project, doc.project_id):
            return candidate
    fallback = candidates[-1]
    return fallback if _is_allowed_project_path(fallback, project, doc.project_id) else None


def _document_payload(doc: Document, source_evidence_units: int = 0) -> dict[str, Any]:
    data = doc.to_dict()
    source_text = reveal_document_text(doc.content_text or doc.content_preview or "")
    data["research_spine"] = document_research_spine_summary(
        source_evidence_units=source_evidence_units,
        status=data.get("status", "ready"),
        source=data.get("source", "user_upload"),
        text_available=bool(source_text),
    )
    return data


async def _document_payloads(
    db: AsyncSession, project_id: str, docs: list[Document]
) -> list[dict[str, Any]]:
    counts = await document_source_unit_count_map(
        db,
        project_id=project_id,
        document_ids=[doc.id for doc in docs],
    )
    return [_document_payload(doc, counts.get(doc.id, 0)) for doc in docs]


async def _persist_document_source_units(
    db: AsyncSession,
    doc: Document,
    *,
    qa_provisional: bool = False,
    source_kind: str = "",
) -> list[Any]:
    if doc.status != DocumentStatus.READY:
        return []
    source_text = reveal_document_text(doc.content_text or doc.content_preview or "")
    if not source_text.strip():
        return []
    metadata: dict[str, Any] = {
        "file_name": doc.file_name,
        "file_type": doc.file_type,
        "ingestion_surface": "documents_api",
    }
    if qa_provisional:
        # Explicit QA provenance boundary (master plan §6.4): synthetic QA rows
        # are stamped provisional at ingestion and can never reach
        # accepted/reportable states. The coding-run guard blocks promotion for
        # any evidence unit carrying this marker.
        metadata.update(
            {
                "is_qa_provisional": True,
                "source_kind": source_kind or "synthetic_qa",
                "promotion_blocked": True,
                "qa_run_boundary": "synthetic_qa_provisional",
            }
        )
    return await persist_document_source_evidence_units(
        db,
        project_id=doc.project_id,
        document_id=doc.id,
        source_text=source_text,
        source_location=doc.file_name or doc.title or doc.id,
        source_document_id=doc.id,
        source_type=doc.source.value if doc.source else "document",
        method="document_ingestion",
        phase=doc.phase,
        task_id=doc.task_id,
        version=doc.version or 1,
        metadata=metadata,
    )


def _safe_json_list(value: str | None) -> list:
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _source_matches_document(source: str, doc: Document) -> bool:
    if not source:
        return False
    source_name = Path(source).name
    names = {doc.file_name, doc.title, Path(doc.file_path or "").name}
    return any(name and (name in source or source_name == name) for name in names)


def _require_active_project_id(project_id: str | None) -> str:
    if not project_id or not project_id.strip():
        raise HTTPException(status_code=400, detail="project_id is required")
    return project_id.strip()


async def _require_active_project_document(
    db: AsyncSession,
    request: Request,
    document_id: str,
    project_id: str | None,
    *,
    min_role: str,
) -> tuple[str, Document]:
    scoped_project_id = _require_active_project_id(project_id)
    await get_visible_project_or_404(db, request, scoped_project_id, min_role=min_role)
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.project_id == scoped_project_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return scoped_project_id, doc


async def _project_tag_counts(db: AsyncSession, project_id: str) -> dict[str, int]:
    """Aggregate project tags from documents, nuggets, and code applications."""
    tag_counts: dict[str, int] = {}

    doc_rows = (
        (await db.execute(select(Document.tags).where(Document.project_id == project_id)))
        .scalars()
        .all()
    )
    for tags_json in doc_rows:
        for tag in _safe_json_list(tags_json):
            if isinstance(tag, str) and tag.strip():
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

    nugget_rows = (
        (await db.execute(select(Nugget.tags).where(Nugget.project_id == project_id)))
        .scalars()
        .all()
    )
    for tags_json in nugget_rows:
        for tag in _safe_json_list(tags_json):
            if isinstance(tag, str) and tag.strip():
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

    code_rows = (
        (
            await db.execute(
                select(CodeApplication.code_id).where(CodeApplication.project_id == project_id)
            )
        )
        .scalars()
        .all()
    )
    for code_id in code_rows:
        if code_id and code_id.strip():
            tag_counts[code_id] = tag_counts.get(code_id, 0) + 1

    return tag_counts


async def _document_ids_for_project_tag(
    db: AsyncSession, project_id: str | None, tag: str
) -> list[str]:
    """Find documents related to a tag through direct tags or nugget sources."""
    if not project_id:
        return []

    docs = (
        (await db.execute(select(Document).where(Document.project_id == project_id)))
        .scalars()
        .all()
    )
    matched_ids = {
        doc.id for doc in docs if tag in [t for t in doc.get_tags() if isinstance(t, str)]
    }

    nugget_rows = (
        (
            await db.execute(
                select(Nugget.source).where(
                    Nugget.project_id == project_id,
                    Nugget.tags.contains(f'"{tag}"'),
                )
            )
        )
        .scalars()
        .all()
    )
    for source in nugget_rows:
        for doc in docs:
            if _source_matches_document(source or "", doc):
                matched_ids.add(doc.id)

    return list(matched_ids)


# --- Request / Response Schemas ---


class DocumentCreate(BaseModel):
    """Create a new document record."""

    project_id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=20000)
    file_path: str = Field(default="", max_length=1000)
    file_name: str = Field(default="", max_length=500)
    file_type: str = Field(default="", max_length=40)
    file_size: int = Field(default=0, ge=0)
    source: DocumentSource = DocumentSource.USER_UPLOAD
    task_id: str | None = Field(default=None, max_length=80)
    agent_ids: list[str] = Field(default_factory=list, max_length=100)
    skill_names: list[str] = Field(default_factory=list, max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=200)
    phase: str = Field(default="discover", max_length=20)
    atomic_path: dict[str, Any] = Field(default_factory=dict)
    content_preview: str = Field(default="", max_length=2000)
    content_text: str = Field(default="", max_length=5000000)
    # QA provenance boundary (master plan §6.4): when set, every evidence unit
    # persisted for this document is stamped is_qa_provisional=true and can
    # never reach accepted/reportable states. Used by the disposable QA
    # seeder only; normal product ingestion leaves these unset.
    qa_provisional: bool = Field(default=False)
    source_kind: str = Field(default="", max_length=60)

    @field_validator(
        "project_id",
        "title",
        "description",
        "file_path",
        "file_name",
        "file_type",
        "task_id",
        "phase",
        "content_preview",
        "content_text",
        mode="before",
    )
    @classmethod
    def _strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return str(value).strip()

    @field_validator("file_type")
    @classmethod
    def _normalize_file_type(cls, value: str) -> str:
        return value.lower()

    @field_validator("agent_ids", "skill_names", "tags", mode="after")
    @classmethod
    def _normalize_lists(cls, value: list[str]) -> list[str]:
        return _dedupe_text_list(value)


class DocumentUpdate(BaseModel):
    """Update a document."""

    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=20000)
    tags: list[str] | None = Field(default=None, max_length=200)
    phase: str | None = Field(default=None, max_length=20)
    status: DocumentStatus | None = None
    atomic_path: dict[str, Any] | None = None
    content_preview: str | None = Field(default=None, max_length=2000)
    content_text: str | None = Field(default=None, max_length=5000000)
    version: int | None = Field(default=None, ge=1, le=1000000)

    @field_validator(
        "title", "description", "phase", "content_preview", "content_text", mode="before"
    )
    @classmethod
    def _strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return str(value).strip()

    @field_validator("tags", mode="after")
    @classmethod
    def _normalize_tags(cls, value: list[str] | None) -> list[str] | None:
        return _dedupe_text_list(value) if value is not None else None


async def _require_task_in_project(db: AsyncSession, project_id: str, task_id: str | None) -> None:
    if not task_id:
        return
    from app.models.task import Task

    task = (
        await db.execute(select(Task.id).where(Task.id == task_id, Task.project_id == project_id))
    ).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Linked task not found in this project.")


# --- Endpoints ---


@router.get("/documents")
async def list_documents(
    request: Request,
    project_id: str | None = None,
    phase: str | None = None,
    tag: str | None = None,
    source: DocumentSource | None = None,
    status: DocumentStatus | None = None,
    task_id: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List documents with filtering, search, and pagination."""
    scoped_project_id = _require_active_project_id(project_id)
    await get_visible_project_or_404(db, request, scoped_project_id, min_role="viewer")

    query = select(Document).order_by(Document.updated_at.desc())

    # Filters
    conditions = [Document.project_id == scoped_project_id]
    if phase:
        conditions.append(Document.phase == phase)
    if source:
        conditions.append(Document.source == source)
    if status:
        conditions.append(Document.status == status)
    if task_id:
        conditions.append(Document.task_id == task_id)
    if tag:
        # Search direct document tags and tag-bearing nugget sources.
        tagged_doc_ids = await _document_ids_for_project_tag(db, scoped_project_id, tag)
        conditions.append(or_(Document.tags.contains(f'"{tag}"'), Document.id.in_(tagged_doc_ids)))

    decrypted_search = bool(search and settings.file_encryption_enabled)
    # Full-text search across title, description, content, tags
    if search:
        search_pattern = f"%{search}%"
        if not decrypted_search:
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

    if decrypted_search:
        # Encrypted content cannot be searched with SQL LIKE. Fetch the filtered
        # project set, decrypt in application memory, then paginate.
        result = await db.execute(query)
        query_text = (search or "").lower()
        all_docs = []
        for doc in result.scalars().all():
            plain_content = reveal_document_text(doc.content_text or doc.content_preview or "")
            haystack = "\n".join(
                [
                    doc.title or "",
                    doc.description or "",
                    doc.file_name or "",
                    doc.tags or "",
                    plain_content,
                ]
            ).lower()
            if query_text in haystack:
                all_docs.append(doc)
        total = len(all_docs)
        offset = (page - 1) * page_size
        docs = all_docs[offset : offset + page_size]
        payloads = await _document_payloads(db, scoped_project_id, list(docs))
        return {
            "documents": payloads,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }

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
    payloads = await _document_payloads(db, scoped_project_id, list(docs))

    return {
        "documents": payloads,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
    }


@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get a single document with full details."""
    _, doc = await _require_active_project_document(
        db,
        request,
        document_id,
        project_id,
        min_role="viewer",
    )

    counts = await document_source_unit_count_map(
        db,
        project_id=doc.project_id,
        document_ids=[doc.id],
    )
    data = _document_payload(doc, counts.get(doc.id, 0))
    # Include full content for single-document view
    data["content_text"] = reveal_document_text(doc.content_text or "")
    return data


@router.post("/documents", status_code=201)
async def create_document(
    data: DocumentCreate, request: Request, db: AsyncSession = Depends(get_db)
):
    """Create a new document record."""
    await get_visible_project_or_404(db, request, data.project_id, min_role="researcher")
    await _require_task_in_project(db, data.project_id, data.task_id)
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
        source=data.source,
        task_id=data.task_id,
        phase=data.phase,
        content_preview=protect_document_text(
            (data.content_preview or data.content_text[:2000])[:2000]
        )
        if (data.content_preview or data.content_text)
        else "",
        content_text=protect_document_text(data.content_text),
        version=1,
    )
    doc.set_agent_ids(data.agent_ids)
    doc.set_skill_names(data.skill_names)
    doc.set_tags(data.tags)
    doc.set_atomic_path(data.atomic_path)
    if data.file_path:
        candidate_path = Path(data.file_path)
        if candidate_path.exists() and _is_managed_upload_path(candidate_path):
            encrypt_file_in_place(candidate_path)

    db.add(doc)
    units = await _persist_document_source_units(
        db,
        doc,
        qa_provisional=data.qa_provisional,
        source_kind=data.source_kind,
    )
    await db.commit()
    await record_source_evidence_unit_telemetry(
        project_id=doc.project_id,
        task_id=doc.task_id,
        units=units,
    )
    await db.refresh(doc)

    # Broadcast to agents via WebSocket
    try:
        from app.api.websocket import broadcast

        await broadcast(
            {
                "type": "document_created",
                "data": {"document_id": doc_id, "title": data.title, "project_id": data.project_id},
            }
        )
    except Exception:
        pass

    return _document_payload(doc, len(units))


@router.patch("/documents/{document_id}")
async def update_document(
    document_id: str,
    data: DocumentUpdate,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Update a document."""
    _, doc = await _require_active_project_document(
        db,
        request,
        document_id,
        project_id,
        min_role="researcher",
    )

    if data.title is not None:
        doc.title = data.title
    if data.description is not None:
        doc.description = data.description
    if data.phase is not None:
        doc.phase = data.phase
    if data.status is not None:
        doc.status = data.status
    if data.tags is not None:
        doc.set_tags(data.tags)
    if data.atomic_path is not None:
        doc.set_atomic_path(data.atomic_path)
    content_changed = False
    if data.content_preview is not None:
        doc.content_preview = protect_document_text(data.content_preview[:2000])
    if data.content_text is not None:
        current_content = reveal_document_text(doc.content_text or "")
        content_changed = data.content_text != current_content
        doc.content_text = protect_document_text(data.content_text)
        if data.content_preview is None:
            doc.content_preview = protect_document_text(data.content_text[:2000])
    if data.version is not None:
        doc.version = data.version
    elif content_changed:
        doc.version = (doc.version or 1) + 1

    units = []
    if content_changed:
        units = await _persist_document_source_units(db, doc)

    await db.commit()
    await record_source_evidence_unit_telemetry(
        project_id=doc.project_id,
        task_id=doc.task_id,
        units=units,
    )
    await db.refresh(doc)

    # Broadcast update
    try:
        from app.api.websocket import broadcast

        await broadcast(
            {
                "type": "document_updated",
                "data": {
                    "document_id": document_id,
                    "title": doc.title,
                    "project_id": doc.project_id,
                },
            }
        )
    except Exception:
        pass

    counts = await document_source_unit_count_map(
        db,
        project_id=doc.project_id,
        document_ids=[doc.id],
    )
    return _document_payload(doc, counts.get(doc.id, len(units)))


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Delete a document."""
    _, doc = await _require_active_project_document(
        db,
        request,
        document_id,
        project_id,
        min_role="researcher",
    )

    # Uploaded files live in the managed upload root and are scanned by the
    # automatic project-folder sync. Remove the physical artifact with the
    # USER_UPLOAD row so a later sync cannot resurrect a UUID-named duplicate.
    # Never remove PROJECT_FILE/watch-folder sources or paths outside the
    # managed root; those files remain owned by the user/project folder.
    if doc.source == DocumentSource.USER_UPLOAD:
        managed_file_path = _resolve_document_file_path(doc)
        if managed_file_path and _is_managed_upload_path(managed_file_path):
            try:
                if managed_file_path.exists() and managed_file_path.is_file():
                    managed_file_path.unlink()
            except OSError as exc:
                raise HTTPException(
                    status_code=500,
                    detail="Unable to remove the managed upload; document was not deleted",
                ) from exc

    await db.delete(doc)
    await db.commit()


@router.get("/documents/{document_id}/content")
async def get_document_content(
    document_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get full document content for preview."""
    _, doc = await _require_active_project_document(
        db,
        request,
        document_id,
        project_id,
        min_role="viewer",
    )
    project = (
        await db.execute(select(Project).where(Project.id == doc.project_id))
    ).scalar_one_or_none()

    # If the document has a file_path, try to read directly
    file_path = _resolve_document_file_path(doc, project)
    if file_path:
        if file_path.exists() and file_path.is_file():
            suffix = file_path.suffix.lower()
            if suffix in {".txt", ".md", ".csv", ".json"}:
                content = read_file_text(file_path)
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
            elif suffix in {".mp3", ".wav", ".m4a", ".ogg"}:
                content = reveal_document_text(doc.content_text or doc.content_preview or "")
                return {
                    "id": doc.id,
                    "file_name": doc.file_name,
                    "type": suffix,
                    "content": content,
                    "media_url": f"/api/files/{doc.project_id}/serve/{file_path.name}",
                    "size": file_path.stat().st_size,
                    "status": doc.status.value if doc.status else "ready",
                    "tags": doc.get_tags(),
                    "transcription": doc.get_atomic_path().get("transcription"),
                }
            elif suffix in {".mp4", ".webm", ".mov"}:
                return {
                    "id": doc.id,
                    "file_name": doc.file_name,
                    "type": suffix,
                    "content": None,
                    "media_url": f"/api/files/{doc.project_id}/serve/{file_path.name}",
                    "size": file_path.stat().st_size,
                }

    # Fallback to stored content_text
    stored_content = reveal_document_text(doc.content_text or doc.content_preview or "")
    return {
        "id": doc.id,
        "file_name": doc.file_name,
        "type": doc.file_type,
        "content": stored_content,
        "size": len(stored_content),
    }


@router.get("/documents/search/full")
async def search_documents(
    request: Request,
    project_id: str,
    q: str = Query(..., min_length=1, max_length=500),
    phase: str | None = None,
    tag: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Full-text search across document titles, descriptions, content, and tags."""
    await get_visible_project_or_404(db, request, project_id, min_role="viewer")
    conditions = [Document.project_id == project_id]

    if phase:
        conditions.append(Document.phase == phase)
    if tag:
        conditions.append(Document.tags.contains(f'"{tag}"'))

    query = select(Document).where(and_(*conditions)).order_by(Document.updated_at.desc())

    result = await db.execute(query)
    query_text = q.lower()
    docs = []
    for doc in result.scalars().all():
        plain_content = reveal_document_text(doc.content_text or doc.content_preview or "")
        haystack = "\n".join(
            [
                doc.title or "",
                doc.description or "",
                doc.file_name or "",
                doc.tags or "",
                plain_content,
            ]
        ).lower()
        if query_text in haystack:
            docs.append(doc)
        if len(docs) >= limit:
            break

    return {
        "query": q,
        "results": [d.to_dict() for d in docs],
        "total": len(docs),
    }


@router.get("/documents/tags/{project_id}")
async def get_document_tags(project_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Get all unique project tags across documents, findings, and code applications."""
    await get_visible_project_or_404(db, request, project_id, min_role="viewer")
    tag_counts = await _project_tag_counts(db, project_id)

    return {
        "tags": [
            {"name": t, "count": c} for t, c in sorted(tag_counts.items(), key=lambda x: -x[1])
        ],
    }


@router.post("/documents/sync/{project_id}")
async def sync_project_documents(
    project_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Scan the project's folder (external watch folder if linked, otherwise internal uploads)
    and register any untracked files as documents.

    This ensures files placed directly in the project folder instantly appear in the Documents UI.
    """
    project = await get_visible_project_or_404(db, request, project_id, min_role="researcher")

    scan_dir = _resolve_project_folder(project, project_id)
    if not scan_dir.exists():
        return {"synced": 0, "total": 0}

    from app.core.file_processor import get_supported_extensions, process_file
    from app.core.rag import VectorStore, ingest_chunks

    supported = set(get_supported_extensions()) | MEDIA_EXTENSIONS

    # Get existing document file paths to avoid duplicates. Older documents may
    # only have a filename, so keep that as a legacy fallback without letting
    # same-named files in different linked folders block each other.
    existing_result = await db.execute(
        select(Document.file_name, Document.file_path).where(Document.project_id == project_id)
    )
    existing_paths: set[str] = set()
    existing_names_without_path: set[str] = set()
    for file_name, stored_path in existing_result.all():
        if stored_path:
            try:
                existing_paths.add(str(Path(stored_path).expanduser().resolve()))
            except OSError:
                existing_paths.add(str(Path(stored_path).expanduser()))
        elif file_name:
            existing_names_without_path.add(file_name)

    synced = 0
    total_chunks_indexed = 0
    synced_units = []
    for file_path in sorted(scan_dir.iterdir()):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in supported:
            continue
        try:
            resolved_file_path = str(file_path.expanduser().resolve())
        except OSError:
            resolved_file_path = str(file_path.expanduser())
        if resolved_file_path in existing_paths or file_path.name in existing_names_without_path:
            continue

        stat = file_path.stat()
        suffix = file_path.suffix.lower()

        content_preview = ""
        content_text = ""
        status = DocumentStatus.PROCESSING if suffix in AUDIO_EXTENSIONS else DocumentStatus.READY
        description = f"File added to project folder: {file_path.name}"
        chunks_indexed = 0

        if suffix not in MEDIA_EXTENSIONS:
            result = process_file(file_path)
            if result.error and suffix not in AUDIO_EXTENSIONS:
                status = DocumentStatus.ERROR
                description = f"Processing error: {result.error}"
            elif suffix not in AUDIO_EXTENSIONS:
                content_text = "\n\n".join(chunk.text for chunk in result.chunks)
                content_preview = content_text[:2000]
                if result.chunks:
                    store = VectorStore(project_id)
                    await store.delete_by_source(file_path.name)
                    chunks_indexed = await ingest_chunks(project_id, result.chunks)
                    total_chunks_indexed += chunks_indexed

        # Generate a human-readable title from filename
        title = file_path.stem.replace("-", " ").replace("_", " ").title()

        doc = Document(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title=title,
            description=description,
            file_path=str(file_path),
            file_name=file_path.name,
            file_type=suffix,
            file_size=stat.st_size,
            status=status,
            source=DocumentSource.PROJECT_FILE,
            content_preview=protect_document_text(content_preview),
            content_text=protect_document_text(content_text),
        )
        doc.set_tags([])

        db.add(doc)
        if content_text and status == DocumentStatus.READY:
            synced_units.extend(await _persist_document_source_units(db, doc))
        if _is_managed_upload_path(file_path):
            encrypt_file_in_place(file_path)
        if suffix in AUDIO_EXTENSIONS:
            from app.api.routes.files import _process_audio_background

            background_tasks.add_task(
                _process_audio_background,
                project_id=project_id,
                doc_id=doc.id,
                file_path=file_path,
            )
        synced += 1

    if synced > 0:
        await db.commit()
        await record_source_evidence_unit_telemetry(
            project_id=project_id,
            units=synced_units,
        )

    total_result = await db.execute(
        select(func.count(Document.id)).where(Document.project_id == project_id)
    )
    total = total_result.scalar() or 0

    return {"synced": synced, "total": total, "chunks_indexed": total_chunks_indexed}


@router.get("/documents/stats/{project_id}")
async def document_stats(project_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Get document statistics for a project."""
    await get_visible_project_or_404(db, request, project_id, min_role="viewer")
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
    by_source = {
        str(r[0].value) if hasattr(r[0], "value") else str(r[0]): r[1]
        for r in source_result.fetchall()
    }

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
    by_status = {
        str(r[0].value) if hasattr(r[0], "value") else str(r[0]): r[1]
        for r in status_result.fetchall()
    }

    return {
        "total": total,
        "by_source": by_source,
        "by_phase": by_phase,
        "by_status": by_status,
    }
