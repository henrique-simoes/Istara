"""Chat API route — streaming LLM responses with tool-use augmentation.

Architecture:
1. Agent identity loaded via Prompt RAG (query-aware persona sections)
2. System action tools injected into the system prompt (13 tools)
3. LLM decides which tools to call based on conversation context
4. Tool calls are parsed from LLM output, executed, and results injected
5. ReAct loop: LLM → tool call → execute → result → LLM (max 3 iterations)
6. RAG context and project files provide grounding for all responses

This replaces the old hardcoded intent detection with LLM-native tool
selection, following patterns from OpenClaw, Anthropic tool use, and ReAct.
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
from app.core.prompt_rag import compose_dynamic_prompt, compose_keyword_prompt
from app.core.context_summarizer import context_summarizer
from app.core.ollama import ollama
from app.core.rag import build_augmented_prompt, retrieve_context
from app.core.token_counter import context_guard
from app.models.database import get_db, async_session
from app.models.agent import Agent
from app.models.message import Message
from app.models.project import Project
from app.models.session import ChatSession, INFERENCE_PRESETS
from app.skills.registry import registry
from app.skills.system_actions import build_tools_prompt, execute_tool, SYSTEM_TOOLS

_chat_log = logging.getLogger(__name__)

router = APIRouter()

# Maximum tool-call iterations per message (prevents infinite loops)
MAX_TOOL_ITERATIONS = 3

# Regex to extract tool call JSON from LLM output
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
    # Try fenced code block first (preferred format)
    match = _TOOL_CALL_RE.search(text)
    if not match:
        # Try inline JSON
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

    # If no agent identity loaded yet, default to reclaw-main
    if not agent_identity_prompt:
        try:
            agent_identity_prompt = await compose_dynamic_prompt(
                "reclaw-main",
                query=request.message,
                use_embeddings=True,
            )
        except Exception:
            agent_identity_prompt = load_agent_identity("reclaw-main")

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

    # Inject system action tools so the LLM can perform actions
    tools_prompt = build_tools_prompt()
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

    # Prepend the system prompt into the messages list directly so the LLM
    # client doesn't receive a separate `system=` param that would create
    # duplicate system messages (root cause of LM Studio 400 errors).
    messages = [{"role": "system", "content": system_prompt}, *messages]

    async def generate():
        """Stream the LLM response with ReAct tool-use loop.

        Flow:
        1. Get LLM response (non-streaming for tool detection)
        2. Check for tool call JSON in the response
        3. If found: execute tool, inject result, get follow-up response
        4. Repeat up to MAX_TOOL_ITERATIONS times
        5. Stream the final text response to the client

        Uses its own DB session to avoid leak when client disconnects.
        """
        conversation = list(messages)  # Local copy for the tool loop
        all_text_parts = []  # Accumulate text for the full response
        tool_results = []  # Track executed tools for the response

        try:
            for iteration in range(MAX_TOOL_ITERATIONS + 1):
                # Get LLM response (collect fully to detect tool calls)
                full_text = []
                async for chunk in ollama.chat_stream(
                    messages=conversation,
                    model=llm_model,
                    temperature=llm_temperature,
                    max_tokens=llm_max_tokens,
                ):
                    full_text.append(chunk)

                response_text = "".join(full_text)

                # Check for tool call in the response
                tool_call, text_before, text_after = _extract_tool_call(response_text)

                if tool_call and iteration < MAX_TOOL_ITERATIONS:
                    tool_name = tool_call.get("tool", "")
                    tool_params = tool_call.get("params", {})

                    _chat_log.info(f"Tool call detected: {tool_name}({json.dumps(tool_params)[:200]})")

                    # Stream the pre-tool text to the client
                    if text_before:
                        all_text_parts.append(text_before)
                        event_data = json.dumps({"type": "chunk", "content": text_before + "\n\n"})
                        yield f"data: {event_data}\n\n"

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
                        agent_id=session_agent_id or "reclaw-main",
                    )

                    result_text = result.get("result", result.get("error", "Unknown result"))
                    tool_results.append({"tool": tool_name, "result": result_text})

                    # Stream tool result notification
                    result_display = f"🔧 **{tool_name}**: {result_text}\n\n"
                    all_text_parts.append(result_display)
                    result_event = json.dumps({"type": "chunk", "content": result_display})
                    yield f"data: {result_event}\n\n"

                    # Add the assistant's partial response and tool result to conversation
                    assistant_turn = text_before + f"\n\n[Tool: {tool_name}]" if text_before else f"[Tool: {tool_name}]"
                    conversation.append({"role": "assistant", "content": assistant_turn})
                    conversation.append({
                        "role": "user",
                        "content": f"[Tool result for {tool_name}]:\n{result_text}\n\nNow respond to the user based on this result. Do not call another tool unless necessary.",
                    })

                    # Continue the loop to get the follow-up response
                    continue

                else:
                    # No tool call — this is the final response. Stream it.
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
