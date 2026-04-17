"""Audit API routes — DevOps, UI audit agent, and system audit log endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.devops_agent import devops_agent
from app.agents.ui_audit_agent import ui_audit_agent
from app.models.database import get_db
from app.core.audit_middleware import AuditLog

router = APIRouter()


@router.get("/audit/devops/latest")
async def get_devops_audit():
    """Get the latest DevOps audit report."""
    report = devops_agent.get_latest_report()
    if not report:
        return {"status": "no_reports", "message": "No audit has run yet."}
    return report


@router.get("/audit/devops/history")
async def get_devops_history(limit: int = 10):
    """Get recent DevOps audit reports."""
    return {"reports": devops_agent.get_reports(limit)}


@router.post("/audit/devops/run")
async def trigger_devops_audit():
    """Trigger an immediate DevOps audit cycle."""
    report = await devops_agent.run_audit_cycle()
    return report


@router.get("/audit/ui/latest")
async def get_ui_audit():
    """Get the latest UI audit report."""
    report = ui_audit_agent.get_latest_report()
    if not report:
        return {"status": "no_reports", "message": "No UI audit has run yet."}
    return {
        "timestamp": report.timestamp,
        "issues_count": len(report.issues),
        "critical_count": report.critical_count,
        "scores": report.scores,
        "overall_score": report.overall_score,
        "issues": [
            {
                "category": i.category,
                "severity": i.severity.value,
                "location": i.location,
                "description": i.description,
                "heuristic": i.heuristic,
                "recommendation": i.recommendation,
            }
            for i in report.issues
        ],
    }


@router.get("/audit/ui/history")
async def get_ui_history(limit: int = 10):
    """Get recent UI audit reports."""
    reports = ui_audit_agent.get_reports(limit)
    return {
        "reports": [
            {
                "timestamp": r.timestamp,
                "issues_count": len(r.issues),
                "critical_count": r.critical_count,
                "overall_score": r.overall_score,
            }
            for r in reports
        ]
    }


@router.post("/audit/ui/run")
async def trigger_ui_audit():
    """Trigger an immediate UI audit cycle."""
    report = await ui_audit_agent.run_audit()
    return {
        "timestamp": report.timestamp,
        "issues_count": len(report.issues),
        "critical_count": report.critical_count,
        "scores": report.scores,
        "overall_score": report.overall_score,
        "issues": [
            {
                "category": i.category,
                "severity": i.severity.value,
                "location": i.location,
                "description": i.description,
                "recommendation": i.recommendation,
            }
            for i in report.issues
        ],
    }


@router.get("/audit/logs")
async def get_audit_logs(
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    user_id: str | None = None,
    project_id: str | None = None,
    method: str | None = None,
    path_prefix: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get recent system audit log entries.

    Provides a persistent trail of all API requests for compliance,
    debugging, and research audit requirements.
    """
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if project_id:
        stmt = stmt.where(AuditLog.project_id == project_id)
    if method:
        stmt = stmt.where(AuditLog.method == method)
    if path_prefix:
        stmt = stmt.where(AuditLog.path.startswith(path_prefix))

    result = await db.execute(stmt)
    rows = result.scalars().all()

    count_stmt = select(func.count(AuditLog.id))
    if user_id:
        count_stmt = count_stmt.where(AuditLog.user_id == user_id)
    if project_id:
        count_stmt = count_stmt.where(AuditLog.project_id == project_id)
    total = (await db.execute(count_stmt)).scalar() or 0

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "entries": [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                "user_id": r.user_id,
                "method": r.method,
                "path": r.path,
                "status_code": r.status_code,
                "duration_ms": round(r.duration_ms, 2),
                "ip_address": r.ip_address,
                "project_id": r.project_id,
            }
            for r in rows
        ],
    }
