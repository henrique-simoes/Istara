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
