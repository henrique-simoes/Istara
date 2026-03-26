"""Interfaces API routes -- Design chat, screen management, Figma, and handoff.

This module powers the Interfaces menu in ReClaw, providing:
1. Design-chat: SSE streaming with ReAct tool loop (mirrors chat.py)
2. Screen CRUD: list, get, generate, edit, variant, delete
3. Figma integration: import and export
4. Handoff: design brief and dev spec generation
5. Status and configuration endpoints
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.content_guard import ContentGuard
from app.core.context_summarizer import context_summarizer
from app.core.ollama import ollama
from app.core.prompt_rag import compose_dynamic_prompt
from app.core.rag import build_augmented_prompt, retrieve_context
from app.core.token_counter import context_guard
from app.models.database import async_session, get_db
from app.models.design_screen import DesignBrief, DesignDecision, DesignScreen
from app.models.message import Message
from app.models.project import Project
from app.models.session import ChatSession, INFERENCE_PRESETS
from app.skills.design_tools import (
    build_design_tools_prompt,
    execute_design_tool,
)

_log = logging.getLogger(__name__)
_guard = ContentGuard()

router = APIRouter()

# Maximum tool-call iterations per message (prevents infinite loops)
MAX_TOOL_ITERATIONS = 3

# Regex to extract tool call JSON from LLM output (same pattern as chat.py)
_TOOL_CALL_RE = re.compile(
    r'```(?:json)?\s*(\{\s*"tool"\s*:.+?\})\s*```',
    re.DOTALL,
)
_TOOL_CALL_INLINE_RE = re.compile(
    r'(\{\s*"tool"\s*:\s*"[a-z_]+".*?\})',
    re.DOTALL,
)


def _extract_tool_call(text: str) -> tuple[dict | None, str, str]:
    """Extract a tool call from LLM output.

    Returns (tool_call_dict, text_before_call, text_after_call).
    Returns (None, full_text, "") if no tool call found.
    """
    match = _TOOL_CALL_RE.search(text)
    if not match:
        match = _TOOL_CALL_INLINE_RE.search(text)

    if not match:
        return None, text, ""

    try:
        call = json.loads(match.group(1) if _TOOL_CALL_RE.search(text) else match.group(1))
        if "tool" not in call:
            return None, text, ""
        before = text[: match.start()].strip()
        after = text[match.end() :].strip()
        return call, before, after
    except (json.JSONDecodeError, IndexError):
        return None, text, ""


# -- Request Models ----------------------------------------------------------


class DesignChatRequest(BaseModel):
    message: str
    project_id: str
    session_id: str | None = None


class GenerateRequest(BaseModel):
    project_id: str
    prompt: str
    device_type: str = "DESKTOP"
    model: str = "GEMINI_3_FLASH"
    seed_finding_ids: list[str] = []


class EditRequest(BaseModel):
    screen_id: str
    instructions: str


class VariantRequest(BaseModel):
    screen_id: str
    variant_type: str
    count: int = 3


class FigmaImportRequest(BaseModel):
    project_id: str
    figma_url: str


class FigmaExportRequest(BaseModel):
    screen_id: str
    figma_file_key: str


class HandoffBriefRequest(BaseModel):
    project_id: str


class HandoffDevSpecRequest(BaseModel):
    screen_id: str


class ConfigureStitchRequest(BaseModel):
    api_key: str


class ConfigureFigmaRequest(BaseModel):
    api_token: str


# -- Design Chat (SSE streaming with ReAct tool loop) -----------------------


DESIGN_LEAD_PREAMBLE = """\
You are the Design Lead agent in ReClaw. You bridge UX Research and Product Design.
Your role is to translate research insights into actionable design specifications,
generate UI concepts using available design tools, and ensure every design decision
is grounded in evidence from the research findings. You are collaborative,
evidence-driven, and accessibility-first (WCAG 2.1 AA baseline).

When the user asks you to generate screens, create variants, or work with designs,
use the design tools below. For general design conversation and critique, respond normally.
"""


@router.post("/interfaces/design-chat")
async def design_chat(request: DesignChatRequest, db: AsyncSession = Depends(get_db)):
    """Send a message to the Design Lead and get a streaming response with design tools.

    The response is streamed as Server-Sent Events (SSE) with a ReAct tool loop.
    """
    # Verify project exists
    result = await db.execute(select(Project).where(Project.id == request.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Save user message
    user_msg = Message(
        id=str(uuid.uuid4()),
        project_id=request.project_id,
        session_id=request.session_id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)
    await db.commit()

    # Content Guard: scan user message
    user_scan = _guard.scan_text(request.message)
    if user_scan.threat_level in ("medium", "high"):
        _log.warning(
            "Content guard flagged design-chat message: %s - %s",
            user_scan.threat_level,
            user_scan.threats,
        )

    # Resolve session-specific inference settings
    llm_temperature = 0.7
    llm_max_tokens: int | None = None
    llm_model: str | None = None
    session_agent_id: str | None = "design-lead"

    if request.session_id:
        sess_result = await db.execute(
            select(ChatSession).where(ChatSession.id == request.session_id)
        )
        session = sess_result.scalar_one_or_none()
        if session:
            preset_key = session.inference_preset.value if session.inference_preset else "medium"
            preset = INFERENCE_PRESETS.get(preset_key, INFERENCE_PRESETS["medium"])

            if preset_key == "custom":
                llm_temperature = session.custom_temperature if session.custom_temperature is not None else 0.7
                llm_max_tokens = session.custom_max_tokens
            else:
                llm_temperature = preset["temperature"] if preset["temperature"] is not None else 0.7
                llm_max_tokens = preset["max_tokens"]

            if session.model_override:
                llm_model = session.model_override

            session_agent_id = session.agent_id or "design-lead"

            # Update session stats
            session.message_count = (session.message_count or 0) + 1
            session.last_message_at = user_msg.created_at
            await db.commit()

    # Load Design Lead identity via Prompt RAG
    agent_identity_prompt = ""
    try:
        agent_identity_prompt = await compose_dynamic_prompt(
            "design-lead",
            query=request.message,
            use_embeddings=True,
        )
    except Exception:
        pass

    if not agent_identity_prompt:
        # Fallback: use the preamble directly
        agent_identity_prompt = DESIGN_LEAD_PREAMBLE

    # Retrieve RAG context
    rag_context = await retrieve_context(request.project_id, request.message)

    # Build system prompt
    system_prompt = build_augmented_prompt(
        query=request.message,
        rag_context=rag_context,
        project_context=project.project_context or None,
        company_context=project.company_context or None,
    )

    # Inject Design Lead identity at the top
    system_prompt = agent_identity_prompt + "\n\n---\n\n" + system_prompt

    # Inject design tools
    tools_prompt = build_design_tools_prompt()
    system_prompt += "\n\n" + tools_prompt

    # Inject project folder file awareness
    upload_dir = Path(settings.upload_dir) / request.project_id
    if upload_dir.exists():
        project_files = [
            f.name for f in upload_dir.iterdir()
            if f.is_file() and not f.name.startswith(".")
        ]
        if project_files:
            files_context = (
                "\n\n## Project Files Available\n"
                "The following files are in this project's scope:\n"
                + "\n".join(f"- {name}" for name in project_files[:50])
            )
            system_prompt += files_context

    # Build message history
    messages: list[dict[str, str]] = []
    history_query = select(Message).where(Message.project_id == request.project_id)
    if request.session_id:
        history_query = history_query.where(Message.session_id == request.session_id)
    history_result = await db.execute(
        history_query.order_by(Message.created_at.desc()).limit(20)
    )
    history = list(reversed(history_result.scalars().all()))

    for msg in history:
        if msg.role in ("user", "assistant"):
            messages.append({"role": msg.role, "content": msg.content})

    # Add current message if not already in history
    if not messages or messages[-1]["content"] != request.message:
        messages.append({"role": "user", "content": request.message})

    # Context summarization
    try:
        messages, ctx_summary = await context_summarizer.apply_summarization(
            system_prompt, messages, session_id=request.session_id
        )
    except Exception:
        pass

    # Context window guard
    messages, trim_summary = context_guard.summarize_if_needed(system_prompt, messages)
    if trim_summary:
        messages.insert(0, {"role": "system", "content": trim_summary})

    # Prepend system prompt
    messages = [{"role": "system", "content": system_prompt}, *messages]

    async def generate():
        """Stream the LLM response with ReAct tool-use loop for design tools."""
        conversation = list(messages)
        all_text_parts: list[str] = []
        tool_results: list[dict] = []

        try:
            for iteration in range(MAX_TOOL_ITERATIONS + 1):
                full_text: list[str] = []
                async for chunk in ollama.chat_stream(
                    messages=conversation,
                    model=llm_model,
                    temperature=llm_temperature,
                    max_tokens=llm_max_tokens,
                ):
                    full_text.append(chunk)

                response_text = "".join(full_text)

                tool_call, text_before, text_after = _extract_tool_call(response_text)

                if tool_call and iteration < MAX_TOOL_ITERATIONS:
                    tool_name = tool_call.get("tool", "")
                    tool_params = tool_call.get("params", {})

                    _log.info(f"Design tool call: {tool_name}({json.dumps(tool_params)[:200]})")

                    if text_before:
                        all_text_parts.append(text_before)
                        event_data = json.dumps({"type": "chunk", "content": text_before + "\n\n"})
                        yield f"data: {event_data}\n\n"

                    tool_event = json.dumps({
                        "type": "tool_call",
                        "tool": tool_name,
                        "params": tool_params,
                    })
                    yield f"data: {tool_event}\n\n"

                    result = await execute_design_tool(
                        tool_name, tool_params, request.project_id,
                        agent_id=session_agent_id or "design-lead",
                    )

                    result_text = result.get("result", result.get("error", "Unknown result"))
                    tool_results.append({"tool": tool_name, "result": result_text})

                    result_display = f"**{tool_name}**: {result_text}\n\n"
                    all_text_parts.append(result_display)
                    result_event = json.dumps({"type": "chunk", "content": result_display})
                    yield f"data: {result_event}\n\n"

                    assistant_turn = (
                        text_before + f"\n\n[Tool: {tool_name}]"
                        if text_before
                        else f"[Tool: {tool_name}]"
                    )
                    conversation.append({"role": "assistant", "content": assistant_turn})
                    conversation.append({
                        "role": "user",
                        "content": (
                            f"[Tool result for {tool_name}]:\n{result_text}\n\n"
                            "Now respond to the user based on this result. "
                            "Do not call another tool unless necessary."
                        ),
                    })
                    continue

                else:
                    all_text_parts.append(response_text)
                    event_data = json.dumps({"type": "chunk", "content": response_text})
                    yield f"data: {event_data}\n\n"
                    break

            # Save the full assistant response
            async with async_session() as save_db:
                assistant_content = "".join(all_text_parts)
                assistant_msg = Message(
                    id=str(uuid.uuid4()),
                    project_id=request.project_id,
                    session_id=request.session_id,
                    role="assistant",
                    content=assistant_content,
                )
                save_db.add(assistant_msg)
                await save_db.commit()

                sources = [
                    {"source": r.source, "score": r.score, "page": r.page}
                    for r in rag_context.retrieved
                ]
                done_data = json.dumps({
                    "type": "done",
                    "message_id": assistant_msg.id,
                    "sources": sources,
                    "tools_used": [t["tool"] for t in tool_results] if tool_results else [],
                })
                yield f"data: {done_data}\n\n"

        except GeneratorExit:
            if all_text_parts:
                try:
                    async with async_session() as save_db:
                        msg = Message(
                            id=str(uuid.uuid4()),
                            project_id=request.project_id,
                            session_id=request.session_id,
                            role="assistant",
                            content="".join(all_text_parts) + "\n\n[Response interrupted]",
                        )
                        save_db.add(msg)
                        await save_db.commit()
                except Exception:
                    pass
        except Exception as e:
            error_data = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# -- Screen CRUD -------------------------------------------------------------


@router.get("/interfaces/screens")
async def list_screens(
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List design screens, optionally filtered by project."""
    query = select(DesignScreen).order_by(DesignScreen.created_at.desc())
    if project_id:
        query = query.where(DesignScreen.project_id == project_id)
    result = await db.execute(query)
    return [s.to_dict() for s in result.scalars().all()]


@router.get("/interfaces/screens/{screen_id}")
async def get_screen(screen_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single design screen by ID."""
    result = await db.execute(select(DesignScreen).where(DesignScreen.id == screen_id))
    screen = result.scalar_one_or_none()
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")
    return screen.to_dict()


@router.post("/interfaces/screens/generate")
async def generate_screen(data: GenerateRequest, db: AsyncSession = Depends(get_db)):
    """Generate a new screen via design tools."""
    result = await execute_design_tool(
        "generate_screen",
        {
            "prompt": data.prompt,
            "device_type": data.device_type,
            "model": data.model,
            "seed_finding_ids": data.seed_finding_ids,
        },
        data.project_id,
    )
    return result


@router.post("/interfaces/screens/edit")
async def edit_screen(data: EditRequest, db: AsyncSession = Depends(get_db)):
    """Edit an existing screen with instructions."""
    # Resolve project_id from the screen
    screen_result = await db.execute(
        select(DesignScreen).where(DesignScreen.id == data.screen_id)
    )
    screen = screen_result.scalar_one_or_none()
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    result = await execute_design_tool(
        "edit_screen",
        {"screen_id": data.screen_id, "instructions": data.instructions},
        screen.project_id,
    )
    return result


@router.post("/interfaces/screens/variant")
async def create_variant(data: VariantRequest, db: AsyncSession = Depends(get_db)):
    """Create variants of an existing screen."""
    screen_result = await db.execute(
        select(DesignScreen).where(DesignScreen.id == data.screen_id)
    )
    screen = screen_result.scalar_one_or_none()
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    result = await execute_design_tool(
        "create_variant",
        {
            "screen_id": data.screen_id,
            "variant_type": data.variant_type,
            "count": data.count,
        },
        screen.project_id,
    )
    return result


@router.delete("/interfaces/screens/{screen_id}", status_code=204)
async def delete_screen(screen_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a design screen."""
    result = await db.execute(select(DesignScreen).where(DesignScreen.id == screen_id))
    screen = result.scalar_one_or_none()
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")
    await db.delete(screen)
    await db.commit()


# -- Figma Integration -------------------------------------------------------


@router.post("/interfaces/figma/import")
async def figma_import(data: FigmaImportRequest, db: AsyncSession = Depends(get_db)):
    """Import design context from a Figma URL."""
    result = await execute_design_tool(
        "import_from_figma",
        {"figma_url": data.figma_url},
        data.project_id,
    )
    return result


@router.post("/interfaces/figma/export")
async def figma_export(data: FigmaExportRequest, db: AsyncSession = Depends(get_db)):
    """Export a design screen to Figma."""
    screen_result = await db.execute(
        select(DesignScreen).where(DesignScreen.id == data.screen_id)
    )
    screen = screen_result.scalar_one_or_none()
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    # Store the Figma link on the screen record
    screen.figma_file_key = data.figma_file_key
    await db.commit()

    return {
        "success": True,
        "screen_id": data.screen_id,
        "figma_file_key": data.figma_file_key,
        "message": f"Screen '{screen.title}' linked to Figma file {data.figma_file_key}",
    }


# -- Handoff -----------------------------------------------------------------


@router.get("/interfaces/handoff/briefs")
async def list_briefs(project_id: str | None = None, db: AsyncSession = Depends(get_db)):
    """List design briefs for a project."""
    query = select(DesignBrief).order_by(DesignBrief.created_at.desc())
    if project_id:
        query = query.where(DesignBrief.project_id == project_id)
    result = await db.execute(query)
    briefs = result.scalars().all()
    return {"briefs": [b.to_dict() for b in briefs]}


@router.post("/interfaces/handoff/brief")
async def handoff_brief(data: HandoffBriefRequest, db: AsyncSession = Depends(get_db)):
    """Generate a design brief from project findings."""
    result = await execute_design_tool(
        "create_design_brief",
        {},
        data.project_id,
    )
    return result


@router.post("/interfaces/handoff/dev-spec")
async def handoff_dev_spec(data: HandoffDevSpecRequest, db: AsyncSession = Depends(get_db)):
    """Generate a developer handoff spec from a design screen."""
    screen_result = await db.execute(
        select(DesignScreen).where(DesignScreen.id == data.screen_id)
    )
    screen = screen_result.scalar_one_or_none()
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")

    # Build a structured dev spec from the screen data
    findings = []
    try:
        finding_ids = json.loads(screen.source_findings or "[]")
        if finding_ids:
            from app.models.finding import Insight, Recommendation

            for fid in finding_ids[:10]:
                for Model in [Insight, Recommendation]:
                    r = await db.execute(select(Model).where(Model.id == fid))
                    item = r.scalar_one_or_none()
                    if item:
                        findings.append({"type": Model.__tablename__, "text": item.text, "id": item.id})
    except Exception:
        pass

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

    return {"success": True, "dev_spec": spec}


# -- Status and Configuration ------------------------------------------------


@router.get("/interfaces/status")
async def interfaces_status(db: AsyncSession = Depends(get_db)):
    """Get the current status of the Interfaces module."""
    screens_count = await db.execute(
        select(func.count()).select_from(DesignScreen)
    )
    briefs_count = await db.execute(
        select(func.count()).select_from(DesignBrief)
    )

    return {
        "stitch_configured": bool(settings.stitch_api_key),
        "figma_configured": bool(settings.figma_api_token),
        "onboarding_needed": not bool(settings.stitch_api_key) and not bool(settings.figma_api_token),
        "screens_count": screens_count.scalar() or 0,
        "briefs_count": briefs_count.scalar() or 0,
    }


@router.post("/interfaces/configure/stitch")
async def configure_stitch(data: ConfigureStitchRequest):
    """Configure the Stitch (Google Generative AI) API key."""
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
async def configure_figma(data: ConfigureFigmaRequest):
    """Configure the Figma API token."""
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
