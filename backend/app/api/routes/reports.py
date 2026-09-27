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


@router.get("/{project_id}/{report_id}/export")
async def export_report(
    project_id: str,
    report_id: str,
    request: Request,
    format: str = "md",
    db: AsyncSession = Depends(get_db),
):
    """Download a report as Markdown, Word or CSV, every finding with its evidence trail."""
    from fastapi import HTTPException, Response

    from app.models.project_report import ProjectReport
    from app.services.report_export import render_csv, render_docx, render_markdown, trace_report

    await require_project_access(db, request, project_id, min_role="viewer")
    report = await db.get(ProjectReport, report_id)
    if report is None or report.project_id != project_id:
        raise HTTPException(status_code=404, detail="Report not found")
    findings = await trace_report(db, report)
    stem = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in report.title).strip("-")
    stem = stem or "report"
    if format == "md":
        body, media, ext = render_markdown(report, findings).encode(), "text/markdown", "md"
    elif format == "csv":
        body, media, ext = render_csv(findings).encode(), "text/csv", "csv"
    elif format == "docx":
        body = render_docx(report, findings)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ext = "docx"
    else:
        raise HTTPException(status_code=400, detail="format must be md, docx or csv")
    return Response(
        content=body,
        media_type=f"{media}; charset=utf-8" if ext != "docx" else media,
        headers={"Content-Disposition": f'attachment; filename="{stem}.{ext}"'},
    )
