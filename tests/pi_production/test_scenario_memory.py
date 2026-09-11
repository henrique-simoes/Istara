"""Production scenario 5 (memory.rag.slice) — a selected Pi turn drives the real
``search_memory`` tool (project-scoped RAG) and the project reasoning-memory
store enforces project-only reads with cross-project denial.

The model can never widen the authenticated project scope, so a cross-project
memory read is structurally impossible; the reasoning-memory store confirms the
same isolation for seeded, source-grounded memories.
"""

from __future__ import annotations

import uuid

import pytest

from app.core.pi_runtime.supervisor import PiRuntimeSupervisor
from app.core.reasoning_bank import reasoning_bank
from app.models.database import async_session, init_db
from app.models.project import Project
from app.skills.system_actions import execute_tool

from .harness import faux_service, final_text, requires_node, tool_call

pytestmark = requires_node

_SYS = "You run inside Istara. Pi owns the loop."


@pytest.mark.asyncio
async def test_scenario5_search_memory_and_reasoning_store_are_project_scoped():
    await init_db()
    project_a = f"pi-prod-s5a-{uuid.uuid4()}"
    project_b = f"pi-prod-s5b-{uuid.uuid4()}"
    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_a, name="Pi Prod S5 A"),
                Project(id=project_b, name="Pi Prod S5 B"),
            ]
        )
        await db.commit()

    # Seed a source-grounded reasoning memory in each project.
    marker = uuid.uuid4().hex
    await reasoning_bank.record_memory(
        project_id=project_a,
        agent_id="istara-main",
        source_kind="manual",
        outcome="success",
        title=f"Retention insight {marker}",
        content=f"Project A retention memory {marker}: onboarding drives 30-day retention.",
        confidence=0.9,
    )
    await reasoning_bank.record_memory(
        project_id=project_b,
        agent_id="istara-main",
        source_kind="manual",
        outcome="success",
        title="Project B secret",
        content=f"Project B private memory {marker}: unrelated experiment note.",
        confidence=0.9,
    )

    sup = PiRuntimeSupervisor()
    svc = faux_service(
        [
            tool_call("search_memory", {"query": "retention"}),
            final_text("Searched project memory."),
        ],
        sup,
    )

    scopes: list[str] = []

    async def scoped_exec(name, params, pid, aid):
        # The authenticated project scope is fixed by the caller — project A.
        scopes.append(pid)
        return await execute_tool(name, params, pid, agent_id=aid)

    try:
        async for _ in svc.run_chat_turn(
            project_id=project_a,
            agent_id="istara-main",
            system_prompt=_SYS,
            history=[],
            user_text="What do we know about retention?",
            tool_executor=scoped_exec,
            session_key=f"{project_a}:memory",
        ):
            pass
    finally:
        await sup.shutdown()

    # The Pi turn ran search_memory under project A scope only — never project B.
    assert scopes == [project_a]

    # Project-only reads: A retrieves A's memory; the cross-project read is denied
    # and global memory is not mixed in without explicit opt-in.
    a_hits = await reasoning_bank.retrieve(
        project_id=project_a, query="retention", include_global=False
    )
    a_blob = " ".join(str(h) for h in a_hits)
    assert marker in a_blob
    assert "Project A retention memory" in a_blob
    assert "Project B private memory" not in a_blob

    b_hits = await reasoning_bank.retrieve(
        project_id=project_b, query="retention", include_global=False
    )
    b_blob = " ".join(str(h) for h in b_hits)
    assert (
        "Project A retention memory" not in b_blob
    )  # cross-project content never leaks
    assert sup.is_running is False
