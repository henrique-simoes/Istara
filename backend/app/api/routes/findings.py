"""Findings CRUD API routes — Nuggets, Facts, Insights, Recommendations."""

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.finding import Fact, Insight, Nugget, Recommendation

router = APIRouter()


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
    text: str
    source: str
    source_location: str
    tags: list[str]
    phase: str
    confidence: float
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_tags(cls, nugget: Nugget) -> "NuggetResponse":
        tags = json.loads(nugget.tags) if nugget.tags else []
        return cls(
            id=nugget.id,
            project_id=nugget.project_id,
            text=nugget.text,
            source=nugget.source,
            source_location=nugget.source_location,
            tags=tags,
            phase=nugget.phase,
            confidence=nugget.confidence,
            created_at=nugget.created_at,
        )


class FactCreate(BaseModel):
    project_id: str
    text: str
    nugget_ids: list[str] = []
    phase: str = "discover"


class FactResponse(BaseModel):
    id: str
    project_id: str
    text: str
    nugget_ids: list[str]
    phase: str
    confidence: float
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_ids(cls, fact: Fact) -> "FactResponse":
        nugget_ids = json.loads(fact.nugget_ids) if fact.nugget_ids else []
        return cls(
            id=fact.id, project_id=fact.project_id, text=fact.text,
            nugget_ids=nugget_ids, phase=fact.phase, confidence=fact.confidence,
            created_at=fact.created_at,
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
    text: str
    fact_ids: list[str]
    phase: str
    confidence: float
    impact: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_ids(cls, insight: Insight) -> "InsightResponse":
        fact_ids = json.loads(insight.fact_ids) if insight.fact_ids else []
        return cls(
            id=insight.id, project_id=insight.project_id, text=insight.text,
            fact_ids=fact_ids, phase=insight.phase, confidence=insight.confidence,
            impact=insight.impact, created_at=insight.created_at,
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
    text: str
    insight_ids: list[str]
    phase: str
    priority: str
    effort: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_ids(cls, rec: Recommendation) -> "RecommendationResponse":
        insight_ids = json.loads(rec.insight_ids) if rec.insight_ids else []
        return cls(
            id=rec.id, project_id=rec.project_id, text=rec.text,
            insight_ids=insight_ids, phase=rec.phase, priority=rec.priority,
            effort=rec.effort, status=rec.status, created_at=rec.created_at,
        )


# --- Nugget Routes ---

@router.get("/findings/nuggets", response_model=list[NuggetResponse])
async def list_nuggets(
    project_id: str | None = None,
    phase: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Nugget).order_by(Nugget.created_at.desc())
    if project_id:
        query = query.where(Nugget.project_id == project_id)
    if phase:
        query = query.where(Nugget.phase == phase)
    result = await db.execute(query)
    return [NuggetResponse.from_orm_with_tags(n) for n in result.scalars().all()]


@router.post("/findings/nuggets", response_model=NuggetResponse, status_code=201)
async def create_nugget(data: NuggetCreate, db: AsyncSession = Depends(get_db)):
    nugget = Nugget(
        id=str(uuid.uuid4()),
        project_id=data.project_id,
        text=data.text,
        source=data.source,
        source_location=data.source_location,
        tags=json.dumps(data.tags),
        phase=data.phase,
    )
    db.add(nugget)
    await db.commit()
    await db.refresh(nugget)
    return NuggetResponse.from_orm_with_tags(nugget)


@router.delete("/findings/nuggets/{nugget_id}", status_code=204)
async def delete_nugget(nugget_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Nugget).where(Nugget.id == nugget_id))
    nugget = result.scalar_one_or_none()
    if not nugget:
        raise HTTPException(status_code=404, detail="Nugget not found")
    await db.delete(nugget)
    await db.commit()


# --- Fact Routes ---

@router.get("/findings/facts", response_model=list[FactResponse])
async def list_facts(
    project_id: str | None = None,
    phase: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Fact).order_by(Fact.created_at.desc())
    if project_id:
        query = query.where(Fact.project_id == project_id)
    if phase:
        query = query.where(Fact.phase == phase)
    result = await db.execute(query)
    return [FactResponse.from_orm_with_ids(f) for f in result.scalars().all()]


@router.post("/findings/facts", response_model=FactResponse, status_code=201)
async def create_fact(data: FactCreate, db: AsyncSession = Depends(get_db)):
    fact = Fact(
        id=str(uuid.uuid4()),
        project_id=data.project_id,
        text=data.text,
        nugget_ids=json.dumps(data.nugget_ids),
        phase=data.phase,
    )
    db.add(fact)
    await db.commit()
    await db.refresh(fact)
    return FactResponse.from_orm_with_ids(fact)


@router.delete("/findings/facts/{fact_id}", status_code=204)
async def delete_fact(fact_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Fact).where(Fact.id == fact_id))
    fact = result.scalar_one_or_none()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")
    await db.delete(fact)
    await db.commit()


# --- Insight Routes ---

@router.get("/findings/insights", response_model=list[InsightResponse])
async def list_insights(
    project_id: str | None = None,
    phase: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Insight).order_by(Insight.created_at.desc())
    if project_id:
        query = query.where(Insight.project_id == project_id)
    if phase:
        query = query.where(Insight.phase == phase)
    result = await db.execute(query)
    return [InsightResponse.from_orm_with_ids(i) for i in result.scalars().all()]


@router.post("/findings/insights", response_model=InsightResponse, status_code=201)
async def create_insight(data: InsightCreate, db: AsyncSession = Depends(get_db)):
    insight = Insight(
        id=str(uuid.uuid4()),
        project_id=data.project_id,
        text=data.text,
        fact_ids=json.dumps(data.fact_ids),
        phase=data.phase,
        impact=data.impact,
    )
    db.add(insight)
    await db.commit()
    await db.refresh(insight)
    return InsightResponse.from_orm_with_ids(insight)


@router.delete("/findings/insights/{insight_id}", status_code=204)
async def delete_insight(insight_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Insight).where(Insight.id == insight_id))
    insight = result.scalar_one_or_none()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    await db.delete(insight)
    await db.commit()


# --- Recommendation Routes ---

@router.get("/findings/recommendations", response_model=list[RecommendationResponse])
async def list_recommendations(
    project_id: str | None = None,
    phase: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Recommendation).order_by(Recommendation.created_at.desc())
    if project_id:
        query = query.where(Recommendation.project_id == project_id)
    if phase:
        query = query.where(Recommendation.phase == phase)
    result = await db.execute(query)
    return [RecommendationResponse.from_orm_with_ids(r) for r in result.scalars().all()]


@router.post("/findings/recommendations", response_model=RecommendationResponse, status_code=201)
async def create_recommendation(data: RecommendationCreate, db: AsyncSession = Depends(get_db)):
    rec = Recommendation(
        id=str(uuid.uuid4()),
        project_id=data.project_id,
        text=data.text,
        insight_ids=json.dumps(data.insight_ids),
        phase=data.phase,
        priority=data.priority,
        effort=data.effort,
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return RecommendationResponse.from_orm_with_ids(rec)


@router.delete("/findings/recommendations/{rec_id}", status_code=204)
async def delete_recommendation(rec_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Recommendation).where(Recommendation.id == rec_id))
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    await db.delete(rec)
    await db.commit()


# --- Aggregated Findings View ---

@router.get("/findings/search/global")
async def search_all_findings(
    query: str = "",
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Search across ALL projects' findings (text-based)."""
    if not query:
        return {"results": [], "query": ""}

    q = f"%{query}%"
    results = []

    for model, ftype in [(Nugget, "nugget"), (Fact, "fact"), (Insight, "insight"), (Recommendation, "recommendation")]:
        rows = await db.execute(
            select(model).where(model.text.ilike(q)).limit(limit // 4)
        )
        for item in rows.scalars().all():
            results.append({
                "type": ftype,
                "text": item.text,
                "project_id": item.project_id,
                "phase": getattr(item, "phase", ""),
                "confidence": getattr(item, "confidence", None),
            })

    return {"query": query, "results": results[:limit], "count": len(results)}


@router.get("/findings/search/{project_id}")
async def search_findings(
    project_id: str,
    query: str = "",
    top_k: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Semantic search across project findings using the vector store."""
    if not query:
        return {"results": [], "query": ""}

    from app.core.rag import retrieve_context

    rag_context = await retrieve_context(project_id, query, top_k=top_k)

    return {
        "query": query,
        "results": [
            {
                "text": r.text,
                "source": r.source,
                "page": r.page,
                "score": round(r.score, 3),
            }
            for r in rag_context.retrieved
        ],
        "count": len(rag_context.retrieved),
    }


@router.get("/findings/{finding_type}/{finding_id}/evidence-chain")
async def get_evidence_chain(
    finding_type: str,
    finding_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the full evidence chain for a finding — traversing links up and down."""
    type_map = {
        "nugget": Nugget, "fact": Fact, "insight": Insight, "recommendation": Recommendation,
    }
    model = type_map.get(finding_type)
    if not model:
        raise HTTPException(status_code=400, detail=f"Invalid finding type: {finding_type}")

    result = await db.execute(select(model).where(model.id == finding_id))
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    chain = {"recommendation": [], "insight": [], "fact": [], "nugget": []}

    def parse_ids(raw):
        if not raw:
            return []
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []

    project_id = finding.project_id

    if finding_type == "recommendation":
        # Drill down: rec → insights → facts → nuggets
        chain["recommendation"] = [RecommendationResponse.from_orm_with_ids(finding)]
        insight_ids = parse_ids(finding.insight_ids)
        if insight_ids:
            rows = await db.execute(select(Insight).where(Insight.id.in_(insight_ids)))
            linked_insights = rows.scalars().all()
            chain["insight"] = [InsightResponse.from_orm_with_ids(i) for i in linked_insights]
            fact_ids = []
            for i in linked_insights:
                fact_ids.extend(parse_ids(i.fact_ids))
            if fact_ids:
                rows = await db.execute(select(Fact).where(Fact.id.in_(list(set(fact_ids)))))
                linked_facts = rows.scalars().all()
                chain["fact"] = [FactResponse.from_orm_with_ids(f) for f in linked_facts]
                nugget_ids = []
                for f in linked_facts:
                    nugget_ids.extend(parse_ids(f.nugget_ids))
                if nugget_ids:
                    rows = await db.execute(select(Nugget).where(Nugget.id.in_(list(set(nugget_ids)))))
                    chain["nugget"] = [NuggetResponse.from_orm_with_tags(n) for n in rows.scalars().all()]

    elif finding_type == "insight":
        chain["insight"] = [InsightResponse.from_orm_with_ids(finding)]
        # Down: facts → nuggets
        fact_ids = parse_ids(finding.fact_ids)
        if fact_ids:
            rows = await db.execute(select(Fact).where(Fact.id.in_(fact_ids)))
            linked_facts = rows.scalars().all()
            chain["fact"] = [FactResponse.from_orm_with_ids(f) for f in linked_facts]
            nugget_ids = []
            for f in linked_facts:
                nugget_ids.extend(parse_ids(f.nugget_ids))
            if nugget_ids:
                rows = await db.execute(select(Nugget).where(Nugget.id.in_(list(set(nugget_ids)))))
                chain["nugget"] = [NuggetResponse.from_orm_with_tags(n) for n in rows.scalars().all()]
        # Up: recommendations that link to this insight
        rows = await db.execute(select(Recommendation).where(Recommendation.project_id == project_id))
        for rec in rows.scalars().all():
            if finding_id in parse_ids(rec.insight_ids):
                chain["recommendation"].append(RecommendationResponse.from_orm_with_ids(rec))

    elif finding_type == "fact":
        chain["fact"] = [FactResponse.from_orm_with_ids(finding)]
        # Down: nuggets
        nugget_ids = parse_ids(finding.nugget_ids)
        if nugget_ids:
            rows = await db.execute(select(Nugget).where(Nugget.id.in_(nugget_ids)))
            chain["nugget"] = [NuggetResponse.from_orm_with_tags(n) for n in rows.scalars().all()]
        # Up: insights → recommendations
        rows = await db.execute(select(Insight).where(Insight.project_id == project_id))
        for insight in rows.scalars().all():
            if finding_id in parse_ids(insight.fact_ids):
                chain["insight"].append(InsightResponse.from_orm_with_ids(insight))
        if chain["insight"]:
            insight_id_set = {i.id for i in chain["insight"]}
            rows = await db.execute(select(Recommendation).where(Recommendation.project_id == project_id))
            for rec in rows.scalars().all():
                if any(iid in insight_id_set for iid in parse_ids(rec.insight_ids)):
                    chain["recommendation"].append(RecommendationResponse.from_orm_with_ids(rec))

    elif finding_type == "nugget":
        chain["nugget"] = [NuggetResponse.from_orm_with_tags(finding)]
        # Up: facts → insights → recommendations
        rows = await db.execute(select(Fact).where(Fact.project_id == project_id))
        for fact in rows.scalars().all():
            if finding_id in parse_ids(fact.nugget_ids):
                chain["fact"].append(FactResponse.from_orm_with_ids(fact))
        if chain["fact"]:
            fact_id_set = {f.id for f in chain["fact"]}
            rows = await db.execute(select(Insight).where(Insight.project_id == project_id))
            for insight in rows.scalars().all():
                if any(fid in fact_id_set for fid in parse_ids(insight.fact_ids)):
                    chain["insight"].append(InsightResponse.from_orm_with_ids(insight))
        if chain["insight"]:
            insight_id_set = {i.id for i in chain["insight"]}
            rows = await db.execute(select(Recommendation).where(Recommendation.project_id == project_id))
            for rec in rows.scalars().all():
                if any(iid in insight_id_set for iid in parse_ids(rec.insight_ids)):
                    chain["recommendation"].append(RecommendationResponse.from_orm_with_ids(rec))

    return {
        "finding_type": finding_type,
        "finding_id": finding_id,
        "chain": chain,
    }


class LinkEvidenceRequest(BaseModel):
    link_id: str
    link_type: str  # "fact" | "nugget" | "insight"


@router.patch("/findings/{finding_type}/{finding_id}/link")
async def link_evidence(
    finding_type: str,
    finding_id: str,
    data: LinkEvidenceRequest,
    db: AsyncSession = Depends(get_db),
):
    """Add an evidence link to a finding's _ids array.

    Valid combinations:
    - insight  + link_type=fact    -> adds to insight.fact_ids
    - fact     + link_type=nugget  -> adds to fact.nugget_ids
    - recommendation + link_type=insight -> adds to recommendation.insight_ids
    """
    type_map = {
        "nugget": Nugget, "fact": Fact, "insight": Insight, "recommendation": Recommendation,
    }

    # Validate the finding being modified
    model = type_map.get(finding_type)
    if not model:
        raise HTTPException(status_code=400, detail=f"Invalid finding type: {finding_type}")

    result = await db.execute(select(model).where(model.id == finding_id))
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")

    # Validate the target being linked exists
    link_model = type_map.get(data.link_type)
    if not link_model:
        raise HTTPException(status_code=400, detail=f"Invalid link type: {data.link_type}")

    link_result = await db.execute(select(link_model).where(link_model.id == data.link_id))
    link_target = link_result.scalar_one_or_none()
    if not link_target:
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
async def get_findings_summary(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get a summary of all findings for a project, organized by phase."""
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
