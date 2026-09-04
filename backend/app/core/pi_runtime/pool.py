"""Bounded, lazy pool of supervised Pi worker children (H-12).

The pool grows the single-worker supervisor into a bounded set of workers whose
size is the configured ``pi_worker_pool_size`` (default 2). A session is routed
to exactly one worker by hashing its ``session_key`` — a deterministic,
process-stable mapping (``blake2b``, not the salted built-in ``hash``) so the
same session always lands on the same worker and traffic spreads evenly across
the pool without any shared per-worker load counter. This is the routing
contract W3 orchestrator traffic depends on.
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import AsyncIterator
from typing import Any

from app.config import settings

from .supervisor import PiRuntimeSupervisor, PiWorkerError, ToolHandler


class PiRuntimePool:
    """Spread independent sessions across a bounded pool of workers, routed by
    a stable ``session_key`` hash."""

    def __init__(self, *, pool_size: int | None = None, **worker_kwargs: Any) -> None:
        size = settings.pi_worker_pool_size if pool_size is None else pool_size
        size = max(1, int(size))
        self._workers = [PiRuntimeSupervisor(**worker_kwargs) for _ in range(size)]
        self._owners: dict[str, PiRuntimeSupervisor] = {}
        self._allocation_lock = asyncio.Lock()

    @property
    def is_running(self) -> bool:
        return any(worker.is_running for worker in self._workers)

    async def ensure_started(self) -> None:
        await self._workers[0].ensure_started()

    def _route_index(self, session_key: str) -> int:
        """Deterministic worker index for ``session_key`` (round-robin by hash).

        ``blake2b`` is used instead of the built-in ``hash`` so routing is
        stable across processes (PYTHONHASHSEED randomizes ``str`` hashing),
        which the reconnect/steering seams rely on to reach the same worker.
        """
        digest = hashlib.blake2b(session_key.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, "big") % len(self._workers)

    def _worker_for_open(self, session_key: str) -> PiRuntimeSupervisor:
        return self._workers[self._route_index(session_key)]

    async def open_session(self, session_key: str, **kwargs: Any) -> None:
        async with self._allocation_lock:
            if session_key in self._owners:
                raise PiWorkerError("session_busy")
            worker = self._worker_for_open(session_key)
            self._owners[session_key] = worker
        try:
            await worker.ensure_started()
            await worker.open_session(session_key, **kwargs)
        except Exception:
            async with self._allocation_lock:
                self._owners.pop(session_key, None)
            raise

    def _owner(self, session_key: str) -> PiRuntimeSupervisor:
        worker = self._owners.get(session_key)
        if worker is None:
            raise PiWorkerError("unknown_session")
        return worker

    async def bind_provider(self, session_key: str, endpoint: dict[str, Any]) -> None:
        await self._owner(session_key).bind_provider(session_key, endpoint)

    async def run_turn(
        self,
        session_key: str,
        text: str,
        tool_handler: ToolHandler,
        **kwargs: Any,
    ) -> AsyncIterator[dict[str, Any]]:
        async for frame in self._owner(session_key).run_turn(
            session_key, text, tool_handler, **kwargs
        ):
            yield frame

    async def run_provider_turn(
        self,
        session_key: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> AsyncIterator[dict[str, Any]]:
        """Forward a provider-only legacy turn to the session's owner.

        The legacy Istara loop retains tool-iteration authority while the Pi
        worker owns provider selection and execution. Provider-only turns must
        therefore follow the same sticky session routing as ordinary turns.
        """
        async for frame in self._owner(session_key).run_provider_turn(session_key, messages, tools):
            yield frame

    def active_run_id(self, session_key: str) -> str | None:
        return self._owner(session_key).active_run_id(session_key)

    async def steer(self, session_key: str, text: str) -> None:
        await self._owner(session_key).steer(session_key, text)

    async def follow_up(self, session_key: str, text: str) -> None:
        await self._owner(session_key).follow_up(session_key, text)

    async def abort(self, session_key: str, run_id: str | None = None) -> None:
        await self._owner(session_key).abort(session_key, run_id)

    async def close_session(self, session_key: str) -> None:
        worker = self._owners.pop(session_key, None)
        if worker is not None:
            await worker.close_session(session_key)

    async def shutdown(self) -> None:
        await asyncio.gather(*(worker.shutdown() for worker in self._workers))
        self._owners.clear()
