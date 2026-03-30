"""Update checking API — version info, update availability, pre-update backup."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

# Read version from VERSION file at project root
VERSION_FILE = Path(__file__).resolve().parents[3] / "VERSION"


def get_current_version() -> str:
    """Read the current Istara version from the VERSION file."""
    try:
        if VERSION_FILE.exists():
            return VERSION_FILE.read_text().strip()
    except Exception:
        pass
    return "unknown"


@router.get("/updates/version")
async def current_version():
    """Return the current Istara version."""
    return {
        "version": get_current_version(),
        "format": "calver",
        "description": "CalVer date-based versioning (YYYY.MM.DD[.N])",
    }


@router.get("/updates/check")
async def check_for_updates():
    """Check GitHub Releases for a newer version.

    Compares the local VERSION against the latest GitHub Release tag.
    Returns update availability, download URLs, and changelog.
    """
    current = get_current_version()

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            # GitHub API: get latest release
            resp = await client.get(
                "https://api.github.com/repos/henrique-simoes/Istara/releases/latest",
                headers={"Accept": "application/vnd.github.v3+json"},
            )

            if resp.status_code == 404:
                return {
                    "update_available": False,
                    "current_version": current,
                    "latest_version": current,
                    "message": "No releases published yet",
                }

            if resp.status_code != 200:
                return {
                    "update_available": False,
                    "current_version": current,
                    "error": f"GitHub API returned {resp.status_code}",
                }

            release = resp.json()
            latest_tag = release.get("tag_name", "").lstrip("v")
            latest_name = release.get("name", "")
            published_at = release.get("published_at", "")
            body = release.get("body", "")
            html_url = release.get("html_url", "")

            # Compare versions (CalVer: lexicographic comparison works)
            update_available = latest_tag > current if latest_tag and current != "unknown" else False

            # Extract download URLs for each platform
            assets = release.get("assets", [])
            downloads = {}
            for asset in assets:
                name = asset.get("name", "").lower()
                url = asset.get("browser_download_url", "")
                if ".dmg" in name:
                    downloads["macos"] = url
                elif ".exe" in name or ".msi" in name:
                    downloads["windows"] = url

            return {
                "update_available": update_available,
                "current_version": current,
                "latest_version": latest_tag,
                "release_name": latest_name,
                "published_at": published_at,
                "changelog": body[:500] if body else "",
                "release_url": html_url,
                "downloads": downloads,
            }

    except Exception as e:
        logger.warning(f"Update check failed: {e}")
        return {
            "update_available": False,
            "current_version": current,
            "error": str(e),
        }


@router.post("/updates/prepare")
async def prepare_update(request: Request, db: AsyncSession = Depends(get_db)):
    """Create a backup before updating. Admin only in team mode.

    This should be called before downloading/applying an update.
    Returns the backup record so the update can be rolled back if needed.
    """
    if settings.team_mode:
        from app.core.security_middleware import require_admin_from_request
        try:
            require_admin_from_request(request)
        except Exception:
            raise HTTPException(status_code=403, detail="Admin required to prepare updates")

    try:
        from app.core.backup_manager import backup_manager
        record = await backup_manager.create_backup(
            backup_type="pre_update",
            note=f"Pre-update backup (current version: {get_current_version()})",
        )
        return {
            "status": "ready",
            "backup_id": record.get("id") if isinstance(record, dict) else str(record),
            "message": "Backup created. Safe to proceed with update.",
            "current_version": get_current_version(),
        }
    except Exception as e:
        logger.error(f"Pre-update backup failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Backup failed: {e}. Do NOT proceed with update.",
        )
