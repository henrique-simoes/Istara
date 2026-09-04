"""Findings CRUD API routes — Nuggets, Facts, Insights, Recommendations, DesignDecisions."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import get_subject, is_global_admin, require_project_access
from app.models.database import get_db
from app.models.design_screen import DesignDecision, DesignScreen
from app.models.finding import Fact, Insight, Nugget, Recommendation
from app.services.finding_validity_service import (
    chain_research_validity_diagnostics,
    design_decision_research_validity_map,
    ensure_project_link_ids,
    finding_research_validity_map,
    provisional_finding_validity,
)
from app.services.finding_validity_service import (
    parse_json_list as _parse_json_list,
)
from app.services.research_validity_service import persist_task_nugget_evidence_units

router = APIRouter()


async def _require_project_scope(
    db: AsyncSession, request: Request, project_id: str | None, min_role: str = "viewer"
) -> str:
    scoped_project_id = (project_id or "").strip()
    if not scoped_project_id:
        raise HTTPException(status_code=422, detail="project_id is required")
    await require_project_access(db, request, scoped_project_id, min_role=min_role)
    return scoped_project_id


async def _get_project_record_or_404(
    db: AsyncSession,
    request: Request,
    model,
    record_id: str,
    not_found_detail: str,
    project_id: str | None,
    *,
    min_role: str,
):
    scoped_project_id = await _require_project_scope(db, request, project_id, min_role=min_role)
    result = await db.execute(
        select(model).where(model.id == record_id, model.project_id == scoped_project_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail=not_found_detail)
    return scoped_project_id, record


async def _get_project_finding_or_404(
    db: AsyncSession,
    request: Request,
    finding_type: str,
    finding_id: str,
    project_id: str | None,
    *,
    min_role: str,
    include_design_decision: bool = False,
):
    type_map = {
        "nugget": Nugget,
        "fact": Fact,
        "insight": Insight,
        "recommendation": Recommendation,
    }
    if include_design_decision:
        type_map["design_decision"] = DesignDecision
    model = type_map.get(finding_type)
    if not model:
        raise HTTPException(status_code=400, detail=f"Invalid finding type: {finding_type}")
    return await _get_project_record_or_404(
        db,
        request,
        model,
        finding_id,
        "Finding not found",
        project_id,
        min_role=min_role,
    )


# --- Schemas ---


class NuggetCreate(BaseModel):
    project_id: str
    text: str
    source: str
    source_location: str = ""
    tags: list[str] = []
    phase: str = "discover"


class NuggetResponse(BaseModel):
    id: str
    project_id: str
    task_id: str | None = None
    text: str
    source: str
    source_location: str
    tags: list[str]
    phase: str
    confidence: float
    created_at: datetime
    research_validity: dict[str, Any] | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_tags(
        cls,
        nugget: Nugget,
        research_validity: dict[str, Any] | None = None,
    ) -> NuggetResponse:
        tags = _parse_json_list(nugget.tags) or ["untagged"]
        source_location = nugget.source_location or nugget.source or "unknown"
        return cls(
            id=nugget.id,
            project_id=nugget.project_id,
            task_id=nugget.task_id,
            text=nugget.text,
            source=nugget.source,
            source_location=source_location,
            tags=tags,
            phase=nugget.phase,
            confidence=nugget.confidence,
            created_at=nugget.created_at,
            research_validity=research_validity,
        )


class FactCreate(BaseModel):
    project_id: str
    text: str
    nugget_ids: list[str] = []
    phase: str = "discover"


class FactResponse(BaseModel):
    id: str
    project_id: str
    task_id: str | None = None
    text: str
    nugget_ids: list[str]
    phase: str
    confidence: float
    created_at: datetime
    research_validity: dict[str, Any] | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_ids(
        cls,
        fact: Fact,
        research_validity: dict[str, Any] | None = None,
    ) -> FactResponse:
        nugget_ids = _parse_json_list(fact.nugget_ids)
        return cls(
            id=fact.id,
            project_id=fact.project_id,
            task_id=fact.task_id,
            text=fact.text,
            nugget_ids=nugget_ids,
            phase=fact.phase,
            confidence=fact.confidence,
            created_at=fact.created_at,
            research_validity=research_validity,
        )


class InsightCreate(BaseModel):
    project_id: str
    text: str
    fact_ids: list[str] = []
    phase: str = "define"
    impact: str = "medium"


class InsightResponse(BaseModel):
    id: str
    project_id: str
    task_id: str | None = None
    text: str
    fact_ids: list[str]
    phase: str
    confidence: float
    impact: str
    created_at: datetime
    research_validity: dict[str, Any] | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_ids(
        cls,
        insight: Insight,
        research_validity: dict[str, Any] | None = None,
    ) -> InsightResponse:
        fact_ids = _parse_json_list(insight.fact_ids)
        return cls(
            id=insight.id,
            project_id=insight.project_id,
            task_id=insight.task_id,
            text=insight.text,
            fact_ids=fact_ids,
            phase=insight.phase,
            confidence=insight.confidence,
            impact=insight.impact,
            created_at=insight.created_at,
            research_validity=research_validity,
        )


class RecommendationCreate(BaseModel):
    project_id: str
    text: str
    insight_ids: list[str] = []
    phase: str = "deliver"
    priority: str = "medium"
    effort: str = "medium"


class RecommendationResponse(BaseModel):
    id: str
    project_id: str
    task_id: str | None = None
    text: str
    insight_ids: list[str]
    phase: str
    priority: str
    effort: str
    status: str
    created_at: datetime
    research_validity: dict[str, Any] | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_ids(
        cls,
        rec: Recommendation,
        research_validity: dict[str, Any] | None = None,
    ) -> RecommendationResponse:
        insight_ids = _parse_json_list(rec.insight_ids)
        return cls(
            id=rec.id,
            project_id=rec.project_id,
            task_id=rec.task_id,
            text=rec.text,
            insight_ids=insight_ids,
            phase=rec.phase,
            priority=rec.priority,
            effort=rec.effort,
            status=rec.status,
            created_at=rec.created_at,
            research_validity=research_validity,
        )


# --- Nugget Routes ---


@router.get("/findings/nuggets", response_model=list[NuggetResponse])
async def list_nuggets(
    request: Request,
    project_id: str | None = None,
    phase: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    scoped_project_id = await _require_project_scope(db, request, project_id, min_role="viewer")
    query = (
        select(Nugget)
        .where(Nugget.project_id == scoped_project_id)
        .order_by(Nugget.created_at.desc())
    )
    if phase:
        query = query.where(Nugget.phase == phase)
    result = await db.execute(query)
    rows = list(result.scalars().all())
    validity = await finding_research_validity_map(
        db,
        project_id=scoped_project_id,
        findings=rows,
    )
    return [NuggetResponse.from_orm_with_tags(n, validity.get(n.id)) for n in rows]


@router.post("/findings/nuggets", response_model=NuggetResponse, status_code=201)
async def create_nugget(data: NuggetCreate, request: Request, db: AsyncSession = Depends(get_db)):
    await require_project_access(db, request, data.project_id, min_role="researcher")
    source_location = data.source_location or data.source or "unknown"
    nugget = Nugget(
        id=str(uuid.uuid4()),
        project_id=data.project_id,
        text=data.text,
        source=data.source,
        source_location=source_location,
        tags=json.dumps(data.tags or ["untagged"]),
        phase=data.phase,
    )
    db.add(nugget)
    await persist_task_nugget_evidence_units(
        db,
        project_id=data.project_id,
        task_id=None,
        nugget_id=nugget.id,
        source_text=data.text,
        source_location=source_location,
        method="manual_finding",
        phase=data.phase,
        source_type="manual_finding",
        candidate_only=True,
    )
    await db.commit()
    await db.refresh(nugget)
    return NuggetResponse.from_orm_with_tags(nugget, provisional_finding_validity())


@router.delete("/findings/nuggets/{nugget_id}", status_code=204)
async def delete_nugget(
    nugget_id: str,
    request: Request,
    project_id: str | None = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
):
    _, nugget = await _get_project_record_or_404(
        db,
        request,
        Nugget,
        nugget_id,
        "Nugget not found",
        project_id,
        min_role="researcher",
    )
    await db.delete(nugget)
    await db.commit()


# --- Fact Routes ---


@router.get("/findings/facts", response_model=list[FactResponse])
async def list_facts(
    request: Request,
    project_id: str | None = None,
    phase: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    scoped_project_id = await _require_project_scope(db, request, project_id, min_role="viewer")
    query = (
        select(Fact).where(Fact.project_id == scoped_project_id).order_by(Fact.created_at.desc())
    )
    if phase:
        query = query.where(Fact.phase == phase)
    result = await db.execute(query)
    rows = list(result.scalars().all())
    validity = await finding_research_validity_map(
        db,
        project_id=scoped_project_id,
        findings=rows,
    )
    return [FactResponse.from_orm_with_ids(f, validity.get(f.id)) for f in rows]


@router.post("/findings/facts", response_model=FactResponse, status_code=201)
async def create_fact(data: FactCreate, request: Request, db: AsyncSession = Depends(get_db)):
    await require_project_access(db, request, data.project_id, min_role="researcher")
    nugget_ids = await ensure_project_link_ids(
        db,
        project_id=data.project_id,
        model=Nugget,
        ids=data.nugget_ids,
        field_name="nugget_ids",
    )
    fact = Fact(
        id=str(uuid.uuid4()),
        project_id=data.project_id,
        text=data.text,
        nugget_ids=json.dumps(nugget_ids),
        phase=data.phase,
    )
    db.add(fact)
    await db.commit()
    await db.refresh(fact)
    return FactResponse.from_orm_with_ids(fact, provisional_finding_validity())


@router.delete("/findings/facts/{fact_id}", status_code=204)
async def delete_fact(
    fact_id: str,
    request: Request,
    project_id: str | None = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
):
    _, fact = await _get_project_record_or_404(
        db,
        request,
        Fact,
        fact_id,
        "Fact not found",
        project_id,
        min_role="researcher",
    )
    await db.delete(fact)
    await db.commit()


# --- Insight Routes ---


@router.get("/findings/insights", response_model=list[InsightResponse])
async def list_insights(
    request: Request,
    project_id: str | None = None,
    phase: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    scoped_project_id = await _require_project_scope(db, request, project_id, min_role="viewer")
    query = (
        select(Insight)
        .where(Insight.project_id == scoped_project_id)
        .order_by(Insight.created_at.desc())
    )
    if phase:
        query = query.where(Insight.phase == phase)
    result = await db.execute(query)
    rows = list(result.scalars().all())
    validity = await finding_research_validity_map(
        db,
        project_id=scoped_project_id,
        findings=rows,
    )
    return [InsightResponse.from_orm_with_ids(i, validity.get(i.id)) for i in rows]


@router.post("/findings/insights", response_model=InsightResponse, status_code=201)
async def create_insight(data: InsightCreate, request: Request, db: AsyncSession = Depends(get_db)):
    await require_project_access(db, request, data.project_id, min_role="researcher")
    fact_ids = await ensure_project_link_ids(
        db,
        project_id=data.project_id,
        model=Fact,
        ids=data.fact_ids,
        field_name="fact_ids",
    )
    insight = Insight(
        id=str(uuid.uuid4()),
        project_id=data.project_id,
        text=data.text,
        fact_ids=json.dumps(fact_ids),
        phase=data.phase,
        impact=data.impact,
    )
    db.add(insight)
    await db.commit()
    await db.refresh(insight)
    return InsightResponse.from_orm_with_ids(insight, provisional_finding_validity())


@router.delete("/findings/insights/{insight_id}", status_code=204)
async def delete_insight(
    insight_id: str,
    request: Request,
    project_id: str | None = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
):
    _, insight = await _get_project_record_or_404(
        db,
        request,
        Insight,
        insight_id,
        "Insight not found",
        project_id,
        min_role="researcher",
    )
    await db.delete(insight)
    await db.commit()


# --- Recommendation Routes ---


@router.get("/findings/recommendations", response_model=list[RecommendationResponse])
async def list_recommendations(
    request: Request,
    project_id: str | None = None,
    phase: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    scoped_project_id = await _require_project_scope(db, request, project_id, min_role="viewer")
    query = (
        select(Recommendation)
        .where(Recommendation.project_id == scoped_project_id)
        .order_by(Recommendation.created_at.desc())
    )
    if phase:
        query = query.where(Recommendation.phase == phase)
    result = await db.execute(query)
    rows = list(result.scalars().all())
    validity = await finding_research_validity_map(
        db,
        project_id=scoped_project_id,
        findings=rows,
    )
    return [RecommendationResponse.from_orm_with_ids(r, validity.get(r.id)) for r in rows]


@router.post("/findings/recommendations", response_model=RecommendationResponse, status_code=201)
async def create_recommendation(
    data: RecommendationCreate, request: Request, db: AsyncSession = Depends(get_db)
):
    await require_project_access(db, request, data.project_id, min_role="researcher")
    insight_ids = await ensure_project_link_ids(
        db,
        project_id=data.project_id,
        model=Insight,
        ids=data.insight_ids,
        field_name="insight_ids",
    )
    rec = Recommendation(
        id=str(uuid.uuid4()),
        project_id=data.project_id,
        text=data.text,
        insight_ids=json.dumps(insight_ids),
        phase=data.phase,
        priority=data.priority,
        effort=data.effort,
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return RecommendationResponse.from_orm_with_ids(rec, provisional_finding_validity())


@router.delete("/findings/recommendations/{rec_id}", status_code=204)
async def delete_recommendation(
    rec_id: str,
    request: Request,
    project_id: str | None = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
):
    _, rec = await _get_project_record_or_404(
        db,
        request,
        Recommendation,
        rec_id,
        "Recommendation not found",
        project_id,
        min_role="researcher",
    )
    await db.delete(rec)
    await db.commit()


# --- Aggregated Findings View ---


@router.get("/findings/search/global")
async def search_all_findings(
    request: Request,
    query: str = "",
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Search across ALL projects' findings (text-based)."""
    if not is_global_admin(get_subject(request)):
        raise HTTPException(status_code=403, detail="Global findings search requires admin access")
    if not query:
        return {"results": [], "query": ""}

    q = f"%{query}%"
    results = []

    for model, ftype in [
        (Nugget, "nugget"),
        (Fact, "fact"),
        (Insight, "insight"),
        (Recommendation, "recommendation"),
    ]:
        rows = await db.execute(select(model).where(model.text.ilike(q)).limit(limit // 4))
        for item in rows.scalars().all():
            results.append(
                {
                    "type": ftype,
                    "text": item.text,
                    "project_id": item.project_id,
                    "phase": getattr(item, "phase", ""),
                    "confidence": getattr(item, "confidence", None),
                }
            )

    return {"query": query, "results": results[:limit], "count": len(results)}


@router.get("/findings/search/{project_id}")
async def search_findings(
    project_id: str,
    request: Request,
    query: str = "",
    top_k: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Semantic search across project findings using the vector store."""
    await require_project_access(db, request, project_id, min_role="viewer")
    if not query:
        return {"results": [], "query": ""}

    from app.core.rag import retrieve_context
    from app.services.finding_search import search_project_findings

    rag_context = await retrieve_context(project_id, query, top_k=top_k)
    results = await search_project_findings(db, project_id, query, top_k, rag_context.retrieved)

    return {
        "query": query,
        "results": results,
        "count": len(results),
    }


@router.get("/findings/{finding_type}/{finding_id}/evidence-chain")
async def get_evidence_chain(
    finding_type: str,
    finding_id: str,
    request: Request,
    project_id: str | None = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
):
    """Get the full evidence chain for a finding — traversing links up and down."""
    scoped_project_id, finding = await _get_project_finding_or_404(
        db,
        request,
        finding_type,
        finding_id,
        project_id,
        min_role="viewer",
    )
    from app.services.finding_chain import collect_evidence_chain

    records = await collect_evidence_chain(db, finding_type, finding, finding_id, scoped_project_id)
    chain = {
        "recommendation": [
            RecommendationResponse.from_orm_with_ids(item) for item in records["recommendation"]
        ],
        "insight": [InsightResponse.from_orm_with_ids(item) for item in records["insight"]],
        "fact": [FactResponse.from_orm_with_ids(item) for item in records["fact"]],
        "nugget": [NuggetResponse.from_orm_with_tags(item) for item in records["nugget"]],
    }
    project_id = scoped_project_id

    supporting_counts = {key: len(value) for key, value in chain.items() if key != finding_type}
    missing_links: list[str] = []
    if finding_type == "recommendation":
        if not chain["insight"]:
            missing_links.append("recommendation_to_insight")
        elif not chain["fact"]:
            missing_links.append("insight_to_fact")
        elif not chain["nugget"]:
            missing_links.append("fact_to_nugget")
    elif finding_type == "insight":
        if not chain["fact"]:
            missing_links.append("insight_to_fact")
        elif not chain["nugget"]:
            missing_links.append("fact_to_nugget")
    elif finding_type == "fact" and not chain["nugget"]:
        missing_links.append("fact_to_nugget")
    elif finding_type == "nugget" and not chain["fact"]:
        missing_links.append("nugget_to_fact")

    research_validity = await chain_research_validity_diagnostics(
        db,
        project_id=project_id,
        chain=chain,
    )
    return {
        "finding_type": finding_type,
        "finding_id": finding_id,
        "chain": chain,
        "diagnostics": {
            "supporting_counts": supporting_counts,
            "has_supporting_evidence": any(supporting_counts.values()),
            "missing_links": missing_links,
            "research_validity": research_validity,
        },
    }


@router.get("/findings/evidence-chain")
async def get_evidence_chain_query(
    finding_type: str,
    finding_id: str,
    request: Request,
    project_id: str | None = Query(None, description="Active project"),
    extended: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """Compatibility endpoint for query-style evidence-chain callers."""
    if extended:
        return await get_evidence_chain_extended(
            finding_type,
            finding_id,
            request,
            project_id,
            db,
        )
    return await get_evidence_chain(finding_type, finding_id, request, project_id, db)


class LinkEvidenceRequest(BaseModel):
    link_id: str
    link_type: str  # "fact" | "nugget" | "insight"


@router.patch("/findings/{finding_type}/{finding_id}/link")
async def link_evidence(
    finding_type: str,
    finding_id: str,
    data: LinkEvidenceRequest,
    request: Request,
    project_id: str | None = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
):
    """Add an evidence link to a finding's _ids array.

    Valid combinations:
    - insight  + link_type=fact    -> adds to insight.fact_ids
    - fact     + link_type=nugget  -> adds to fact.nugget_ids
    - recommendation + link_type=insight -> adds to recommendation.insight_ids
    """
    type_map = {
        "nugget": Nugget,
        "fact": Fact,
        "insight": Insight,
        "recommendation": Recommendation,
    }

    # Validate the finding being modified
    scoped_project_id, finding = await _get_project_finding_or_404(
        db,
        request,
        finding_type,
        finding_id,
        project_id,
        min_role="researcher",
    )

    # Validate the target being linked exists
    link_model = type_map.get(data.link_type)
    if not link_model:
        raise HTTPException(status_code=400, detail=f"Invalid link type: {data.link_type}")

    link_result = await db.execute(
        select(link_model).where(
            link_model.id == data.link_id,
            link_model.project_id == scoped_project_id,
        )
    )
    link_target = link_result.scalar_one_or_none()
    if not link_target:
        raise HTTPException(status_code=404, detail=f"Target {data.link_type} not found")
    if link_target.project_id != finding.project_id:
        raise HTTPException(status_code=404, detail=f"Target {data.link_type} not found")

    # Determine which _ids field to update based on finding type and link type
    field_map = {
        ("insight", "fact"): "fact_ids",
        ("fact", "nugget"): "nugget_ids",
        ("recommendation", "insight"): "insight_ids",
    }

    ids_field = field_map.get((finding_type, data.link_type))
    if not ids_field:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot link {data.link_type} to {finding_type}. "
            f"Valid: insight+fact, fact+nugget, recommendation+insight.",
        )

    # Parse existing ids, add new one, and save
    raw = getattr(finding, ids_field, None)
    existing_ids: list[str] = []
    if raw:
        try:
            existing_ids = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            existing_ids = []

    if data.link_id in existing_ids:
        return {"status": "already_linked", "finding_id": finding_id, "link_id": data.link_id}

    existing_ids.append(data.link_id)
    setattr(finding, ids_field, json.dumps(existing_ids))
    await db.commit()
    await db.refresh(finding)

    return {
        "status": "linked",
        "finding_type": finding_type,
        "finding_id": finding_id,
        "link_type": data.link_type,
        "link_id": data.link_id,
        ids_field: existing_ids,
    }


@router.get("/findings/summary/{project_id}")
async def get_findings_summary(
    project_id: str, request: Request, db: AsyncSession = Depends(get_db)
):
    """Get a summary of all findings for a project, organized by phase."""
    await require_project_access(db, request, project_id, min_role="viewer")
    nuggets = await db.execute(select(Nugget).where(Nugget.project_id == project_id))
    facts = await db.execute(select(Fact).where(Fact.project_id == project_id))
    insights = await db.execute(select(Insight).where(Insight.project_id == project_id))
    recs = await db.execute(select(Recommendation).where(Recommendation.project_id == project_id))

    nugget_list = nuggets.scalars().all()
    fact_list = facts.scalars().all()
    insight_list = insights.scalars().all()
    rec_list = recs.scalars().all()

    # Group by phase
    phases = {}
    for phase in ["discover", "define", "develop", "deliver"]:
        phases[phase] = {
            "nuggets": len([n for n in nugget_list if n.phase == phase]),
            "facts": len([f for f in fact_list if f.phase == phase]),
            "insights": len([i for i in insight_list if i.phase == phase]),
            "recommendations": len([r for r in rec_list if r.phase == phase]),
        }

    return {
        "project_id": project_id,
        "totals": {
            "nuggets": len(nugget_list),
            "facts": len(fact_list),
            "insights": len(insight_list),
            "recommendations": len(rec_list),
        },
        "by_phase": phases,
    }


# --- Design Decision Schemas ---


class DesignDecisionCreate(BaseModel):
    project_id: str
    text: str
    recommendation_ids: list[str] = []
    screen_ids: list[str] = []
    rationale: str = ""
    phase: str = "develop"
    agent_id: str | None = None


class DesignDecisionResponse(BaseModel):
    id: str
    project_id: str
    agent_id: str | None
    text: str
    recommendation_ids: list[str]
    screen_ids: list[str]
    rationale: str
    phase: str
    confidence: float
    created_at: datetime
    research_validity: dict[str, Any] | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_ids(
        cls,
        dd: DesignDecision,
        research_validity: dict[str, Any] | None = None,
    ) -> DesignDecisionResponse:
        rec_ids = _parse_json_list(dd.recommendation_ids)
        scr_ids = _parse_json_list(dd.screen_ids)
        return cls(
            id=dd.id,
            project_id=dd.project_id,
            agent_id=dd.agent_id,
            text=dd.text,
            recommendation_ids=rec_ids,
            screen_ids=scr_ids,
            rationale=dd.rationale,
            phase=dd.phase,
            confidence=dd.confidence,
            created_at=dd.created_at,
            research_validity=research_validity
            or provisional_finding_validity(
                reason=(
                    "Design decision is provisional until its recommendations trace to "
                    "accepted/reconciled evidence and a human-approved Done task."
                )
            ),
        )


# --- Design Decision Routes ---


@router.get("/findings/design-decisions", response_model=list[DesignDecisionResponse])
async def list_design_decisions(
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List design decisions for an authorized project."""
    scoped_project_id = await _require_project_scope(db, request, project_id, min_role="viewer")
    query = (
        select(DesignDecision)
        .where(DesignDecision.project_id == scoped_project_id)
        .order_by(DesignDecision.created_at.desc())
    )
    result = await db.execute(query)
    decisions = list(result.scalars().all())
    validity = await design_decision_research_validity_map(
        db,
        project_id=scoped_project_id,
        decisions=decisions,
    )
    return [
        DesignDecisionResponse.from_orm_with_ids(dd, validity.get(str(dd.id))) for dd in decisions
    ]


@router.post("/findings/design-decisions", response_model=DesignDecisionResponse, status_code=201)
async def create_design_decision(
    data: DesignDecisionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a new design decision linking recommendations to screens."""
    await require_project_access(db, request, data.project_id, min_role="researcher")
    recommendation_ids = await ensure_project_link_ids(
        db,
        project_id=data.project_id,
        model=Recommendation,
        ids=data.recommendation_ids,
        field_name="recommendation_ids",
    )
    screen_ids = await ensure_project_link_ids(
        db,
        project_id=data.project_id,
        model=DesignScreen,
        ids=data.screen_ids,
        field_name="screen_ids",
    )
    dd = DesignDecision(
        id=str(uuid.uuid4()),
        project_id=data.project_id,
        agent_id=data.agent_id,
        text=data.text,
        recommendation_ids=json.dumps(recommendation_ids),
        screen_ids=json.dumps(screen_ids),
        rationale=data.rationale,
        phase=data.phase,
    )
    db.add(dd)
    await db.commit()
    await db.refresh(dd)
    validity = await design_decision_research_validity_map(
        db,
        project_id=data.project_id,
        decisions=[dd],
    )
    return DesignDecisionResponse.from_orm_with_ids(dd, validity.get(str(dd.id)))


@router.delete("/findings/design-decisions/{dd_id}", status_code=204)
async def delete_design_decision(
    dd_id: str,
    request: Request,
    project_id: str | None = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
):
    """Delete a design decision."""
    _, dd = await _get_project_record_or_404(
        db,
        request,
        DesignDecision,
        dd_id,
        "Design decision not found",
        project_id,
        min_role="researcher",
    )
    await db.delete(dd)
    await db.commit()


# --- Extended Evidence Chain (with DesignDecision -> DesignScreen) ---


@router.get("/findings/{finding_type}/{finding_id}/evidence-chain-extended")
async def get_evidence_chain_extended(
    finding_type: str,
    finding_id: str,
    request: Request,
    project_id: str | None = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
):
    """Get the full evidence chain including DesignDecision and DesignScreen nodes.

    Extends the standard evidence chain to traverse accepted/provisional state:
    Atom/Nugget -> Fact -> Insight -> Recommendation -> DesignDecision -> DesignScreen
    """
    scoped_project_id, finding = await _get_project_finding_or_404(
        db,
        request,
        finding_type,
        finding_id,
        project_id,
        min_role="viewer",
        include_design_decision=True,
    )

    chain: dict[str, list] = {
        "recommendation": [],
        "insight": [],
        "fact": [],
        "nugget": [],
        "design_decision": [],
        "design_screen": [],
    }

    def parse_ids(raw: str | None) -> list[str]:
        return _parse_json_list(raw)

    project_id = scoped_project_id

    async def append_design_nodes_for_recommendations(recommendation_ids: set[str]) -> None:
        if not recommendation_ids:
            return
        seen_decisions: set[str] = set()
        seen_screens: set[str] = set()
        dd_rows = await db.execute(
            select(DesignDecision).where(DesignDecision.project_id == project_id)
        )
        for dd in dd_rows.scalars().all():
            if not recommendation_ids.intersection(parse_ids(dd.recommendation_ids)):
                continue
            if dd.id not in seen_decisions:
                seen_decisions.add(dd.id)
                chain["design_decision"].append(dd.to_dict())
            for sid in parse_ids(dd.screen_ids):
                if sid in seen_screens:
                    continue
                sr = await db.execute(
                    select(DesignScreen).where(
                        DesignScreen.id == sid,
                        DesignScreen.project_id == project_id,
                    )
                )
                scr = sr.scalar_one_or_none()
                if scr:
                    seen_screens.add(sid)
                    chain["design_screen"].append(scr.to_dict())

    def response_id(item) -> str | None:
        if isinstance(item, dict):
            return item.get("id")
        return getattr(item, "id", None)

    if finding_type in {"nugget", "fact", "insight", "recommendation"}:
        base = await get_evidence_chain(
            finding_type,
            finding_id,
            request,
            project_id,
            db,
        )
        for key in ("recommendation", "insight", "fact", "nugget"):
            chain[key] = list(base["chain"].get(key, []))
        diagnostics = base.get("diagnostics", {})

        recommendation_ids: set[str] = {
            rid for rid in (response_id(rec) for rec in chain["recommendation"]) if rid
        }
        await append_design_nodes_for_recommendations(recommendation_ids)

    elif finding_type == "design_decision":
        diagnostics = {}
        chain["design_decision"] = [finding.to_dict()]
        # Down: screens
        for sid in parse_ids(finding.screen_ids):
            sr = await db.execute(
                select(DesignScreen).where(
                    DesignScreen.id == sid,
                    DesignScreen.project_id == project_id,
                )
            )
            scr = sr.scalar_one_or_none()
            if scr:
                chain["design_screen"].append(scr.to_dict())
        # Up: recommendations
        for rid in parse_ids(finding.recommendation_ids):
            rr = await db.execute(
                select(Recommendation).where(
                    Recommendation.id == rid,
                    Recommendation.project_id == project_id,
                )
            )
            rec = rr.scalar_one_or_none()
            if rec:
                chain["recommendation"].append(RecommendationResponse.from_orm_with_ids(rec))
        recommendation_ids = {
            rid for rid in (response_id(rec) for rec in chain["recommendation"]) if rid
        }
        if recommendation_ids:
            base = await get_evidence_chain(
                "recommendation",
                next(iter(recommendation_ids)),
                request,
                project_id,
                db,
            )
            for key in ("insight", "fact", "nugget"):
                chain[key] = list(base["chain"].get(key, []))

    return {
        "finding_type": finding_type,
        "finding_id": finding_id,
        "chain": chain,
        "diagnostics": diagnostics,
    }
