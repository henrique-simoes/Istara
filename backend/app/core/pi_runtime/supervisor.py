"""Supervised Pi runtime worker.

Owns exactly one Node child per backend process, speaking the versioned NDJSON
protocol over stdin/stdout. Responsibilities:

* lazy start on the first validated Pi request + handshake,
* per-session frame routing (one asyncio queue per ``session_key``),
* a run driver that pumps worker events and round-trips authority tool calls,
* owned teardown (cancel runs, drain, terminate, then kill only the owned PID).

Secrets arrive only inside ``provider.bind`` frames and are never logged. This
module never imports or mutates the donated-compute registry.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable

from .protocol import MAX_CHUNK_DATA_BYTES, MAX_HISTORY_MESSAGES, MAX_LINE_BYTES, PROTOCOL_VERSION, TERMINAL_RUN_TYPES

logger = logging.getLogger(__name__)

# repo_root/backend/app/core/pi_runtime/supervisor.py -> repo_root
_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_WORKER_ENTRY = _REPO_ROOT / "pi-runtime" / "src" / "worker.mjs"

ToolHandler = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


class PiWorkerError(RuntimeError):
    """The worker failed to start, handshake, or stay alive."""


class PiRuntimeSupervisor:
    def __init__(
        self,
        *,
        worker_entry: Path | None = None,
        node_path: str = "node",
        handshake_timeout: float = 15.0,
        run_timeout: float = 120.0,
        max_turns: int = 8,
        max_cost_usd: float = 1.0,
        max_sessions: int = 10,
    ) -> None:
        self._worker_entry = Path(worker_entry) if worker_entry else DEFAULT_WORKER_ENTRY
        self._node_path = node_path
        self._handshake_timeout = handshake_timeout
        self._run_timeout = run_timeout
        self._max_turns = max_turns
        self._max_cost_usd = max_cost_usd
        self._max_sessions = max_sessions

        self._proc: asyncio.subprocess.Process | None = None
        self._sessions: dict[str, asyncio.Queue[dict[str, Any]]] = {}
        self._session_runs: dict[str, str] = {}
        self._session_locks: dict[str, asyncio.Lock] = {}
        self._reader_task: asyncio.Task | None = None
        self._stderr_task: asyncio.Task | None = None
        self._ready = asyncio.Event()
        self._ready_info: dict[str, Any] = {}
        self._start_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
        # The Node worker validates monotonically increasing sequence numbers
        # independently for every session (and for connection-scoped frames).
        # Keep the producer-side counter here so callers never need to know
        # about the transport detail.
        self._outbound_seqs: dict[str | None, int] = {}
        self._fatal: str | None = None
        self._run_counter = 0
        self._restart_times: list[float] = []

    # ── lifecycle ────────────────────────────────────────────────────────
    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    async def ensure_started(self) -> None:
        async with self._start_lock:
            if self.is_running and self._ready.is_set():
                return
            # EOF leaves a process handle behind.  Reclaim it before starting
            # again so a poisoned reader cannot strand a child (H-2).
            if self._proc is not None:
                await self._force_stop()
            now = time.monotonic()
            self._restart_times = [at for at in self._restart_times if now - at < 60.0]
            if len(self._restart_times) >= 3:
                raise PiWorkerError("worker_restart_backoff")
            self._restart_times.append(now)
            if not self._worker_entry.exists():
                raise PiWorkerError(f"worker_entry_missing:{self._worker_entry}")
            worker_env = dict(os.environ)
            worker_env["PI_MAX_SESSIONS"] = str(self._max_sessions)
            self._proc = await asyncio.create_subprocess_exec(
                self._node_path,
                str(self._worker_entry),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self._worker_entry.parent.parent),
                env=worker_env,
                # A worker can legitimately emit chunked protocol payloads
                # larger than asyncio's default 64 KiB reader limit (H-2).
                limit=8 * 1024 * 1024,
            )
            self._fatal = None
            self._ready.clear()
            self._reader_task = asyncio.create_task(self._read_loop())
            self._stderr_task = asyncio.create_task(self._drain_stderr())
            await self._send({"v": PROTOCOL_VERSION, "type": "hello", "protocol_version": PROTOCOL_VERSION})
            try:
                await asyncio.wait_for(self._ready.wait(), timeout=self._handshake_timeout)
            except asyncio.TimeoutError as exc:
                await self._force_stop()
                raise PiWorkerError("handshake_timeout") from exc

    async def _send(self, frame: dict[str, Any]) -> None:
        if self._proc is None or self._proc.stdin is None:
            raise PiWorkerError("worker_not_started")
        frame = dict(frame)
        key = frame.get("session_key")
        if "seq" not in frame:
            next_seq = self._outbound_seqs.get(key, 0) + 1
            self._outbound_seqs[key] = next_seq
            frame["seq"] = next_seq
        serialized = json.dumps(frame, separators=(",", ":"), ensure_ascii=False)
        line = (serialized + "\n").encode("utf-8")
        # Match the Node codec: large tool results/session opens are encoded as
        # bounded payload.chunk frames, preserving the original frame's seq.
        if len(line) > MAX_LINE_BYTES:
            raw = serialized.encode("utf-8")
            parts: list[bytes] = []
            offset = 0
            while offset < len(raw):
                end = min(offset + MAX_CHUNK_DATA_BYTES, len(raw))
                # A chunk payload is JSON text, so keep UTF-8 codepoints whole.
                while end > offset:
                    try:
                        raw[offset:end].decode("utf-8")
                        break
                    except UnicodeDecodeError:
                        end -= 1
                if end == offset:  # defensive; a UTF-8 scalar is at most 4 bytes
                    raise PiWorkerError("chunk_encoding_error")
                parts.append(raw[offset:end])
                offset = end
            chunk_id = f"py-{uuid.uuid4().hex}"
            line = b"".join(
                (json.dumps({
                    "v": PROTOCOL_VERSION,
                    "type": "payload.chunk",
                    "chunk_id": chunk_id,
                    "seq": index,
                    "total": len(parts),
                    "data": part.decode("utf-8"),
                }, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
                for index, part in enumerate(parts, start=1)
            )
        async with self._write_lock:
            self._proc.stdin.write(line)
            await self._proc.stdin.drain()

    async def _read_loop(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        stdout = self._proc.stdout
        try:
            while True:
                line = await stdout.readline()
                if not line:
                    break
                try:
                    frame = json.loads(line.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    logger.warning("pi-runtime: dropped malformed worker line")
                    continue
                self._dispatch(frame)
        except asyncio.CancelledError:  # pragma: no cover - teardown
            raise
        except Exception:  # pragma: no cover - defensive
            logger.exception("pi-runtime: reader loop crashed")
        finally:
            # EOF or crash: fail every open session so no run hangs.
            self._fatal = self._fatal or "worker_eof"
            # A live child may have closed stdout while retaining stdin.  Make
            # it ineligible immediately; ensure_started then reclaims it
            # instead of reusing a poisoned, apparently-ready worker (H-2).
            self._ready.clear()
            for queue in self._sessions.values():
                queue.put_nowait({"type": "fatal", "error": self._fatal})

    def _dispatch(self, frame: dict[str, Any]) -> None:
        ftype = frame.get("type")
        if ftype == "ready":
            self._ready_info = frame
            self._ready.set()
            return
        if ftype == "fatal":
            self._fatal = frame.get("error", "fatal")
            for queue in self._sessions.values():
                queue.put_nowait(frame)
            return
        key = frame.get("session_key")
        queue = self._sessions.get(key)
        if queue is not None:
            queue.put_nowait(frame)

    async def _drain_stderr(self) -> None:
        assert self._proc is not None and self._proc.stderr is not None
        try:
            while True:
                line = await self._proc.stderr.readline()
                if not line:
                    break
                logger.debug("pi-runtime[stderr]: %s", line.decode("utf-8", "replace").rstrip())
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except Exception:  # pragma: no cover
            pass

    # ── session + run driver ─────────────────────────────────────────────
    async def open_session(
        self,
        session_key: str,
        *,
        system_prompt: str,
        history: list[dict[str, Any]],
        revision: str | None,
        catalog: list[dict[str, Any]],
    ) -> None:
        lock = self._session_locks.setdefault(session_key, asyncio.Lock())
        async with lock:
            # A caller must close a successful session before reusing its key.
            # Reject instead of replacing its queue, which used to cross-wire runs.
            if session_key in self._sessions:
                raise PiWorkerError("session_busy")
            queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
            self._sessions[session_key] = queue
            try:
                await self._send(
                    {
                        "v": PROTOCOL_VERSION,
                        "type": "session.open",
                        "session_key": session_key,
                        "system_prompt": system_prompt,
                        "history": (history or [])[-MAX_HISTORY_MESSAGES:],
                        "revision": revision,
                        "catalog": catalog,
                        "limits": {
                            "max_turns": self._max_turns,
                            "max_wall_clock_ms": int(self._run_timeout * 1000),
                            "max_cost_usd": self._max_cost_usd,
                        },
                    }
                )
                frame = await asyncio.wait_for(queue.get(), timeout=self._handshake_timeout)
                if frame.get("type") != "session.opened":
                    raise PiWorkerError(f"session_open_failed:{frame.get('error') or frame.get('type')}")
            except Exception:
                self._sessions.pop(session_key, None)
                raise

    async def bind_provider(self, session_key: str, endpoint: dict[str, Any]) -> None:
        await self._send(
            {
                "v": PROTOCOL_VERSION,
                "type": "provider.bind",
                "session_key": session_key,
                "endpoint": endpoint,
            }
        )

    async def run_turn(
        self,
        session_key: str,
        text: str,
        tool_handler: ToolHandler,
    ) -> AsyncIterator[dict[str, Any]]:
        """Drive one prompt run, yielding worker frames until a terminal frame.

        Authority tool calls are executed via ``tool_handler`` and the result is
        sent back; every other frame is yielded to the caller.
        """
        queue = self._sessions.get(session_key)
        if queue is None:
            raise PiWorkerError("unknown_session")
        self._run_counter += 1
        run_id = f"run-{self._run_counter}"
        lock = self._session_locks.setdefault(session_key, asyncio.Lock())
        async with lock:
            if session_key in self._session_runs:
                raise PiWorkerError("session_busy")
            self._session_runs[session_key] = run_id
            await self._send(
                {"v": PROTOCOL_VERSION, "type": "turn.prompt", "session_key": session_key, "run_id": run_id, "text": text}
            )
            try:
                while True:
                    frame = await asyncio.wait_for(queue.get(), timeout=self._run_timeout)
                    # Session queues can contain delayed frames from a prior run.
                    # They must never terminate or yield into this run.
                    frame_run_id = frame.get("run_id")
                    if frame_run_id is not None and frame_run_id != run_id:
                        continue
                    ftype = frame.get("type")
                    if ftype == "fatal":
                        yield {"type": "run.failed", "run_id": run_id, "error": frame.get("error", "fatal")}
                        return
                    if ftype == "tool.call":
                        outcome = await self._safe_tool_call(tool_handler, frame)
                        await self._send(
                            {
                                "v": PROTOCOL_VERSION,
                                "type": "tool.result",
                                "session_key": session_key,
                                "run_id": run_id,
                                "tool_call_id": frame.get("tool_call_id"),
                                "ok": bool(outcome.get("ok")),
                                "result": outcome.get("result"),
                                "error": outcome.get("error"),
                            }
                        )
                        yield frame
                        continue
                    yield frame
                    if ftype in TERMINAL_RUN_TYPES:
                        return
            finally:
                self._session_runs.pop(session_key, None)

    async def _safe_tool_call(self, tool_handler: ToolHandler, frame: dict[str, Any]) -> dict[str, Any]:
        try:
            return await tool_handler(frame.get("name", ""), frame.get("arguments") or {})
        except Exception as exc:  # authority errors never kill the run
            logger.warning("pi-runtime: tool handler raised for %s", frame.get("name"))
            return {"ok": False, "error": f"tool_handler_error:{type(exc).__name__}"}

    def active_run_id(self, session_key: str) -> str | None:
        """Run id of the turn currently in flight for ``session_key`` (or None)."""
        return self._session_runs.get(session_key)

    async def steer(self, session_key: str, text: str) -> None:
        await self._send(
            {
                "v": PROTOCOL_VERSION,
                "type": "turn.steer",
                "session_key": session_key,
                "run_id": self._session_runs.get(session_key),
                "text": text,
            }
        )

    async def follow_up(self, session_key: str, text: str) -> None:
        await self._send(
            {
                "v": PROTOCOL_VERSION,
                "type": "turn.follow_up",
                "session_key": session_key,
                "run_id": self._session_runs.get(session_key),
                "text": text,
            }
        )

    async def abort(self, session_key: str, run_id: str | None = None) -> None:
        # A clean ``run.aborted`` requires the worker's current run id; look it
        # up when the caller (e.g. the steering bridge) does not track it.
        rid = run_id or self._session_runs.get(session_key)
        await self._send(
            {"v": PROTOCOL_VERSION, "type": "turn.abort", "session_key": session_key, "run_id": rid}
        )

    async def close_session(self, session_key: str) -> None:
        queue = self._sessions.get(session_key)
        if queue is None:
            return
        try:
            await self._send({"v": PROTOCOL_VERSION, "type": "session.close", "session_key": session_key})
            # Best-effort wait for the ack, but never hang teardown on it.
            try:
                while True:
                    frame = await asyncio.wait_for(queue.get(), timeout=5.0)
                    if frame.get("type") in ("session.closed", "fatal"):
                        break
            except asyncio.TimeoutError:
                pass
        finally:
            self._sessions.pop(session_key, None)
            self._session_locks.pop(session_key, None)

    async def shutdown(self) -> None:
        if self._proc is None:
            return
        try:
            if self.is_running:
                await self._send({"v": PROTOCOL_VERSION, "type": "shutdown"})
                try:
                    await asyncio.wait_for(self._proc.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    await self._force_stop()
        except Exception:  # pragma: no cover - defensive teardown
            await self._force_stop()
        finally:
            await self._cancel_tasks()
            self._sessions.clear()
            self._session_runs.clear()
            self._session_locks.clear()
            self._outbound_seqs.clear()
            self._restart_times.clear()

    async def _force_stop(self) -> None:
        if self._proc is None:
            return
        if self._proc.returncode is None:
            self._proc.terminate()
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=3.0)
            except asyncio.TimeoutError:
                self._proc.kill()
                try:
                    await asyncio.wait_for(self._proc.wait(), timeout=3.0)
                except asyncio.TimeoutError:  # pragma: no cover
                    pass
        await self._cancel_tasks()

    async def _cancel_tasks(self) -> None:
        for task in (self._reader_task, self._stderr_task):
            if task is not None and not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):  # pragma: no cover
                    pass
        self._reader_task = None
        self._stderr_task = None
        self._proc = None
        self._ready.clear()


# Process-wide singleton — one worker child per backend process.
_supervisor: Any | None = None


def get_supervisor() -> Any:
    global _supervisor
    if _supervisor is None:
        from .pool import PiRuntimePool

        _supervisor = PiRuntimePool()
    return _supervisor


async def shutdown_supervisor() -> None:
    global _supervisor
    if _supervisor is not None:
        await _supervisor.shutdown()
        _supervisor = None
