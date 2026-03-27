"""Survey integration API — manage platform connections, link surveys, sync responses."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.survey_integration import SurveyIntegration, SurveyLink

router = APIRouter()

SUPPORTED_PLATFORMS = {"surveymonkey", "google_forms", "typeform"}


# ---------------------------------------------------------------------------
# Pydantic request / response schemas
# ---------------------------------------------------------------------------


class IntegrationCreate(BaseModel):
    platform: str
    name: str
    config: dict = {}
    project_id: str | None = None


class LinkCreate(BaseModel):
    integration_id: str
    project_id: str
    external_survey_id: str
    external_survey_name: str = ""


class SurveyCreateRequest(BaseModel):
    title: str
    questions: list[dict] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_adapter(integration: SurveyIntegration):
    """Instantiate the correct adapter for an integration row."""
    config = json.loads(integration.config_json) if integration.config_json else {}

    if integration.platform == "surveymonkey":
        from app.services.survey_platforms.surveymonkey import SurveyMonkeyAdapter
        return SurveyMonkeyAdapter(config)
    elif integration.platform == "google_forms":
        from app.services.survey_platforms.google_forms import GoogleFormsAdapter
        return GoogleFormsAdapter(config)
    elif integration.platform == "typeform":
        from app.services.survey_platforms.typeform import TypeformAdapter
        return TypeformAdapter(config)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported platform: {integration.platform}",
        )


async def _get_integration(db: AsyncSession, integration_id: str) -> SurveyIntegration:
    result = await db.execute(
        select(SurveyIntegration).where(SurveyIntegration.id == integration_id)
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return integration


async def _get_link(db: AsyncSession, link_id: str) -> SurveyLink:
    result = await db.execute(
        select(SurveyLink).where(SurveyLink.id == link_id)
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Survey link not found")
    return link


# ---------------------------------------------------------------------------
# Integration CRUD
# ---------------------------------------------------------------------------


@router.get("/surveys/integrations")
async def list_integrations(
    platform: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all configured survey platform integrations."""
    query = select(SurveyIntegration).order_by(SurveyIntegration.created_at.desc())
    if platform:
        query = query.where(SurveyIntegration.platform == platform)
    result = await db.execute(query)
    integrations = result.scalars().all()
    return {
        "integrations": [i.to_dict() for i in integrations],
        "count": len(integrations),
    }


@router.post("/surveys/integrations", status_code=201)
async def create_integration(
    data: IntegrationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new survey platform integration."""
    if data.platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported platform: {data.platform}. "
                   f"Supported: {', '.join(sorted(SUPPORTED_PLATFORMS))}",
        )

    integration = SurveyIntegration(
        id=str(uuid.uuid4()),
        platform=data.platform,
        name=data.name,
        config_json=json.dumps(data.config),
        project_id=data.project_id,
    )
    db.add(integration)
    await db.commit()
    await db.refresh(integration)
    return integration.to_dict()


@router.delete("/surveys/integrations/{integration_id}", status_code=204)
async def delete_integration(
    integration_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Remove a survey platform integration and its linked surveys."""
    integration = await _get_integration(db, integration_id)
    await db.delete(integration)
    await db.commit()


# ---------------------------------------------------------------------------
# Platform survey listing / creation
# ---------------------------------------------------------------------------


@router.get("/surveys/integrations/{integration_id}/surveys")
async def list_platform_surveys(
    integration_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List surveys available on the connected platform."""
    integration = await _get_integration(db, integration_id)
    adapter = _get_adapter(integration)

    try:
        surveys = await adapter.list_surveys()
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to list surveys from {integration.platform}: {exc}",
        )

    # Update last_sync_at
    integration.last_sync_at = datetime.now(timezone.utc)
    await db.commit()

    return {"platform": integration.platform, "surveys": surveys, "count": len(surveys)}


@router.post("/surveys/integrations/{integration_id}/create")
async def create_platform_survey(
    integration_id: str,
    data: SurveyCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new survey on the connected platform from ReClaw data."""
    integration = await _get_integration(db, integration_id)
    adapter = _get_adapter(integration)

    try:
        result = await adapter.create_survey(data.title, data.questions)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to create survey on {integration.platform}: {exc}",
        )

    return {
        "platform": integration.platform,
        "survey": result,
    }


# ---------------------------------------------------------------------------
# Survey Links (tie an external survey to a ReClaw project)
# ---------------------------------------------------------------------------


@router.post("/surveys/links", status_code=201)
async def create_link(
    data: LinkCreate,
    db: AsyncSession = Depends(get_db),
):
    """Link an external survey to a ReClaw project for response ingestion."""
    # Verify integration exists
    await _get_integration(db, data.integration_id)

    link = SurveyLink(
        id=str(uuid.uuid4()),
        integration_id=data.integration_id,
        project_id=data.project_id,
        external_survey_id=data.external_survey_id,
        external_survey_name=data.external_survey_name,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link.to_dict()


@router.get("/surveys/links")
async def list_links(
    project_id: str | None = None,
    integration_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List survey links, optionally filtered by project or integration."""
    query = select(SurveyLink).order_by(SurveyLink.created_at.desc())
    if project_id:
        query = query.where(SurveyLink.project_id == project_id)
    if integration_id:
        query = query.where(SurveyLink.integration_id == integration_id)
    result = await db.execute(query)
    links = result.scalars().all()
    return {"links": [l.to_dict() for l in links], "count": len(links)}


# ---------------------------------------------------------------------------
# Response sync / retrieval
# ---------------------------------------------------------------------------


@router.post("/surveys/links/{link_id}/sync")
async def sync_responses(
    link_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Manually pull responses from the platform and ingest as Nuggets."""
    link = await _get_link(db, link_id)

    # Resolve integration for adapter
    integration = await _get_integration(db, link.integration_id)
    adapter = _get_adapter(integration)

    try:
        responses = await adapter.get_responses(link.external_survey_id)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch responses from {integration.platform}: {exc}",
        )

    if not responses:
        return {
            "status": "no_new_responses",
            "link_id": link_id,
            "responses_fetched": 0,
        }

    # Ingest into Nuggets
    from app.services.survey_ingestion import ingest_responses

    result = await ingest_responses(db, link, responses, link.project_id)

    # Update integration sync timestamp
    integration.last_sync_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "status": "synced",
        "link_id": link_id,
        **result,
    }


@router.get("/surveys/links/{link_id}/responses")
async def get_link_responses(
    link_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get responses that have been synced for this link (read from platform)."""
    link = await _get_link(db, link_id)
    integration = await _get_integration(db, link.integration_id)
    adapter = _get_adapter(integration)

    try:
        responses = await adapter.get_responses(link.external_survey_id)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch responses: {exc}",
        )

    return {
        "link_id": link_id,
        "survey_id": link.external_survey_id,
        "survey_name": link.external_survey_name,
        "responses": responses,
        "count": len(responses),
    }
