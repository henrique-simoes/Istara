"""File upload and processing API routes."""

import os
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.file_processor import get_supported_extensions, process_file
from app.core.keyword_index import KeywordIndex
from app.core.permissions import get_visible_project_or_404
from app.core.rag import VectorStore, ingest_chunks
from app.models.database import async_session, get_db
from app.models.document import Document, DocumentSource, DocumentStatus
from app.models.project import Project

# Media and image extensions that can be uploaded/served but not text-processed
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

# Audio extensions that we can transcribe
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg"}

router = APIRouter()


def _project_roots(project: Project | None, project_id: str) -> list[Path]:
    roots = [Path(settings.upload_dir) / project_id]
    watch_folder_path = getattr(project, "watch_folder_path", None) if project else None
    if watch_folder_path:
        watch_root = Path(watch_folder_path)
        if watch_root not in roots:
            roots.append(watch_root)
    return roots


def _safe_filename(filename: str) -> str:
    name = Path(filename or "").name
    if not name or name != filename or name in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid filename")
    return name


def _path_within_roots(path: Path, roots: list[Path]) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    for root in roots:
        try:
            resolved.relative_to(root.resolve())
            return True
        except (OSError, ValueError):
            continue
    return False


async def _get_project(
    db: AsyncSession, request: Request, project_id: str, min_role: str = "viewer"
) -> Project:
    return await get_visible_project_or_404(db, request, project_id, min_role=min_role)  # type: ignore[arg-type]


async def _resolve_project_folder(db, project_id: str) -> Path:
    """Resolve the primary folder to scan for project files.

    Returns watch_folder_path if the project has one set, otherwise falls
    back to the internal uploads directory.
    """
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project and getattr(project, "watch_folder_path", None):
        return Path(project.watch_folder_path)
    return Path(settings.upload_dir) / project_id


async def _resolve_project_file(
    db: AsyncSession, project: Project, project_id: str, filename: str
) -> tuple[Path, Document | None]:
    safe_name = _safe_filename(filename)
    roots = _project_roots(project, project_id)
    doc_rows = (
        (await db.execute(select(Document).where(Document.project_id == project_id)))
        .scalars()
        .all()
    )

    for doc in doc_rows:
        doc_path = Path(doc.file_path or "")
        if (
            doc_path.name == safe_name
            and doc_path.exists()
            and doc_path.is_file()
            and _path_within_roots(doc_path, roots)
        ):
            return doc_path, doc

    for root in roots:
        candidate = root / safe_name
        if candidate.exists() and candidate.is_file() and _path_within_roots(candidate, roots):
            doc = next(
                (
                    row
                    for row in doc_rows
                    if row.file_name == safe_name or Path(row.file_path or "").name == safe_name
                ),
                None,
            )
            return candidate, doc

    raise HTTPException(status_code=404, detail="File not found")


@router.post("/files/upload/{project_id}")
async def upload_file(
    project_id: str,
    request: Request,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Upload a file and process it into the project's knowledge base."""
    await _get_project(db, request, project_id, min_role="researcher")

    # Validate extension
    suffix = Path(file.filename or "").suffix.lower()
    all_supported = set(get_supported_extensions()) | MEDIA_EXTENSIONS
    if suffix not in all_supported:
        supported = ", ".join(sorted(all_supported))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Supported: {supported}",
        )

    # Save file to upload directory
    project_upload_dir = Path(settings.upload_dir) / project_id
    project_upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    safe_filename = f"{file_id}{suffix}"
    file_path = project_upload_dir / safe_filename

    async with aiofiles.open(file_path, "wb") as f:
        content = await file.read()
        await f.write(content)

    # Media files (Images/Video): store only, skip text extraction
    if suffix in MEDIA_EXTENSIONS and suffix not in AUDIO_EXTENSIONS:
        doc = Document(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title=(file.filename or "")
            .rsplit(".", 1)[0]
            .replace("-", " ")
            .replace("_", " ")
            .title(),
            file_name=file.filename or safe_filename,
            file_path=str(file_path),
            file_type=suffix,
            file_size=len(content),
            source=DocumentSource.USER_UPLOAD,
            status=DocumentStatus.READY,
        )
        db.add(doc)
        await db.commit()
        return {
            "status": "stored",
            "file_id": file_id,
            "filename": file.filename,
            "saved_as": safe_filename,
            "total_chars": 0,
            "pages": 0,
            "chunks_indexed": 0,
        }

    # Audio files: trigger background transcription
    if suffix in AUDIO_EXTENSIONS:
        doc_id = str(uuid.uuid4())
        doc = Document(
            id=doc_id,
            project_id=project_id,
            title=(file.filename or "")
            .rsplit(".", 1)[0]
            .replace("-", " ")
            .replace("_", " ")
            .title(),
            file_name=file.filename or safe_filename,
            file_path=str(file_path),
            file_type=suffix,
            file_size=len(content),
            source=DocumentSource.USER_UPLOAD,
            status=DocumentStatus.PROCESSING,
        )
        db.add(doc)
        await db.commit()

        background_tasks.add_task(
            _process_audio_background,
            project_id=project_id,
            doc_id=doc_id,
            file_path=file_path,
        )

        return {
            "status": "processing",
            "file_id": file_id,
            "doc_id": doc_id,
            "filename": file.filename,
            "saved_as": safe_filename,
        }

    # Text-based files: Process the file synchronously (usually fast)
    result = process_file(file_path)

    if result.error:
        return {
            "status": "error",
            "file_id": file_id,
            "filename": file.filename,
            "error": result.error,
        }

    # Remove existing chunks for this source before re-ingesting
    store = VectorStore(project_id)
    await store.delete_by_source(file_path.name)

    # Ingest chunks into vector store
    chunks_indexed = await ingest_chunks(project_id, result.chunks)
    content_text = "\n\n".join(c.text for c in result.chunks)

    # Create a Document record so the file appears in Documents view immediately
    doc = Document(
        id=str(uuid.uuid4()),
        project_id=project_id,
        title=(file.filename or "").rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title(),
        file_name=file.filename or safe_filename,
        file_path=str(file_path),
        file_type=suffix,
        file_size=len(content),
        source=DocumentSource.USER_UPLOAD,
        status=DocumentStatus.READY,
        content_text=content_text,
        content_preview=content_text[:2000],
    )
    db.add(doc)
    await db.commit()

    response = {
        "status": "processed",
        "file_id": file_id,
        "filename": file.filename,
        "saved_as": safe_filename,
        "total_chars": result.total_chars,
        "pages": result.pages,
        "chunks_indexed": chunks_indexed,
        "indexing_status": "vector" if chunks_indexed else "keyword_only",
        "threat_level": result.threat_level,
    }
    if result.threats:
        response["threats"] = result.threats
    return response


async def _process_audio_background(project_id: str, doc_id: str, file_path: Path):
    """Background task to transcribe audio and index results."""
    from app.core.file_processor import process_file

    try:
        # 1. Transcribe and chunk
        result = process_file(file_path)

        async with async_session() as db:
            doc = await db.get(Document, doc_id)
            if not doc:
                return

            transcription = result.metadata.get("transcription", {}) if result.metadata else {}
            transcription_tags = (
                transcription.get("tags") if isinstance(transcription, dict) else []
            )
            if transcription_tags:
                doc.set_tags(transcription_tags)
            if transcription:
                doc.set_atomic_path({"transcription": transcription})

            if result.error:
                doc.status = DocumentStatus.ERROR
                doc.description = f"Transcription error: {result.error}"
                try:
                    from app.core.improvement_governance import improvement_governance

                    await improvement_governance.record_feature_evidence(
                        feature="interviews_audio_upload_transcription_tagging_documents",
                        source_system="transcription",
                        source_id=doc_id,
                        project_id=project_id,
                        agent_id="transcription-pipeline",
                        summary="Audio transcription failed during document processing.",
                        evidence={
                            "passed": False,
                            "document_id": doc_id,
                            "file_name": file_path.name,
                            "error": result.error,
                            "transcription": transcription,
                        },
                        metrics_after={"needs_review": True},
                        db=db,
                    )
                except Exception:
                    pass
                await db.commit()
                return

            # 2. Ingest chunks into vector store
            await ingest_chunks(project_id, result.chunks)

            # 3. Update document record
            doc.content_text = "\n\n".join(c.text for c in result.chunks)
            doc.content_preview = doc.content_text[:2000]
            if isinstance(transcription, dict):
                doc.description = (
                    f"Audio transcript. Language: {transcription.get('language', 'unknown')}. "
                    f"ICR: {transcription.get('icr_confidence', 'insufficient')}. "
                    f"Needs review: {bool(transcription.get('needs_review'))}."
                )
            doc.status = DocumentStatus.READY
            try:
                from app.core.improvement_governance import improvement_governance

                await improvement_governance.record_feature_evidence(
                    feature="interviews_audio_upload_transcription_tagging_documents",
                    source_system="transcription",
                    source_id=doc_id,
                    project_id=project_id,
                    agent_id="transcription-pipeline",
                    summary="Audio upload was transcribed, tagged, and stored as a document.",
                    evidence={
                        "passed": not bool(transcription.get("needs_review"))
                        if isinstance(transcription, dict)
                        else True,
                        "document_id": doc_id,
                        "file_name": file_path.name,
                        "language": transcription.get("language")
                        if isinstance(transcription, dict)
                        else None,
                        "requested_language": transcription.get("engine_metadata", {}).get(
                            "requested_language"
                        )
                        if isinstance(transcription, dict)
                        else None,
                        "detected_language": transcription.get("engine_metadata", {}).get(
                            "detected_language"
                        )
                        if isinstance(transcription, dict)
                        else None,
                        "confidence": transcription.get("confidence")
                        if isinstance(transcription, dict)
                        else None,
                        "icr_kappa": transcription.get("icr_kappa")
                        if isinstance(transcription, dict)
                        else None,
                        "icr_confidence": transcription.get("icr_confidence")
                        if isinstance(transcription, dict)
                        else None,
                        "tags": transcription_tags,
                    },
                    metrics_after={
                        "confidence": transcription.get("confidence")
                        if isinstance(transcription, dict)
                        else None,
                        "icr_kappa": transcription.get("icr_kappa")
                        if isinstance(transcription, dict)
                        else None,
                        "needs_review": bool(transcription.get("needs_review"))
                        if isinstance(transcription, dict)
                        else False,
                    },
                    confidence=float(transcription.get("confidence", 0.5))
                    if isinstance(transcription, dict)
                    else 0.5,
                    db=db,
                )
            except Exception:
                pass
            await db.commit()

    except Exception as e:
        import logging

        logging.getLogger(__name__).error(
            f"Background audio processing failed for {file_path}: {e}"
        )
        async with async_session() as db:
            doc = await db.get(Document, doc_id)
            if doc:
                doc.status = DocumentStatus.ERROR
                doc.description = f"Fatal processing error: {e}"
                await db.commit()


@router.get("/files/{project_id}")
async def list_files(project_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """List all uploaded files for a project."""
    project = await _get_project(db, request, project_id, min_role="viewer")

    project_roots = _project_roots(project, project_id)

    doc_rows = (
        (await db.execute(select(Document).where(Document.project_id == project_id)))
        .scalars()
        .all()
    )
    docs_by_path_name = {Path(doc.file_path or "").name: doc for doc in doc_rows if doc.file_path}
    docs_by_file_name = {doc.file_name: doc for doc in doc_rows if doc.file_name}

    files = []
    seen: set[str] = set()
    supported = set(get_supported_extensions()) | MEDIA_EXTENSIONS

    for project_upload_dir in project_roots:
        if not project_upload_dir.exists():
            continue
        for file_path in sorted(project_upload_dir.iterdir()):
            if file_path.name in seen:
                continue
            if file_path.is_file() and file_path.suffix.lower() in supported:
                seen.add(file_path.name)
                stat = file_path.stat()
                doc = docs_by_path_name.get(file_path.name) or docs_by_file_name.get(file_path.name)
                item = {
                    "name": file_path.name,
                    "display_name": doc.file_name if doc else file_path.name,
                    "document_id": doc.id if doc else None,
                    "document_status": doc.status.value if doc and doc.status else None,
                    "size_bytes": stat.st_size,
                    "modified": stat.st_mtime,
                    "type": file_path.suffix.lower(),
                    "tags": doc.get_tags() if doc else [],
                    "has_transcript": bool(doc and doc.content_text),
                }
                if doc:
                    atomic_path = doc.get_atomic_path()
                    transcription = (
                        atomic_path.get("transcription") if isinstance(atomic_path, dict) else None
                    )
                    if isinstance(transcription, dict):
                        item["transcription_language"] = transcription.get("language")
                        item["transcription_needs_review"] = transcription.get("needs_review")
                files.append(item)

    return {"files": files, "count": len(files)}


@router.post("/files/{project_id}/reprocess")
async def reprocess_files(project_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Reprocess all files for a project (re-embed and re-index)."""
    project = await _get_project(db, request, project_id, min_role="researcher")

    project_roots = [root for root in _project_roots(project, project_id) if root.exists()]
    if not project_roots:
        return {"status": "no files", "processed": 0}

    total_chunks = 0
    processed_files = 0
    errors = []

    for project_upload_dir in project_roots:
        for file_path in project_upload_dir.iterdir():
            if not file_path.is_file():
                continue

            result = process_file(file_path)
            if result.error:
                errors.append({"file": file_path.name, "error": result.error})
                continue

            if result.chunks:
                # Remove existing chunks for this source before re-ingesting
                store = VectorStore(project_id)
                await store.delete_by_source(file_path.name)

                chunks = await ingest_chunks(project_id, result.chunks)
                total_chunks += chunks
                processed_files += 1

    return {
        "status": "complete",
        "processed": processed_files,
        "total_chunks": total_chunks,
        "errors": errors,
    }


@router.get("/files/{project_id}/stats")
async def file_stats(project_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Get vector store stats for a project."""
    await _get_project(db, request, project_id, min_role="viewer")

    store = VectorStore(project_id)
    vector_count = await store.count()
    keyword_count = await KeywordIndex(project_id).count()
    if vector_count and keyword_count:
        indexing_status = "hybrid"
    elif vector_count:
        indexing_status = "vector_only"
    elif keyword_count:
        indexing_status = "keyword_only"
    else:
        indexing_status = "empty"

    return {
        "project_id": project_id,
        "indexed_chunks": vector_count,
        "keyword_chunks": keyword_count,
        "total_chunks": vector_count,
        "searchable_chunks": max(vector_count, keyword_count),
        "indexing_status": indexing_status,
    }


@router.get("/files/{project_id}/content/{filename}")
async def get_file_content(
    project_id: str,
    filename: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get file content for preview. Returns text content for supported formats."""
    project = await _get_project(db, request, project_id, min_role="viewer")
    file_path, doc = await _resolve_project_file(db, project, project_id, filename)

    suffix = file_path.suffix.lower()

    # Text-based files: return content directly
    if suffix in {".txt", ".md", ".csv"}:
        async with aiofiles.open(file_path, errors="replace") as f:
            content = await f.read()
        return {"filename": filename, "type": suffix, "content": content, "size": len(content)}

    # PDF: try to extract text
    if suffix == ".pdf":
        result = process_file(file_path)
        text = "\n\n".join(chunk.text for chunk in result.chunks) if result.chunks else ""
        return {
            "filename": filename,
            "type": suffix,
            "content": text,
            "pages": result.pages,
            "size": len(text),
        }

    # DOCX: extract text
    if suffix == ".docx":
        result = process_file(file_path)
        text = "\n\n".join(chunk.text for chunk in result.chunks) if result.chunks else ""
        return {"filename": filename, "type": suffix, "content": text, "size": len(text)}

    # Media files: return metadata only (frontend handles playback via direct URL)
    if suffix in MEDIA_EXTENSIONS:
        stat = os.stat(file_path)
        content = (doc.content_text or doc.content_preview) if doc else None
        atomic_path = doc.get_atomic_path() if doc else {}
        return {
            "filename": filename,
            "type": suffix,
            "content": content,
            "media_url": f"/api/files/{project_id}/serve/{filename}",
            "size": stat.st_size,
            "document_id": doc.id if doc else None,
            "document_status": doc.status.value if doc and doc.status else None,
            "tags": doc.get_tags() if doc else [],
            "transcription": atomic_path.get("transcription")
            if isinstance(atomic_path, dict)
            else None,
        }

    return {"filename": filename, "type": suffix, "content": None, "size": 0}


@router.post("/files/{project_id}/scan")
async def scan_project_files(project_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Trigger a file watcher scan for the project's folder.

    Used by the seeder script and for manual re-scans that also create
    research tasks based on file classification.
    """
    await _get_project(db, request, project_id, min_role="researcher")

    scan_dir = await _resolve_project_folder(db, project_id)
    if not scan_dir.exists():
        return {"status": "no files", "scanned": 0}

    file_watcher = getattr(request.app.state, "file_watcher", None)
    if not file_watcher:
        raise HTTPException(status_code=503, detail="File watcher not available")

    results = await file_watcher.scan_directory(str(scan_dir), project_id)
    return {
        "status": "complete",
        "scanned": len(results),
        "results": results,
    }


@router.get("/files/{project_id}/serve/{filename}")
async def serve_file(
    project_id: str,
    filename: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Serve a file directly (for media playback, image display, PDF viewer)."""
    project = await _get_project(db, request, project_id, min_role="viewer")
    file_path, _doc = await _resolve_project_file(db, project, project_id, filename)

    return FileResponse(file_path)
