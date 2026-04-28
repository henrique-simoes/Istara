"""File upload and processing API routes."""

import os
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.file_processor import get_supported_extensions, process_file
from app.core.rag import VectorStore, ingest_chunks
from app.models.database import get_db, async_session
from app.models.document import Document, DocumentSource, DocumentStatus
from app.models.project import Project
from sqlalchemy import select
from sqlalchemy import select

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


@router.post("/files/upload/{project_id}")
async def upload_file(
    project_id: str,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Upload a file and process it into the project's knowledge base."""
    # Validate extension
    suffix = Path(file.filename or "").suffix.lower()
    all_supported = set(get_supported_extensions()) | MEDIA_EXTENSIONS
    if suffix not in all_supported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Supported: {', '.join(sorted(all_supported))}",
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

            if result.error:
                doc.status = DocumentStatus.ERROR
                doc.description = f"Transcription error: {result.error}"
                await db.commit()
                return

            # 2. Ingest chunks into vector store
            await ingest_chunks(project_id, result.chunks)

            # 3. Update document record
            doc.content_text = "\n\n".join(c.text for c in result.chunks)
            doc.content_preview = doc.content_text[:2000]
            doc.status = DocumentStatus.READY
            await db.commit()

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Background audio processing failed for {file_path}: {e}")
        async with async_session() as db:
            doc = await db.get(Document, doc_id)
            if doc:
                doc.status = DocumentStatus.ERROR
                doc.description = f"Fatal processing error: {e}"
                await db.commit()


@router.get("/files/{project_id}")
async def list_files(project_id: str, db: AsyncSession = Depends(get_db)):
    """List all uploaded files for a project."""
    project_upload_dir = await _resolve_project_folder(db, project_id)
    if not project_upload_dir.exists():
        return {"files": []}

    files = []
    supported = set(get_supported_extensions()) | MEDIA_EXTENSIONS

    for file_path in sorted(project_upload_dir.iterdir()):
        if file_path.is_file() and file_path.suffix.lower() in supported:
            stat = file_path.stat()
            files.append(
                {
                    "name": file_path.name,
                    "size_bytes": stat.st_size,
                    "modified": stat.st_mtime,
                    "type": file_path.suffix.lower(),
                }
            )

    return {"files": files, "count": len(files)}


@router.post("/files/{project_id}/reprocess")
async def reprocess_files(project_id: str, db: AsyncSession = Depends(get_db)):
    """Reprocess all files for a project (re-embed and re-index)."""
    project_upload_dir = await _resolve_project_folder(db, project_id)
    if not project_upload_dir.exists():
        return {"status": "no files", "processed": 0}

    total_chunks = 0
    processed_files = 0
    errors = []

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
async def file_stats(project_id: str):
    """Get vector store stats for a project."""
    store = VectorStore(project_id)
    count = await store.count()
    return {
        "project_id": project_id,
        "indexed_chunks": count,
    }


@router.get("/files/{project_id}/content/{filename}")
async def get_file_content(project_id: str, filename: str):
    """Get file content for preview. Returns text content for supported formats."""
    project_upload_dir = Path(settings.upload_dir) / project_id
    file_path = project_upload_dir / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # Security: ensure file is within upload dir
    try:
        file_path.resolve().relative_to(project_upload_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    suffix = file_path.suffix.lower()

    # Text-based files: return content directly
    if suffix in {".txt", ".md", ".csv"}:
        async with aiofiles.open(file_path, "r", errors="replace") as f:
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
        return {
            "filename": filename,
            "type": suffix,
            "content": None,
            "media_url": f"/api/files/{project_id}/serve/{filename}",
            "size": stat.st_size,
        }

    return {"filename": filename, "type": suffix, "content": None, "size": 0}


@router.post("/files/{project_id}/scan")
async def scan_project_files(project_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Trigger a file watcher scan for the project's folder.

    Used by the seeder script and for manual re-scans that also create
    research tasks based on file classification.
    """
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
async def serve_file(project_id: str, filename: str):
    """Serve a file directly (for media playback, image display, PDF viewer)."""
    project_upload_dir = Path(settings.upload_dir) / project_id
    file_path = project_upload_dir / filename

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        file_path.resolve().relative_to(project_upload_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(file_path)
