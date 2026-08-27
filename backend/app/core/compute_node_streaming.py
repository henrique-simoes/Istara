"""Provider streaming helpers for :class:`ComputeNode`.

Keeping provider-specific parsing outside the invocation mixin keeps the public
node method small enough for the architecture gate to inspect while preserving
the existing text/tool-call stream contract.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

from app.config import settings
from app.core.llm_output import ThinkingContentFilter


async def stream_node_chat(
    node: Any,
    client: Any,
    messages: list[dict],
    *,
    model: str | None,
    temperature: float,
    max_tokens: int | None,
    tools: list[dict] | None,
    project_id: str | None,
) -> AsyncGenerator[str | dict, None]:
    """Yield the legacy node stream shape for one already-authorized node."""
    if node.is_anthropic:
        async for piece in _stream_anthropic(
            node,
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            project_id=project_id,
        ):
            yield piece
        return
    if node.provider_type == "ollama":
        async for piece in _stream_ollama(node, client, messages, model, temperature, max_tokens):
            yield piece
        return
    async for piece in _stream_openai(
        node, client, messages, model, temperature, max_tokens, tools
    ):
        yield piece


async def _stream_anthropic(
    node: Any,
    messages: list[dict],
    *,
    model: str | None,
    temperature: float,
    max_tokens: int | None,
    tools: list[dict] | None,
    project_id: str | None,
) -> AsyncGenerator[str | dict, None]:
    result = await node.chat(
        messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        tools=tools,
        thinking_mode=None,
        project_id=project_id,
    )
    content = result.get("message", {}).get("content", "")
    if content:
        yield content
    if result.get("message", {}).get("tool_calls"):
        yield {
            "tool_calls": result["message"]["tool_calls"],
            "finish_reason": result.get("finish_reason", "tool_calls"),
        }


async def _stream_ollama(
    node: Any,
    client: Any,
    messages: list[dict],
    model: str | None,
    temperature: float,
    max_tokens: int | None,
) -> AsyncGenerator[str, None]:
    del node
    options: dict = {"temperature": temperature}
    if max_tokens:
        options["num_predict"] = max_tokens
    payload = {
        "model": model or settings.ollama_model,
        "messages": messages,
        "stream": True,
        "options": options,
    }
    async with client.stream("POST", "/api/chat", json=payload, timeout=None) as resp:
        resp.raise_for_status()
        content_filter = ThinkingContentFilter()
        async for line in resp.aiter_lines():
            if not line.strip():
                continue
            data = json.loads(line)
            content = content_filter.push(data.get("message", {}).get("content", ""))
            if content:
                yield content
            if data.get("done", False):
                remaining = content_filter.flush()
                if remaining:
                    yield remaining
                return


def _merge_tool_call_delta(accumulated: list[dict], tc_delta: dict) -> None:
    idx = tc_delta.get("index", 0)
    while len(accumulated) <= idx:
        accumulated.append(
            {
                "id": "",
                "type": "function",
                "function": {"name": "", "arguments": ""},
            }
        )
    tc = accumulated[idx]
    if tc_delta.get("id"):
        tc["id"] = tc_delta["id"]
    fn = tc_delta.get("function", {})
    if fn.get("name"):
        tc["function"]["name"] = fn["name"]
    if fn.get("arguments"):
        tc["function"]["arguments"] += fn["arguments"]


async def _stream_openai(
    node: Any,
    client: Any,
    messages: list[dict],
    model: str | None,
    temperature: float,
    max_tokens: int | None,
    tools: list[dict] | None,
) -> AsyncGenerator[str | dict, None]:
    payload = {
        "model": node._resolve_model(model),
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens
    if tools:
        payload["tools"] = tools

    accumulated_tool_calls: list[dict] = []
    tool_call_mode = False
    content_filter = ThinkingContentFilter()

    async with client.stream(
        "POST", node._openai_endpoint("chat/completions"), json=payload, timeout=None
    ) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            event = _parse_openai_line(line, accumulated_tool_calls, content_filter, tool_call_mode)
            if event == "stop":
                break
            if isinstance(event, str):
                yield event
            elif event is True:
                tool_call_mode = True

    remaining = content_filter.flush()
    if remaining:
        yield remaining
    if accumulated_tool_calls and any(
        tc["function"]["name"] for tc in accumulated_tool_calls
    ):
        yield {"tool_calls": accumulated_tool_calls, "finish_reason": "tool_calls"}


def _parse_openai_line(
    line: str,
    accumulated_tool_calls: list[dict],
    content_filter: ThinkingContentFilter,
    tool_call_mode: bool,
) -> str | bool | None:
    """Process one SSE line; return content, tool mode, stop, or no-op."""
    line = line.strip()
    if not line or not line.startswith("data: "):
        return None
    data_str = line[6:]
    if data_str == "[DONE]":
        return "stop"
    try:
        data = json.loads(data_str)
        choice = data.get("choices", [{}])[0]
        delta = choice.get("delta", {})
        finish = choice.get("finish_reason")
        if delta.get("tool_calls"):
            for tc_delta in delta["tool_calls"]:
                _merge_tool_call_delta(accumulated_tool_calls, tc_delta)
            return True
        content = content_filter.push(delta.get("content", ""))
        if content:
            return content
        if finish == "tool_calls" or (finish == "stop" and tool_call_mode):
            return "stop"
    except (json.JSONDecodeError, IndexError, KeyError):
        return None
    return None
