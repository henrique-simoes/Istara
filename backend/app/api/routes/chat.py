"""Chat API route — streaming LLM responses with native tool calling.

Architecture:
1. Agent identity loaded via Prompt RAG (query-aware persona sections)
2. Tools passed via OpenAI-compatible `tools` API parameter (native calling)
3. LLM decides which tools to call; structured tool_calls in the response
4. Tool results sent back as `role: "tool"` messages (OpenAI multi-turn format)
5. ReAct loop: LLM -> tool_calls -> execute -> tool results -> LLM (max 8 iter)
6. RAG context and project files provide grounding for all responses

Falls back to text-based regex parsing when native tool calling is rejected
by the provider (e.g. models without function-calling support).
"""

import json
import logging
import re
import tempfile
import uuid
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.agent_project_scope import require_agent_assignable_to_project
from app.config import settings
from app.core.agent import agent
from app.core.agent_identity import load_agent_identity, get_agent_display_name
from app.core.agentic import AgenticDispatcher
from app.core.agentic.bridge import stream_chat_turn
from app.core.agentic.types import TurnParams
from app.core.content_guard import ContentGuard
from app.core.prompt_rag import compose_dynamic_prompt, compose_keyword_prompt
from app.core.context_summarizer import context_summarizer
from app.core.llm_thinking import apply_thinking_control, normalize_thinking_mode, validate_model_effort
from app.core.ollama import ollama  # noqa: F401 — W2: transport moved to the dispatcher; tests monkeypatch this handle
from app.core.permissions import get_visible_project_or_404, require_project_access
from app.core.pi_replacement import (
    PI_ENGINE_VALUES,
    PiChatRunMetrics,
    ensure_pi_deepseek_registered,
    pi_chat_model,
    record_pi_span,
)
from app.core.pi_runtime import PiExecutionService
from app.core.rag import build_augmented_prompt, retrieve_context
from app.core.research_validity import RESEARCH_VALIDITY_CONTRACT, protected_block
from app.core.token_counter import context_guard
from app.models.database import get_db, async_session

_guard = ContentGuard()
from app.models.message import Message
from app.models.project import Project
from app.models.session import ChatSession, INFERENCE_PRESETS
from app.skills.registry import registry
from app.skills.system_actions import (
    build_tools_prompt,
    execute_tool,
    SYSTEM_TOOLS,
    OPENAI_TOOLS,
)


def _resolve_project_folder(project, project_id: str) -> Path:
    if project and getattr(project, "watch_folder_path", None):
        return Path(project.watch_folder_path)
    return Path(settings.upload_dir) / project_id


_chat_log = logging.getLogger(__name__)

router = APIRouter()

# Maximum tool-call iterations per message (prevents infinite loops)
MAX_TOOL_ITERATIONS = 8


async def _pi_registration_failure_events(
    *, project_id: str, agent_id: str | None, registration_status: str
):
    """Emit a terminal, transport-free response for an unavailable Pi target."""
    await record_pi_span(
        operation="pi_candidate_chat_sse_tool_loop",
        project_id=project_id,
        agent_id=agent_id or "istara-main",
        status="error",
        error_message=registration_status,
    )
    yield "data: " + json.dumps(
        {
            "type": "error",
            "code": "pi_registration_unavailable",
            "error": "pi_transport_unavailable",
            "detail": registration_status,
        }
    ) + "\n\n"
    yield "data: " + json.dumps(
        {"type": "done", "message_id": None, "sources": [], "tools_used": []}
    ) + "\n\n"


_pi_execution_service: PiExecutionService | None = None


def _get_pi_execution_service() -> PiExecutionService:
    global _pi_execution_service
    if _pi_execution_service is None:
        _pi_execution_service = PiExecutionService()
    return _pi_execution_service


def _get_agentic_dispatcher() -> AgenticDispatcher:
    """Dispatcher bound to THIS route's Pi service (W2 single entry point).

    Built per call so tests rebinding ``_pi_execution_service`` (and any future
    reconfiguration) always dispatch through the current service instance.
    """
    return AgenticDispatcher(pi_service=_get_pi_execution_service())


def _engine_choice_from_value(value: str | None) -> str:
    """Map a persisted or header engine value onto the dispatcher vocabulary."""
    return "pi" if str(value or "").strip().lower() in PI_ENGINE_VALUES else "legacy"


async def _resolve_chat_engine(http_request: Request, project_id: str, db: AsyncSession) -> str:
    """Resolve the agentic core for one chat turn (CF-SPEC-1 ITEM-001).

    Resolution order mirrors ``AgenticDispatcher.resolve_engine`` so the UI's
    persisted choice and per-request overrides actually route chat turns:

      1. operator opt-in flag ``settings.pi_replacement_enabled``
      2. request header ``x-istara-agent-engine`` (per-request override;
         recognized Pi values select Pi, anything else selects legacy)
      3. project setting ``projects.agentic_engine``
      4. global default ``settings.agentic_engine_default`` ("legacy")
    """
    if settings.pi_replacement_enabled:
        return "pi"
    header_name = (settings.pi_replacement_request_header or "").strip() or "x-istara-agent-engine"
    header_value = ((http_request.headers.get(header_name)) or "").strip().lower()
    if header_value:
        return _engine_choice_from_value(header_value)
    project_engine = await db.scalar(select(Project.agentic_engine).where(Project.id == project_id))
    if str(project_engine or "").strip():
        return _engine_choice_from_value(project_engine)
    return _engine_choice_from_value(getattr(settings, "agentic_engine_default", "legacy"))


def _provider_stub_chat_blocked_events() -> str:
    """SSE error event for deployments whose provider plane is a wire stub.

    The QA contract stack and the connectivity-acceptance VPS stack declare
    their Ollama-compatible plane as a deterministic stub. Interactive chat
    must fail closed with an actionable error instead of streaming canned
    ``qa-contract-response`` text as if it were a model reply.
    """
    return (
        "data: "
        + json.dumps(
            {
                "type": "error",
                "code": "provider_stub_chat_blocked",
                "message": (
                    "Chat is unavailable: this deployment's model provider is a "
                    "QA contract stub, not a real model. Configure a live provider "
                    "host (OLLAMA_HOST) or select the Pi core with a configured "
                    "endpoint."
                ),
            }
        )
        + "\n\n"
    )


async def _generate_pi_runtime(
    messages: list[dict],
    all_text_parts: list[str],
    tool_results: list[dict],
    request,
    session_agent_id: str | None,
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    thinking_mode: str | None = None,
    endpoint_id: str | None = None,
    turn_status: dict | None = None,
):
    """Drive one chat turn through the AgenticDispatcher's Pi engine (AC-1).

    The already-composed system prompt (with protected research/promotion
    blocks) and prior turns are sent to the worker; the real pi-agent-core
    Agent owns turn progression and every tool call executes in Python under
    the authenticated project/agent scope. Yields the existing SSE envelope
    events and mutates *all_text_parts* / *tool_results* in place so the shared
    persistence block is unchanged. Any runtime failure fails closed with a
    typed error — the legacy Python ReAct loop is never entered. The terminal
    status (``success``/``error``) is reported through *turn_status* so the
    caller can skip persistence for a failed turn (fail-closed, H-9).
    """
    agent_id = session_agent_id or "istara-main"
    system_prompt = ""
    body = list(messages or [])
    if body and body[0].get("role") == "system":
        system_prompt = str(body[0].get("content") or "")
        body = body[1:]
    user_text = ""
    history: list[dict] = []
    if body:
        user_text = str(body[-1].get("content") or "")
        for m in body[:-1]:
            if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str):
                history.append({"role": m["role"], "content": m["content"]})

    metrics = PiChatRunMetrics(project_id=request.project_id, agent_id=agent_id)
    metrics.observe_input(messages)
    session_key = f"{request.project_id}:{getattr(request, 'session_id', None) or 'adhoc'}"

    async def _tool_exec(name, params, project_id, agent):
        # Authority round-trip: authenticated project/agent scope is re-injected.
        result = await execute_tool(name, params, project_id, agent_id=agent)
        metrics.observe_tool_call()
        if isinstance(result, dict):
            result_text = result.get("result", result.get("error", ""))
        else:
            result_text = result
        tool_results.append({"tool": name, "result": result_text})
        return result

    status = "success"
    error_message: str | None = None
    service = _get_pi_execution_service()
    # Bind this live Pi chat turn to the project-scoped steering queue so a user's
    # steer / follow-up / abort (via the /steering routes) reaches the real Agent
    # mid-turn. Only Pi-selected turns reach here, so non-Pi chat is unchanged.
    steering = service.steering_binding(agent_id=agent_id, project_id=request.project_id)
    try:
        async for event in stream_chat_turn(
            _get_agentic_dispatcher(),
            project_id=request.project_id,
            agent_id=agent_id,
            session_key=session_key,
            session_id=getattr(request, "session_id", None),
            system_prompt=system_prompt,
            messages=history,
            user_text=user_text,
            tool_executor=_tool_exec,
            params=TurnParams(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                # Pi's worker receives the provider's exact effort level. The
                # legacy server_default sentinel must not be sent as a level.
                thinking_mode=(thinking_mode if thinking_mode not in {None, "", "server_default"} else None),
                endpoint_id=endpoint_id,
                max_turns=MAX_TOOL_ITERATIONS,
            ),
            steering_binding=steering,
            engine="pi",
        ):
            etype = event["type"]
            if etype == "content":
                text = event.get("text", "")
                if text:
                    all_text_parts.append(text)
                    metrics.observe_chunk(text)
                    yield "data: " + json.dumps({"type": "chunk", "content": text}) + "\n\n"
            elif etype == "tool_call":
                yield "data: " + json.dumps(
                    {"type": "tool_call", "tool": event.get("tool"), "params": event.get("params", {})}
                ) + "\n\n"
            elif etype == "error":
                status = "error"
                error_message = event.get("error")
                yield "data: " + json.dumps(
                    {
                        "type": "error",
                        "code": "pi_runtime_error",
                        "error": "pi_runtime_error",
                        "detail": str(error_message),
                    }
                ) + "\n\n"
            elif etype == "_complete":
                result = event.get("result")
                if result is not None:
                    yield "data: " + json.dumps({
                        "type": "usage",
                        "usage": result.usage or {},
                        "model": result.model or model or "",
                        "endpoint_id": result.endpoint_id,
                        "stop_reason": result.stop_reason,
                        "effort": thinking_mode or "server_default",
                    }) + "\n\n"
                if result is not None and result.status != "success" and status == "success":
                    # Terminal abort/error without a streamed error event still
                    # fails closed (H-9): no assistant message is persisted.
                    status = "error"
                    error_message = error_message or f"pi_turn_{result.status}"
    except Exception as exc:  # fail closed, never fall through
        status = "error"
        error_message = str(exc)
        _chat_log.warning("Pi runtime chat turn failed: %s", exc)
        yield "data: " + json.dumps(
            {
                "type": "error",
                "code": "pi_registration_unavailable",
                "error": "pi_transport_unavailable",
                "detail": str(exc),
            }
        ) + "\n\n"
    finally:
        if turn_status is not None:
            turn_status["status"] = status
        try:
            await metrics.finish(status=status, error_message=error_message)
        except Exception:
            pass


def _research_spine_chat_contract() -> str:
    """Protected runtime policy that prevents chat/RAG from bypassing gates."""
    return protected_block(
        "promotion_gate",
        {
            "pipeline": RESEARCH_VALIDITY_CONTRACT["pipeline"],
            "chat_policy": [
                "Chat may discuss provisional findings only when clearly labeled provisional.",
                "Do not present raw model output, RAG snippets, memories, or tool output as accepted research.",
                "Accepted research requires source-grounded evidence units, independent coding, reliability/reconciliation, and human-approved Done tasks.",
                "Reports and report-like recommendations must use accepted/reconciled evidence only.",
            ],
        },
    )


# ── Text-based fallback (kept for models without native tool support) ──

_TOOL_CALL_RE = re.compile(
    r'```(?:json)?\s*(\{\s*"tool"\s*:.+?\})\s*```',
    re.DOTALL,
)
_TOOL_CALL_INLINE_RE = re.compile(
    r'(\{\s*"tool"\s*:\s*"[a-z_]+".*?\})',
    re.DOTALL,
)


def _extract_tool_call(text: str) -> tuple[dict | None, str, str]:
    """Extract a tool call from LLM output text (regex fallback).

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


async def _generate_native_tools(
    conversation: list[dict],
    all_text_parts: list[str],
    tool_results: list[dict],
    request,
    session_agent_id: str | None,
    llm_model: str | None,
    llm_temperature: float,
    llm_max_tokens: int | None,
    *,
    pi_candidate: bool = False,
):
    """Native tool-calling loop via the AgenticDispatcher (W2).

    The legacy ReAct loop (streaming ``ollama.chat_stream`` turns, tool
    execution, hallucinated-tool filtering) now lives in the dispatcher's
    legacy executor; this generator translates its stream events into the
    existing SSE envelope. Provider chunks stream per token, so the wire
    content is unchanged while chunking is finer than the old per-turn chunk.
    """
    pi_metrics = PiChatRunMetrics(
        project_id=request.project_id,
        agent_id=session_agent_id,
    ) if pi_candidate else None
    effective_model = llm_model
    if pi_candidate:
        registered, registration_status = ensure_pi_deepseek_registered()
        effective_model = pi_chat_model(llm_model)
        if pi_metrics:
            pi_metrics.registration_status = registration_status
            pi_metrics.observe_input(conversation)
        if not registered:
            async for event in _pi_registration_failure_events(
                project_id=request.project_id,
                agent_id=session_agent_id,
                registration_status=registration_status,
            ):
                yield event
            return

    queue: asyncio.Queue = asyncio.Queue()

    async def _tool_exec(name, params, project_id, agent):
        tool_started = datetime.now(timezone.utc)
        result = await execute_tool(name, params, project_id, agent_id=agent)
        if pi_metrics:
            pi_metrics.observe_tool_call()
        if pi_candidate:
            tool_duration_ms = (
                datetime.now(timezone.utc) - tool_started
            ).total_seconds() * 1000
            await record_pi_span(
                operation="pi_candidate_tool_call",
                project_id=request.project_id,
                agent_id=session_agent_id or "istara-main",
                tool_name=name,
                tool_success="error" not in result,
                duration_ms=tool_duration_ms,
            )
        if isinstance(result, dict):
            result_text = result.get("result", result.get("error", "Unknown result"))
        else:
            result_text = str(result)
        tool_results.append({"tool": name, "result": result_text})
        # Stream tool result notification to client (persisted, like before).
        # NOTE (F-W2-R1-1): do NOT append to all_text_parts here. The queued
        # content event below is drained by the main SSE loop, which appends it
        # to all_text_parts once, in stream order. A direct append here would
        # duplicate and (racing the async queue drain) misorder every
        # tool-result block in the persisted assistant transcript.
        result_display = f"**{name}**: {result_text}\n\n"
        await queue.put({"type": "content", "text": result_display})
        return result

    try:
        async for event in stream_chat_turn(
            _get_agentic_dispatcher(),
            queue=queue,
            project_id=request.project_id,
            agent_id=session_agent_id or "istara-main",
            session_id=getattr(request, "session_id", None),
            session_key=None,
            system_prompt="",
            messages=list(conversation),
            user_text="",
            tool_executor=_tool_exec,
            tool_names=[t["function"]["name"] for t in OPENAI_TOOLS],
            tools=OPENAI_TOOLS,
            params=TurnParams(
                model=effective_model,
                temperature=llm_temperature,
                max_tokens=llm_max_tokens,
                max_turns=MAX_TOOL_ITERATIONS,
                stream_tokens=True,
                strict_model_routing=True if pi_candidate else None,
            ),
            engine="legacy",
        ):
            etype = event["type"]
            if etype == "content":
                text = event.get("text", "")
                all_text_parts.append(text)
                if pi_metrics:
                    pi_metrics.observe_chunk(text)
                yield f"data: {json.dumps({'type': 'chunk', 'content': text})}\n\n"
            elif etype == "turn_separator":
                yield f"data: {json.dumps({'type': 'chunk', 'content': event.get('text', '')})}\n\n"
            elif etype == "tool_call":
                yield f"data: {json.dumps({'type': 'tool_call', 'tool': event.get('tool'), 'params': event.get('params', {})})}\n\n"
            elif etype == "_complete":
                result = event.get("result")
                if result is not None:
                    yield "data: " + json.dumps({
                        "type": "usage",
                        "usage": result.usage or {},
                        "model": effective_model or "",
                        "endpoint_id": result.endpoint_id,
                        "stop_reason": result.stop_reason,
                        "effort": "server_default",
                    }) + "\n\n"
    except Exception as exc:
        if pi_metrics:
            await pi_metrics.finish(status="error", error_message=str(exc))
        raise
    else:
        if pi_metrics:
            await pi_metrics.finish()


async def _generate_text_fallback(
    conversation: list[dict],
    all_text_parts: list[str],
    tool_results: list[dict],
    request,
    session_agent_id: str | None,
    llm_model: str | None,
    llm_temperature: float,
    llm_max_tokens: int | None,
    *,
    pi_candidate: bool = False,
):
    """Legacy text-based tool parsing loop via the AgenticDispatcher (W2).

    The regex-parsed ReAct loop (chat.py's ``_extract_tool_call`` contract,
    ``[Tool: ...]`` conversation shaping) runs inside the dispatcher's legacy
    executor; this generator translates its stream events into the existing
    SSE envelope. Raw tokens never stream per token here — a turn's text may
    carry the machine-readable tool block, so text events arrive per turn.
    """
    pi_metrics = PiChatRunMetrics(
        project_id=request.project_id,
        agent_id=session_agent_id,
    ) if pi_candidate else None
    if pi_candidate:
        registered, registration_status = ensure_pi_deepseek_registered()
        if pi_metrics:
            pi_metrics.registration_status = registration_status
            pi_metrics.observe_input(conversation)
        if not registered:
            async for event in _pi_registration_failure_events(
                project_id=request.project_id,
                agent_id=session_agent_id,
                registration_status=registration_status,
            ):
                yield event
            return

    queue: asyncio.Queue = asyncio.Queue()

    async def _tool_exec(name, params, project_id, agent):
        result = await execute_tool(name, params, project_id, agent_id=agent)
        if pi_metrics:
            pi_metrics.observe_tool_call()
        if isinstance(result, dict):
            result_text = result.get("result", result.get("error", "Unknown result"))
        else:
            result_text = str(result)
        tool_results.append({"tool": name, "result": result_text})
        # NOTE (F-W2-R1-1): rely solely on the queued content event; the main
        # SSE loop appends it to all_text_parts once, in stream order. A direct
        # append here would duplicate and misorder the persisted tool-result
        # block.
        result_display = f"**{name}**: {result_text}\n\n"
        await queue.put({"type": "content", "text": result_display})
        return result

    try:
        async for event in stream_chat_turn(
            _get_agentic_dispatcher(),
            queue=queue,
            project_id=request.project_id,
            agent_id=session_agent_id or "istara-main",
            session_id=getattr(request, "session_id", None),
            session_key=None,
            system_prompt="",
            messages=list(conversation),
            user_text="",
            tool_executor=_tool_exec,
            params=TurnParams(
                model=pi_chat_model(llm_model) if pi_candidate else llm_model,
                temperature=llm_temperature,
                max_tokens=llm_max_tokens,
                max_turns=MAX_TOOL_ITERATIONS,
                text_fallback=True,
                strict_model_routing=True if pi_candidate else None,
                tool_call_extractor=_extract_tool_call,
            ),
            engine="legacy",
        ):
            etype = event["type"]
            if etype == "content":
                text = event.get("text", "")
                all_text_parts.append(text)
                if pi_metrics:
                    pi_metrics.observe_chunk(text)
                yield f"data: {json.dumps({'type': 'chunk', 'content': text})}\n\n"
            elif etype == "tool_call":
                yield f"data: {json.dumps({'type': 'tool_call', 'tool': event.get('tool'), 'params': event.get('params', {})})}\n\n"
            elif etype == "_complete":
                result = event.get("result")
                if result is not None:
                    yield "data: " + json.dumps({
                        "type": "usage",
                        "usage": result.usage or {},
                        "model": (pi_chat_model(llm_model) if pi_candidate else llm_model) or "",
                        "endpoint_id": result.endpoint_id,
                        "stop_reason": result.stop_reason,
                        "effort": "server_default",
                    }) + "\n\n"
    except Exception as exc:
        if pi_metrics:
            await pi_metrics.finish(status="error", error_message=str(exc))
        raise
    else:
        if pi_metrics:
            await pi_metrics.finish()


class ChatRequest(BaseModel):
    """Chat request body."""

    message: str = Field(..., min_length=1, max_length=20000)
    project_id: str = Field(..., min_length=1, max_length=36)
    session_id: str | None = None
    include_history: bool = True
    max_history: int = Field(default=20, ge=0, le=200)
    thinking_mode: str | None = None

    @field_validator("thinking_mode")
    @classmethod
    def validate_effort(cls, value: str | None) -> str | None:
        return validate_model_effort(value) if value is not None else value

    @field_validator("message")
    @classmethod
    def normalize_message(cls, value: str) -> str:
        message = value.strip()
        if not message:
            raise ValueError("Message cannot be blank")
        return message


class ChatMessage(BaseModel):
    """Chat message response."""

    id: str
    role: str
    content: str
    created_at: datetime


@router.post("/chat")
async def chat(request: ChatRequest, http_request: Request, db: AsyncSession = Depends(get_db)):
    """Send a message and get a streaming response with RAG augmentation.

    The response is streamed as Server-Sent Events (SSE).
    """
    project = await get_visible_project_or_404(
        db,
        http_request,
        request.project_id,
        min_role="researcher",
    )

    # Fail closed BEFORE ANY side effect (session/message persistence, RAG):
    # a deployment that declared its provider plane as a QA wire stub must not
    # serve legacy-plane chat turns at all. The Pi plane is exempt — it talks
    # to configured cloud endpoints (e.g. DeepSeek), never to the local stub.
    resolved_engine = await _resolve_chat_engine(http_request, request.project_id, db)
    if getattr(settings, "llm_provider_contract_stub", False) and resolved_engine != "pi":
        _chat_log.warning(
            "Chat rejected on stub provider plane (project=%s, engine=%s)",
            request.project_id,
            resolved_engine,
        )
        return StreamingResponse(
            iter([_provider_stub_chat_blocked_events()]),
            media_type="text/event-stream",
            headers={
                # Same SSE headers as the main stream so intermediaries
                # (Caddy on the VPS path) never buffer the error frame.
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Resolve or create the chat session before writing messages. A caller may
    # only use sessions that belong to the requested project and chat surface.
    session: ChatSession | None = None
    if request.session_id:
        sess_result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == request.session_id,
                ChatSession.project_id == request.project_id,
                ChatSession.session_type == "chat",
            )
        )
        session = sess_result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = ChatSession(
            id=str(uuid.uuid4()),
            project_id=request.project_id,
            title=f"Chat — {request.message[:50].replace(chr(10), ' ').strip()}",
            message_count=0,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        request.session_id = session.id

    # Save user message
    user_created_at = datetime.now(timezone.utc)
    user_msg = Message(
        id=str(uuid.uuid4()),
        project_id=request.project_id,
        session_id=request.session_id,
        role="user",
        content=request.message,
        created_at=user_created_at,
    )
    db.add(user_msg)
    await db.commit()

    # --- Content Guard: scan user message for injection attempts ---
    user_scan = _guard.scan_text(request.message)
    if user_scan.threat_level in ("medium", "high"):
        _chat_log.warning(
            "Content guard flagged user message: %s - %s",
            user_scan.threat_level,
            user_scan.threats,
        )

    # --- Resolve session-specific inference settings ---
    llm_temperature = 0.7
    llm_max_tokens: int | None = None
    llm_model: str | None = None
    llm_endpoint_id: str | None = None
    llm_effort = request.thinking_mode
    llm_thinking_mode = normalize_thinking_mode(request.thinking_mode)
    session_agent_id: str | None = None
    agent_identity_prompt: str = ""

    if session:
        preset_value = session.inference_preset
        preset_key = (
            preset_value.value if hasattr(preset_value, "value") else str(preset_value or "medium")
        )
        if preset_key not in INFERENCE_PRESETS:
            preset_key = "medium"
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
        if getattr(session, "endpoint_override", None):
            llm_endpoint_id = session.endpoint_override
        if request.thinking_mode is None:
            llm_effort = getattr(session, "thinking_mode", None)
            llm_thinking_mode = normalize_thinking_mode(llm_effort)

        # Load agent identity for this session
        # Use Prompt RAG for query-aware identity (retrieves relevant
        # persona sections based on the user's message)
        session_agent_id = session.agent_id
        if session_agent_id:
            assigned_agent = await require_agent_assignable_to_project(
                db,
                http_request,
                session_agent_id,
                request.project_id,
                min_role="viewer",
            )
            session_agent_id = assigned_agent.id if assigned_agent else None
            try:
                agent_identity_prompt = await compose_dynamic_prompt(
                    session_agent_id,
                    query=request.message,
                    use_embeddings=True,
                    project_id=request.project_id,
                )
            except Exception:
                # Fall back to full identity load
                agent_identity_prompt = load_agent_identity(session_agent_id)

            if agent_identity_prompt:
                _chat_log.info(
                    f"Loaded agent identity for {session_agent_id} "
                    f"({len(agent_identity_prompt)} chars, prompt-rag)"
                )
            else:
                # Fallback: load system_prompt from DB agent record
                if assigned_agent and assigned_agent.system_prompt:
                    agent_identity_prompt = assigned_agent.system_prompt

        # Update session message count and last_message_at
        session.message_count = (session.message_count or 0) + 1
        session.last_message_at = user_created_at
        await db.commit()

    # If no agent identity loaded yet, default to istara-main
    if not agent_identity_prompt:
        try:
            agent_identity_prompt = await compose_dynamic_prompt(
                "istara-main",
                query=request.message,
                use_embeddings=True,
                project_id=request.project_id,
            )
        except Exception:
            agent_identity_prompt = load_agent_identity("istara-main")

    # Retrieve context via RAG
    rag_result = await retrieve_context(request.project_id, request.message)

    # Budget-aware pipeline: allocate tokens based on detected context window
    from app.core.budget_coordinator import budget_coordinator, compute_surplus_level
    from app.core.prompt_compressor import (
        compress_rag_chunks,
        record_protected_compression_telemetry,
    )

    budget = budget_coordinator.allocate(settings.max_context_tokens)
    surplus = compute_surplus_level()

    # Re-compose agent identity with budget-aware token limit
    if session_agent_id and agent_identity_prompt:
        try:
            agent_identity_prompt = await compose_dynamic_prompt(
                session_agent_id,
                query=request.message,
                max_tokens=budget.identity_tokens,
                use_embeddings=True,
                project_id=request.project_id,
            )
        except Exception:
            pass  # Keep the previously loaded identity

    # Compress RAG chunks with question-aware scoring within budget
    rag_context = ""
    if rag_result and rag_result.retrieved:
        chunk_texts = [r.text for r in rag_result.retrieved if r.text]
        compressed_chunks, _ = compress_rag_chunks(
            chunk_texts, request.message, budget.rag_tokens, surplus
        )
        await record_protected_compression_telemetry(
            project_id=request.project_id,
            original_chunks=chunk_texts,
            compressed_chunks=compressed_chunks,
        )
        rag_context = "\n---\n".join(compressed_chunks) if compressed_chunks else ""

    # Build system prompt with context layers + agent identity
    system_prompt = build_augmented_prompt(
        query=request.message,
        rag_context=rag_context,
        project_context=project.project_context or None,
        company_context=project.company_context or None,
    )

    # Inject agent identity at the top of the system prompt
    if agent_identity_prompt:
        system_prompt = agent_identity_prompt + "\n\n---\n\n" + system_prompt
    system_prompt += "\n\n" + _research_spine_chat_contract()

    # Native tool calling: tools are passed via the `tools` API parameter.
    # The text-based tools prompt is only injected as a fallback (see below).
    use_native_tools = True  # Will be flipped to False on API rejection

    # Inject project folder file awareness
    folder = _resolve_project_folder(project, request.project_id)
    if folder.exists():
        project_files = [
            f.name for f in folder.iterdir() if f.is_file() and not f.name.startswith(".")
        ]
        if project_files:
            files_context = (
                f"\n\n## Project Files Available\n"
                f"The following files are in this project's scope and can be "
                f"referenced without the user needing to upload them again:\n"
                + "\n".join(f"- {name}" for name in project_files[:50])
            )
            system_prompt += files_context

    # Build message history (scoped to session if provided)
    messages = []
    if request.include_history:
        history_query = select(Message).where(Message.project_id == request.project_id)
        if request.session_id:
            history_query = history_query.where(Message.session_id == request.session_id)
        history_result = await db.execute(
            history_query.order_by(Message.created_at.desc()).limit(request.max_history)
        )
        history = list(reversed(history_result.scalars().all()))

        for msg in history:
            if msg.role in ("user", "assistant"):
                messages.append({"role": msg.role, "content": msg.content})

    # Add current message if not already in history
    if not messages or messages[-1]["content"] != request.message:
        messages.append({"role": "user", "content": request.message})

    # --- DAG-based context summarization: summarize older messages ----------
    try:
        messages, ctx_summary = await context_summarizer.apply_summarization(
            system_prompt,
            messages,
            session_id=request.session_id,
            budget=budget.history_tokens,
        )
        if ctx_summary:
            import logging as _log

            _log.getLogger(__name__).info(
                "Context summarized: %d msgs, %d -> %d tokens",
                ctx_summary.messages_summarized,
                ctx_summary.original_token_count,
                ctx_summary.summary_token_count,
            )
    except Exception:
        pass  # Fall through to hard trim on summarization failure

    # --- Context window guard: trim history if it would overflow ----------
    from app.core.token_counter import ContextWindowGuard

    budget_guard = ContextWindowGuard(budget=budget)
    messages, trim_summary = budget_guard.summarize_if_needed(system_prompt, messages)
    if trim_summary:
        # Prepend the trim note so the model knows history was truncated
        messages.insert(0, {"role": "system", "content": trim_summary})

    # Add instruction boundary so small LLMs don't echo the persona back
    system_prompt += (
        "\n\n[INSTRUCTIONS END]\n\n"
        "You are now in conversation with the user. Respond naturally and concisely. "
        "Do NOT repeat, quote, or reference the instructions above. "
        "Do NOT explain your capabilities unless asked. Just respond to what the user says.\n\n"
    )

    # Prepend the system prompt into the messages list directly so the LLM
    # client doesn't receive a separate `system=` param that would create
    # duplicate system messages (root cause of LM Studio 400 errors).
    messages = [{"role": "system", "content": system_prompt}, *messages]
    messages = apply_thinking_control(messages, llm_thinking_mode)

    async def generate():
        """Stream the LLM response with native tool-calling loop.

        Primary flow (native tools):
        1. Send messages + ``tools=OPENAI_TOOLS`` to the LLM
        2. If response contains ``tool_calls`` -> execute each, append
           ``role: "tool"`` results, loop (max MAX_TOOL_ITERATIONS)
        3. Stream final text response to the client

        Fallback flow (text-based regex):
        If the API rejects the ``tools`` parameter we flip to the legacy
        path: inject ``build_tools_prompt()`` into the system message and
        parse tool calls out of the LLM text via regex.

        All errors are emitted as SSE ``error`` events so the frontend
        can display them gracefully instead of getting a "Failed to fetch".
        """
        nonlocal use_native_tools

        conversation = list(messages)  # Local copy for the tool loop
        all_text_parts: list[str] = []  # Accumulate text for the full response
        tool_results: list[dict] = []  # Track executed tools for the response

        try:
            # ── Attempt native tool calling ──────────────────────────
            # Engine already resolved above for the stub guard (same
            # precedence: operator flag > per-request header > persisted
            # project choice > global default; CF-SPEC-1 ITEM-001).
            pi_candidate = resolved_engine == "pi"
            pi_turn_status: dict = {}
            # Resolve the opt-in target before choosing either tool-loop transport.
            # A missing Keychain registration is terminal: falling back would silently
            # route a Pi-selected request through the default provider.
            if pi_candidate:
                registered, registration_status = ensure_pi_deepseek_registered()
                if not registered:
                    async for event in _pi_registration_failure_events(
                        project_id=request.project_id,
                        agent_id=session_agent_id,
                        registration_status=registration_status,
                    ):
                        yield event
                    return
                # Registration OK → the real Pi Agent Core owns this turn. The
                # legacy Python ReAct loop (_generate_native_tools /
                # _generate_text_fallback) is never entered for a selected Pi
                # request (AC-1). Non-Pi requests are byte-identical (AC-2).
                async for event in _generate_pi_runtime(
                    messages,
                    all_text_parts,
                    tool_results,
                    request,
                    session_agent_id,
                    model=llm_model,
                    temperature=llm_temperature,
                    max_tokens=llm_max_tokens,
                    thinking_mode=llm_effort,
                    endpoint_id=llm_endpoint_id,
                    turn_status=pi_turn_status,
                ):
                    yield event
            elif use_native_tools:
                try:
                    async for event in _generate_native_tools(
                        conversation,
                        all_text_parts,
                        tool_results,
                        request,
                        session_agent_id,
                        llm_model,
                        llm_temperature,
                        llm_max_tokens,
                        pi_candidate=pi_candidate,
                    ):
                        yield event
                except Exception as native_err:
                    # If the API rejected the tools param (400/422), fall back
                    err_str = str(native_err).lower()
                    if any(
                        k in err_str
                        for k in (
                            "tools",
                            "400",
                            "422",
                            "unprocessable",
                            "not supported",
                            "no compute nodes available",
                        )
                    ):
                        _chat_log.warning(
                            "Native tool calling rejected, falling back to text-based: %s",
                            native_err,
                        )
                        use_native_tools = False
                        all_text_parts.clear()
                        tool_results.clear()
                        conversation = list(messages)
                    else:
                        raise

                # If native tools produced no text at all, the model may be
                # too small to handle tools+system prompt. Fall back.
                full_text = "".join(all_text_parts).strip()
                if use_native_tools and not full_text and not tool_results:
                    _chat_log.warning(
                        "Native tool calling produced empty response — "
                        "model may be too small. Falling back to text-based."
                    )
                    use_native_tools = False
                    all_text_parts.clear()
                    conversation = list(messages)

            # ── Fallback: text-based tool parsing ────────────────────
            if not use_native_tools:
                # Inject tools prompt into the system message
                tools_prompt = build_tools_prompt()
                if conversation and conversation[0]["role"] == "system":
                    conversation[0]["content"] += "\n\n" + tools_prompt
                else:
                    conversation.insert(0, {"role": "system", "content": tools_prompt})

                async for event in _generate_text_fallback(
                    conversation,
                    all_text_parts,
                    tool_results,
                    request,
                    session_agent_id,
                    llm_model,
                    llm_temperature,
                    llm_max_tokens,
                    pi_candidate=pi_candidate,
                ):
                    yield event

            # ── Save the full assistant response ─────────────────────
            if pi_candidate and pi_turn_status.get("status") != "success":
                # Fail closed (H-9): a failed Pi turn must NOT persist an
                # assistant message built from a failed or partially-streamed
                # turn — the transcript would otherwise record a false-success
                # reply. Terminate the stream like a registration failure.
                _chat_log.warning(
                    "Pi chat turn failed (%s) — no assistant message persisted",
                    pi_turn_status.get("status"),
                )
                yield "data: " + json.dumps(
                    {"type": "done", "message_id": None, "sources": [], "tools_used": []}
                ) + "\n\n"
                return
            async with async_session() as save_db:
                assistant_content = "".join(all_text_parts)
                assistant_created_at = datetime.now(timezone.utc)
                assistant_msg = Message(
                    id=str(uuid.uuid4()),
                    project_id=request.project_id,
                    session_id=request.session_id,
                    role="assistant",
                    content=assistant_content,
                    created_at=assistant_created_at,
                )
                save_db.add(assistant_msg)
                if request.session_id:
                    session_result = await save_db.execute(
                        select(ChatSession).where(
                            ChatSession.id == request.session_id,
                            ChatSession.project_id == request.project_id,
                        )
                    )
                    saved_session = session_result.scalar_one_or_none()
                    if saved_session:
                        saved_session.message_count = (saved_session.message_count or 0) + 1
                        saved_session.last_message_at = assistant_created_at
                await save_db.commit()

                # Trigger DAG compaction asynchronously
                if settings.dag_enabled and request.session_id:
                    try:
                        from app.core.context_dag import context_dag
                        import asyncio as _asyncio

                        _asyncio.create_task(context_dag.compact_if_needed(request.session_id))
                    except Exception:
                        pass

                sources = (
                    [
                        {"source": r.source, "score": r.score, "page": r.page}
                        for r in rag_result.retrieved
                    ]
                    if rag_result and rag_result.retrieved
                    else []
                )
                done_data = json.dumps(
                    {
                        "type": "done",
                        "message_id": assistant_msg.id,
                        "sources": sources,
                        "tools_used": [t["tool"] for t in tool_results] if tool_results else [],
                    }
                )
                yield f"data: {done_data}\n\n"

        except GeneratorExit:
            # Client disconnected mid-stream — save what we have
            if all_text_parts:
                try:
                    async with async_session() as save_db:
                        interrupted_created_at = datetime.now(timezone.utc)
                        msg = Message(
                            id=str(uuid.uuid4()),
                            project_id=request.project_id,
                            session_id=request.session_id,
                            role="assistant",
                            content="".join(all_text_parts) + "\n\n[Response interrupted]",
                            created_at=interrupted_created_at,
                        )
                        save_db.add(msg)
                        if request.session_id:
                            session_result = await save_db.execute(
                                select(ChatSession).where(
                                    ChatSession.id == request.session_id,
                                    ChatSession.project_id == request.project_id,
                                )
                            )
                            saved_session = session_result.scalar_one_or_none()
                            if saved_session:
                                saved_session.message_count = (
                                    saved_session.message_count or 0
                                ) + 1
                                saved_session.last_message_at = interrupted_created_at
                        await save_db.commit()
                except Exception:
                    pass
        except Exception as e:
            error_data = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {error_data}\n\n"

    async def safe_generate():
        """Wrapper that ensures all errors are emitted as SSE events."""
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


@router.get("/chat/model-catalog")
async def get_chat_model_catalog(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Project-readable model metadata for the in-chat model picker.

    The catalog contains no secrets. ``configured`` is the identity-only Pi
    endpoint view; the frontend keeps unconfigured catalog entries visible but
    disabled so users understand what Settings must enable.
    """
    await require_project_access(db, request, project_id, min_role="viewer")
    from dataclasses import asdict

    from app.core.pi_runtime.catalog import pi_catalog_json
    from app.core.pi_runtime.model_manager import PiModelManager

    configured: list[dict] = []
    try:
        manager = PiModelManager()
        await manager.ensure_db_projection()
        configured = [asdict(info) for info in manager.catalog()]
    except Exception:
        _chat_log.debug("chat model catalog configured projection unavailable", exc_info=True)
    legacy_models: list[str] = []
    try:
        from app.core.compute_registry import compute_registry

        legacy_models = sorted({
            str(item.get("name") or item.get("model") or "").strip()
            for item in await compute_registry.list_models()
            if str(item.get("name") or item.get("model") or "").strip()
        })
    except Exception:
        _chat_log.debug("chat legacy model inventory unavailable", exc_info=True)
    for configured_model in (settings.ollama_model, settings.lmstudio_model):
        if configured_model and configured_model != "default" and configured_model not in legacy_models:
            legacy_models.append(configured_model)
    catalog = pi_catalog_json()
    project_engine = await db.scalar(select(Project.agentic_engine).where(Project.id == project_id))
    from app.core.pi_replacement import PI_ENGINE_VALUES

    configured_engine = str(project_engine or getattr(settings, "agentic_engine_default", "legacy")).strip().lower()
    engine = "pi" if configured_engine in PI_ENGINE_VALUES else "legacy"
    return {
        "providers": catalog,
        "total_models": sum(len(provider["models"]) for provider in catalog),
        "configured": configured,
        "legacy_models": legacy_models,
        "engine": engine,
    }


@router.get("/chat/usage/{project_id}")
async def get_chat_usage(
    project_id: str,
    request: Request,
    session_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Return content-free exact/estimated usage totals for the chat menu."""
    await require_project_access(db, request, project_id, min_role="viewer")
    from app.models.agentic_usage import AgenticUsageRow

    query = select(AgenticUsageRow).where(AgenticUsageRow.project_id == project_id)
    if session_id:
        query = query.where(AgenticUsageRow.session_id == session_id)
    result = await db.execute(query.order_by(AgenticUsageRow.created_at.asc()))
    rows = list(result.scalars().all())
    totals = {
        "input_tokens": sum(int(row.input_tokens or 0) for row in rows),
        "output_tokens": sum(int(row.output_tokens or 0) for row in rows),
        "cache_read": sum(int(row.cache_read or 0) for row in rows),
        "cache_write": sum(int(row.cache_write or 0) for row in rows),
        "total_tokens": sum(int(row.total_tokens or 0) for row in rows),
        "cost_usd": sum(float(row.cost_usd or 0) for row in rows),
        "turns": sum(int(row.turns or 0) for row in rows),
    }
    latest = rows[-1] if rows else None
    return {
        **totals,
        "row_count": len(rows),
        "exact": not any(bool(row.estimate) for row in rows),
        "estimated": any(bool(row.estimate) for row in rows),
        "latest": {
            "model": latest.model,
            "endpoint_id": latest.endpoint_id,
            "engine": latest.engine,
            "stop_reason": latest.stop_reason,
            "input_tokens": latest.input_tokens,
            "output_tokens": latest.output_tokens,
            "cache_read": latest.cache_read,
            "cache_write": latest.cache_write,
            "total_tokens": latest.total_tokens,
            "cost_usd": latest.cost_usd,
            "estimate": bool(latest.estimate),
            "created_at": latest.created_at.isoformat() if latest.created_at else None,
        } if latest else None,
    }


@router.get("/chat/history/{project_id}")
async def get_chat_history(
    project_id: str,
    request: Request,
    session_id: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[ChatMessage]:
    """Get chat history for a project, optionally scoped to a session."""
    await require_project_access(db, request, project_id, min_role="viewer")
    query = select(Message).where(Message.project_id == project_id)
    if session_id:
        query = query.where(Message.session_id == session_id)
    result = await db.execute(query.order_by(Message.created_at.asc()).limit(limit))
    messages = result.scalars().all()

    return [
        ChatMessage(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at,
        )
        for msg in messages
    ]


@router.post("/chat/voice")
async def transcribe_voice(
    request: Request,
    audio: UploadFile = File(...),
    project_id: str = Form(...),
    language: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Transcribe voice input from chat mic button.

    Accepts audio files (wav, mp3, ogg, m4a, flac) and returns
    transcribed text with ICR confidence scores.
    """
    scoped_project_id = project_id.strip()
    if not scoped_project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    await get_visible_project_or_404(db, request, scoped_project_id, min_role="researcher")

    try:
        # Save uploaded audio to temp file
        suffix = Path(audio.filename).suffix if audio.filename else ".ogg"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp_path = tmp.name

        # Convert and transcribe
        from app.core.transcription import transcribe_audio, convert_audio_to_wav

        wav_path = convert_audio_to_wav(tmp_path)
        result = transcribe_audio(wav_path, language=language)

        # Clean up temp files
        try:
            Path(tmp_path).unlink(missing_ok=True)
            if wav_path != tmp_path:
                Path(wav_path).unlink(missing_ok=True)
        except Exception:
            pass

        return {
            "text": result.text,
            "language": result.language,
            "confidence": result.confidence,
            "icr_kappa": result.icr_kappa,
            "icr_confidence": result.icr_confidence,
            "needs_review": result.needs_review,
            "tags": result.tags,
        }

    except Exception as e:
        _chat_log.error(f"Voice transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


class VoiceTranscribeRequest(BaseModel):
    project_id: str
    dummy: bool = False

    @field_validator("project_id")
    @classmethod
    def normalize_project_id(cls, value: str) -> str:
        project_id = value.strip()
        if not project_id:
            raise ValueError("project_id is required")
        return project_id


@router.post("/chat/voice-transcribe")
async def voice_transcribe(request: VoiceTranscribeRequest, http_request: Request, db: AsyncSession = Depends(get_db)):
    """Voice transcription endpoint (Phase Alpha)."""
    await get_visible_project_or_404(db, http_request, request.project_id, min_role="researcher")
    if request.dummy:
        return {"status": "success", "text": "Mock transcription"}

    # Real transcription logic would go here
    return {"status": "error", "message": "No audio file provided"}
