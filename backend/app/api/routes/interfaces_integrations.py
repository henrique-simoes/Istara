"""Figma, handoff, status, and configuration routes for Interfaces."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.interfaces_common import (
    ConfigureFigmaRequest,
    ConfigureStitchRequest,
    FigmaExportRequest,
    FigmaImportRequest,
    HandoffBriefRequest,
    HandoffDevSpecRequest,
    get_screen_or_404,
    require_integration_admin,
)
from app.config import settings
from app.core.permissions import get_subject, is_global_admin, require_project_access
from app.core.security_middleware import require_admin_from_request
from app.models.database import get_db
from app.models.design_screen import DesignBrief, DesignScreen
from app.services.design_evidence import (
    build_dev_spec_content,
    build_figma_import_html,
    hydrate_design_brief,
    resolve_screen_source_findings,
)
from app.skills.design_tools import execute_design_tool

router = APIRouter()


@router.post("/interfaces/figma/import")
async def figma_import(data: FigmaImportRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Import design context from a Figma URL."""
    from app.services.figma_service import figma_service

    await require_project_access(db, request, data.project_id, min_role="researcher")

    parsed = figma_service.parse_figma_url(data.figma_url)
    file_key = parsed.get("file_key", "")
    node_id = parsed.get("node_id")
    if not file_key:
        raise HTTPException(status_code=422, detail="Could not extract file key from Figma URL")

    if not settings.figma_api_token:
        return await execute_design_tool(
            "import_from_figma",
            {"figma_url": data.figma_url},
            data.project_id,
        )

    try:
        file_data = await figma_service.get_file(file_key)
        file_name = file_data.get("name", "Untitled")

        node_data = None
        if node_id:
            try:
                node_data = await figma_service.get_file_nodes(file_key, [node_id])
            except Exception:
                pass

        components_data = {}
        styles_data = {}
        try:
            components_data = await figma_service.get_components(file_key)
        except Exception:
            pass
        try:
            styles_data = await figma_service.get_styles(file_key)
        except Exception:
            pass

        components = components_data.get("meta", {}).get("components", [])
        styles = styles_data.get("meta", {}).get("styles", [])
        screen_id = str(uuid.uuid4())
        screen = DesignScreen(
            id=screen_id,
            project_id=data.project_id,
            title=f"Figma import: {file_name}",
            description=f"Imported Figma design context from {data.figma_url}",
            prompt=data.figma_url,
            device_type="AGNOSTIC",
            model_used="FIGMA",
            html_content=build_figma_import_html(
                file_name=file_name,
                file_key=file_key,
                node_id=node_id,
                components=components,
                styles=styles,
            ),
            screenshot_path="",
            figma_file_key=file_key,
            figma_node_id=node_id,
            status="ready",
            metadata_json=json.dumps(
                {
                    "figma_file_name": file_name,
                    "components_count": len(components),
                    "styles_count": len(styles),
                    "import_source": "figma",
                }
            ),
        )
        db.add(screen)
        await db.commit()
        await db.refresh(screen)

        return {
            "success": True,
            "file_key": file_key,
            "node_id": node_id,
            "name": file_name,
            "screens_imported": 1,
            "screen_ids": [screen_id],
            "screens": [screen.to_dict()],
            "components": [
                {
                    "name": c.get("name", ""),
                    "key": c.get("key", ""),
                    "description": c.get("description", ""),
                }
                for c in components[:50]
            ],
            "styles": [
                {
                    "name": s.get("name", ""),
                    "key": s.get("key", ""),
                    "style_type": s.get("style_type", ""),
                    "description": s.get("description", ""),
                }
                for s in styles[:50]
            ],
            "node_data": node_data.get("nodes", {}) if node_data else None,
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Figma API error: {e}")


@router.post("/interfaces/figma/export")
async def figma_export(data: FigmaExportRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Export a design screen to Figma."""
    screen = await get_screen_or_404(db, data.screen_id)
    await require_project_access(db, request, screen.project_id, min_role="researcher")
    screen.figma_file_key = data.figma_file_key
    await db.commit()

    return {
        "success": True,
        "screen_id": data.screen_id,
        "figma_file_key": data.figma_file_key,
        "message": f"Screen '{screen.title}' linked to Figma file {data.figma_file_key}",
    }


@router.get("/interfaces/figma/design-system/{file_key}")
async def figma_design_system(file_key: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Extract a design system summary from a Figma file."""
    require_admin_from_request(request)

    from app.services.figma_service import figma_service

    if not settings.figma_api_token:
        raise HTTPException(
            status_code=422,
            detail="Figma API token not configured. Set FIGMA_API_TOKEN in settings.",
        )

    try:
        design_system = await figma_service.extract_design_system(file_key)
        return {
            "success": True,
            "file_key": design_system["file_key"],
            "components": design_system["components"],
            "styles": design_system["styles"],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Figma API error: {e}")


@router.get("/interfaces/figma/components/{file_key}")
async def figma_components(file_key: str, request: Request, db: AsyncSession = Depends(get_db)):
    """List Figma components for a file."""
    require_admin_from_request(request)

    from app.services.figma_service import figma_service

    if not settings.figma_api_token:
        raise HTTPException(
            status_code=422,
            detail="Figma API token not configured. Set FIGMA_API_TOKEN in settings.",
        )

    try:
        data = await figma_service.get_components(file_key)
        components = data.get("meta", {}).get("components", [])
        return {
            "success": True,
            "file_key": file_key,
            "components": [
                {
                    "name": c.get("name", ""),
                    "key": c.get("key", ""),
                    "description": c.get("description", ""),
                }
                for c in components
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Figma API error: {e}")


@router.get("/interfaces/handoff/briefs")
async def list_briefs(
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List design briefs for a project."""
    subject = get_subject(request)
    if project_id:
        await require_project_access(db, request, project_id, min_role="viewer")
    elif not is_global_admin(subject):
        raise HTTPException(status_code=400, detail="project_id is required")

    query = select(DesignBrief).order_by(DesignBrief.created_at.desc())
    if project_id:
        query = query.where(DesignBrief.project_id == project_id)
    result = await db.execute(query)
    briefs = result.scalars().all()
    return {"briefs": [await hydrate_design_brief(db, b) for b in briefs]}


@router.post("/interfaces/handoff/brief")
async def handoff_brief(
    data: HandoffBriefRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Generate a design brief from project findings."""
    await require_project_access(db, request, data.project_id, min_role="researcher")
    result = await execute_design_tool(
        "create_design_brief",
        {},
        data.project_id,
    )
    latest = await db.execute(
        select(DesignBrief)
        .where(DesignBrief.project_id == data.project_id)
        .order_by(DesignBrief.created_at.desc())
        .limit(1)
    )
    brief = latest.scalar_one_or_none()
    if brief:
        result["brief_id"] = brief.id
        result["brief"] = await hydrate_design_brief(db, brief)
    return result


@router.post("/interfaces/handoff/dev-spec")
async def handoff_dev_spec(
    data: HandoffDevSpecRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Generate a developer handoff spec from a design screen."""
    screen = await get_screen_or_404(db, data.screen_id)
    await require_project_access(db, request, screen.project_id, min_role="viewer")

    findings = await resolve_screen_source_findings(db, screen)
    content = build_dev_spec_content(screen, findings)
    spec = {
        "screen_id": screen.id,
        "title": screen.title,
        "description": screen.description,
        "device_type": screen.device_type,
        "html_content": screen.html_content,
        "prompt": screen.prompt,
        "parent_screen_id": screen.parent_screen_id,
        "variant_type": screen.variant_type,
        "source_findings": findings,
        "created_at": screen.created_at.isoformat() if screen.created_at else None,
    }
    return {"success": True, "dev_spec": spec, "content": content}


@router.get("/interfaces/status")
async def interfaces_status(
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get the current status of the Interfaces module."""
    subject = get_subject(request)
    if project_id:
        await require_project_access(db, request, project_id, min_role="viewer")
        screens_query = select(func.count()).select_from(DesignScreen).where(
            DesignScreen.project_id == project_id
        )
        briefs_query = select(func.count()).select_from(DesignBrief).where(
            DesignBrief.project_id == project_id
        )
        scope = "project"
    elif is_global_admin(subject) or not settings.team_mode:
        screens_query = select(func.count()).select_from(DesignScreen)
        briefs_query = select(func.count()).select_from(DesignBrief)
        scope = "global"
    else:
        screens_query = None
        briefs_query = None
        scope = "integration-only"

    screens_count = await db.execute(screens_query) if screens_query is not None else None
    briefs_count = await db.execute(briefs_query) if briefs_query is not None else None

    return {
        "stitch_configured": bool(settings.stitch_api_key),
        "figma_configured": bool(settings.figma_api_token),
        "onboarding_needed": not bool(settings.stitch_api_key)
        and not bool(settings.figma_api_token),
        "screens_count": (screens_count.scalar() if screens_count is not None else 0) or 0,
        "briefs_count": (briefs_count.scalar() if briefs_count is not None else 0) or 0,
        "scope": scope,
    }


@router.post("/interfaces/configure/stitch")
async def configure_stitch(
    data: ConfigureStitchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Configure the Stitch (Google Generative AI) API key."""
    await require_integration_admin(db, request, data.project_id)
    from app.api.routes.settings import _persist_env

    settings.stitch_api_key = data.api_key
    try:
        _persist_env("STITCH_API_KEY", data.api_key)
        persisted = True
    except Exception:
        persisted = False

    return {
        "success": True,
        "stitch_configured": bool(data.api_key),
        "persisted": persisted,
    }


@router.post("/interfaces/configure/figma")
async def configure_figma(
    data: ConfigureFigmaRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Configure the Figma API token."""
    await require_integration_admin(db, request, data.project_id)
    from app.api.routes.settings import _persist_env

    settings.figma_api_token = data.api_token
    try:
        _persist_env("FIGMA_API_TOKEN", data.api_token)
        persisted = True
    except Exception:
        persisted = False

    return {
        "success": True,
        "figma_configured": bool(data.api_token),
        "persisted": persisted,
    }
