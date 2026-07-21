"""Async queue-bridge for streaming dispatcher chat turns (W2).

``AgenticDispatcher.chat_turn`` is an ``await`` that reports progress through a
``stream_cb`` callback, but the interactive routes (chat, design chat) are SSE
async generators. This bridge runs the turn on a task, forwards every engine
event through an ``asyncio.Queue``, and re-yields them to the generator in
order — legacy per-token ``content`` / ``tool_call`` / ``turn_separator``
events, or raw Pi worker events. When the turn settles it yields one terminal
``{"type": "_complete", "result": TurnResult}`` marker; a turn exception is
re-raised only after every already-emitted event was delivered, so the route's
native-tools rejection fallback sees the same failure semantics as the old
inline loops. Closing the generator (client disconnect) cancels the turn task.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator

_SENTINEL = object()


async def stream_chat_turn(
    dispatcher: Any,
    *,
    queue: asyncio.Queue | None = None,
    **chat_turn_kwargs: Any,
) -> AsyncGenerator[dict[str, Any], None]:
    """Yield one chat turn's stream events, then a ``_complete`` marker.

    The caller may pass its own *queue* so auxiliary producers (e.g. a
    tool-executor wrapper emitting tool-result display lines) interleave their
    events in execution order with the engine's stream events.
    """
    events: asyncio.Queue = queue if queue is not None else asyncio.Queue()

    async def stream_cb(event: dict[str, Any]) -> None:
        await events.put(event)

    async def run() -> None:
        try:
            result = await dispatcher.chat_turn(stream_cb=stream_cb, **chat_turn_kwargs)
        except Exception as exc:  # delivered after all prior events, then raised
            await events.put((_SENTINEL, None, exc))
        else:
            await events.put((_SENTINEL, result, None))

    task = asyncio.create_task(run())
    try:
        while True:
            item = await events.get()
            if isinstance(item, tuple) and len(item) == 3 and item[0] is _SENTINEL:
                _, result, exc = item
                if exc is not None:
                    raise exc
                yield {"type": "_complete", "result": result}
                return
            yield item
    finally:
        if not task.done():
            task.cancel()
