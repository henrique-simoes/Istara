"""Presentation API — generate slide creation instructions from reports."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import json

from app.models.database import get_db
from app.models.project_report import ProjectReport
from app.core.llm_router import llm_router

router = APIRouter(prefix="/presentation")

@router.get("/reports/{report_id}/slide-instructions")
async def get_slide_instructions(report_id: str, db: AsyncSession = Depends(get_db)):
    """Generate professional slide creation instructions for an external AI."""
    report = await db.get(ProjectReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
        
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
        response = await llm_router.chat([{"role": "user", "content": prompt}], temperature=0.3)
        instructions = response.get("message", {}).get("content", "Failed to generate instructions.")
        
        return {
            "report_id": report_id,
            "title": f"Slide Instructions: {report.title}",
            "instructions": instructions,
            "methodology": "Minto Pyramid / Action Titles / SCR Framework"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
