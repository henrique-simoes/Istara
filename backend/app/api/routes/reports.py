"""Project Reports API — view convergent research reports."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_project_access
from app.core.report_manager import report_manager
from app.models.database import get_db

router = APIRouter(prefix="/reports")


@router.get("/{project_id}")
async def get_project_reports(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Get all reports for a project, ordered by layer (highest first)."""
    await require_project_access(db, request, project_id, min_role="viewer")
    return await report_manager.get_project_reports(project_id, db)
