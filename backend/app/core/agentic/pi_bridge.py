"""Execution-only bridge: Istara's agentic loop over a pi-managed endpoint.

CF-SPEC-1 Phase 6 (DEC-10): when the unified resolver selects a pi-managed
source for a legacy-plane turn, this module performs the OpenAI-compatible
chat call directly against that endpoint under Istara identity. The endpoint
is NEVER advertised to the compute pool, never counted as donated compute,
and its secret never leaves this call boundary.

Streaming shape mirrors ``legacy._stream_turn``: content deltas are forwarded
as text chunks (when allowed), tool-call deltas accumulate into one assistant
message, and provider usage (``stream_options.include_usage``) flows back so
accounting stays exact whenever the provider reports it.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.core.agentic.model_source import ModelSource

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_S = 300.0


def _message_payload(
    *, history: list[dict[str, Any]], system: str | None
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    if system:
        messages.append({"role": "system", "content": system})
    for item in history or []:
        role = str(item.get("role") or "user")
        messages.append({"role": role, "content": item.get("content", "")})
    return messages


async def stream_openai_chat(
    *,
    source: ModelSource,
    history: list[dict[str, Any]],
    system: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    tools: list[dict[str, Any]] | None = None,
    stream_cb: Any = None,
    forward_tokens: bool = True,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    """One streamed OpenAI-compatible turn. Returns an assistant message dict.

    Shape matches the legacy plane's expectations: ``{"role": "assistant",
    "content": ..., "tool_calls": [...]}`` plus a ``_bridge_meta`` key carrying
    exact usage, the serving endpoint id, and the finish reason. Callers strip
    ``_bridge_meta`` before persisting conversation history.
    """
    payload: dict[str, Any] = {
        "model": source.model,
        "messages": _message_payload(history=history, system=system),
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens:
        payload["max_tokens"] = max_tokens
    if tools:
        payload["tools"] = tools

    headers = {"Authorization": f"Bearer {source.api_key}"} if source.api_key else {}
    content_parts: list[str] = []
    tool_calls: dict[int, dict[str, Any]] = {}
    finish_reason: str | None = None
    usage: dict[str, Any] = {}

    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_S, transport=transport) as client:
        async with client.stream(
            "POST",
            f"{source.base_url.rstrip('/')}/v1/chat/completions",
            json=payload,
            headers=headers,
        ) as response:
            if response.status_code >= 400:
                body = (await response.aread()).decode(errors="replace")[:400]
                raise RuntimeError(f"pi_bridge_http_{response.status_code}:{body}")
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                if chunk.get("usage"):
                    raw = chunk["usage"]
                    usage = {
                        "input_tokens": raw.get("prompt_tokens", 0) or 0,
                        "output_tokens": raw.get("completion_tokens", 0) or 0,
                        "total_tokens": raw.get("total_tokens")
                        or (raw.get("prompt_tokens", 0) or 0)
                        + (raw.get("completion_tokens", 0) or 0),
                        "estimate": False,
                    }
                for choice in chunk.get("choices") or []:
                    delta = choice.get("delta") or {}
                    text = delta.get("content")
                    if isinstance(text, str) and text:
                        content_parts.append(text)
                        if forward_tokens and stream_cb is not None:
                            await _emit(stream_cb, {"type": "content", "text": text})
                    for tc in delta.get("tool_calls") or []:
                        index = int(tc.get("index") or 0)
                        slot = tool_calls.setdefault(
                            index,
                            {
                                "id": "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            },
                        )
                        if tc.get("id"):
                            slot["id"] = tc["id"]
                        fn = tc.get("function") or {}
                        if fn.get("name"):
                            slot["function"]["name"] += fn["name"]
                        if fn.get("arguments"):
                            slot["function"]["arguments"] += fn["arguments"]
                    if choice.get("finish_reason"):
                        finish_reason = choice["finish_reason"]

    assembled_calls = [
        {
            "function": {
                "name": slot["function"]["name"],
                "arguments": slot["function"]["arguments"],
            },
            **({"id": slot["id"]} if slot["id"] else {}),
        }
        for _, slot in sorted(tool_calls.items())
    ]
    message: dict[str, Any] = {
        "role": "assistant",
        "content": "".join(content_parts),
        "tool_calls": assembled_calls,
    }
    message["_bridge_meta"] = {
        "usage": usage,
        "endpoint_id": source.endpoint_id,
        "model": source.model,
        "plane": source.plane,
        "finish_reason": finish_reason or ("tool_calls" if assembled_calls else "stop"),
    }
    return message


async def _emit(stream_cb: Any, event: dict[str, Any]) -> None:
    maybe = stream_cb(event)
    if hasattr(maybe, "__await__"):
        await maybe
