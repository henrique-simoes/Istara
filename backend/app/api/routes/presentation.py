"""Presentation API — generate slide creation instructions from reports."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.core.permissions import require_project_access
from app.models.database import get_db
from app.models.project_report import ProjectReport
from app.core.agentic import agentic
from app.core.agentic.types import TurnParams

router = APIRouter(prefix="/presentation")


def _fallback_slide_instructions(report: ProjectReport, full_text: str) -> str:
    source = full_text.strip() or report.executive_summary or report.title
    excerpt = source[:1200]
    return (
        "SYSTEM PROMPT\n"
        "Create an executive research deck using Minto Pyramid structure, action titles, and an SCR narrative.\n\n"
        "HORIZONTAL FLOW\n"
        f"1. Situation: frame the research scope for {report.title}.\n"
        "2. Complication: summarize the strongest evidence-backed user or business tension.\n"
        "3. Resolution: present the recommended direction and expected impact.\n"
        "4. Evidence: include the most important findings, grouped into MECE themes.\n"
        "5. Next Steps: show decisions, owners, and validation needed.\n\n"
        "SOURCE EXCERPT\n"
        f"{excerpt}\n\n"
        "JSON SCHEMA\n"
        '{"slides":[{"action_title":"string","evidence":["string"],"visual_idea":"string"}]}'
    )


@router.get("/reports/{report_id}/slide-instructions")
async def get_slide_instructions(
    report_id: str,
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Generate professional slide creation instructions for an external AI."""
    scoped_project_id = project_id.strip() if project_id else ""
    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    report = await db.get(ProjectReport, report_id)
    if not report or report.project_id != scoped_project_id:
        raise HTTPException(status_code=404, detail="Report not found")
    await require_project_access(db, request, scoped_project_id, min_role="viewer")
        
    content = json.loads(report.content_json or "{}")
    full_text = content.get("full_document", "")
    if not full_text:
        # Fallback to executive summary if full doc not yet generated
        full_text = report.executive_summary or "No report content available."
        
    # Generate the instruction package via LLM
    prompt = (
        "You are a presentation design specialist. Based on the following professional research report, "
        "generate a comprehensive instruction package for another AI to create a high-impact slide deck.\n\n"
        "REPORT CONTENT:\n"
        f"{full_text[:5000]}\n\n"
        "OUTPUT REQUIREMENTS:\n"
        "1. SYSTEM PROMPT: A detailed prompt to guide the slide-generating AI (Minto principles, Action Titles, SCR narrative).\n"
        "2. HORIZONTAL FLOW: A slide-by-slide outline. For each slide provide: 'Action Title' (full sentence conclusion), 'Evidence' (bullets), and 'Visual Idea' (chart/diagram suggestion).\n"
        "3. JSON SCHEMA: A strict schema for the slide data.\n\n"
        "Format the response as a clear, copyable guide for executive presentations. Ensure it respects academic rigor and consulting-grade clarity."
    )
    
    try:
        outcome = await agentic.completion(
            purpose="presentation.slides",
            project_id=scoped_project_id,
            system=None,
            messages=[{"role": "user", "content": prompt}],
            params=TurnParams(temperature=0.3),
        )
        instructions = outcome.text or "Failed to generate instructions."
    except Exception:
        instructions = _fallback_slide_instructions(report, full_text)

    return {
        "report_id": report_id,
        "project_id": report.project_id,
        "title": f"Slide Instructions: {report.title}",
        "instructions": instructions,
        "methodology": "Minto Pyramid / Action Titles / SCR Framework"
    }
