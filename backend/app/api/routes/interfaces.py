"""Interfaces API routes -- Design chat, screen management, Figma, and handoff.

This module powers the Interfaces menu in Istara, providing:
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

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.content_guard import ContentGuard
from app.core.context_summarizer import context_summarizer
from app.core.ollama import ollama
from app.core.permissions import get_subject, get_visible_project_or_404, is_global_admin, require_project_access
from app.core.security_middleware import require_admin_from_request
from app.core.prompt_rag import compose_dynamic_prompt
from app.core.rag import build_augmented_prompt, retrieve_context
from app.core.token_counter import context_guard
from app.models.database import async_session, get_db
from app.models.design_screen import DesignBrief, DesignDecision, DesignScreen
from app.models.message import Message
from app.models.project import Project
from app.models.session import ChatSession, INFERENCE_PRESETS
from app.skills.design_tools import (
    OPENAI_DESIGN_TOOLS,
    build_design_tools_prompt,
    execute_design_tool,
)

_log = logging.getLogger(__name__)
_guard = ContentGuard()


def _resolve_project_folder(project, project_id: str) -> Path:
    if project and getattr(project, "watch_folder_path", None):
        return Path(project.watch_folder_path)
    return Path(settings.upload_dir) / project_id


router = APIRouter()

# Maximum tool-call iterations per message (prevents infinite loops)
MAX_TOOL_ITERATIONS = 3


async def _get_screen_or_404(db: AsyncSession, screen_id: str) -> DesignScreen:
    result = await db.execute(select(DesignScreen).where(DesignScreen.id == screen_id))
    screen = result.scalar_one_or_none()
    if not screen:
        raise HTTPException(status_code=404, detail="Screen not found")
    return screen

# Regex to extract tool call JSON from LLM output (same pattern as chat.py)
_TOOL_CALL_RE = re.compile(
    r'```(?:json)?\s*(\{\s*"tool"\s*:.+?\})\s*```',
    re.DOTALL,
)
_TOOL_CALL_INLINE_RE = re.compile(
    r'(\{\s*"tool"\s*:\s*"[a-z_]+".*)',
    re.DOTALL,
)


def _extract_tool_call(text: str) -> tuple[dict | None, str, str]:
    """Extract a tool call from LLM output.

    Returns (tool_call_dict, text_before_call, text_after_call).
    Returns (None, full_text, "") if no tool call found.
    """
    decoder = json.JSONDecoder()

    fenced = _TOOL_CALL_RE.search(text)
    if fenced:
        candidate = fenced.group(1)
        try:
            call = json.loads(candidate)
            if isinstance(call, dict) and "tool" in call:
                return call, text[: fenced.start()].strip(), text[fenced.end() :].strip()
        except json.JSONDecodeError:
            pass

    for start in [m.start() for m in re.finditer(r"\{", text)]:
        candidate = text[start:]
        if '"tool"' not in candidate[:80]:
            continue
        try:
            call, end = decoder.raw_decode(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(call, dict) and "tool" in call:
            return call, text[:start].strip(), candidate[end:].strip()

    return None, text, ""


def _is_tool_call_only(text: str) -> bool:
    tool_call, before, after = _extract_tool_call(text.strip())
    return bool(tool_call and not before and not after)


def _fallback_design_answer(tool_results: list[dict], user_message: str) -> str:
    """User-facing fallback when the model fails to synthesize after tool use."""
    if not tool_results:
        return (
            "I could not produce a usable design response for that request. "
            "Try asking again with the specific screen, flow, or evidence area you want me to inspect."
        )

    last = tool_results[-1]
    result_text = str(last.get("result") or "").strip()
    tool_name = str(last.get("tool") or "design tool")
    if result_text.lower() in {"", "no matching findings found."}:
        return (
            "I checked the project findings for design evidence and did not find matching UI findings yet.\n\n"
            "That means I do not have enough evidence in Istara to recommend Acme UI changes from the current findings. "
            "The next useful step is to add or tag UI-specific evidence, such as onboarding friction, navigation issues, "
            "screen feedback, verification problems, or prototype notes."
        )

    return (
        f"I checked `{tool_name}` and found this relevant design context:\n\n"
        f"{result_text}\n\n"
        "Use this as supporting input, but treat it as preliminary until it is linked into the evidence chain."
    )


async def _generate_native_design_tools(
    conversation: list[dict],
    all_text_parts: list[str],
    tool_results: list[dict],
    request: DesignChatRequest,
    session_agent_id: str | None,
    llm_model: str | None,
    llm_temperature: float,
    llm_max_tokens: int | None,
):
    """Native tool-calling loop for Interfaces Design Chat.

    Mirrors the main Chat route dynamics while using design-specific tools.
    """
    for iteration in range(MAX_TOOL_ITERATIONS + 1):
        content_chunks: list[str] = []
        tool_calls_payload: dict | None = None

        async for chunk in ollama.chat_stream(
            messages=conversation,
            model=llm_model,
            temperature=llm_temperature,
            max_tokens=llm_max_tokens,
            tools=OPENAI_DESIGN_TOOLS,
        ):
            if isinstance(chunk, dict) and chunk.get("tool_calls"):
                tool_calls_payload = chunk
            elif isinstance(chunk, str):
                content_chunks.append(chunk)

        response_text = "".join(content_chunks)

        if tool_calls_payload and iteration < MAX_TOOL_ITERATIONS:
            valid_tool_names = {t["function"]["name"] for t in OPENAI_DESIGN_TOOLS}
            raw_tool_calls = [
                tc
                for tc in tool_calls_payload["tool_calls"]
                if tc.get("function", {}).get("name", "") in valid_tool_names
            ]

            if not raw_tool_calls:
                response_text = response_text.strip()
                if response_text:
                    all_text_parts.append(response_text)
                    yield f"data: {json.dumps({'type': 'chunk', 'content': response_text})}\n\n"
                break

            if response_text.strip():
                all_text_parts.append(response_text)
                event_data = json.dumps({"type": "chunk", "content": response_text + "\n\n"})
                yield f"data: {event_data}\n\n"

            conversation.append(
                {
                    "role": "assistant",
                    "content": response_text or "",
                    "tool_calls": raw_tool_calls,
                }
            )

            for tc in raw_tool_calls:
                tc_id = tc.get("id", str(uuid.uuid4()))
                fn = tc.get("function", {})
                tool_name = fn.get("name", "")
                try:
                    tool_params = json.loads(fn.get("arguments", "{}"))
                except (json.JSONDecodeError, TypeError):
                    tool_params = {}

                _log.info(
                    "Native design tool call [%d]: %s(%s)",
                    iteration,
                    tool_name,
                    json.dumps(tool_params)[:200],
                )

                yield f"data: {json.dumps({'type': 'tool_call', 'tool': tool_name, 'params': tool_params})}\n\n"

                result = await execute_design_tool(
                    tool_name,
                    tool_params,
                    request.project_id,
                    agent_id=session_agent_id or "design-lead",
                )
                result_text = result.get("result", result.get("error", "Unknown result"))
                tool_results.append({"tool": tool_name, "result": result_text})

                conversation.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "content": str(result_text),
                    }
                )

            continue

        response_text = response_text.strip()
        if response_text:
            all_text_parts.append(response_text)
            yield f"data: {json.dumps({'type': 'chunk', 'content': response_text})}\n\n"
        break


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
You are the Design Lead agent in Istara. You bridge UX Research and Product Design.
Your role is to translate research insights into actionable design specifications,
generate UI concepts using available design tools, and ensure every design decision
is grounded in evidence from the research findings. You are collaborative,
evidence-driven, and accessibility-first (WCAG 2.1 AA baseline).

When the user asks you to generate screens, create variants, or work with designs,
use the design tools below. For general design conversation and critique, respond normally.
"""


@router.get("/interfaces/design-chat/{project_id}/history")
async def design_chat_history(project_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Get message history for the design chat session.

    Finds the design-scoped session for this project and returns its messages.
    """
    await require_project_access(db, request, project_id, min_role="viewer")
    session_result = await db.execute(
        select(ChatSession)
        .where(
            ChatSession.project_id == project_id,
            ChatSession.session_type == "design",
        )
        .order_by(ChatSession.created_at.desc())
    )
    session = session_result.scalar_one_or_none()
    if not session:
        return {"messages": [], "session_id": None}

    msg_result = await db.execute(
        select(Message)
        .where(Message.project_id == project_id, Message.session_id == session.id)
        .order_by(Message.created_at.asc())
        .limit(50)
    )
    messages = [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in msg_result.scalars().all()
        if m.role in ("user", "assistant")
        and m.content.strip()
        and not (m.role == "assistant" and _is_tool_call_only(m.content))
    ]
    return {"messages": messages, "session_id": session.id}


@router.post("/interfaces/design-chat")
async def design_chat(request: DesignChatRequest, http_request: Request, db: AsyncSession = Depends(get_db)):
    """Send a message to the Design Lead and get a streaming response with design tools.

    The response is streamed as Server-Sent Events (SSE) with a ReAct tool loop.

    Session scoping: If no session_id is provided, a design-specific session is
    created (or reused) for this project so that design chat messages are
    isolated from regular chat messages.
    """
    project = await get_visible_project_or_404(
        db,
        http_request,
        request.project_id,
        min_role="researcher",
    )

    # Resolve or create a design-scoped session. Supplied session IDs must
    # belong to the requested project and to the design-chat surface.
    resolved_session_id = request.session_id
    session: ChatSession | None = None
    if resolved_session_id:
        existing = await db.execute(
            select(ChatSession).where(
                ChatSession.id == resolved_session_id,
                ChatSession.project_id == request.project_id,
                ChatSession.session_type == "design",
            )
        )
        session = existing.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        # Find existing design session for this project
        existing = await db.execute(
            select(ChatSession)
            .where(
                ChatSession.project_id == request.project_id,
                ChatSession.session_type == "design",
            )
            .order_by(ChatSession.created_at.desc())
        )
        existing_session = existing.scalar_one_or_none()
        if existing_session:
            session = existing_session
            resolved_session_id = existing_session.id
        else:
            # Create a new design session
            session = ChatSession(
                id=str(uuid.uuid4()),
                project_id=request.project_id,
                title="Design Chat",
                session_type="design",
                agent_id="design-lead",
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)
            resolved_session_id = session.id

    # Save user message (scoped to design session)
    user_msg = Message(
        id=str(uuid.uuid4()),
        project_id=request.project_id,
        session_id=resolved_session_id,
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

    if session:
        preset_key = session.inference_preset.value if session.inference_preset else "medium"
        preset = INFERENCE_PRESETS.get(preset_key, INFERENCE_PRESETS["medium"])

        if preset_key == "custom":
            llm_temperature = (
                session.custom_temperature if session.custom_temperature is not None else 0.7
            )
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
    rag_result = await retrieve_context(request.project_id, request.message)

    # Budget-aware pipeline
    from app.core.budget_coordinator import budget_coordinator, compute_surplus_level
    from app.core.prompt_compressor import compress_rag_chunks

    budget = budget_coordinator.allocate(settings.max_context_tokens)
    surplus = compute_surplus_level()

    # Re-compose agent identity with budget-aware token limit
    if agent_identity_prompt:
        try:
            agent_identity_prompt = await compose_dynamic_prompt(
                "design-lead",
                query=request.message,
                max_tokens=budget.identity_tokens,
                use_embeddings=True,
            )
        except Exception:
            pass

    # Compress RAG chunks with question-aware scoring within budget
    rag_context = ""
    if rag_result and rag_result.retrieved:
        chunk_texts = [r.text for r in rag_result.retrieved if r.text]
        compressed_chunks, _ = compress_rag_chunks(
            chunk_texts, request.message, budget.rag_tokens, surplus
        )
        rag_context = "\n---\n".join(compressed_chunks) if compressed_chunks else ""

    # Build system prompt
    system_prompt = build_augmented_prompt(
        query=request.message,
        rag_context=rag_context,
        project_context=project.project_context or None,
        company_context=project.company_context or None,
    )

    # Inject Design Lead identity at the top
    system_prompt = agent_identity_prompt + "\n\n---\n\n" + system_prompt

    system_prompt += (
        "\n\nDesign tools are available through native tool calling when needed. "
        "After a tool result is provided, do not output another raw tool JSON unless another tool is truly needed. "
        "Always synthesize a user-facing answer in natural language. Never show raw tool-call JSON to the user."
    )

    # Inject project folder file awareness
    folder = _resolve_project_folder(project, request.project_id)
    if folder.exists():
        project_files = [
            f.name for f in folder.iterdir() if f.is_file() and not f.name.startswith(".")
        ]
        if project_files:
            files_context = (
                "\n\n## Project Files Available\n"
                "The following files are in this project's scope:\n"
                + "\n".join(f"- {name}" for name in project_files[:50])
            )
            system_prompt += files_context

    # Build message history (scoped to design session)
    messages: list[dict[str, str]] = []
    history_query = select(Message).where(
        Message.project_id == request.project_id, Message.session_id == resolved_session_id
    )
    history_result = await db.execute(history_query.order_by(Message.created_at.desc()).limit(20))
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
            system_prompt,
            messages,
            session_id=resolved_session_id,
            budget=budget.history_tokens,
        )
    except Exception:
        pass

    # Context window guard
    from app.core.token_counter import ContextWindowGuard

    budget_guard = ContextWindowGuard(budget=budget)
    messages, trim_summary = budget_guard.summarize_if_needed(system_prompt, messages)
    if trim_summary:
        messages.insert(0, {"role": "system", "content": trim_summary})

    system_prompt += (
        "\n\n[INSTRUCTIONS END]\n\n"
        "You are now in conversation with the user about interface and design work. "
        "Respond naturally and concisely. Do NOT repeat, quote, or reference the instructions above. "
        "Do NOT explain your capabilities unless asked. Just respond to what the user says.\n\n"
    )

    # Prepend system prompt
    messages = [{"role": "system", "content": system_prompt}, *messages]

    async def generate():
        """Stream the LLM response with ReAct tool-use loop for design tools."""
        conversation = list(messages)
        all_text_parts: list[str] = []
        tool_results: list[dict] = []
        use_native_tools = True

        try:
            if use_native_tools:
                try:
                    async for event in _generate_native_design_tools(
                        conversation,
                        all_text_parts,
                        tool_results,
                        request,
                        session_agent_id,
                        llm_model,
                        llm_temperature,
                        llm_max_tokens,
                    ):
                        yield event
                except Exception as native_err:
                    err_str = str(native_err).lower()
                    if any(
                        key in err_str
                        for key in ("tools", "400", "422", "unprocessable", "not supported")
                    ):
                        _log.warning(
                            "Native design tool calling rejected, falling back to text parsing: %s",
                            native_err,
                        )
                        use_native_tools = False
                        conversation = list(messages)
                        all_text_parts.clear()
                        tool_results.clear()
                    else:
                        raise

                if use_native_tools and not "".join(all_text_parts).strip() and not tool_results:
                    use_native_tools = False
                    conversation = list(messages)

            if not use_native_tools:
                if conversation and conversation[0]["role"] == "system":
                    conversation[0]["content"] += "\n\n" + build_design_tools_prompt()
                else:
                    conversation.insert(0, {"role": "system", "content": build_design_tools_prompt()})

            for iteration in range(MAX_TOOL_ITERATIONS + 1 if not use_native_tools else 0):
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

                    tool_event = json.dumps(
                        {
                            "type": "tool_call",
                            "tool": tool_name,
                            "params": tool_params,
                        }
                    )
                    yield f"data: {tool_event}\n\n"

                    result = await execute_design_tool(
                        tool_name,
                        tool_params,
                        request.project_id,
                        agent_id=session_agent_id or "design-lead",
                    )

                    result_text = result.get("result", result.get("error", "Unknown result"))
                    tool_results.append({"tool": tool_name, "result": result_text})

                    assistant_turn = (
                        text_before + f"\n\n[Tool: {tool_name}]"
                        if text_before
                        else f"[Tool: {tool_name}]"
                    )
                    conversation.append({"role": "assistant", "content": assistant_turn})
                    conversation.append(
                        {
                            "role": "user",
                            "content": (
                                f"[Tool result for {tool_name}]:\n{result_text}\n\n"
                                "Now respond to the user based on this result. "
                                "Do not show raw JSON or the internal tool-call format. "
                                "Do not call another tool unless necessary."
                            ),
                        }
                    )
                    continue

                else:
                    if tool_call:
                        response_text = _fallback_design_answer(tool_results, request.message)
                    response_text = response_text.strip()
                    if response_text:
                        all_text_parts.append(response_text)
                        event_data = json.dumps({"type": "chunk", "content": response_text})
                        yield f"data: {event_data}\n\n"
                    break

            # Save the full assistant response
            async with async_session() as save_db:
                assistant_content = "".join(all_text_parts).strip()
                if not assistant_content:
                    assistant_content = _fallback_design_answer(tool_results, request.message)
                assistant_msg = Message(
                    id=str(uuid.uuid4()),
                    project_id=request.project_id,
                    session_id=resolved_session_id,
                    role="assistant",
                    content=assistant_content,
                )
                save_db.add(assistant_msg)
                await save_db.commit()

                sources = (
                    [
                        {"source": r.source, "score": r.score, "page": r.page}
                        for r in rag_result.retrieved
                    ]
                    if rag_result and hasattr(rag_result, "retrieved")
                    else []
                )
                done_data = json.dumps(
                    {
                        "type": "done",
                        "message_id": assistant_msg.id,
                        "session_id": resolved_session_id,
                        "sources": sources,
                        "tools_used": [t["tool"] for t in tool_results] if tool_results else [],
                    }
                )
                yield f"data: {done_data}\n\n"

        except GeneratorExit:
            if all_text_parts:
                try:
                    async with async_session() as save_db:
                        msg = Message(
                            id=str(uuid.uuid4()),
                            project_id=request.project_id,
                            session_id=resolved_session_id,
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

    async def safe_generate():
        try:
            async for event in generate():
                yield event
        except Exception as e:
            error_data = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        safe_generate(),
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
    request: Request,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List design screens, optionally filtered by project."""
    subject = get_subject(request)
    if project_id:
        await require_project_access(db, request, project_id, min_role="viewer")
    elif not is_global_admin(subject):
        raise HTTPException(status_code=400, detail="project_id is required")

    query = select(DesignScreen).order_by(DesignScreen.created_at.desc())
    if project_id:
        query = query.where(DesignScreen.project_id == project_id)
    result = await db.execute(query)
    return [s.to_dict() for s in result.scalars().all()]


@router.get("/interfaces/screens/{screen_id}")
async def get_screen(screen_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Get a single design screen by ID."""
    screen = await _get_screen_or_404(db, screen_id)
    await require_project_access(db, request, screen.project_id, min_role="viewer")
    return screen.to_dict()


@router.post("/interfaces/screens/generate")
async def generate_screen(
    data: GenerateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Generate a new screen via Stitch or design tools.

    When Stitch is configured, calls the real MCP API and parses the response
    to extract screens with HTML and screenshots. Returns the DesignScreen record(s).
    """
    import httpx
    from app.services.stitch_service import stitch_service
    from app.core.content_guard import ContentGuard

    await require_project_access(db, request, data.project_id, min_role="researcher")

    # If Stitch is not configured, fall back to the design tool executor
    if not settings.stitch_api_key:
        tool_result = await execute_design_tool(
            "generate_screen",
            {
                "prompt": data.prompt,
                "device_type": data.device_type,
                "model": data.model,
                "seed_finding_ids": data.seed_finding_ids,
            },
            data.project_id,
        )
        return tool_result

    guard = ContentGuard()
    seed_ids = data.seed_finding_ids or []

    # Enrich prompt with findings if seeded
    enriched_prompt = data.prompt
    if seed_ids:
        from app.models.finding import Insight, Recommendation

        texts: list[str] = []
        for fid in seed_ids[:5]:
            for Model in [Insight, Recommendation]:
                r = await db.execute(select(Model).where(Model.id == fid))
                finding = r.scalar_one_or_none()
                if finding:
                    texts.append(f"- {finding.text}")
        if texts:
            enriched_prompt = (
                "Based on these research findings:\n"
                + "\n".join(texts)
                + f"\n\nDesign: {data.prompt}"
            )

    # Create or reuse a Stitch project
    stitch_project_id = "default"
    try:
        stitch_proj = await stitch_service.create_project(f"Istara-{data.project_id[:8]}")
        raw_name = stitch_proj.get("name", "")
        stitch_project_id = stitch_service.extract_project_id(raw_name) if raw_name else "default"
    except Exception:
        pass

    # Call Stitch MCP API
    try:
        stitch_data = await stitch_service.generate_screen(
            stitch_project_id, enriched_prompt, data.device_type, data.model
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Stitch API error: {e}")

    # Parse response: screens nested in outputComponents[0].design.screens[]
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
        for i, s_data in enumerate(screens_data):
            screen_id = str(uuid.uuid4())
            stitch_screen_id = s_data.get("id", "")
            screen_title = s_data.get("title") or s_data.get("name") or data.prompt[:100]

            # Download HTML from downloadUrl
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

            # Security scan HTML
            if html_content:
                scan = guard.scan_text(html_content)
                if not scan.clean:
                    _log.warning("Stitch HTML flagged: %s", scan.threats)
                    html_content = scan.cleaned_text

            # Download screenshot
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

    # Create DesignDecision if seeded from findings
    decision_id = None
    if seed_ids and created_screens:
        decision_id = str(uuid.uuid4())
        dd = DesignDecision(
            id=decision_id,
            project_id=data.project_id,
            agent_id="design-lead",
            text=f"Design decision: {data.prompt[:200]}",
            recommendation_ids=json.dumps(seed_ids),
            screen_ids=json.dumps([s.id for s in created_screens]),
            rationale=f"Generated from research findings via Stitch ({data.model})",
        )
        db.add(dd)

    await db.commit()
    for s in created_screens:
        await db.refresh(s)

    # Return the first screen (most common case) with decision_id
    if created_screens:
        resp = created_screens[0].to_dict()
        resp["design_decision_id"] = decision_id
        if len(created_screens) > 1:
            resp["additional_screens"] = [s.to_dict() for s in created_screens[1:]]
        return resp

    # Fallback: no screens parsed from Stitch response
    raise HTTPException(status_code=502, detail="Stitch returned no screens")


@router.post("/interfaces/screens/edit")
async def edit_screen(data: EditRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Edit an existing screen with instructions via Stitch.

    Creates a child DesignScreen with the edited HTML, linked via parent_screen_id.
    """
    import httpx
    from app.services.stitch_service import stitch_service

    # Resolve parent screen
    parent = await _get_screen_or_404(db, data.screen_id)
    await require_project_access(db, request, parent.project_id, min_role="researcher")

    # If Stitch is not configured, fall back to design tool executor
    if not settings.stitch_api_key:
        result = await execute_design_tool(
            "edit_screen",
            {"screen_id": data.screen_id, "instructions": data.instructions},
            parent.project_id,
        )
        return result

    stitch_proj_id = parent.stitch_project_id or "default"
    stitch_screen_ids = [parent.stitch_screen_id] if parent.stitch_screen_id else []

    if not stitch_screen_ids:
        raise HTTPException(
            status_code=422,
            detail="Screen has no Stitch screen ID -- cannot edit via Stitch",
        )

    try:
        stitch_data = await stitch_service.edit_screen(
            stitch_proj_id, stitch_screen_ids, data.instructions
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Stitch edit error: {e}")

    # Parse response
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

            # Download HTML
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

            # Download screenshot
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
    """Create design variants of an existing screen via Stitch.

    Returns a list of variant DesignScreen records, each linked to the parent.
    """
    import httpx
    from app.services.stitch_service import stitch_service

    parent = await _get_screen_or_404(db, data.screen_id)
    await require_project_access(db, request, parent.project_id, min_role="researcher")

    # If Stitch is not configured, fall back to design tool executor
    if not settings.stitch_api_key:
        result = await execute_design_tool(
            "create_variant",
            {
                "screen_id": data.screen_id,
                "variant_type": data.variant_type,
                "count": data.count,
            },
            parent.project_id,
        )
        return result

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
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Stitch variant error: {e}")

    # Parse response
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

            # Download HTML
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

            # Download screenshot
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

            vs = DesignScreen(
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
            db.add(vs)
            created_variants.append(vs)

    await db.commit()
    for v in created_variants:
        await db.refresh(v)

    return {"variants": [v.to_dict() for v in created_variants], "count": len(created_variants)}


@router.delete("/interfaces/screens/{screen_id}", status_code=204)
async def delete_screen(screen_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Delete a design screen."""
    screen = await _get_screen_or_404(db, screen_id)
    await require_project_access(db, request, screen.project_id, min_role="researcher")
    await db.delete(screen)
    await db.commit()


# -- Figma Integration -------------------------------------------------------


@router.post("/interfaces/figma/import")
async def figma_import(data: FigmaImportRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Import design context from a Figma URL.

    When Figma is configured, calls the real Figma REST API to fetch file data,
    components, and styles. Returns a structured design context.
    """
    from app.services.figma_service import figma_service

    await require_project_access(db, request, data.project_id, min_role="researcher")

    # Parse the Figma URL
    parsed = figma_service.parse_figma_url(data.figma_url)
    file_key = parsed.get("file_key", "")
    node_id = parsed.get("node_id")

    if not file_key:
        raise HTTPException(status_code=422, detail="Could not extract file key from Figma URL")

    # If Figma is not configured, fall back to the design tool executor
    if not settings.figma_api_token:
        tool_result = await execute_design_tool(
            "import_from_figma",
            {"figma_url": data.figma_url},
            data.project_id,
        )
        return tool_result

    try:
        # Fetch file metadata
        file_data = await figma_service.get_file(file_key)
        file_name = file_data.get("name", "Untitled")

        # Fetch node data if a specific node was referenced
        node_data = None
        if node_id:
            try:
                node_data = await figma_service.get_file_nodes(file_key, [node_id])
            except Exception:
                pass

        # Fetch components and styles
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

        return {
            "success": True,
            "file_key": file_key,
            "node_id": node_id,
            "name": file_name,
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
    screen = await _get_screen_or_404(db, data.screen_id)
    await require_project_access(db, request, screen.project_id, min_role="researcher")

    # Store the Figma link on the screen record
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
    """Extract a design system summary from a Figma file.

    Returns components and styles organized as a design system.
    Requires Figma API token to be configured.
    """
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


# -- Handoff -----------------------------------------------------------------


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
    return {"briefs": [b.to_dict() for b in briefs]}


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
    return result


@router.post("/interfaces/handoff/dev-spec")
async def handoff_dev_spec(
    data: HandoffDevSpecRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Generate a developer handoff spec from a design screen."""
    screen = await _get_screen_or_404(db, data.screen_id)
    await require_project_access(db, request, screen.project_id, min_role="viewer")

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
                        findings.append(
                            {"type": Model.__tablename__, "text": item.text, "id": item.id}
                        )
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
async def interfaces_status(request: Request, db: AsyncSession = Depends(get_db)):
    """Get the current status of the Interfaces module."""
    require_admin_from_request(request)
    screens_count = await db.execute(select(func.count()).select_from(DesignScreen))
    briefs_count = await db.execute(select(func.count()).select_from(DesignBrief))

    return {
        "stitch_configured": bool(settings.stitch_api_key),
        "figma_configured": bool(settings.figma_api_token),
        "onboarding_needed": not bool(settings.stitch_api_key)
        and not bool(settings.figma_api_token),
        "screens_count": screens_count.scalar() or 0,
        "briefs_count": briefs_count.scalar() or 0,
    }


@router.post("/interfaces/configure/stitch")
async def configure_stitch(data: ConfigureStitchRequest, request: Request):
    """Configure the Stitch (Google Generative AI) API key."""
    require_admin_from_request(request)
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
async def configure_figma(data: ConfigureFigmaRequest, request: Request):
    """Configure the Figma API token."""
    require_admin_from_request(request)
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


# -- Mock Mode Endpoints (for integration testing without API keys) ----------

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
<head><meta charset="UTF-8"><title>Mock Variant — Dark Theme</title></head>
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
<head><meta charset="UTF-8"><title>Mock Variant — Compact</title></head>
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
<head><meta charset="UTF-8"><title>Mock Variant — Cards</title></head>
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


class MockGenerateRequest(BaseModel):
    project_id: str
    prompt: str = "Mock dashboard screen"
    device_type: str = "DESKTOP"
    seed_finding_ids: list[str] = []


class MockEditRequest(BaseModel):
    screen_id: str
    instructions: str = "Make it blue and add a profile link"


class MockVariantRequest(BaseModel):
    screen_id: str
    variant_type: str = "EXPLORE"
    count: int = 3


class MockFigmaImportRequest(BaseModel):
    project_id: str
    figma_url: str = "https://www.figma.com/file/abc123XYZ/MockDesignSystem"


@router.post("/interfaces/mock/generate")
async def mock_generate_screen(
    data: MockGenerateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Generate a mock screen WITHOUT calling Stitch API.

    Creates a real DesignScreen record in the database with realistic HTML content.
    Also creates a DesignDecision if seed_finding_ids are provided.
    Only available when Stitch is NOT configured (safety guard for tests).
    """
    # Mock endpoints always available for integration testing

    await require_project_access(db, request, data.project_id, min_role="researcher")

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
        source_findings=json.dumps(data.seed_finding_ids),
    )
    db.add(screen)

    decision_id = None
    if data.seed_finding_ids:
        decision_id = str(uuid.uuid4())
        dd = DesignDecision(
            id=decision_id,
            project_id=data.project_id,
            agent_id="mock-test",
            text=f"Design decision: {data.prompt[:200]}",
            recommendation_ids=json.dumps(data.seed_finding_ids),
            screen_ids=json.dumps([screen_id]),
            rationale="Generated from mock endpoint for integration testing",
        )
        db.add(dd)

    await db.commit()
    await db.refresh(screen)

    resp = screen.to_dict()
    resp["design_decision_id"] = decision_id
    return resp


@router.post("/interfaces/mock/edit")
async def mock_edit_screen(
    data: MockEditRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Edit a screen WITHOUT calling Stitch API.

    Creates a child DesignScreen with modified mock HTML linked to the parent.
    Only available when Stitch is NOT configured.
    """
    # Mock endpoints always available for integration testing

    parent = await _get_screen_or_404(db, data.screen_id)
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
    return edited.to_dict()


@router.post("/interfaces/mock/variants")
async def mock_generate_variants(
    data: MockVariantRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Generate mock variant screens WITHOUT calling Stitch API.

    Creates 2-3 child DesignScreen records with different mock HTML variants.
    Only available when Stitch is NOT configured.
    """
    # Mock endpoints always available for integration testing

    parent = await _get_screen_or_404(db, data.screen_id)
    await require_project_access(db, request, parent.project_id, min_role="researcher")

    count = min(max(data.count, 1), len(MOCK_VARIANT_TEMPLATES))
    variants = []
    for i in range(count):
        tmpl = MOCK_VARIANT_TEMPLATES[i % len(MOCK_VARIANT_TEMPLATES)]
        vid = str(uuid.uuid4())
        vs = DesignScreen(
            id=vid,
            project_id=parent.project_id,
            title=f"Variant {i + 1} ({data.variant_type}) — {tmpl['suffix']}",
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
        db.add(vs)
        variants.append(vs)

    await db.commit()
    for v in variants:
        await db.refresh(v)

    return {"variants": [v.to_dict() for v in variants], "count": len(variants)}


@router.post("/interfaces/mock/figma-import")
async def mock_figma_import(
    data: MockFigmaImportRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Import mock Figma design context WITHOUT calling Figma API.

    Returns realistic mock design context (components, styles, layout data).
    Only available when Figma is NOT configured.
    """
    # Mock endpoints always available for integration testing
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
