"""Screen CRUD and Stitch generation routes for Interfaces."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.interfaces_common import (
    EditRequest,
    GenerateRequest,
    VariantRequest,
    get_project_interface_config,
    get_screen_or_404,
    require_project_id,
)
from app.config import settings
from app.core.permissions import require_project_access
from app.models.database import get_db
from app.models.design_screen import DesignDecision, DesignScreen
from app.services.design_evidence import build_seeded_prompt, resolve_seed_findings
from app.skills.design_tools import execute_design_tool

router = APIRouter()
_log = logging.getLogger(__name__)


@router.get("/interfaces/screens")
async def list_screens(
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List design screens for the active project."""
    scoped_project_id = require_project_id(project_id)
    await require_project_access(db, request, scoped_project_id, min_role="viewer")

    query = (
        select(DesignScreen)
        .where(DesignScreen.project_id == scoped_project_id)
        .order_by(DesignScreen.created_at.desc())
    )
    result = await db.execute(query)
    return [s.to_dict() for s in result.scalars().all()]


@router.get("/interfaces/screens/{screen_id}")
async def get_screen(screen_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Get a single design screen by ID."""
    screen = await get_screen_or_404(db, screen_id)
    await require_project_access(db, request, screen.project_id, min_role="viewer")
    return screen.to_dict()


@router.post("/interfaces/screens/generate")
async def generate_screen(
    data: GenerateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Generate a new screen via Stitch or design tools."""
    import httpx
    from app.core.content_guard import ContentGuard
    from app.services.stitch_service import stitch_service

    await require_project_access(db, request, data.project_id, min_role="researcher")

    seed_findings, missing_seed_ids = await resolve_seed_findings(
        db,
        data.project_id,
        data.seed_finding_ids,
        max_items=10,
    )
    if missing_seed_ids:
        raise HTTPException(
            status_code=422,
            detail="Seed findings were not found in this project: " + ", ".join(missing_seed_ids),
        )
    seed_ids = [finding.id for finding in seed_findings]
    enriched_prompt = build_seeded_prompt(data.prompt, seed_findings)

    interface_config = await get_project_interface_config(db, data.project_id)
    stitch_api_key = interface_config.stitch_api_key if interface_config else ""

    if not stitch_api_key:
        return await execute_design_tool(
            "generate_screen",
            {
                "prompt": data.prompt,
                "device_type": data.device_type,
                "model": data.model,
                "seed_finding_ids": seed_ids,
            },
            data.project_id,
        )

    guard = ContentGuard()
    stitch_project_id = "default"
    try:
        stitch_proj = await stitch_service.create_project(
            f"Istara-{data.project_id[:8]}",
            api_key=stitch_api_key,
        )
        raw_name = stitch_proj.get("name", "")
        stitch_project_id = stitch_service.extract_project_id(raw_name) if raw_name else "default"
    except Exception:
        pass

    try:
        stitch_data = await stitch_service.generate_screen(
            stitch_project_id,
            enriched_prompt,
            data.device_type,
            data.model,
            api_key=stitch_api_key,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Stitch API error: {e}")

    output_components = stitch_data.get("outputComponents", [{}])
    screens_data = []
    if output_components:
        design_block = output_components[0].get("design", {})
        screens_data = design_block.get("screens", [])
    if not screens_data and stitch_data.get("screens"):
        screens_data = stitch_data["screens"]

    stitch_session_id = stitch_data.get("sessionId", "")
    created_screens: list[DesignScreen] = []

    async with httpx.AsyncClient(timeout=60) as http:
        for s_data in screens_data:
            screen_id = str(uuid.uuid4())
            stitch_screen_id = s_data.get("id", "")
            screen_title = s_data.get("title") or s_data.get("name") or data.prompt[:100]

            html_content = ""
            html_code = s_data.get("htmlCode", {})
            html_url = html_code.get("downloadUrl", "") if isinstance(html_code, dict) else ""
            if html_url:
                try:
                    resp = await http.get(html_url)
                    resp.raise_for_status()
                    html_content = resp.text
                except Exception:
                    pass
            if not html_content:
                html_content = s_data.get("html", s_data.get("htmlContent", ""))

            if html_content:
                scan = guard.scan_text(html_content)
                if not scan.clean:
                    _log.warning("Stitch HTML flagged: %s", scan.threats)
                    html_content = scan.cleaned_text

            screenshot_path = ""
            screenshot_info = s_data.get("screenshot", {})
            screenshot_url = (
                screenshot_info.get("downloadUrl", "") if isinstance(screenshot_info, dict) else ""
            )
            if screenshot_url:
                try:
                    resp = await http.get(screenshot_url)
                    resp.raise_for_status()
                    save_dir = Path(settings.design_screens_dir)
                    save_dir.mkdir(parents=True, exist_ok=True)
                    img_path = save_dir / f"{screen_id}.png"
                    img_path.write_bytes(resp.content)
                    screenshot_path = str(img_path)
                except Exception:
                    pass

            screen = DesignScreen(
                id=screen_id,
                project_id=data.project_id,
                title=screen_title,
                description=data.prompt,
                prompt=enriched_prompt,
                device_type=data.device_type,
                model_used=data.model,
                html_content=html_content,
                screenshot_path=screenshot_path,
                stitch_project_id=stitch_project_id,
                stitch_screen_id=stitch_screen_id,
                status="ready",
                source_findings=json.dumps(seed_ids),
                metadata_json=json.dumps(
                    {
                        "stitch_session_id": stitch_session_id,
                        "stitch_width": s_data.get("width"),
                        "stitch_height": s_data.get("height"),
                    }
                ),
            )
            db.add(screen)
            created_screens.append(screen)

    decision_id = None
    if seed_ids and created_screens:
        decision_id = str(uuid.uuid4())
        db.add(
            DesignDecision(
                id=decision_id,
                project_id=data.project_id,
                agent_id="design-lead",
                text=f"Design decision: {data.prompt[:200]}",
                recommendation_ids=json.dumps(seed_ids),
                screen_ids=json.dumps([s.id for s in created_screens]),
                rationale=f"Generated from research findings via Stitch ({data.model})",
            )
        )

    await db.commit()
    for screen in created_screens:
        await db.refresh(screen)

    if created_screens:
        resp = created_screens[0].to_dict()
        resp["design_decision_id"] = decision_id
        if len(created_screens) > 1:
            resp["additional_screens"] = [s.to_dict() for s in created_screens[1:]]
        return resp

    raise HTTPException(status_code=502, detail="Stitch returned no screens")


@router.post("/interfaces/screens/edit")
async def edit_screen(data: EditRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Edit an existing screen with instructions via Stitch."""
    import httpx
    from app.services.stitch_service import stitch_service

    parent = await get_screen_or_404(db, data.screen_id)
    await require_project_access(db, request, parent.project_id, min_role="researcher")

    interface_config = await get_project_interface_config(db, parent.project_id)
    stitch_api_key = interface_config.stitch_api_key if interface_config else ""

    if not stitch_api_key:
        return await execute_design_tool(
            "edit_screen",
            {"screen_id": data.screen_id, "instructions": data.instructions},
            parent.project_id,
        )

    stitch_proj_id = parent.stitch_project_id or "default"
    stitch_screen_ids = [parent.stitch_screen_id] if parent.stitch_screen_id else []
    if not stitch_screen_ids:
        raise HTTPException(
            status_code=422,
            detail="Screen has no Stitch screen ID -- cannot edit via Stitch",
        )

    try:
        stitch_data = await stitch_service.edit_screen(
            stitch_proj_id,
            stitch_screen_ids,
            data.instructions,
            api_key=stitch_api_key,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Stitch edit error: {e}")

    output_components = stitch_data.get("outputComponents", [{}])
    screens_data = []
    if output_components:
        design_block = output_components[0].get("design", {})
        screens_data = design_block.get("screens", [])
    if not screens_data and stitch_data.get("screens"):
        screens_data = stitch_data["screens"]

    new_id = str(uuid.uuid4())
    html_content = ""
    screenshot_path = ""
    stitch_screen_id_new = ""

    async with httpx.AsyncClient(timeout=60) as http:
        if screens_data:
            s_data = screens_data[0]
            stitch_screen_id_new = s_data.get("id", "")

            html_code = s_data.get("htmlCode", {})
            html_url = html_code.get("downloadUrl", "") if isinstance(html_code, dict) else ""
            if html_url:
                try:
                    resp = await http.get(html_url)
                    resp.raise_for_status()
                    html_content = resp.text
                except Exception:
                    pass
            if not html_content:
                html_content = s_data.get("html", s_data.get("htmlContent", ""))

            screenshot_info = s_data.get("screenshot", {})
            screenshot_url = (
                screenshot_info.get("downloadUrl", "") if isinstance(screenshot_info, dict) else ""
            )
            if screenshot_url:
                try:
                    resp = await http.get(screenshot_url)
                    resp.raise_for_status()
                    save_dir = Path(settings.design_screens_dir)
                    save_dir.mkdir(parents=True, exist_ok=True)
                    img_path = save_dir / f"{new_id}.png"
                    img_path.write_bytes(resp.content)
                    screenshot_path = str(img_path)
                except Exception:
                    pass
        else:
            html_content = stitch_data.get("html", stitch_data.get("text", ""))

    edited = DesignScreen(
        id=new_id,
        project_id=parent.project_id,
        title=f"Edit: {data.instructions[:80]}",
        description=data.instructions,
        prompt=data.instructions,
        device_type=parent.device_type,
        model_used=parent.model_used,
        html_content=html_content,
        screenshot_path=screenshot_path,
        parent_screen_id=data.screen_id,
        stitch_project_id=stitch_proj_id,
        stitch_screen_id=stitch_screen_id_new,
        status="ready",
        source_findings=parent.source_findings,
    )
    db.add(edited)
    await db.commit()
    await db.refresh(edited)
    return edited.to_dict()


@router.post("/interfaces/screens/variant")
async def create_variant(data: VariantRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Create design variants of an existing screen via Stitch."""
    import httpx
    from app.services.stitch_service import stitch_service

    parent = await get_screen_or_404(db, data.screen_id)
    await require_project_access(db, request, parent.project_id, min_role="researcher")

    interface_config = await get_project_interface_config(db, parent.project_id)
    stitch_api_key = interface_config.stitch_api_key if interface_config else ""

    if not stitch_api_key:
        return await execute_design_tool(
            "create_variant",
            {
                "screen_id": data.screen_id,
                "variant_type": data.variant_type,
                "count": data.count,
            },
            parent.project_id,
        )

    stitch_proj_id = parent.stitch_project_id or "default"
    stitch_screen_ids = [parent.stitch_screen_id] if parent.stitch_screen_id else []
    if not stitch_screen_ids:
        raise HTTPException(
            status_code=422,
            detail="Screen has no Stitch screen ID -- cannot generate variants via Stitch",
        )

    try:
        stitch_data = await stitch_service.generate_variants(
            stitch_proj_id,
            stitch_screen_ids,
            parent.prompt or f"Create {data.variant_type} variants",
            variant_count=data.count,
            creative_range=data.variant_type,
            api_key=stitch_api_key,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Stitch variant error: {e}")

    output_components = stitch_data.get("outputComponents", [{}])
    screens_data = []
    if output_components:
        design_block = output_components[0].get("design", {})
        screens_data = design_block.get("screens", [])
    if not screens_data and stitch_data.get("screens"):
        screens_data = stitch_data["screens"]

    created_variants: list[DesignScreen] = []
    async with httpx.AsyncClient(timeout=60) as http:
        for i, s_data in enumerate(screens_data):
            vid = str(uuid.uuid4())
            stitch_vid = s_data.get("id", "")
            html_content = ""
            html_code = s_data.get("htmlCode", {})
            html_url = html_code.get("downloadUrl", "") if isinstance(html_code, dict) else ""
            if html_url:
                try:
                    resp = await http.get(html_url)
                    resp.raise_for_status()
                    html_content = resp.text
                except Exception:
                    pass
            if not html_content:
                html_content = s_data.get("html", s_data.get("htmlContent", ""))

            screenshot_path = ""
            screenshot_info = s_data.get("screenshot", {})
            screenshot_url = (
                screenshot_info.get("downloadUrl", "") if isinstance(screenshot_info, dict) else ""
            )
            if screenshot_url:
                try:
                    resp = await http.get(screenshot_url)
                    resp.raise_for_status()
                    save_dir = Path(settings.design_screens_dir)
                    save_dir.mkdir(parents=True, exist_ok=True)
                    img_path = save_dir / f"{vid}.png"
                    img_path.write_bytes(resp.content)
                    screenshot_path = str(img_path)
                except Exception:
                    pass

            variant = DesignScreen(
                id=vid,
                project_id=parent.project_id,
                title=s_data.get("title") or f"Variant {i + 1} ({data.variant_type})",
                description=f"{data.variant_type} variant of {data.screen_id}",
                prompt=parent.prompt,
                device_type=parent.device_type,
                model_used=parent.model_used,
                html_content=html_content,
                screenshot_path=screenshot_path,
                parent_screen_id=data.screen_id,
                variant_type=data.variant_type.lower(),
                stitch_project_id=stitch_proj_id,
                stitch_screen_id=stitch_vid,
                status="ready",
                source_findings=parent.source_findings,
            )
            db.add(variant)
            created_variants.append(variant)

    await db.commit()
    for variant in created_variants:
        await db.refresh(variant)

    return {"variants": [v.to_dict() for v in created_variants], "count": len(created_variants)}


@router.delete("/interfaces/screens/{screen_id}", status_code=204)
async def delete_screen(screen_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Delete a design screen."""
    screen = await get_screen_or_404(db, screen_id)
    await require_project_access(db, request, screen.project_id, min_role="researcher")
    await db.delete(screen)
    await db.commit()
