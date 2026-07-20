"""Production scenario 13 (steering.system_prompt.loop.slice) — the steering
bridge against a live Pi turn: a queued steer is delivered once mid-turn, and an
abort produces exactly one terminal event with full cleanup.
"""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

import pytest

from app.core.pi_runtime import seams
from app.api.routes import chat as chat_route
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor
from app.core.steering import steering_manager
from app.models.database import async_session, init_db
from app.models.project import Project
from app.skills.system_actions import execute_tool

from .harness import faux_service, final_text, requires_node, tool_call

pytestmark = requires_node

_SYS = "You run inside Istara. Pi owns the loop."


@pytest.mark.asyncio
async def test_scenario13_queued_steer_delivered_once_mid_turn():
    await init_db()
    project_id = f"pi-prod-s13a-{uuid.uuid4()}"
    agent_id = f"steer-agent-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi Production Scenario 13a"))
        await db.commit()

    sup = PiRuntimeSupervisor()
    svc = faux_service([tool_call("list_tasks", {}), final_text("done")], sup)

    steer_calls: list[str] = []
    original_steer = sup.steer

    async def spy_steer(session_key, text):
        steer_calls.append(text)
        await original_steer(session_key, text)

    sup.steer = spy_steer  # type: ignore[assignment]

    # Queue a steering message before the turn; the bridge must deliver it once.
    await steering_manager.steer(
        agent_id, "Also confirm the accessibility pass.", project_id=project_id
    )

    async def slow_exec(name, params, pid, aid):
        # Pause inside the tool call so the steering pump runs mid-turn.
        await asyncio.sleep(0.2)
        return await execute_tool(name, params, pid, agent_id=aid)

    try:
        binding = svc.steering_binding(agent_id=agent_id, project_id=project_id)
        async for _ in svc.run_chat_turn(
            project_id=project_id, agent_id=agent_id, system_prompt=_SYS,
            history=[], user_text="List tasks.", tool_executor=slow_exec,
            session_key=f"{project_id}:steer", steering=binding,
        ):
            pass
    finally:
        await sup.shutdown()
        await steering_manager.abort(agent_id, project_id=project_id)

    assert steer_calls == ["Also confirm the accessibility pass."]  # delivered exactly once
    # The queue was drained (not left pending).
    assert steering_manager.get_status(agent_id, project_id=project_id)["steering_queue_count"] == 0


@pytest.mark.asyncio
async def test_scenario13_abort_yields_exactly_one_terminal_event_and_cleanup():
    await init_db()
    project_id = f"pi-prod-s13b-{uuid.uuid4()}"
    agent_id = f"abort-agent-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi Production Scenario 13b"))
        await db.commit()

    sup = PiRuntimeSupervisor()
    svc = faux_service([tool_call("list_tasks", {}), final_text("should not finish")], sup)

    async def abort_mid_turn(name, params, pid, aid):
        # An external abort arrives while the turn is paused on this tool call.
        await steering_manager.abort(agent_id, project_id=project_id)
        await asyncio.sleep(0.3)  # let the steering pump observe the abort
        return await execute_tool(name, params, pid, agent_id=aid)

    events: list[dict] = []
    try:
        binding = svc.steering_binding(agent_id=agent_id, project_id=project_id)
        async for e in svc.run_chat_turn(
            project_id=project_id, agent_id=agent_id, system_prompt=_SYS,
            history=[], user_text="List tasks.", tool_executor=abort_mid_turn,
            session_key=f"{project_id}:abort", steering=binding,
        ):
            events.append(e)
    finally:
        await sup.shutdown()

    terminals = [e for e in events if e["type"] in ("done", "error", "aborted")]
    assert len(terminals) == 1
    assert terminals[0]["type"] == "aborted"
    # No live worker, no stuck session after teardown.
    assert sup.is_running is False


@pytest.mark.asyncio
async def test_scenario13_production_chat_caller_binds_project_scoped_steering(monkeypatch):
    """The real Pi chat caller constructs and forwards its steering binding.

    This guards the integration boundary that a direct engine test cannot: a
    selected chat turn must hand the exact authenticated project and selected
    agent to ``steering_binding`` before it calls ``run_chat_turn``.
    """
    await init_db()
    project_id = f"pi-prod-s13-route-{uuid.uuid4()}"
    agent_id = f"chat-steer-agent-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi Production Scenario 13 Chat Route"))
        await db.commit()

    captured: dict[str, object] = {}

    class _ChatService:
        def steering_binding(self, *, agent_id: str, project_id: str):
            captured["binding_args"] = (agent_id, project_id)
            return "bound-steering"

        async def run_chat_turn(self, **kwargs):
            captured["turn_steering"] = kwargs["steering"]
            yield {"type": "content", "text": "Steering is bound."}
            yield {"type": "done"}

    monkeypatch.setattr(chat_route, "_get_pi_execution_service", lambda: _ChatService())
    request = SimpleNamespace(project_id=project_id, session_id="steering-route")
    events = [
        event
        async for event in chat_route._generate_pi_runtime(
            [{"role": "user", "content": "Confirm steering."}], [], [], request, agent_id
        )
    ]

    assert captured["binding_args"] == (agent_id, project_id)
    assert captured["turn_steering"] == "bound-steering"
    assert any("Steering is bound." in event for event in events)
