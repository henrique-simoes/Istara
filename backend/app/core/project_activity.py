"""Project activity helpers shared by autonomous background systems."""

from __future__ import annotations

import logging

from app.models.database import async_session
from app.models.project import Project

logger = logging.getLogger(__name__)


async def is_project_active(project_id: str) -> bool:
    """Return whether a project exists and is not paused."""
    try:
        async with async_session() as db:
            project = await db.get(Project, project_id)
            return bool(project and not project.is_paused)
    except Exception as exc:
        logger.error("Project activity check failed for %s: %s", project_id, exc)
        return False
