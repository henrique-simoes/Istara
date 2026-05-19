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

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.interfaces_common import DesignChatRequest, resolve_project_folder
from app.config import settings
from app.core.content_guard import ContentGuard
from app.core.context_summarizer import context_summarizer
from app.core.llm_thinking import ThinkingMode, apply_thinking_control, normalize_thinking_mode
from app.core.ollama import ollama
from app.core.permissions import get_visible_project_or_404, require_project_access
from app.core.prompt_rag import compose_dynamic_prompt
from app.core.rag import build_augmented_prompt, retrieve_context
from app.models.database import async_session, get_db
from app.models.message import Message
from app.models.session import ChatSession, INFERENCE_PRESETS
from app.skills.design_tools import (
    OPENAI_DESIGN_TOOLS,
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
            project_id=request.project_id,
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
    llm_thinking_mode = normalize_thinking_mode(request.thinking_mode)
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
        if request.thinking_mode is None:
            llm_thinking_mode = normalize_thinking_mode(getattr(session, "thinking_mode", None))

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
    folder = resolve_project_folder(project, request.project_id)
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
    messages = apply_thinking_control(messages, llm_thinking_mode)

    async def generate():
        """Stream the LLM response with ReAct tool-use loop for design tools."""
        conversation = list(messages)
        all_text_parts: list[str] = []
        tool_results: list[dict] = []
        use_native_tools = True

        try:
            start_data = json.dumps(
                {
                    "type": "start",
                    "session_id": resolved_session_id,
                }
            )
            yield f"data: {start_data}\n\n"

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
                    project_id=request.project_id,
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

# -- Composed Interfaces Subrouters -----------------------------------------

from app.api.routes.interfaces_integrations import router as integrations_router
from app.api.routes.interfaces_mock import router as mock_router
from app.api.routes.interfaces_screens import router as screens_router

router.include_router(screens_router)
router.include_router(integrations_router)
router.include_router(mock_router)
