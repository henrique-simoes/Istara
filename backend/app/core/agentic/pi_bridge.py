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
import urllib.request
from typing import Any

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


def build_bridge_request(
    *, base_url: str, payload: dict[str, Any], api_key: str
) -> urllib.request.Request:
    """Build the outbound chat-completions request (pure; unit-testable)."""
    headers = {
        "User-Agent": "istara-pi-runtime/1.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )


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
    line_iter: Any = None,
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

    # Provider edge protection rejects default client UAs AND non-browser TLS
    # fingerprints (httpx → 403 HTML challenge on api.deepseek.com while
    # urllib passes). Transport = urllib via build_bridge_request; `line_iter`
    # is the test injection seam (an iterable of raw SSE lines).
    content_parts: list[str] = []
    tool_calls: dict[int, dict[str, Any]] = {}
    finish_reason: str | None = None
    usage: dict[str, Any] = {}

    def _open_stream() -> Any:
        request = build_bridge_request(
            base_url=source.base_url, payload=payload, api_key=source.api_key
        )
        return urllib.request.urlopen(request, timeout=_DEFAULT_TIMEOUT_S)

    stream_ctx = line_iter() if line_iter is not None else _open_stream()
    try:
        for raw_line in stream_ctx:
            line = raw_line.decode("utf-8", "replace") if isinstance(raw_line, bytes) else raw_line
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
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"pi_bridge_http_{exc.code}") from exc

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
