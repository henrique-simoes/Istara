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
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.agent import agent
from app.core.agent_identity import load_agent_identity, get_agent_display_name
from app.core.content_guard import ContentGuard
from app.core.prompt_rag import compose_dynamic_prompt, compose_keyword_prompt
from app.core.context_summarizer import context_summarizer
from app.core.ollama import ollama
from app.core.rag import build_augmented_prompt, retrieve_context
from app.core.token_counter import context_guard
from app.models.database import get_db, async_session

_guard = ContentGuard()
from app.models.agent import Agent
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

_chat_log = logging.getLogger(__name__)

router = APIRouter()

# Maximum tool-call iterations per message (prevents infinite loops)
MAX_TOOL_ITERATIONS = 8

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
):
    """Native tool-calling loop using the OpenAI `tools` parameter.

    Yields SSE event strings.  Modifies *conversation*, *all_text_parts*,
    and *tool_results* in place.
    """
    for iteration in range(MAX_TOOL_ITERATIONS + 1):
        # Collect the full response (text + possible tool_calls dict)
        content_chunks: list[str] = []
        tool_calls_payload: dict | None = None

        async for chunk in ollama.chat_stream(
            messages=conversation,
            model=llm_model,
            temperature=llm_temperature,
            max_tokens=llm_max_tokens,
            tools=OPENAI_TOOLS,
        ):
            if isinstance(chunk, dict) and chunk.get("tool_calls"):
                tool_calls_payload = chunk
            elif isinstance(chunk, str):
                content_chunks.append(chunk)

        response_text = "".join(content_chunks)

        # If we got tool_calls AND we haven't exceeded iterations, execute them
        if tool_calls_payload and iteration < MAX_TOOL_ITERATIONS:
            raw_tool_calls = tool_calls_payload["tool_calls"]

            # Filter out hallucinated tool calls (model calls non-existent tools)
            valid_tool_names = {t["function"]["name"] for t in OPENAI_TOOLS}
            real_tool_calls = []
            for tc in raw_tool_calls:
                fn_name = tc.get("function", {}).get("name", "")
                if fn_name in valid_tool_names:
                    real_tool_calls.append(tc)
                else:
                    # Hallucinated tool — extract text from arguments as response
                    _chat_log.info("Hallucinated tool call '%s' — extracting text from arguments", fn_name)
                    try:
                        args = json.loads(tc.get("function", {}).get("arguments", "{}"))
                        # Common patterns: {"text": "..."}, {"content": "..."}, {"response": "..."}
                        extracted = args.get("text", args.get("content", args.get("response", "")))
                        if extracted:
                            response_text += str(extracted)
                    except (json.JSONDecodeError, TypeError):
                        pass

            if not real_tool_calls:
                # All tool calls were hallucinated — treat as final text response
                all_text_parts.append(response_text)
                event_data = json.dumps({"type": "chunk", "content": response_text})
                yield f"data: {event_data}\n\n"
                break

            raw_tool_calls = real_tool_calls

            # Stream any text the model produced before the tool calls
            if response_text.strip():
                all_text_parts.append(response_text)
                event_data = json.dumps({"type": "chunk", "content": response_text + "\n\n"})
                yield f"data: {event_data}\n\n"

            # Build the assistant message with tool_calls for the conversation
            assistant_msg_for_conv: dict = {
                "role": "assistant",
                "content": response_text or "",
                "tool_calls": raw_tool_calls,
            }
            conversation.append(assistant_msg_for_conv)

            # Execute each tool call and add role:"tool" result messages
            for tc in raw_tool_calls:
                tc_id = tc.get("id", str(uuid.uuid4()))
                fn = tc.get("function", {})
                tool_name = fn.get("name", "")
                try:
                    tool_params = json.loads(fn.get("arguments", "{}"))
                except (json.JSONDecodeError, TypeError):
                    tool_params = {}

                _chat_log.info(
                    "Native tool call [%d]: %s(%s)",
                    iteration, tool_name, json.dumps(tool_params)[:200],
                )

                # Notify client about tool execution
                tool_event = json.dumps({
                    "type": "tool_call",
                    "tool": tool_name,
                    "params": tool_params,
                })
                yield f"data: {tool_event}\n\n"

                # Execute the tool
                result = await execute_tool(
                    tool_name, tool_params, request.project_id,
                    agent_id=session_agent_id or "istara-main",
                )

                result_text = result.get("result", result.get("error", "Unknown result"))
                tool_results.append({"tool": tool_name, "result": result_text})

                # Stream tool result notification to client
                result_display = f"**{tool_name}**: {result_text}\n\n"
                all_text_parts.append(result_display)
                result_event = json.dumps({"type": "chunk", "content": result_display})
                yield f"data: {result_event}\n\n"

                # Append role:"tool" message for multi-turn tool use
                conversation.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": str(result_text),
                })

            # Loop back for the model's follow-up
            continue
        else:
            # No tool calls -- final text response
            all_text_parts.append(response_text)
            event_data = json.dumps({"type": "chunk", "content": response_text})
            yield f"data: {event_data}\n\n"
            break


async def _generate_text_fallback(
    conversation: list[dict],
    all_text_parts: list[str],
    tool_results: list[dict],
    request,
    session_agent_id: str | None,
    llm_model: str | None,
    llm_temperature: float,
    llm_max_tokens: int | None,
):
    """Legacy text-based tool parsing loop (regex fallback).

    Yields SSE event strings.  Used when native tool calling is not
    supported by the current model/provider.
    """
    for iteration in range(MAX_TOOL_ITERATIONS + 1):
        full_text: list[str] = []
        async for chunk in ollama.chat_stream(
            messages=conversation,
            model=llm_model,
            temperature=llm_temperature,
            max_tokens=llm_max_tokens,
        ):
            if isinstance(chunk, str):
                full_text.append(chunk)

        response_text = "".join(full_text)
        tool_call, text_before, text_after = _extract_tool_call(response_text)

        if tool_call and iteration < MAX_TOOL_ITERATIONS:
            tool_name = tool_call.get("tool", "")
            tool_params = tool_call.get("params", {})

            _chat_log.info(
                "Text fallback tool call [%d]: %s(%s)",
                iteration, tool_name, json.dumps(tool_params)[:200],
            )

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

            result = await execute_tool(
                tool_name, tool_params, request.project_id,
                agent_id=session_agent_id or "istara-main",
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


class ChatRequest(BaseModel):
    """Chat request body."""

    message: str
    project_id: str
    session_id: str | None = None
    include_history: bool = True
    max_history: int = 20


class ChatMessage(BaseModel):
    """Chat message response."""

    id: str
    role: str
    content: str
    created_at: datetime


@router.post("/chat")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Send a message and get a streaming response with RAG augmentation.

    The response is streamed as Server-Sent Events (SSE).
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
    session_agent_id: str | None = None
    agent_identity_prompt: str = ""

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

            # Load agent identity for this session
            # Use Prompt RAG for query-aware identity (retrieves relevant
            # persona sections based on the user's message)
            session_agent_id = session.agent_id
            if session_agent_id:
                try:
                    agent_identity_prompt = await compose_dynamic_prompt(
                        session_agent_id,
                        query=request.message,
                        use_embeddings=True,
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
                    agent_result = await db.execute(
                        select(Agent).where(Agent.id == session_agent_id)
                    )
                    db_agent = agent_result.scalar_one_or_none()
                    if db_agent and db_agent.system_prompt:
                        agent_identity_prompt = db_agent.system_prompt

            # Update session message count and last_message_at
            session.message_count = (session.message_count or 0) + 1
            session.last_message_at = user_msg.created_at
            await db.commit()

    # If no agent identity loaded yet, default to istara-main
    if not agent_identity_prompt:
        try:
            agent_identity_prompt = await compose_dynamic_prompt(
                "istara-main",
                query=request.message,
                use_embeddings=True,
            )
        except Exception:
            agent_identity_prompt = load_agent_identity("istara-main")

    # Retrieve context via RAG
    rag_context = await retrieve_context(request.project_id, request.message)

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

    # Native tool calling: tools are passed via the `tools` API parameter.
    # The text-based tools prompt is only injected as a fallback (see below).
    use_native_tools = True  # Will be flipped to False on API rejection

    # Inject project folder file awareness
    upload_dir = Path(settings.upload_dir) / request.project_id
    if upload_dir.exists():
        project_files = [
            f.name for f in upload_dir.iterdir()
            if f.is_file() and not f.name.startswith(".")
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
            system_prompt, messages, session_id=request.session_id
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
    messages, trim_summary = context_guard.summarize_if_needed(
        system_prompt, messages
    )
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

        Uses its own DB session to avoid leak when client disconnects.
        """
        nonlocal use_native_tools

        conversation = list(messages)  # Local copy for the tool loop
        all_text_parts: list[str] = []  # Accumulate text for the full response
        tool_results: list[dict] = []   # Track executed tools for the response

        try:
            # ── Attempt native tool calling ──────────────────────────
            if use_native_tools:
                try:
                    async for event in _generate_native_tools(
                        conversation, all_text_parts, tool_results, request,
                        session_agent_id, llm_model, llm_temperature, llm_max_tokens,
                    ):
                        yield event
                except Exception as native_err:
                    # If the API rejected the tools param (400/422), fall back
                    err_str = str(native_err).lower()
                    if any(k in err_str for k in ("tools", "400", "422", "unprocessable", "not supported")):
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
                    conversation, all_text_parts, tool_results, request,
                    session_agent_id, llm_model, llm_temperature, llm_max_tokens,
                ):
                    yield event

            # ── Save the full assistant response ─────────────────────
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

                # Trigger DAG compaction asynchronously
                if settings.dag_enabled and request.session_id:
                    try:
                        from app.core.context_dag import context_dag
                        import asyncio as _asyncio
                        _asyncio.create_task(context_dag.compact_if_needed(request.session_id))
                    except Exception:
                        pass

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
            # Client disconnected mid-stream — save what we have
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


@router.get("/chat/history/{project_id}")
async def get_chat_history(
    project_id: str,
    session_id: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[ChatMessage]:
    """Get chat history for a project, optionally scoped to a session."""
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
