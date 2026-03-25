"""Data Integrity Check — detects orphaned filesystem data on startup.

Runs lightweight checks to ensure database records match filesystem state:
- LanceDB project directories have matching DB projects
- Keyword indexes have matching DB projects
- Uploaded files have matching document records
- Persona directories have matching agent records

Reports warnings but does NOT delete orphaned data (user must decide).
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)


async def run_integrity_check(db: AsyncSession) -> dict:
    """Run a complete data integrity check. Returns a health report."""
    report = {
        "status": "healthy",
        "checks": [],
        "orphans": {
            "lance_db": [],
            "keyword_index": [],
            "uploads": [],
            "personas": [],
        },
        "warnings": [],
    }

    # 1. Check LanceDB projects
    lance_path = Path(settings.lance_db_path)
    db_projects = await _get_project_ids(db)
    if lance_path.exists():
        lance_dirs = [d.name for d in lance_path.iterdir() if d.is_dir()]

        orphaned_lance = [d for d in lance_dirs if d not in db_projects]
        report["orphans"]["lance_db"] = orphaned_lance
        report["checks"].append({
            "name": "LanceDB vector stores",
            "total": len(lance_dirs),
            "orphaned": len(orphaned_lance),
            "status": "warning" if orphaned_lance else "ok",
        })
        if orphaned_lance:
            report["warnings"].append(
                f"{len(orphaned_lance)} LanceDB directories have no matching project in the database"
            )

    # 2. Check keyword indexes
    keyword_path = Path("./data/keyword_index")
    if keyword_path.exists():
        keyword_files = [f.stem for f in keyword_path.glob("*.db")]

        orphaned_kw = [f for f in keyword_files if f not in db_projects]
        report["orphans"]["keyword_index"] = orphaned_kw
        report["checks"].append({
            "name": "Keyword indexes (BM25)",
            "total": len(keyword_files),
            "orphaned": len(orphaned_kw),
            "status": "warning" if orphaned_kw else "ok",
        })
        if orphaned_kw:
            report["warnings"].append(
                f"{len(orphaned_kw)} keyword index files have no matching project"
            )

    # 3. Check upload directories
    upload_path = Path(settings.upload_dir)
    if upload_path.exists():
        upload_dirs = [d.name for d in upload_path.iterdir() if d.is_dir()]

        orphaned_uploads = [d for d in upload_dirs if d not in db_projects]
        report["orphans"]["uploads"] = orphaned_uploads
        report["checks"].append({
            "name": "Upload directories",
            "total": len(upload_dirs),
            "orphaned": len(orphaned_uploads),
            "status": "warning" if orphaned_uploads else "ok",
        })
        if orphaned_uploads:
            report["warnings"].append(
                f"{len(orphaned_uploads)} upload directories have no matching project"
            )

    # 4. Check persona directories
    persona_path = Path(__file__).parent.parent / "agents" / "personas"
    if persona_path.exists():
        persona_dirs = [d.name for d in persona_path.iterdir() if d.is_dir()]
        db_agents = await _get_agent_ids(db)
        # System agents are always valid
        system_agents = {"reclaw-main", "reclaw-devops", "reclaw-ui-audit", "reclaw-ux-eval", "reclaw-sim"}

        orphaned_personas = [
            d for d in persona_dirs
            if d not in db_agents and d not in system_agents
        ]
        report["orphans"]["personas"] = orphaned_personas
        report["checks"].append({
            "name": "Agent persona directories",
            "total": len(persona_dirs),
            "orphaned": len(orphaned_personas),
            "status": "warning" if orphaned_personas else "ok",
        })
        if orphaned_personas:
            report["warnings"].append(
                f"{len(orphaned_personas)} persona directories have no matching agent record"
            )

    # Overall status
    if report["warnings"]:
        report["status"] = "warning"

    return report


async def _get_project_ids(db: AsyncSession) -> set:
    """Get all project IDs from the database."""
    try:
        result = await db.execute(text("SELECT id FROM projects"))
        return {row[0] for row in result.fetchall()}
    except Exception:
        return set()


async def _get_agent_ids(db: AsyncSession) -> set:
    """Get all agent IDs from the database."""
    try:
        result = await db.execute(text("SELECT id FROM agents"))
        return {row[0] for row in result.fetchall()}
    except Exception:
        return set()
