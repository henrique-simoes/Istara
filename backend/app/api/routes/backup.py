"""Backup management API routes."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings
from app.core.backup_manager import backup_manager
from app.core.security_middleware import require_admin_from_request

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------


class BackupConfigUpdate(BaseModel):
    """Request body for updating backup configuration."""

    backup_enabled: bool | None = None
    backup_interval_hours: int | None = None
    backup_retention_count: int | None = None
    backup_full_interval_days: int | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/backups")
async def list_backups():
    """List all backup records ordered by creation date descending."""
    backups = await backup_manager.list_backups()
    return {"backups": backups, "total": len(backups)}


@router.post("/backups/create")
async def create_backup(backup_type: str = "full", request: Request = None):
    """Create a new backup (full or incremental). Admin only."""
    require_admin_from_request(request)
    # Accept backup_type from query param or JSON body
    if request:
        try:
            body = await request.json()
            if isinstance(body, dict) and "backup_type" in body:
                backup_type = body["backup_type"]
        except Exception:
            pass
    if backup_type not in ("full", "incremental"):
        raise HTTPException(status_code=400, detail="backup_type must be 'full' or 'incremental'")

    try:
        result = await backup_manager.create_backup(backup_type=backup_type)
        return result
    except Exception as exc:
        logger.exception("Backup creation failed")
        raise HTTPException(status_code=500, detail=f"Backup failed: {exc}") from exc


@router.post("/backups/{backup_id}/restore")
async def restore_from_backup(backup_id: str, request: Request):
    """Restore from a specific backup archive. Admin only."""
    require_admin_from_request(request)
    try:
        result = await backup_manager.restore_from_backup(backup_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Restore failed")
        raise HTTPException(status_code=500, detail=f"Restore failed: {exc}") from exc


@router.post("/backups/{backup_id}/verify")
async def verify_backup(backup_id: str):
    """Verify checksums of a backup archive against its manifest."""
    try:
        result = await backup_manager.verify_backup(backup_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Verification failed")
        raise HTTPException(status_code=500, detail=f"Verify failed: {exc}") from exc


@router.delete("/backups/{backup_id}")
async def delete_backup(backup_id: str, request: Request):
    """Delete a single backup record and its archive file. Admin only."""
    require_admin_from_request(request)
    deleted = await backup_manager.delete_backup(backup_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Backup not found")
    return {"success": True, "deleted": backup_id}


@router.get("/backups/config")
async def get_backup_config():
    """Get current backup configuration."""
    return {
        "backup_enabled": settings.backup_enabled,
        "backup_dir": settings.backup_dir,
        "backup_interval_hours": settings.backup_interval_hours,
        "backup_retention_count": settings.backup_retention_count,
        "backup_full_interval_days": settings.backup_full_interval_days,
    }


@router.post("/backups/config")
async def update_backup_config(data: BackupConfigUpdate, request: Request):
    """Update backup configuration and persist to .env. Admin only."""
    require_admin_from_request(request)
    from app.api.routes.settings import _persist_env

    updated: dict[str, object] = {}

    if data.backup_enabled is not None:
        settings.backup_enabled = data.backup_enabled
        _persist_env("BACKUP_ENABLED", str(data.backup_enabled).lower())
        updated["backup_enabled"] = data.backup_enabled

    if data.backup_interval_hours is not None:
        settings.backup_interval_hours = data.backup_interval_hours
        _persist_env("BACKUP_INTERVAL_HOURS", str(data.backup_interval_hours))
        updated["backup_interval_hours"] = data.backup_interval_hours

    if data.backup_retention_count is not None:
        settings.backup_retention_count = data.backup_retention_count
        _persist_env("BACKUP_RETENTION_COUNT", str(data.backup_retention_count))
        updated["backup_retention_count"] = data.backup_retention_count

    if data.backup_full_interval_days is not None:
        settings.backup_full_interval_days = data.backup_full_interval_days
        _persist_env("BACKUP_FULL_INTERVAL_DAYS", str(data.backup_full_interval_days))
        updated["backup_full_interval_days"] = data.backup_full_interval_days

    return {"status": "updated", "updated_fields": updated}


@router.get("/backups/estimate")
async def get_backup_estimate():
    """Get an estimated size for the next backup."""
    return backup_manager.get_backup_size_estimate()


@router.post("/backups/upload-restore")
async def upload_and_restore_backup(request: Request):
    """Upload a .tar.gz backup and restore the system from it. Admin only."""
    require_admin_from_request(request)
    
    from fastapi import UploadFile, File
    form = await request.form()
    file = form.get("file")
    if not isinstance(file, UploadFile):
        raise HTTPException(status_code=400, detail="No backup file provided")

    if not file.filename.endswith(".tar.gz"):
        raise HTTPException(status_code=400, detail="Invalid file format. Must be .tar.gz")

    # Save to temp location
    temp_path = Path(settings.backup_dir) / f"upload_{int(time.time())}.tar.gz"
    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Initiate restore
        success = await backup_manager.restore_backup(temp_path)
        if not success:
            raise HTTPException(status_code=500, detail="Restoration failed during extraction")
            
        # Trigger async restart
        asyncio.create_task(_delayed_restart())
        
        return {"status": "restoring", "message": "Restoration started. Server will restart in 5 seconds."}
        
    finally:
        # Cleanup temp file is handled by restore_backup or here if failed
        if temp_path.exists():
            temp_path.unlink()

async def _delayed_restart():
    """Give the API time to return before killing the server."""
    await asyncio.sleep(5)
    # The install-istara.sh systemd/launchd will auto-restart the process
    os._exit(0)


@router.get("/backups/{backup_id}/download")
async def download_backup(backup_id: str, request: Request):
    """Stream the backup tar.gz archive as a download. Admin only."""
    require_admin_from_request(request)
    archive_path = await backup_manager.get_archive_path(backup_id)
    if not archive_path:
        raise HTTPException(status_code=404, detail="Backup archive not found")

    def _iter_file():
        with open(archive_path, "rb") as f:
            while chunk := f.read(1 << 16):  # 64KB chunks
                yield chunk

    return StreamingResponse(
        _iter_file(),
        media_type="application/gzip",
        headers={
            "Content-Disposition": f"attachment; filename={archive_path.name}",
            "Content-Length": str(archive_path.stat().st_size),
        },
    )
