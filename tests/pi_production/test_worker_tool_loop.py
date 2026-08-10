"""Production scenario 1 (chat.tool_loop.task_and_finding) — driven through the
real supervised Pi worker.

Proves AC-1/AC-4 for the tool loop: the real pi-agent-core Agent owns turn
progression and tool execution in a spawned Node child, while every tool call
round-trips to Python and executes the real canonical ``create_task`` tool
against the test-owned DB. No network, no ComputeRegistry, no orphan process.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.pi_runtime.supervisor import PiRuntimeSupervisor
from app.core.pi_runtime.tools import build_tool_catalog
from app.models.database import async_session, init_db
from app.models.project import Project
from app.models.task import Task
from app.skills.system_actions import execute_tool

from .harness import requires_node

pytestmark = requires_node


@pytest.mark.asyncio
async def test_pi_worker_owns_tool_loop_and_persists_task():
    await init_db()
    project_id = f"pi-prod-scenario1-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi Production Scenario 1"))
        await db.commit()

    supervisor = PiRuntimeSupervisor()
    observed: list[str] = []
    executed_tools: list[tuple[str, dict]] = []
    final_text: list[str] = []

    try:
        await supervisor.ensure_started()
        assert supervisor.is_running

        catalog = build_tool_catalog(["create_task"])
        assert catalog and catalog[0]["name"] == "create_task"

        session_key = f"{project_id}:scenario-1"
        await supervisor.open_session(
            session_key,
            system_prompt="You run inside Istara. Pi owns the loop; Istara owns product state.",
            history=[],
            revision="rev-1",
            catalog=catalog,
        )
        await supervisor.bind_provider(
            session_key,
            {
                "endpoint_id": "faux-test",
                "provider_kind": "faux",
                "faux_responses": [
                    {
                        "tool_calls": [
                            {
                                "name": "create_task",
                                "arguments": {"title": "Pi runtime scenario task", "priority": "high"},
                            }
                        ],
                        "stop_reason": "toolUse",
                    },
                    {"text": "Created a task through Istara canonical tools."},
                ],
            },
        )

        async def tool_handler(name: str, args: dict) -> dict:
            executed_tools.append((name, args))
            # Authority executes the real canonical tool against the test DB.
            result = await execute_tool(name, args, project_id, agent_id="istara-main")
            if result.get("success"):
                return {"ok": True, "result": result.get("result")}
            return {"ok": False, "error": result.get("error")}

        async for frame in supervisor.run_turn(
            session_key, "Create a task through Istara tools.", tool_handler
        ):
            observed.append(frame["type"])
            if frame["type"] == "assistant.delta":
                final_text.append(frame.get("text", ""))

        await supervisor.close_session(session_key)
    finally:
        await supervisor.shutdown()

    # The real Agent observably owned the turn and the tool loop.
    assert "run.started" in observed
    assert "tool.call" in observed
    assert "run.completed" in observed
    assert executed_tools == [("create_task", {"title": "Pi runtime scenario task", "priority": "high"})]
    assert "".join(final_text).strip()

    # Istara persisted the task via the real canonical tool — not a lab facade.
    async with async_session() as db:
        tasks = (
            await db.execute(select(Task).where(Task.project_id == project_id))
        ).scalars().all()
    assert len(tasks) == 1
    assert tasks[0].title == "Pi runtime scenario task"

    # Owned teardown: no live worker after shutdown.
    assert supervisor.is_running is False


@pytest.mark.asyncio
async def test_pi_worker_fails_closed_without_provider_binding():
    """A prompt before any provider binding must fail closed, never silently
    fall back to another transport."""
    supervisor = PiRuntimeSupervisor()
    terminal: list[dict] = []
    try:
        await supervisor.ensure_started()
        session_key = f"nobind-{uuid.uuid4()}"
        await supervisor.open_session(
            session_key, system_prompt="s", history=[], revision="r", catalog=[]
        )

        async def tool_handler(name, args):  # pragma: no cover - never called
            return {"ok": False, "error": "unexpected"}

        async for frame in supervisor.run_turn(session_key, "go", tool_handler):
            terminal.append(frame)
        await supervisor.close_session(session_key)
    finally:
        await supervisor.shutdown()

    assert terminal and terminal[-1]["type"] == "run.failed"
    assert terminal[-1]["error"] == "no_provider_bound"
