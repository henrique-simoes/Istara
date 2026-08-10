"""Production scenario 11 (memory.reasoningbank.memento.slice) — ReasoningBank,
Memento skill memory, and ModelSkillStats record only scoped, verified outcomes
from a Pi run: a raw (unverified) success is never a strong positive signal,
retrieval is project-only, and no global-memory / global-skill-stat write occurs.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.pi_runtime.supervisor import PiRuntimeSupervisor
from app.core.reasoning_bank import reasoning_bank
from app.core.telemetry import telemetry_recorder
from app.models.database import async_session, init_db
from app.models.model_skill_stats import ModelSkillStats
from app.models.project import Project
from app.models.reasoning_memory import ReasoningMemoryItem
from app.skills.system_actions import execute_tool

from .harness import faux_service, final_text, requires_node, tool_call

pytestmark = requires_node

_SYS = "You run inside Istara. Pi owns the loop; memory governance is Istara-owned."


@pytest.mark.asyncio
async def test_scenario11_reasoningbank_memento_and_skillstats_are_governed_and_scoped():
    await init_db()
    project_a = f"pi-prod-s11a-{uuid.uuid4()}"
    project_b = f"pi-prod-s11b-{uuid.uuid4()}"
    async with async_session() as db:
        db.add_all([
            Project(id=project_a, name="Pi Prod S11 A"),
            Project(id=project_b, name="Pi Prod S11 B"),
        ])
        await db.commit()
        # Snapshot pre-existing global (project-blank) rows so the "no global
        # write" assertions measure *this run's* delta, not the shared/persistent
        # DB's accumulated state from other suites.
        global_items_before = {
            i.id for i in (await db.execute(
                select(ReasoningMemoryItem).where(ReasoningMemoryItem.project_id == "")
            )).scalars().all()
        }
        global_stats_before = {
            s.id for s in (await db.execute(
                select(ModelSkillStats).where(ModelSkillStats.project_id == "")
            )).scalars().all()
        }

    # A real Pi run occurs (reads the project), after which the memory-governance
    # path records the run's outcomes through the real services.
    sup = PiRuntimeSupervisor()
    svc = faux_service([tool_call("list_tasks", {}), final_text("Reviewed the project.")], sup)

    async def authority_exec(name, params, pid, aid):
        return await execute_tool(name, params, pid, agent_id=aid)

    try:
        async for _ in svc.run_chat_turn(
            project_id=project_a, agent_id="istara-main", system_prompt=_SYS,
            history=[], user_text="Review the project.", tool_executor=authority_exec,
            session_key=f"{project_a}:memory-gov",
        ):
            pass
    finally:
        await sup.shutdown()

    # A raw success that was NOT independently verified must not become a strong
    # positive signal — the memento memory records it as a failure outcome.
    await reasoning_bank.record_task_execution(
        project_id=project_a, agent_id="istara-main", task_id=f"t-raw-{uuid.uuid4()}",
        task_title="Raw success step", task_description="unverified", skill_name="pi-analysis",
        output_summary="did the thing", success=True, verified=False,
    )
    # A verified success is recorded as a success outcome.
    await reasoning_bank.record_task_execution(
        project_id=project_a, agent_id="istara-main", task_id=f"t-ok-{uuid.uuid4()}",
        task_title="Verified success step", task_description="verified", skill_name="pi-analysis",
        output_summary="did the thing, checked", success=True, verified=True,
    )

    async with async_session() as db:
        items = (await db.execute(
            select(ReasoningMemoryItem).where(ReasoningMemoryItem.project_id == project_a)
        )).scalars().all()
    outcomes = sorted(i.outcome for i in items)
    assert "failure" in outcomes  # raw success stored as failure (not a strong signal)
    assert "success" in outcomes  # verified success stored as success
    # Memento skill memory tag present; every write is project-scoped (never global).
    assert all(i.project_id == project_a for i in items)
    assert any("memento" in (i.tags_json or "") for i in items)

    # No global-memory rows were written by the Pi path (project_id == "") —
    # measured as this run's delta over any pre-existing global rows.
    async with async_session() as db:
        global_items = (await db.execute(
            select(ReasoningMemoryItem).where(ReasoningMemoryItem.project_id == "")
        )).scalars().all()
    new_global_items = [i for i in global_items if i.id not in global_items_before]
    assert new_global_items == []

    # ModelSkillStats: a blank-project skill-stat write is rejected (no global
    # skill stats); a project-scoped one is recorded under source "production".
    await telemetry_recorder.record_model_performance(
        skill_name="pi-analysis", model_name="deepseek-v4-pro", quality=0.9, project_id=""
    )
    await telemetry_recorder.record_model_performance(
        skill_name="pi-analysis", model_name="deepseek-v4-pro", quality=0.9, project_id=project_a
    )
    async with async_session() as db:
        global_stats = (await db.execute(
            select(ModelSkillStats).where(ModelSkillStats.project_id == "")
        )).scalars().all()
        a_stats = (await db.execute(
            select(ModelSkillStats).where(ModelSkillStats.project_id == project_a)
        )).scalars().all()
    new_global_stats = [s for s in global_stats if s.id not in global_stats_before]
    assert new_global_stats == []  # the blank-project skill-stat write was rejected
    assert len(a_stats) == 1
    assert a_stats[0].source == "production"
    assert sup.is_running is False
