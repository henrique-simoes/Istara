"""Update checking API — version info, update availability, backup, and auto-update."""

import asyncio
import logging
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

# Read version from VERSION file at project root.
# Path: backend/app/api/routes/updates.py → 4 parents up → project root
# Also tries CWD-based paths for robustness across install methods.
_CANDIDATES = [
    Path(__file__).resolve().parents[4] / "VERSION",  # from backend/app/api/routes/
    Path(__file__).resolve().parents[3] / "VERSION",  # fallback (different layout)
    Path.cwd() / "VERSION",                            # CWD is project root
    Path.cwd().parent / "VERSION",                     # CWD is backend/
]


def get_current_version() -> str:
    """Read the current Istara version from the VERSION file."""
    for p in _CANDIDATES:
        try:
            if p.exists():
                v = p.read_text().strip()
                if v:
                    return v
        except Exception:
            continue
    return "unknown"


def get_install_dir() -> Path | None:
    """Find the Istara install directory (contains VERSION + backend/ + frontend/)."""
    for p in _CANDIDATES:
        try:
            if p.exists() and (p.parent / "backend").is_dir():
                return p.parent
        except Exception:
            continue
    return None


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


@router.post("/updates/apply")
async def apply_update(request: Request):
    """Auto-update Istara via git pull + rebuild + restart.

    For git-based installs (shell one-liner, from source):
      1. Creates a pre-update backup
      2. Runs git pull in the install directory
      3. Updates backend deps (pip install)
      4. Rebuilds frontend (npm install + npm run build)
      5. Restarts services via istara.sh

    Admin only in team mode. Returns immediately — the update runs async.
    """
    if settings.team_mode:
        from app.core.security_middleware import require_admin_from_request
        try:
            require_admin_from_request(request)
        except Exception:
            raise HTTPException(status_code=403, detail="Admin required to apply updates")

    install_dir = get_install_dir()
    if not install_dir:
        raise HTTPException(status_code=500, detail="Cannot find Istara install directory")

    if not (install_dir / ".git").is_dir():
        raise HTTPException(
            status_code=400,
            detail="Auto-update requires a git-based install. Use: curl -fsSL .../install-istara.sh | bash",
        )

    # Run the update in background so the API can respond immediately
    asyncio.create_task(_run_update(install_dir))

    return {
        "status": "updating",
        "message": "Update started. Istara will backup, update, and restart automatically. This may take 1-3 minutes.",
        "install_dir": str(install_dir),
    }


async def _run_update(install_dir: Path):
    """Background task: backup → git pull → rebuild → restart."""
    try:
        # 1. Create pre-update backup
        logger.info("Auto-update: creating backup...")
        try:
            from app.core.backup_manager import backup_manager
            await backup_manager.create_backup(
                backup_type="pre_update",
                note=f"Auto-update backup (from {get_current_version()})",
            )
            logger.info("Auto-update: backup complete")
        except Exception as e:
            logger.warning(f"Auto-update: backup failed ({e}), continuing anyway...")

        # 2. Broadcast update notification
        try:
            from app.api.websocket import manager
            await manager.broadcast("system", {
                "type": "update_started",
                "message": "Istara is updating. The server will restart in a moment...",
            })
        except Exception:
            pass

        # 3. Run the update script
        # Create a temporary update script that survives server restart
        update_script = install_dir / ".istara-update.sh"
        venv_pip = install_dir / "venv" / "bin" / "pip"
        npm_cmd = "npm"
        # Find npm
        for p in ["/opt/homebrew/bin/npm", "/opt/homebrew/opt/node/bin/npm", "/usr/local/bin/npm"]:
            if Path(p).exists():
                npm_cmd = p
                break

        update_script.write_text(f"""#!/usr/bin/env bash
set -e
cd "{install_dir}"

# Stop services
if [ -f istara.sh ]; then
    ./istara.sh stop 2>/dev/null || true
fi

# Pull latest code
git pull --ff-only 2>/dev/null || git pull

# Update backend deps
if [ -x "{venv_pip}" ]; then
    "{venv_pip}" install -r backend/requirements.txt --quiet 2>/dev/null || true
fi

# Rebuild frontend
cd frontend
"{npm_cmd}" install --silent 2>/dev/null || true
NEXT_PUBLIC_API_URL="http://localhost:8000" NEXT_PUBLIC_WS_URL="ws://localhost:8000" \\
    "{npm_cmd}" run build 2>/dev/null || true
cd ..

# Restart services
if [ -f istara.sh ]; then
    ./istara.sh start
fi

# Clean up
rm -f .istara-update.sh
""")
        update_script.chmod(0o755)

        # Execute update script in background (detached from this process)
        logger.info("Auto-update: launching update script...")
        subprocess.Popen(
            ["bash", str(update_script)],
            cwd=str(install_dir),
            stdout=open(str(install_dir / ".istara-update.log"), "w"),
            stderr=subprocess.STDOUT,
            start_new_session=True,  # Survives parent process death
        )

        logger.info("Auto-update: script launched, server will restart soon")

    except Exception as e:
        logger.error(f"Auto-update failed: {e}")
        # Try to notify clients
        try:
            from app.api.websocket import manager
            await manager.broadcast("system", {
                "type": "update_failed",
                "message": f"Update failed: {e}",
            })
        except Exception:
            pass


async def check_for_updates_on_startup():
    """Called once on app startup — checks for updates and creates a notification if available.

    This runs in a background task after the server is fully started.
    """
    await asyncio.sleep(15)  # Wait for server to fully initialize

    try:
        current = get_current_version()
        if current == "unknown":
            return

        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.github.com/repos/henrique-simoes/Istara/releases/latest",
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            if resp.status_code != 200:
                return

            release = resp.json()
            latest_tag = release.get("tag_name", "").lstrip("v")
            if not latest_tag or latest_tag <= current:
                return

            # Update is available — create a notification
            logger.info(f"Update available: {current} → {latest_tag}")
            changelog = release.get("body", "")[:200]

            try:
                from app.api.websocket import manager
                await manager.broadcast("update_available", {
                    "current_version": current,
                    "latest_version": latest_tag,
                    "release_name": release.get("name", ""),
                    "changelog": changelog,
                    "release_url": release.get("html_url", ""),
                })
            except Exception:
                pass

            # Also persist as a notification in the database
            try:
                from app.services.notification_service import persist_notification
                await persist_notification("update_available", {
                    "title": f"Istara {latest_tag} is available",
                    "message": f"Update from {current} to {latest_tag}. Go to Settings to update.",
                    "current_version": current,
                    "latest_version": latest_tag,
                })
            except Exception as e:
                logger.debug(f"Failed to persist update notification: {e}")

    except Exception as e:
        logger.debug(f"Startup update check failed: {e}")
