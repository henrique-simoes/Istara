"""Project Reports API — view convergent research reports."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.core.report_manager import report_manager

router = APIRouter(prefix="/reports")


@router.get("/{project_id}")
async def get_project_reports(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get all reports for a project, ordered by layer (highest first)."""
    return await report_manager.get_project_reports(project_id, db)
