"""F-W1-R1-1: Python-side per-frame protocol-version validation.

PROTOCOL.md ("Versioning") requires *both* sides to validate the protocol
version on every frame, not only at the handshake: "Every other inbound frame
whose ``v`` mismatches is rejected before its ``seq`` is consumed: the
session's active run settles ``run.failed{error:"protocol_version_mismatch"}``
(or that frame is emitted directly when no run is active). A version mismatch
is never process-fatal."

The Node worker already enforces this on inbound frames. These tests pin the
Python half — ``PiRuntimeSupervisor._dispatch`` — so a worker that completes a
valid v2 handshake and then emits a ``v:1`` run frame can never have that frame
consumed as trusted protocol data (no tool executes, no artifact/usage is
accepted, the run settles as a typed ``protocol_version_mismatch``).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.core.pi_runtime.protocol import PROTOCOL_VERSION
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor

from .harness import requires_node


# ── unit: _dispatch per-frame rejection (no node required) ────────────────
@pytest.mark.asyncio
async def test_dispatch_rejects_v1_run_completed_and_settles_active_run():
    """A post-handshake v1 ``run.completed`` never queues its forged terminal;
    the session's active run settles as a typed version mismatch instead."""
    sup = PiRuntimeSupervisor()
    key = "s1"
    queue: asyncio.Queue = asyncio.Queue()
    sup._sessions[key] = queue
    sup._session_runs[key] = "run-1"

    sup._dispatch(
        {
            "v": 1,
            "type": "run.completed",
            "session_key": key,
            "run_id": "run-1",
            "usage": {"input_tokens": 9, "output_tokens": 9},
            "structured": {"pwned": True},
            "stop_reason": "stop",
        }
    )

    frame = queue.get_nowait()
    # The raw v1 frame is NOT queued; a v2 run.failed settles the active run.
    assert frame["type"] == "run.failed"
    assert frame["error"] == "protocol_version_mismatch"
    assert frame["run_id"] == "run-1"
    assert frame["v"] == PROTOCOL_VERSION
    # None of the forged terminal payload leaked through.
    assert "structured" not in frame and "usage" not in frame
    assert queue.empty()


@pytest.mark.asyncio
async def test_dispatch_rejects_v1_tool_call_without_queuing_it():
    """A v1 ``tool.call`` is rejected before it reaches ``run_turn``, so the
    authority ``tool_handler`` is never invoked (no wrong-version tool run)."""
    sup = PiRuntimeSupervisor()
    key = "s2"
    queue: asyncio.Queue = asyncio.Queue()
    sup._sessions[key] = queue
    sup._session_runs[key] = "run-7"

    sup._dispatch(
        {
            "v": 1,
            "type": "tool.call",
            "session_key": key,
            "run_id": "run-7",
            "tool_call_id": "t-1",
            "name": "create_task",
            "arguments": {"title": "pwned"},
        }
    )

    frame = queue.get_nowait()
    assert frame["type"] == "run.failed"  # never a tool.call the driver would run
    assert frame["error"] == "protocol_version_mismatch"
    assert frame["run_id"] == "run-7"
    assert queue.empty()


@pytest.mark.asyncio
async def test_dispatch_rejects_v1_frame_with_no_active_run_using_frame_run_id():
    """With no active run, the rejection targets the offending frame's own run
    id (emitted directly) so a stale rejection can't terminate a future run."""
    sup = PiRuntimeSupervisor()
    key = "s3"
    queue: asyncio.Queue = asyncio.Queue()
    sup._sessions[key] = queue
    # No entry in _session_runs: no run is active for this session.

    sup._dispatch(
        {"v": 1, "type": "run.completed", "session_key": key, "run_id": "orphan-run", "stop_reason": "stop"}
    )

    frame = queue.get_nowait()
    assert frame["type"] == "run.failed"
    assert frame["error"] == "protocol_version_mismatch"
    assert frame["run_id"] == "orphan-run"


@pytest.mark.asyncio
async def test_dispatch_drops_v1_frame_for_unknown_session():
    """A mismatched frame for a session we do not own is dropped, never
    process-fatal and never cross-wired into another session's queue."""
    sup = PiRuntimeSupervisor()
    other: asyncio.Queue = asyncio.Queue()
    sup._sessions["known"] = other

    sup._dispatch({"v": 1, "type": "run.completed", "session_key": "ghost", "run_id": "r"})

    assert other.empty()
    assert sup._fatal is None  # a version mismatch never poisons the worker


@pytest.mark.asyncio
async def test_dispatch_keeps_valid_v2_session_frame():
    """The per-frame check is a version gate only: a well-formed v2 frame is
    still routed to its session queue verbatim (no false positive)."""
    sup = PiRuntimeSupervisor()
    key = "s4"
    queue: asyncio.Queue = asyncio.Queue()
    sup._sessions[key] = queue

    valid = {"v": PROTOCOL_VERSION, "type": "assistant.delta", "session_key": key, "run_id": "run-1", "text": "hi"}
    sup._dispatch(valid)

    assert queue.get_nowait() is valid


def test_dispatch_exempts_ready_and_fatal_from_the_per_frame_check():
    """`ready`/`fatal` are the version-negotiation channel: they must still be
    processed (so ensure_started can surface the typed handshake mismatch via
    ``protocol_version``) rather than being dropped by the per-frame ``v``
    gate — mirroring the worker exempting inbound ``hello``."""
    sup = PiRuntimeSupervisor()
    # A v1 ready must still unblock the handshake (ensure_started then rejects
    # it on protocol_version), never be silently swallowed by the v gate.
    sup._dispatch({"v": 1, "type": "ready", "protocol_version": 1})
    assert sup._ready.is_set()
    assert sup._ready_info.get("protocol_version") == 1

    # A v1 handshake fatal must still record the fatal and release the wait.
    sup2 = PiRuntimeSupervisor()
    sup2._dispatch({"v": 1, "type": "fatal", "error": "protocol_version_mismatch"})
    assert sup2._ready.is_set()
    assert sup2._fatal == "protocol_version_mismatch"


# ── integration: real supervisor vs a v2-handshake-then-v1-run worker ─────
@requires_node
@pytest.mark.asyncio
async def test_post_handshake_v1_run_frame_is_rejected_without_tool_or_artifact():
    """End to end (F-W1-R1-1): a worker that handshakes v2 then emits v1 run
    frames is refused per-frame — the run settles ``protocol_version_mismatch``,
    the v1 ``tool.call`` never executes, and the forged v1 ``run.completed``
    artifact/usage is never surfaced."""
    stub = Path(__file__).parent / "adversarial_worker_v1_run.mjs"
    supervisor = PiRuntimeSupervisor(worker_entry=stub)
    tool_invocations: list[str] = []

    async def tool_handler(name, args):
        tool_invocations.append(name)
        return {"ok": True, "result": {"echo": name}}

    frames: list[dict] = []
    try:
        await supervisor.ensure_started()
        assert supervisor.is_running  # the v2 handshake succeeded
        await supervisor.open_session(
            "adv-session", system_prompt="sys", history=[], revision="r1", catalog=[],
        )
        async for frame in supervisor.run_turn("adv-session", "go", tool_handler):
            frames.append(frame)
    finally:
        await supervisor.shutdown()

    # Exactly one terminal, and it is the typed per-frame version mismatch.
    assert frames, "run produced no frames"
    terminal = frames[-1]
    assert terminal["type"] == "run.failed"
    assert terminal["error"] == "protocol_version_mismatch"
    # The v1 tool.call never reached the authority (no wrong-version execution).
    assert tool_invocations == []
    # No content/tool/terminal frame from the mismatched v1 stream was ever
    # yielded to the caller — no partial artifact or forged usage.
    assert not any(f.get("type") in ("tool.call", "run.completed") for f in frames)
    assert not any("structured" in f for f in frames)
