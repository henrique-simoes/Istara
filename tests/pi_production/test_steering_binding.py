"""W0 hardening regressions for the Pi steering binding and turn lifecycle.

* H-5 (B-5): the steering binding is keyed ``(agent_id, project_id,
  session_key)`` and the pump polls its own binding — never a global single
  slot. Two concurrent turns of the same agent with independent bindings must
  produce zero spurious aborts.
* H-7 (B-7): the session queue is registered only after a successful open and
  the full turn (including open) is wrapped in try/finally — failed opens
  never leak or clobber a live session.
* H-9 (engine): turn telemetry distinguishes ``aborted`` from ``error``.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest

from app.core.pi_runtime.supervisor import PiWorkerError, PiRuntimeSupervisor
from app.core.steering import steering_manager
from app.core.telemetry import telemetry_recorder
from app.models.database import async_session, init_db
from app.models.project import Project
from app.skills.system_actions import execute_tool

from .harness import (
    error_after_partial,
    faux_service,
    final_text,
    requires_node,
    tool_call,
)

pytestmark = requires_node

_SYS = "You run inside Istara. Pi owns the loop."


async def _mk_project(project_id: str, name: str) -> None:
    async with async_session() as db:
        db.add(Project(id=project_id, name=name))
        await db.commit()


async def _collect(service, events: list[dict], **kwargs) -> None:
    async for event in service.run_chat_turn(**kwargs):
        events.append(event)


# ── H-5: concurrent turns, independent bindings, zero spurious aborts ────────
@pytest.mark.asyncio
async def test_two_concurrent_turns_independent_bindings_no_spurious_aborts():
    """Turn B finishing (same agent, same project, different session) must not
    read as an abort on turn A's steering pump."""
    await init_db()
    project_id = f"pi-prod-h5-{uuid.uuid4()}"
    agent_id = f"h5-agent-{uuid.uuid4()}"
    await _mk_project(project_id, "Pi H-5 concurrent bindings")

    sup = PiRuntimeSupervisor()
    # Turn A pauses inside its tool call until turn B has fully completed.
    b_done = asyncio.Event()
    svc_a = faux_service([tool_call("list_tasks", {}), final_text("A done")], sup)
    svc_b = faux_service([final_text("B done")], sup)

    async def slow_exec(name, params, pid, aid):
        await asyncio.wait_for(b_done.wait(), timeout=30.0)
        return await execute_tool(name, params, pid, agent_id=aid)

    async def fast_exec(name, params, pid, aid):
        return await execute_tool(name, params, pid, agent_id=aid)

    events_a: list[dict] = []
    events_b: list[dict] = []
    try:
        binding_a = svc_a.steering_binding(agent_id=agent_id, project_id=project_id)
        binding_b = svc_b.steering_binding(agent_id=agent_id, project_id=project_id)

        async def run_b():
            await _collect(
                svc_b,
                events_b,
                project_id=project_id,
                agent_id=agent_id,
                system_prompt=_SYS,
                history=[],
                user_text="Turn B.",
                tool_executor=fast_exec,
                session_key=f"{project_id}:b",
                steering=binding_b,
            )
            b_done.set()

        await asyncio.gather(
            _collect(
                svc_a,
                events_a,
                project_id=project_id,
                agent_id=agent_id,
                system_prompt=_SYS,
                history=[],
                user_text="Turn A.",
                tool_executor=slow_exec,
                session_key=f"{project_id}:a",
                steering=binding_a,
            ),
            run_b(),
        )
    finally:
        await sup.shutdown()
        await steering_manager.abort(agent_id, project_id=project_id)

    terminals_a = [
        e["type"] for e in events_a if e["type"] in ("done", "error", "aborted")
    ]
    terminals_b = [
        e["type"] for e in events_b if e["type"] in ("done", "error", "aborted")
    ]
    # Zero spurious aborts: both turns complete cleanly on their own bindings.
    assert terminals_a == ["done"]
    assert terminals_b == ["done"]


@pytest.mark.asyncio
async def test_external_abort_still_reaches_only_the_scoped_binding():
    """An abort for project A must not leak into a concurrent project B turn."""
    await init_db()
    project_a = f"pi-prod-h5a-{uuid.uuid4()}"
    project_b = f"pi-prod-h5b-{uuid.uuid4()}"
    agent_id = f"h5-agent-{uuid.uuid4()}"
    await _mk_project(project_a, "Pi H-5 project A")
    await _mk_project(project_b, "Pi H-5 project B")

    sup = PiRuntimeSupervisor()
    abort_sent = asyncio.Event()
    svc_a = faux_service(
        [tool_call("list_tasks", {}), final_text("A should not finish")], sup
    )
    svc_b = faux_service([tool_call("list_tasks", {}), final_text("B done")], sup)

    async def exec_a(name, params, pid, aid):
        # An external abort for project A arrives while A is mid-turn.
        await steering_manager.abort(agent_id, project_id=project_a)
        abort_sent.set()
        await asyncio.sleep(0.3)  # let A's pump observe the abort
        return await execute_tool(name, params, pid, agent_id=aid)

    async def exec_b(name, params, pid, aid):
        # B stays alive across A's abort; its binding must keep working.
        await asyncio.wait_for(abort_sent.wait(), timeout=30.0)
        await asyncio.sleep(0.3)
        return await execute_tool(name, params, pid, agent_id=aid)

    events_a: list[dict] = []
    events_b: list[dict] = []
    try:
        await asyncio.gather(
            _collect(
                svc_a,
                events_a,
                project_id=project_a,
                agent_id=agent_id,
                system_prompt=_SYS,
                history=[],
                user_text="Turn A.",
                tool_executor=exec_a,
                session_key=f"{project_a}:a",
                steering=svc_a.steering_binding(
                    agent_id=agent_id, project_id=project_a
                ),
            ),
            _collect(
                svc_b,
                events_b,
                project_id=project_b,
                agent_id=agent_id,
                system_prompt=_SYS,
                history=[],
                user_text="Turn B.",
                tool_executor=exec_b,
                session_key=f"{project_b}:b",
                steering=svc_b.steering_binding(
                    agent_id=agent_id, project_id=project_b
                ),
            ),
        )
    finally:
        await sup.shutdown()
        await steering_manager.abort(agent_id)

    terminals_a = [
        e["type"] for e in events_a if e["type"] in ("done", "error", "aborted")
    ]
    terminals_b = [
        e["type"] for e in events_b if e["type"] in ("done", "error", "aborted")
    ]
    assert terminals_a == ["aborted"]  # the scoped abort lands on A exactly once
    assert terminals_b == ["done"]  # and never leaks into B


# ── H-7: failed session opens never leak or clobber ──────────────────────────
@pytest.mark.asyncio
async def test_hundred_failed_opens_leave_sessions_empty_and_capacity_intact():
    """100 failed opens against a live session key raise ``session_busy``,
    leave ``_sessions`` untouched, and the worker still accepts new sessions."""
    await init_db()
    project_id = f"pi-prod-h7-{uuid.uuid4()}"
    agent_id = f"h7-agent-{uuid.uuid4()}"
    await _mk_project(project_id, "Pi H-7 failed opens")

    sup = PiRuntimeSupervisor()
    svc = faux_service([final_text("capacity intact")], sup)

    async def exec_ok(name, params, pid, aid):
        return {"success": True, "result": {}}

    taken_key = f"{project_id}:taken"
    try:
        # Occupy one session for real so duplicate opens fail with session_busy.
        await sup.ensure_started()
        await sup.open_session(
            taken_key, system_prompt=_SYS, history=[], revision=None, catalog=[]
        )
        assert set(sup._sessions) == {taken_key}

        for _ in range(100):
            with pytest.raises(PiWorkerError):
                await svc.run_delegation(
                    project_id=project_id,
                    agent_id=agent_id,
                    system_prompt=_SYS,
                    task_text="duplicate open must fail",
                    tool_executor=exec_ok,
                    session_key=taken_key,
                )

        # No leak, no clobber: exactly the pre-opened session survives.
        assert set(sup._sessions) == {taken_key}
        await sup.close_session(taken_key)
        assert sup._sessions == {}

        # Capacity intact: a fresh real turn still opens and completes.
        result = await svc.run_delegation(
            project_id=project_id,
            agent_id=agent_id,
            system_prompt=_SYS,
            task_text="prove the worker still accepts sessions",
            tool_executor=exec_ok,
            session_key=f"{project_id}:fresh",
        )
        assert result["status"] == "success"
        assert result["text"] == "capacity intact"
        assert sup._sessions == {}
    finally:
        await sup.shutdown()


# ── H-9 (engine): telemetry distinguishes aborted from error ─────────────────
@pytest.mark.asyncio
async def test_turn_telemetry_distinguishes_aborted_from_error(monkeypatch):
    """An externally aborted turn records status ``aborted``; a failed turn
    records status ``error`` — never conflated."""
    await init_db()
    project_id = f"pi-prod-h9-{uuid.uuid4()}"
    agent_id = f"h9-agent-{uuid.uuid4()}"
    await _mk_project(project_id, "Pi H-9 telemetry")

    spans: list[dict] = []

    async def capture_span(**kwargs):
        spans.append(kwargs)

    monkeypatch.setattr(telemetry_recorder, "record_span", capture_span)

    sup = PiRuntimeSupervisor()
    svc_abort = faux_service([tool_call("list_tasks", {}), final_text("no")], sup)
    svc_error = faux_service([error_after_partial("partial before failure")], sup)

    async def abort_mid_turn(name, params, pid, aid):
        await steering_manager.abort(agent_id, project_id=project_id)
        await asyncio.sleep(0.3)
        return await execute_tool(name, params, pid, agent_id=aid)

    async def exec_ok(name, params, pid, aid):
        return await execute_tool(name, params, pid, agent_id=aid)

    try:
        events_a: list[dict] = []
        await _collect(
            svc_abort,
            events_a,
            project_id=project_id,
            agent_id=agent_id,
            system_prompt=_SYS,
            history=[],
            user_text="Abort me.",
            tool_executor=abort_mid_turn,
            session_key=f"{project_id}:abort",
            steering=svc_abort.steering_binding(
                agent_id=agent_id, project_id=project_id
            ),
        )
        assert [
            e["type"] for e in events_a if e["type"] in ("done", "error", "aborted")
        ] == ["aborted"]

        events_e: list[dict] = []
        await _collect(
            svc_error,
            events_e,
            project_id=project_id,
            agent_id=agent_id,
            system_prompt=_SYS,
            history=[],
            user_text="Fail.",
            tool_executor=exec_ok,
            session_key=f"{project_id}:error",
        )
        assert [
            e["type"] for e in events_e if e["type"] in ("done", "error", "aborted")
        ] == ["error"]
    finally:
        await sup.shutdown()

    turn_spans = [s for s in spans if s.get("event_kind") == "pi_runtime_turn"]
    assert [s["status"] for s in turn_spans] == ["aborted", "error"]
