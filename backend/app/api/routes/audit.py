"""Audit API routes — DevOps and UI audit agent endpoints."""

from fastapi import APIRouter

from app.agents.devops_agent import devops_agent
from app.agents.ui_audit_agent import ui_audit_agent

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
