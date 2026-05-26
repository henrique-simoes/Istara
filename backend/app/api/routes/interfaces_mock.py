"""Mock Interfaces endpoints used by integration tests and local demos."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.interfaces_common import (
    MockEditRequest,
    MockFigmaImportRequest,
    MockGenerateRequest,
    MockVariantRequest,
    get_screen_or_404,
    require_mock_interfaces_enabled,
)
from app.core.permissions import require_project_access
from app.models.database import get_db
from app.models.design_screen import DesignDecision, DesignScreen
from app.services.design_evidence import hydrate_design_screen, resolve_seed_findings
from app.services.finding_validity_service import provisional_design_decision_rationale

router = APIRouter()

MOCK_HTML_DASHBOARD = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Mock Generated Screen</title></head>
<body>
  <header style="background:#1a1a2e;color:white;padding:20px;">
    <h1>Dashboard</h1>
    <nav><a href="#">Home</a> <a href="#">Settings</a></nav>
  </header>
  <main style="padding:20px;">
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;">
      <div style="background:#f0f0f0;padding:16px;border-radius:8px;">
        <h3>Active Users</h3><p style="font-size:2em;">1,234</p>
      </div>
      <div style="background:#f0f0f0;padding:16px;border-radius:8px;">
        <h3>Completion Rate</h3><p style="font-size:2em;">87%</p>
      </div>
      <div style="background:#f0f0f0;padding:16px;border-radius:8px;">
        <h3>Satisfaction</h3><p style="font-size:2em;">4.2/5</p>
      </div>
    </div>
  </main>
</body>
</html>"""

MOCK_HTML_EDITED = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Mock Edited Screen</title></head>
<body>
  <header style="background:#2563eb;color:white;padding:20px;">
    <h1>Dashboard (Edited)</h1>
    <nav><a href="#">Home</a> <a href="#">Settings</a> <a href="#">Profile</a></nav>
  </header>
  <main style="padding:20px;">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
      <div style="background:#e0e7ff;padding:16px;border-radius:8px;">
        <h3>Active Users</h3><p style="font-size:2em;">1,234</p>
      </div>
      <div style="background:#e0e7ff;padding:16px;border-radius:8px;">
        <h3>Completion Rate</h3><p style="font-size:2em;">87%</p>
      </div>
    </div>
  </main>
</body>
</html>"""

MOCK_VARIANT_TEMPLATES = [
    {
        "suffix": "Dark Theme",
        "html": """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Mock Variant - Dark Theme</title></head>
<body style="background:#111827;color:#f9fafb;">
  <header style="background:#1f2937;padding:20px;">
    <h1>Dashboard</h1>
  </header>
  <main style="padding:20px;">
    <div style="background:#374151;padding:16px;border-radius:8px;">
      <h3>Active Users</h3><p style="font-size:2em;">1,234</p>
    </div>
  </main>
</body>
</html>""",
    },
    {
        "suffix": "Compact",
        "html": """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Mock Variant - Compact</title></head>
<body>
  <header style="background:#1a1a2e;color:white;padding:10px;">
    <h1 style="font-size:1em;">Dashboard</h1>
  </header>
  <main style="padding:8px;">
    <div style="display:flex;gap:8px;">
      <div style="background:#f0f0f0;padding:8px;border-radius:4px;flex:1;">
        <small>Users</small><b>1,234</b>
      </div>
      <div style="background:#f0f0f0;padding:8px;border-radius:4px;flex:1;">
        <small>Rate</small><b>87%</b>
      </div>
    </div>
  </main>
</body>
</html>""",
    },
    {
        "suffix": "Cards",
        "html": """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Mock Variant - Cards</title></head>
<body>
  <header style="background:#1a1a2e;color:white;padding:20px;">
    <h1>Dashboard</h1>
  </header>
  <main style="padding:20px;">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;">
      <div style="background:white;box-shadow:0 2px 8px rgba(0,0,0,0.1);padding:24px;border-radius:12px;">
        <h3>Active Users</h3><p style="font-size:2.5em;color:#2563eb;">1,234</p>
      </div>
      <div style="background:white;box-shadow:0 2px 8px rgba(0,0,0,0.1);padding:24px;border-radius:12px;">
        <h3>Satisfaction</h3><p style="font-size:2.5em;color:#059669;">4.2/5</p>
      </div>
    </div>
  </main>
</body>
</html>""",
    },
]


@router.post("/interfaces/mock/generate")
async def mock_generate_screen(
    data: MockGenerateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Generate a mock screen without calling Stitch API."""
    require_mock_interfaces_enabled()
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

    screen_id = str(uuid.uuid4())
    screen = DesignScreen(
        id=screen_id,
        project_id=data.project_id,
        title=data.prompt[:100],
        description=data.prompt,
        prompt=data.prompt,
        device_type=data.device_type,
        model_used="MOCK",
        html_content=MOCK_HTML_DASHBOARD,
        screenshot_path="",
        status="ready",
        source_findings=json.dumps(seed_ids),
    )
    db.add(screen)

    decision_id = None
    if seed_ids:
        decision_id = str(uuid.uuid4())
        db.add(
            DesignDecision(
                id=decision_id,
                project_id=data.project_id,
                agent_id="mock-test",
                text=f"Design decision: {data.prompt[:200]}",
                recommendation_ids=json.dumps(seed_ids),
                screen_ids=json.dumps([screen_id]),
                rationale=provisional_design_decision_rationale(
                    "Generated from mock endpoint for integration testing"
                ),
            )
        )

    await db.commit()
    await db.refresh(screen)
    resp = await hydrate_design_screen(db, screen)
    resp["design_decision_id"] = decision_id
    return resp


@router.post("/interfaces/mock/edit")
async def mock_edit_screen(
    data: MockEditRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Edit a screen without calling Stitch API."""
    require_mock_interfaces_enabled()

    parent = await get_screen_or_404(db, data.screen_id)
    await require_project_access(db, request, parent.project_id, min_role="researcher")

    new_id = str(uuid.uuid4())
    edited = DesignScreen(
        id=new_id,
        project_id=parent.project_id,
        title=f"Edit: {data.instructions[:80]}",
        description=data.instructions,
        prompt=data.instructions,
        device_type=parent.device_type,
        model_used="MOCK",
        html_content=MOCK_HTML_EDITED,
        screenshot_path="",
        parent_screen_id=data.screen_id,
        status="ready",
        source_findings=parent.source_findings,
    )
    db.add(edited)
    await db.commit()
    await db.refresh(edited)
    return await hydrate_design_screen(db, edited)


@router.post("/interfaces/mock/variants")
async def mock_generate_variants(
    data: MockVariantRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Generate mock variant screens without calling Stitch API."""
    require_mock_interfaces_enabled()

    parent = await get_screen_or_404(db, data.screen_id)
    await require_project_access(db, request, parent.project_id, min_role="researcher")

    count = min(max(data.count, 1), len(MOCK_VARIANT_TEMPLATES))
    variants = []
    for i in range(count):
        tmpl = MOCK_VARIANT_TEMPLATES[i % len(MOCK_VARIANT_TEMPLATES)]
        vid = str(uuid.uuid4())
        variant = DesignScreen(
            id=vid,
            project_id=parent.project_id,
            title=f"Variant {i + 1} ({data.variant_type}) - {tmpl['suffix']}",
            description=f"{data.variant_type} variant of {data.screen_id}",
            prompt=parent.prompt,
            device_type=parent.device_type,
            model_used="MOCK",
            html_content=tmpl["html"],
            parent_screen_id=data.screen_id,
            variant_type=data.variant_type.lower(),
            status="ready",
            source_findings=parent.source_findings,
        )
        db.add(variant)
        variants.append(variant)

    await db.commit()
    for variant in variants:
        await db.refresh(variant)

    return {
        "variants": [await hydrate_design_screen(db, v) for v in variants],
        "count": len(variants),
    }


@router.post("/interfaces/mock/figma-import")
async def mock_figma_import(
    data: MockFigmaImportRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Import mock Figma design context without calling Figma API."""
    require_mock_interfaces_enabled()
    await require_project_access(db, request, data.project_id, min_role="researcher")

    from app.services.figma_service import figma_service

    parsed = figma_service.parse_figma_url(data.figma_url)
    file_key = parsed.get("file_key") or "mockFileKey123"
    node_id = parsed.get("node_id")

    return {
        "success": True,
        "file_key": file_key,
        "node_id": node_id,
        "name": "Mock Design System",
        "components": [
            {"name": "Button/Primary", "key": "comp_001", "description": "Primary action button"},
            {
                "name": "Button/Secondary",
                "key": "comp_002",
                "description": "Secondary action button",
            },
            {"name": "Input/Text", "key": "comp_003", "description": "Standard text input field"},
            {"name": "Card/Default", "key": "comp_004", "description": "Content card container"},
            {"name": "NavBar/Top", "key": "comp_005", "description": "Top navigation bar"},
        ],
        "styles": [
            {
                "name": "Primary/500",
                "key": "style_001",
                "style_type": "FILL",
                "description": "#2563eb",
            },
            {
                "name": "Neutral/100",
                "key": "style_002",
                "style_type": "FILL",
                "description": "#f3f4f6",
            },
            {
                "name": "Text/Body",
                "key": "style_003",
                "style_type": "TEXT",
                "description": "16px Inter Regular",
            },
            {
                "name": "Text/Heading",
                "key": "style_004",
                "style_type": "TEXT",
                "description": "24px Inter Bold",
            },
            {
                "name": "Shadow/Card",
                "key": "style_005",
                "style_type": "EFFECT",
                "description": "0 2px 8px rgba(0,0,0,0.1)",
            },
        ],
        "layout": {
            "grid": "12-column",
            "breakpoints": {"mobile": 375, "tablet": 768, "desktop": 1280},
            "spacing_unit": 8,
        },
    }
