"""Laws of UX API — query the knowledge base and compute compliance profiles."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.finding import Nugget
from app.services.laws_of_ux_service import laws_service

router = APIRouter(prefix="/laws")


@router.get("")
async def list_laws(category: str | None = None):
    """List all 30 Laws of UX, optionally filtered by category."""
    if category:
        return laws_service.get_by_category(category)
    return laws_service.get_all()


@router.get("/by-heuristic/{heuristic_id}")
async def get_laws_for_heuristic(heuristic_id: str):
    """Get laws related to a Nielsen heuristic (e.g., H4)."""
    return laws_service.get_related_to_heuristic(heuristic_id)


@router.get("/match")
async def match_laws(query: str = Query(...), top_k: int = 5):
    """Find relevant laws for a text query using keyword matching."""
    matches = laws_service.match_text(query, top_k=top_k)
    return [
        {"law_id": lid, "score": round(s, 3), "law": laws_service.get_by_id(lid)}
        for lid, s in matches
    ]


@router.get("/compliance/{project_id}")
async def get_compliance(project_id: str, db: AsyncSession = Depends(get_db)):
    """Compute UX Law compliance profile for a project from tagged findings."""
    import json

    result = await db.execute(
        select(Nugget).where(Nugget.project_id == project_id)
    )
    nuggets = result.scalars().all()
    nugget_dicts = [{"id": n.id, "tags": n.tags, "text": n.text} for n in nuggets]
    profile = laws_service.compute_compliance_profile(nugget_dicts)
    return profile


@router.get("/compliance/{project_id}/radar")
async def get_radar(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get radar chart data for the compliance profile."""
    import json

    result = await db.execute(
        select(Nugget).where(Nugget.project_id == project_id)
    )
    nuggets = result.scalars().all()
    nugget_dicts = [{"id": n.id, "tags": n.tags, "text": n.text} for n in nuggets]
    profile = laws_service.compute_compliance_profile(nugget_dicts)
    return laws_service.get_radar_chart_data(profile)


@router.get("/{law_id}")
async def get_law(law_id: str):
    """Get a single law with full details."""
    law = laws_service.get_by_id(law_id)
    if not law:
        raise HTTPException(status_code=404, detail=f"Law '{law_id}' not found")
    return law
