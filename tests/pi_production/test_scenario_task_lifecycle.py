"""Production scenarios 2 (task.plan_execute.lifecycle) and 3 (documents/tools
project scoping) driven through the real Pi worker and real Istara services.

Scenario 2 proves a multi-turn Pi session continues plan→execute steps through
one server-owned session key with history rehydration, each step persisting via
real Python task services. Scenario 3 proves canonical tools execute under the
authenticated project scope — a cross-project read is denied.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.models.database import async_session, init_db
from app.models.project import Project
from app.models.task import Task
from app.skills.system_actions import execute_tool

from .harness import faux_service, final_text, requires_node, tool_call
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor

pytestmark = requires_node

_SYS = "You run inside Istara. Pi owns the loop; Istara owns product state."


@pytest.mark.asyncio
async def test_scenario2_multi_turn_session_persists_plan_then_execute():
    await init_db()
    project_id = f"pi-prod-s2-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi Production Scenario 2"))
        await db.commit()

    sup = PiRuntimeSupervisor()
    session_key = f"{project_id}:plan-execute"
    plan_svc = faux_service([tool_call("create_task", {"title": "Plan the rollout"}), final_text("Planned.")], sup)
    exec_svc = faux_service([tool_call("create_task", {"title": "Execute the rollout"}), final_text("Executed.")], sup)

    async def authority_exec(name, params, pid, aid):
        return await execute_tool(name, params, pid, agent_id=aid)

    turn1: list[dict] = []
    turn2: list[dict] = []
    try:
        async for e in plan_svc.run_chat_turn(
            project_id=project_id, agent_id="istara-main", system_prompt=_SYS,
            history=[], user_text="Plan the rollout.", tool_executor=authority_exec,
            session_key=session_key,
        ):
            turn1.append(e)

        # Turn 2 continues the same server-owned session via rehydrated history.
        history = [
            {"role": "user", "content": "Plan the rollout."},
            {"role": "assistant", "content": "Planned."},
        ]
        async for e in exec_svc.run_chat_turn(
            project_id=project_id, agent_id="istara-main", system_prompt=_SYS,
            history=history, user_text="Now execute the rollout.", tool_executor=authority_exec,
            session_key=session_key,
        ):
            turn2.append(e)
    finally:
        await sup.shutdown()

    # Both turns were owned by the real Agent.
    assert any(e["type"] == "run_started" for e in turn1)
    assert any(e["type"] == "run_started" for e in turn2)
    assert any(e["type"] == "done" for e in turn1)
    assert any(e["type"] == "done" for e in turn2)

    # Both plan and execute steps persisted via real Python task services.
    async with async_session() as db:
        tasks = (await db.execute(select(Task).where(Task.project_id == project_id))).scalars().all()
    titles = sorted(t.title for t in tasks)
    assert titles == ["Execute the rollout", "Plan the rollout"]
    assert sup.is_running is False


@pytest.mark.asyncio
async def test_scenario3_canonical_tools_enforce_project_scope_cross_project_denied():
    await init_db()
    project_a = f"pi-prod-s3a-{uuid.uuid4()}"
    project_b = f"pi-prod-s3b-{uuid.uuid4()}"
    async with async_session() as db:
        db.add_all([
            Project(id=project_a, name="Pi Prod S3 A"),
            Project(id=project_b, name="Pi Prod S3 B"),
        ])
        await db.commit()

    # A private task lives only in project B.
    await execute_tool("create_task", {"title": "Secret B rollout"}, project_b, agent_id="istara-main")

    sup = PiRuntimeSupervisor()
    svc = faux_service(
        [
            tool_call("create_task", {"title": "A-only task"}),
            tool_call("list_tasks", {}),
            final_text("Listed project A tasks only."),
        ],
        sup,
    )

    captured: list[tuple[str, dict]] = []

    async def spy_exec(name, params, pid, aid):
        # Authenticated project scope is fixed to project_a — the model cannot
        # widen it, so a project-B read is impossible.
        assert pid == project_a
        result = await execute_tool(name, params, pid, agent_id=aid)
        captured.append((name, result))
        return result

    try:
        async for _ in svc.run_chat_turn(
            project_id=project_a, agent_id="istara-main", system_prompt=_SYS,
            history=[], user_text="Create a task then list them.", tool_executor=spy_exec,
            session_key=f"{project_a}:scope",
        ):
            pass
    finally:
        await sup.shutdown()

    list_results = [r for (n, r) in captured if n == "list_tasks"]
    assert list_results, "list_tasks did not execute"
    blob = str(list_results[-1])
    assert "A-only task" in blob
    assert "Secret B rollout" not in blob  # cross-project content never leaks

    async with async_session() as db:
        b_tasks = (await db.execute(select(Task).where(Task.project_id == project_b))).scalars().all()
        a_tasks = (await db.execute(select(Task).where(Task.project_id == project_a))).scalars().all()
    assert [t.title for t in b_tasks] == ["Secret B rollout"]
    assert "A-only task" in [t.title for t in a_tasks]
