"""Database traversal for the project-scoped Atomic Research evidence chain."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import Fact, Insight, Nugget, Recommendation
from app.services.finding_validity_service import parse_json_list


async def _linked(
    db: AsyncSession,
    model: Any,
    ids: list[str],
    project_id: str,
) -> list[Any]:
    if not ids:
        return []
    rows = await db.execute(
        select(model).where(
            model.id.in_(list(set(ids))),
            model.project_id == project_id,
        )
    )
    return list(rows.scalars().all())


async def _project_rows(db: AsyncSession, model: Any, project_id: str) -> list[Any]:
    rows = await db.execute(select(model).where(model.project_id == project_id))
    return list(rows.scalars().all())


async def _recommendation_chain(
    db: AsyncSession,
    finding: Recommendation,
    project_id: str,
) -> dict[str, list[Any]]:
    insights = await _linked(db, Insight, parse_json_list(finding.insight_ids), project_id)
    fact_ids = [fact_id for item in insights for fact_id in parse_json_list(item.fact_ids)]
    facts = await _linked(db, Fact, fact_ids, project_id)
    nugget_ids = [nugget_id for item in facts for nugget_id in parse_json_list(item.nugget_ids)]
    nuggets = await _linked(db, Nugget, nugget_ids, project_id)
    return {
        "recommendation": [finding],
        "insight": insights,
        "fact": facts,
        "nugget": nuggets,
    }


async def _insight_chain(
    db: AsyncSession,
    finding: Insight,
    finding_id: str,
    project_id: str,
) -> dict[str, list[Any]]:
    facts = await _linked(db, Fact, parse_json_list(finding.fact_ids), project_id)
    nugget_ids = [nugget_id for item in facts for nugget_id in parse_json_list(item.nugget_ids)]
    nuggets = await _linked(db, Nugget, nugget_ids, project_id)
    recommendations = [
        item
        for item in await _project_rows(db, Recommendation, project_id)
        if finding_id in parse_json_list(item.insight_ids)
    ]
    return {
        "recommendation": recommendations,
        "insight": [finding],
        "fact": facts,
        "nugget": nuggets,
    }


async def _fact_chain(
    db: AsyncSession,
    finding: Fact,
    finding_id: str,
    project_id: str,
) -> dict[str, list[Any]]:
    nuggets = await _linked(db, Nugget, parse_json_list(finding.nugget_ids), project_id)
    insights = [
        item
        for item in await _project_rows(db, Insight, project_id)
        if finding_id in parse_json_list(item.fact_ids)
    ]
    insight_ids = {item.id for item in insights}
    recommendations = [
        item
        for item in await _project_rows(db, Recommendation, project_id)
        if any(linked_id in insight_ids for linked_id in parse_json_list(item.insight_ids))
    ]
    return {
        "recommendation": recommendations,
        "insight": insights,
        "fact": [finding],
        "nugget": nuggets,
    }


async def _nugget_chain(
    db: AsyncSession,
    finding: Nugget,
    finding_id: str,
    project_id: str,
) -> dict[str, list[Any]]:
    facts = [
        item
        for item in await _project_rows(db, Fact, project_id)
        if finding_id in parse_json_list(item.nugget_ids)
    ]
    fact_ids = {item.id for item in facts}
    insights = [
        item
        for item in await _project_rows(db, Insight, project_id)
        if any(linked_id in fact_ids for linked_id in parse_json_list(item.fact_ids))
    ]
    insight_ids = {item.id for item in insights}
    recommendations = [
        item
        for item in await _project_rows(db, Recommendation, project_id)
        if any(linked_id in insight_ids for linked_id in parse_json_list(item.insight_ids))
    ]
    return {
        "recommendation": recommendations,
        "insight": insights,
        "fact": facts,
        "nugget": [finding],
    }


async def collect_evidence_chain(
    db: AsyncSession,
    finding_type: str,
    finding: Any,
    finding_id: str,
    project_id: str,
) -> dict[str, list[Any]]:
    """Return linked ORM findings, constrained to the active project."""
    if finding_type == "recommendation":
        return await _recommendation_chain(db, finding, project_id)
    if finding_type == "insight":
        return await _insight_chain(db, finding, finding_id, project_id)
    if finding_type == "fact":
        return await _fact_chain(db, finding, finding_id, project_id)
    return await _nugget_chain(db, finding, finding_id, project_id)
