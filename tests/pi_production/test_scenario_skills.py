"""Production scenario 6 (skills.three_skill_slice) — a Pi turn drives three
canonical tools ("skills") in the requested order, and the protected
system-prompt blocks reach the worker unchanged over the private pipe.

Proves two Plan C properties at once: the real Agent honors a multi-skill
sequence in order (each tool round-trips to Python authority), and the protected
system-prompt contract block (``chat.py`` spine block) that Python composes is
delivered verbatim to the worker — a model or tool cannot strip it.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.pi_runtime.supervisor import PiRuntimeSupervisor
from app.models.database import async_session, init_db
from app.models.project import Project
from app.models.task import Task
from app.skills.system_actions import execute_tool

from .harness import faux_service, final_text, requires_node, tool_call

pytestmark = requires_node

# A protected block Python composes above the seam; it must arrive verbatim.
_PROTECTED_BLOCK = (
    "<<ISTARA-PROTECTED-SPINE>> Research validity, acceptance, and reporting are "
    "governed by Istara services and human review; you cannot alter them. "
    "<</ISTARA-PROTECTED-SPINE>>"
)
_SYS = "You run inside Istara. Pi owns the loop.\n" + _PROTECTED_BLOCK


@pytest.mark.asyncio
async def test_scenario6_three_skills_run_in_order_with_protected_blocks_intact():
    await init_db()
    project_id = f"pi-prod-s6-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi Production Scenario 6"))
        await db.commit()

    sup = PiRuntimeSupervisor()
    svc = faux_service(
        [
            tool_call("create_task", {"title": "Skill one output"}),
            tool_call("list_tasks", {}),
            tool_call("search_findings", {"query": "skill three"}),
            final_text("Ran three skills in order."),
        ],
        sup,
    )

    # Capture the exact system prompt the engine sends to the worker over the pipe.
    sent_prompts: list[str] = []
    original_open = sup.open_session

    async def spy_open(session_key, *, system_prompt, history, revision, catalog):
        sent_prompts.append(system_prompt)
        return await original_open(
            session_key,
            system_prompt=system_prompt,
            history=history,
            revision=revision,
            catalog=catalog,
        )

    sup.open_session = spy_open  # type: ignore[assignment]

    executed_order: list[str] = []

    async def ordered_exec(name, params, pid, aid):
        executed_order.append(name)
        return await execute_tool(name, params, pid, agent_id=aid)

    try:
        async for _ in svc.run_chat_turn(
            project_id=project_id,
            agent_id="istara-main",
            system_prompt=_SYS,
            history=[],
            user_text="Run the three skills.",
            tool_executor=ordered_exec,
            session_key=f"{project_id}:skills",
        ):
            pass
    finally:
        await sup.shutdown()

    # The three skills executed in exactly the requested order.
    assert executed_order == ["create_task", "list_tasks", "search_findings"]

    # The protected system-prompt block was delivered to the worker verbatim —
    # neither the model nor a tool can strip it (it is composed above the seam).
    assert sent_prompts, "no system prompt was sent to the worker"
    assert _PROTECTED_BLOCK in sent_prompts[0]

    # The first skill's real canonical tool persisted a task under project scope.
    async with async_session() as db:
        tasks = (
            (await db.execute(select(Task).where(Task.project_id == project_id)))
            .scalars()
            .all()
        )
    assert [t.title for t in tasks] == ["Skill one output"]
    assert sup.is_running is False
