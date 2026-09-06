"""Survey integration API — manage platform connections, link surveys, sync responses."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.field_encryption import decrypt_field, encrypt_field
from app.core.permissions import ProjectRole, get_visible_project_or_404
from app.models.database import get_db
from app.models.survey_integration import SurveyIntegration, SurveyLink

logger = logging.getLogger(__name__)
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
    raw = decrypt_field(integration.config_json) if integration.config_json else "{}"
    config = json.loads(raw)

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


def _is_demo_integration(integration: SurveyIntegration) -> bool:
    """Return true for explicit local/demo integrations used in simulations."""
    if integration.name.startswith("SIM:"):
        return True
    raw = decrypt_field(integration.config_json) if integration.config_json else "{}"
    try:
        config = json.loads(raw)
    except json.JSONDecodeError:
        return False
    return any(isinstance(value, str) and value.startswith("sim-") for value in config.values())


async def _get_integration(db: AsyncSession, integration_id: str) -> SurveyIntegration:
    result = await db.execute(
        select(SurveyIntegration).where(SurveyIntegration.id == integration_id)
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return integration


async def _get_link(db: AsyncSession, link_id: str) -> SurveyLink:
    result = await db.execute(select(SurveyLink).where(SurveyLink.id == link_id))
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Survey link not found")
    return link


def _require_project_id(project_id: str | None) -> str:
    scoped_project_id = (project_id or "").strip()
    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    return scoped_project_id


async def _require_project_scope(
    db: AsyncSession,
    request: Request,
    project_id: str | None,
    *,
    min_role: ProjectRole = "viewer",
) -> str:
    scoped_project_id = _require_project_id(project_id)
    await get_visible_project_or_404(db, request, scoped_project_id, min_role=min_role)
    return scoped_project_id


def _require_matching_project(integration: SurveyIntegration, project_id: str) -> None:
    if not integration.project_id or integration.project_id != project_id:
        raise HTTPException(
            status_code=403,
            detail="Survey integration is not bound to this project.",
        )


async def _get_project_integration_or_404(
    db: AsyncSession,
    request: Request,
    integration_id: str,
    project_id: str | None,
    *,
    min_role: ProjectRole,
) -> tuple[str, SurveyIntegration]:
    scoped_project_id = await _require_project_scope(db, request, project_id, min_role=min_role)
    integration = await _get_integration(db, integration_id)
    if integration.project_id != scoped_project_id:
        raise HTTPException(status_code=404, detail="Integration not found")
    return scoped_project_id, integration


async def _get_project_link_or_404(
    db: AsyncSession,
    request: Request,
    link_id: str,
    project_id: str | None,
    *,
    min_role: ProjectRole,
) -> tuple[str, SurveyLink]:
    scoped_project_id = await _require_project_scope(db, request, project_id, min_role=min_role)
    link = await _get_link(db, link_id)
    if link.project_id != scoped_project_id:
        raise HTTPException(status_code=404, detail="Survey link not found")
    return scoped_project_id, link


# ---------------------------------------------------------------------------
# Integration CRUD
# ---------------------------------------------------------------------------


@router.get("/surveys/integrations")
async def list_integrations(
    request: Request,
    platform: str | None = None,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List all configured survey platform integrations."""
    scoped_project_id = await _require_project_scope(db, request, project_id, min_role="viewer")
    query = select(SurveyIntegration).order_by(SurveyIntegration.created_at.desc())
    if platform:
        query = query.where(SurveyIntegration.platform == platform)
    query = query.where(SurveyIntegration.project_id == scoped_project_id)
    result = await db.execute(query)
    integrations = result.scalars().all()
    return {
        "integrations": [i.to_dict() for i in integrations],
        "count": len(integrations),
    }


@router.post("/surveys/integrations", status_code=201)
async def create_integration(
    data: IntegrationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a new survey platform integration."""
    scoped_project_id = await _require_project_scope(
        db, request, data.project_id, min_role="project_admin"
    )
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
        config_json=encrypt_field(json.dumps(data.config)),
        project_id=scoped_project_id,
    )
    db.add(integration)
    await db.commit()
    await db.refresh(integration)
    return integration.to_dict()


@router.delete("/surveys/integrations/{integration_id}", status_code=204)
async def delete_integration(
    integration_id: str,
    request: Request,
    project_id: str | None = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
):
    """Remove a survey platform integration and its linked surveys."""
    _, integration = await _get_project_integration_or_404(
        db, request, integration_id, project_id, min_role="project_admin"
    )
    await db.delete(integration)
    await db.commit()


@router.get("/surveys/integrations/{integration_id}/health")
async def health_check_survey_integration(
    integration_id: str,
    request: Request,
    project_id: str | None = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Run a live connectivity and credential health check on a survey platform integration."""
    scoped_project_id, integration = await _get_project_integration_or_404(
        db, request, integration_id, project_id, min_role="viewer"
    )
    if _is_demo_integration(integration):
        return {
            "healthy": True,
            "platform": integration.platform,
            "status": "healthy",
            "demo": True,
        }

    adapter = _get_adapter(integration)
    try:
        result = await adapter.health_check()
        result.setdefault("platform", integration.platform)
        result.setdefault("status", "healthy" if result.get("healthy") else "unhealthy")
        return result
    except Exception as exc:
        logger.warning(
            "Survey integration health check failed for %s (%s): %s",
            integration_id,
            integration.platform,
            exc,
        )
        return {
            "healthy": False,
            "platform": integration.platform,
            "status": "unhealthy",
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Platform survey listing / creation
# ---------------------------------------------------------------------------


@router.get("/surveys/integrations/{integration_id}/surveys")
async def list_platform_surveys(
    integration_id: str,
    request: Request,
    project_id: str | None = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
):
    """List surveys available on the connected platform."""
    scoped_project_id, integration = await _get_project_integration_or_404(
        db, request, integration_id, project_id, min_role="project_admin"
    )
    adapter = _get_adapter(integration)

    try:
        surveys = await adapter.list_surveys()
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to list surveys from {integration.platform}: {exc}",
        )

    # Update last_sync_at
    integration.last_sync_at = datetime.now(UTC)
    await db.commit()

    return {
        "project_id": scoped_project_id,
        "platform": integration.platform,
        "surveys": surveys,
        "count": len(surveys),
    }


@router.post("/surveys/integrations/{integration_id}/create")
async def create_platform_survey(
    integration_id: str,
    data: SurveyCreateRequest,
    request: Request,
    project_id: str | None = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
):
    """Create a new survey on the connected platform from Istara data."""
    scoped_project_id, integration = await _get_project_integration_or_404(
        db, request, integration_id, project_id, min_role="project_admin"
    )
    adapter = _get_adapter(integration)

    try:
        result = await adapter.create_survey(data.title, data.questions)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to create survey on {integration.platform}: {exc}",
        )

    return {
        "project_id": scoped_project_id,
        "platform": integration.platform,
        "survey": result,
    }


# ---------------------------------------------------------------------------
# Survey Links (tie an external survey to a Istara project)
# ---------------------------------------------------------------------------


@router.post("/surveys/links", status_code=201)
async def create_link(
    data: LinkCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Link an external survey to a Istara project for response ingestion."""
    scoped_project_id, _ = await _get_project_integration_or_404(
        db, request, data.integration_id, data.project_id, min_role="project_admin"
    )

    link = SurveyLink(
        id=str(uuid.uuid4()),
        integration_id=data.integration_id,
        project_id=scoped_project_id,
        external_survey_id=data.external_survey_id,
        external_survey_name=data.external_survey_name,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link.to_dict()


@router.get("/surveys/links")
async def list_links(
    request: Request,
    project_id: str | None = None,
    integration_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List survey links, optionally filtered by project or integration."""
    scoped_project_id = await _require_project_scope(db, request, project_id, min_role="viewer")

    query = select(SurveyLink).order_by(SurveyLink.created_at.desc())
    query = query.where(SurveyLink.project_id == scoped_project_id)
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
    request: Request,
    project_id: str | None = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
):
    """Manually pull responses from the platform and ingest as Nuggets."""
    scoped_project_id, link = await _get_project_link_or_404(
        db, request, link_id, project_id, min_role="researcher"
    )

    # Resolve integration for adapter
    integration = await _get_integration(db, link.integration_id)
    _require_matching_project(integration, link.project_id)
    if _is_demo_integration(integration):
        integration.last_sync_at = datetime.now(UTC)
        await db.commit()
        return {
            "status": "no_new_responses",
            "link_id": link_id,
            "project_id": scoped_project_id,
            "responses_fetched": 0,
            "demo": True,
        }

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
            "project_id": scoped_project_id,
            "responses_fetched": 0,
        }

    # Ingest into Nuggets
    from app.services.survey_ingestion import ingest_responses

    result = await ingest_responses(db, link, responses, link.project_id)

    # Update integration sync timestamp
    integration.last_sync_at = datetime.now(UTC)
    await db.commit()

    return {
        "status": "synced",
        "link_id": link_id,
        "project_id": scoped_project_id,
        "responses_fetched": len(responses),
        **result,
    }


@router.get("/surveys/links/{link_id}/responses")
async def get_link_responses(
    link_id: str,
    request: Request,
    project_id: str | None = Query(None, description="Active project"),
    db: AsyncSession = Depends(get_db),
):
    """Get responses that have been synced for this link (read from platform)."""
    scoped_project_id, link = await _get_project_link_or_404(
        db, request, link_id, project_id, min_role="viewer"
    )
    integration = await _get_integration(db, link.integration_id)
    _require_matching_project(integration, link.project_id)
    if _is_demo_integration(integration):
        return {
            "link_id": link_id,
            "project_id": scoped_project_id,
            "survey_id": link.external_survey_id,
            "survey_name": link.external_survey_name,
            "responses": [],
            "count": 0,
            "demo": True,
        }

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
        "project_id": scoped_project_id,
        "survey_id": link.external_survey_id,
        "survey_name": link.external_survey_name,
        "responses": responses,
        "count": len(responses),
    }
