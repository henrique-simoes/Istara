"""Design Tools — LLM-callable tools for the Interfaces menu.

These tools allow the Design Lead agent to generate UI screens via
Google Stitch, manage design variants, import/export Figma files,
and maintain the Atomic Research evidence chain from research
findings through design decisions to generated screens.

Architecture mirrors system_actions.py: structured tool schemas
injected into the system prompt with a ReAct execution loop.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import select

from app.models.database import async_session

logger = logging.getLogger(__name__)


# -- Tool Definitions --------------------------------------------------------

DESIGN_TOOLS = [
    {
        "name": "generate_screen",
        "description": "Generate a UI screen from a text description using Google Stitch. Creates a DesignDecision linking research findings to the generated screen.",
        "parameters": {
            "prompt": {"type": "string", "required": True, "description": "Description of the UI screen to generate"},
            "device_type": {"type": "string", "required": False, "description": "Device type: MOBILE, DESKTOP, TABLET, or AGNOSTIC (default: DESKTOP)"},
            "model": {"type": "string", "required": False, "description": "AI model: GEMINI_3_PRO or GEMINI_3_FLASH (default: GEMINI_3_FLASH)"},
            "seed_finding_ids": {"type": "array", "required": False, "description": "Array of finding IDs (insights/recommendations) to seed the design from"},
        },
    },
    {
        "name": "edit_screen",
        "description": "Edit an existing generated screen with text instructions",
        "parameters": {
            "screen_id": {"type": "string", "required": True, "description": "ID of the screen to edit"},
            "instructions": {"type": "string", "required": True, "description": "Edit instructions for the screen"},
        },
    },
    {
        "name": "create_variant",
        "description": "Generate design variants of an existing screen. Types: REFINE (small tweaks), EXPLORE (moderate changes), REIMAGINE (major rethink)",
        "parameters": {
            "screen_id": {"type": "string", "required": True, "description": "ID of the screen to create variants from"},
            "variant_type": {"type": "string", "required": True, "description": "Type: REFINE, EXPLORE, or REIMAGINE"},
            "count": {"type": "integer", "required": False, "description": "Number of variants (1-5, default: 3)"},
        },
    },
    {
        "name": "search_findings_for_design",
        "description": "Search research findings (insights, recommendations, facts) relevant to a design task",
        "parameters": {
            "query": {"type": "string", "required": True, "description": "Search query for findings"},
        },
    },
    {
        "name": "create_design_brief",
        "description": "Generate a design brief from the project's research findings. Synthesizes insights and recommendations into actionable design requirements.",
        "parameters": {},
    },
    {
        "name": "import_from_figma",
        "description": "Import design context from a Figma URL (file or specific frame)",
        "parameters": {
            "figma_url": {"type": "string", "required": True, "description": "Figma URL to import from"},
        },
    },
    {
        "name": "list_screens",
        "description": "List all generated design screens in the current project",
        "parameters": {},
    },
]


def build_design_tools_prompt() -> str:
    """Build the design tools section for the system prompt."""
    lines = [
        "## Available Design Tools",
        "",
        "You can perform design actions by responding with a tool call in this exact JSON format:",
        "```json",
        '{"tool": "tool_name", "params": {"param1": "value1"}}',
        "```",
        "",
        "After executing the tool, I will show you the result. You can then call another tool or respond to the user.",
        "Only call a tool when the user's request requires a design action. For general design conversation, respond normally.",
        "",
        "### Design Tools:",
        "",
    ]
    for tool in DESIGN_TOOLS:
        params_desc = []
        for pname, pinfo in tool["parameters"].items():
            req = " (required)" if pinfo.get("required") else ""
            params_desc.append(f"  - {pname}: {pinfo['description']}{req}")
        lines.append(f"**{tool['name']}** -- {tool['description']}")
        if params_desc:
            lines.extend(params_desc)
        lines.append("")
    return "\n".join(lines)


# -- Tool Executors ----------------------------------------------------------


async def _exec_generate_screen(params: dict, project_id: str, agent_id: str) -> str:
    from app.services.stitch_service import stitch_service
    from app.models.design_screen import DesignScreen, DesignDecision

    prompt = params["prompt"]
    device = params.get("device_type", "DESKTOP")
    model = params.get("model", "GEMINI_3_FLASH")
    seed_ids = params.get("seed_finding_ids", [])

    # Enrich prompt with findings if seeded
    enriched_prompt = prompt
    if seed_ids:
        from app.models.finding import Insight, Recommendation

        async with async_session() as db:
            texts: list[str] = []
            for fid in seed_ids[:5]:  # max 5 findings
                for Model in [Insight, Recommendation]:
                    result = await db.execute(select(Model).where(Model.id == fid))
                    finding = result.scalar_one_or_none()
                    if finding:
                        texts.append(f"- {finding.text}")
            if texts:
                enriched_prompt = (
                    "Based on these research findings:\n"
                    + "\n".join(texts)
                    + f"\n\nDesign: {prompt}"
                )

    try:
        data = await stitch_service.generate_screen("default", enriched_prompt, device, model)
        screen_id = str(uuid.uuid4())
        async with async_session() as db:
            screen = DesignScreen(
                id=screen_id,
                project_id=project_id,
                title=prompt[:100],
                description=prompt,
                prompt=enriched_prompt,
                device_type=device,
                model_used=model,
                html_content=data.get("html", ""),
                screenshot_path="",
                status="ready",
                source_findings=json.dumps(seed_ids),
            )
            db.add(screen)
            # Create DesignDecision for Atomic Research traceability
            if seed_ids:
                dd = DesignDecision(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    agent_id=agent_id,
                    text=f"Design decision: {prompt[:200]}",
                    recommendation_ids=json.dumps(seed_ids),
                    screen_ids=json.dumps([screen_id]),
                    rationale=f"Generated from research findings via Stitch ({model})",
                )
                db.add(dd)
            await db.commit()
        return f"Screen generated: '{prompt[:60]}...' (ID: {screen_id}, device: {device}, status: ready)"
    except ValueError as e:
        return f"Stitch not configured: {e}"
    except Exception as e:
        return f"Screen generation failed: {e}"


async def _exec_edit_screen(params: dict, project_id: str, agent_id: str) -> str:
    from app.services.stitch_service import stitch_service
    from app.models.design_screen import DesignScreen

    screen_id = params["screen_id"]
    instructions = params["instructions"]

    async with async_session() as db:
        result = await db.execute(select(DesignScreen).where(DesignScreen.id == screen_id))
        screen = result.scalar_one_or_none()
        if not screen:
            return f"Screen not found: {screen_id}"

    try:
        data = await stitch_service.edit_screen(
            screen.stitch_screen_id or screen_id,
            screen.stitch_project_id or "default",
            instructions,
        )
        new_id = str(uuid.uuid4())
        async with async_session() as db:
            edited = DesignScreen(
                id=new_id,
                project_id=project_id,
                title=f"Edit: {instructions[:80]}",
                description=instructions,
                prompt=instructions,
                device_type=screen.device_type,
                model_used=screen.model_used,
                html_content=data.get("html", ""),
                screenshot_path="",
                parent_screen_id=screen_id,
                status="ready",
                source_findings=screen.source_findings,
            )
            db.add(edited)
            await db.commit()
        return f"Screen edited: '{instructions[:60]}...' (new ID: {new_id}, parent: {screen_id})"
    except ValueError as e:
        return f"Stitch not configured: {e}"
    except Exception as e:
        return f"Edit failed: {e}"


async def _exec_create_variant(params: dict, project_id: str, agent_id: str) -> str:
    from app.services.stitch_service import stitch_service
    from app.models.design_screen import DesignScreen

    screen_id = params["screen_id"]
    variant_type = params.get("variant_type", "EXPLORE")
    count = min(params.get("count", 3), 5)

    async with async_session() as db:
        result = await db.execute(select(DesignScreen).where(DesignScreen.id == screen_id))
        screen = result.scalar_one_or_none()
        if not screen:
            return f"Screen not found: {screen_id}"

    try:
        variants = await stitch_service.generate_variants(
            screen.stitch_screen_id or screen_id,
            screen.stitch_project_id or "default",
            variant_type,
            count,
        )
        variant_ids: list[str] = []
        async with async_session() as db:
            for i, v in enumerate(variants):
                vid = str(uuid.uuid4())
                variant_ids.append(vid)
                vs = DesignScreen(
                    id=vid,
                    project_id=project_id,
                    title=f"Variant {i + 1} ({variant_type})",
                    description=f"{variant_type} variant of {screen_id}",
                    prompt=screen.prompt,
                    device_type=screen.device_type,
                    model_used=screen.model_used,
                    html_content=v.get("html", ""),
                    parent_screen_id=screen_id,
                    variant_type=variant_type.lower(),
                    status="ready",
                    source_findings=screen.source_findings,
                )
                db.add(vs)
            await db.commit()
        return f"Created {len(variant_ids)} {variant_type} variants of screen {screen_id}"
    except ValueError as e:
        return f"Stitch not configured: {e}"
    except Exception as e:
        return f"Variant generation failed: {e}"


async def _exec_search_findings(params: dict, project_id: str, agent_id: str) -> str:
    from app.models.finding import Insight, Recommendation, Fact

    query = params["query"].lower()
    results: list[str] = []
    async with async_session() as db:
        for Model, label in [(Insight, "Insight"), (Recommendation, "Recommendation"), (Fact, "Fact")]:
            result = await db.execute(select(Model).where(Model.project_id == project_id))
            for item in result.scalars().all():
                if query in item.text.lower():
                    results.append(f"[{label}] {item.text[:150]} (ID: {item.id})")
    if not results:
        return "No matching findings found."
    return f"Found {len(results)} matching findings:\n" + "\n".join(results[:10])


async def _exec_create_brief(params: dict, project_id: str, agent_id: str) -> str:
    from app.models.finding import Insight, Recommendation
    from app.models.design_screen import DesignBrief

    async with async_session() as db:
        insight_result = await db.execute(
            select(Insight).where(Insight.project_id == project_id)
        )
        insights = insight_result.scalars().all()
        rec_result = await db.execute(
            select(Recommendation).where(Recommendation.project_id == project_id)
        )
        recs = rec_result.scalars().all()

    if not insights and not recs:
        return "No findings available. Generate research findings first."

    brief_parts = ["# Design Brief\n"]
    insight_ids: list[str] = []
    rec_ids: list[str] = []

    if insights:
        brief_parts.append("## Key Insights\n")
        for ins in insights[:10]:
            brief_parts.append(f"- [{ins.impact or 'medium'} impact] {ins.text}")
            insight_ids.append(ins.id)

    if recs:
        brief_parts.append("\n## Recommendations\n")
        for rec in recs[:10]:
            brief_parts.append(f"- [{rec.priority or 'medium'} priority] {rec.text}")
            rec_ids.append(rec.id)

    content = "\n".join(brief_parts)
    brief_id = str(uuid.uuid4())
    async with async_session() as db:
        brief = DesignBrief(
            id=brief_id,
            project_id=project_id,
            title=f"Design Brief ({len(insights)} insights, {len(recs)} recommendations)",
            content=content,
            source_insight_ids=json.dumps(insight_ids),
            source_recommendation_ids=json.dumps(rec_ids),
        )
        db.add(brief)
        await db.commit()

    return f"Design brief created (ID: {brief_id}) with {len(insight_ids)} insights and {len(rec_ids)} recommendations"


async def _exec_import_figma(params: dict, project_id: str, agent_id: str) -> str:
    from app.services.figma_service import figma_service

    url = params["figma_url"]
    parsed = figma_service.parse_figma_url(url)
    if not parsed["file_key"]:
        return f"Could not parse Figma URL: {url}"

    try:
        file_data = await figma_service.get_file(parsed["file_key"])
        name = file_data.get("name", "Untitled")
        return f"Imported Figma file: '{name}' (key: {parsed['file_key']}, node: {parsed.get('node_id', 'root')})"
    except ValueError as e:
        return f"Figma not configured: {e}"
    except Exception as e:
        return f"Figma import failed: {e}"


async def _exec_list_screens(params: dict, project_id: str, agent_id: str) -> str:
    from app.models.design_screen import DesignScreen

    async with async_session() as db:
        result = await db.execute(
            select(DesignScreen)
            .where(DesignScreen.project_id == project_id)
            .order_by(DesignScreen.created_at.desc())
        )
        screens = result.scalars().all()

    if not screens:
        return "No design screens generated yet."

    lines = [f"Found {len(screens)} screens:"]
    for s in screens[:15]:
        variant = f" [{s.variant_type}]" if s.variant_type else ""
        lines.append(f"- {s.title[:60]} ({s.device_type}, {s.status}){variant} ID: {s.id}")
    return "\n".join(lines)


# -- Executor Registry -------------------------------------------------------

DESIGN_TOOL_EXECUTORS = {
    "generate_screen": _exec_generate_screen,
    "edit_screen": _exec_edit_screen,
    "create_variant": _exec_create_variant,
    "search_findings_for_design": _exec_search_findings,
    "create_design_brief": _exec_create_brief,
    "import_from_figma": _exec_import_figma,
    "list_screens": _exec_list_screens,
}


async def execute_design_tool(
    tool_name: str,
    params: dict,
    project_id: str,
    agent_id: str = "design-lead",
) -> dict[str, Any]:
    """Execute a design tool and return the result."""
    executor = DESIGN_TOOL_EXECUTORS.get(tool_name)
    if not executor:
        return {"success": False, "error": f"Unknown design tool: {tool_name}"}
    try:
        result = await executor(params, project_id, agent_id)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Design tool error ({tool_name}): {e}")
        return {"success": False, "error": str(e)}
