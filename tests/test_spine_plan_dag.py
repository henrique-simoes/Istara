"""Plan DAG execution: a failed prerequisite blocks its dependents; one session is never shared.

F8 (2026-09-25 map): ``_execute_planned_task`` ran ready steps with ``asyncio.gather`` on ONE
``AsyncSession``. SQLAlchemy's asyncio guidance is one session per concurrent task: an
``AsyncSession`` is not safe to use from concurrent tasks. Failed steps were added to the
"executed" set, so their dependents ran anyway on a failed prerequisite, contradicting the
DAG semantics of LLMCompiler (Kim et al., ICML 2024), which the executor cites. Every step also
received ALL earlier results as "Previous findings", not only its dependencies'.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest


class _OverlapDetectingSession:
    """Stands in for the shared AsyncSession and records any concurrent use."""

    def __init__(self) -> None:
        self.in_use = 0
        self.overlaps = 0

    async def use(self) -> None:
        self.in_use += 1
        if self.in_use > 1:
            self.overlaps += 1
        await asyncio.sleep(0.01)
        self.in_use -= 1

    async def commit(self) -> None:
        await self.use()


def _orchestrator(monkeypatch, executed: list[str], contexts: dict[str, str], fail: set[str]):
    from app.core.agent import AgentOrchestrator
    from app.skills.base import SkillOutput

    class _Skill:
        def __init__(self, name):
            self.name = name

        async def execute(self, skill_input):
            step_id = self.name[-1].upper()  # each test plan gives step X the skill s-x
            executed.append(step_id)
            contexts[step_id] = skill_input.user_context
            await asyncio.sleep(0.01)
            if step_id in fail:
                raise RuntimeError(f"{step_id} broke")
            return SkillOutput(success=True, summary=f"result of {step_id}")

    orchestrator = AgentOrchestrator()

    async def _store(db, project_id, output, task):
        await db.use()

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(orchestrator, "_store_findings", _store)
    monkeypatch.setattr(orchestrator, "_mark_task_ready_for_review", _noop)
    monkeypatch.setattr(orchestrator, "_persist_agent_state", _noop)
    for name in (
        "broadcast_plan_progress",
        "broadcast_agent_thinking",
        "broadcast_task_progress",
        "broadcast_agent_status",
    ):
        monkeypatch.setattr(f"app.core.agent_research.{name}", _noop)
    skills = {name: _Skill(name) for name in ("s-a", "s-b", "s-c", "s-d")}
    monkeypatch.setattr(
        "app.core.agent_research.registry", SimpleNamespace(get=lambda name: skills.get(name))
    )
    return orchestrator


def _plan(*steps):
    from app.core.agent_models import ResearchPlan, ResearchStep

    return ResearchPlan(
        question="q",
        steps=[
            ResearchStep(id=i, description=f"step {i}", skill_name=s, depends_on=d)
            for i, s, d in steps
        ],
    )


@pytest.fixture
def run_plan(monkeypatch):
    async def _run(plan, fail=frozenset()):
        executed: list[str] = []
        contexts: dict[str, str] = {}
        orchestrator = _orchestrator(monkeypatch, executed, contexts, set(fail))
        db = _OverlapDetectingSession()
        task = SimpleNamespace(id="t1", project_id="p1", title="t", get_urls=lambda: [])
        project = SimpleNamespace(id="p1", project_context="", company_context="")
        rag = SimpleNamespace(has_context=False, context_text="")
        await orchestrator._execute_planned_task(db, task, project, plan, rag)
        return executed, contexts, db, plan

    return _run


async def test_dependents_of_a_failed_step_never_run(run_plan):
    plan = _plan(("A", "s-a", []), ("B", "s-b", ["A"]), ("C", "s-c", ["B"]))
    executed, _, _, plan = await run_plan(plan, fail={"A"})
    assert executed == ["A"]
    status = {s.id: s.status for s in plan.past_steps}
    assert status == {"A": "failed", "B": "blocked", "C": "blocked"}
    assert "A" in next(s for s in plan.past_steps if s.id == "B").result


async def test_parallel_steps_never_use_the_shared_session_concurrently(run_plan):
    plan = _plan(("A", "s-a", []), ("B", "s-b", []), ("C", "s-c", []), ("D", "s-d", []))
    executed, _, db, _ = await run_plan(plan)
    assert sorted(executed) == ["A", "B", "C", "D"]
    assert db.overlaps == 0


async def test_a_step_sees_only_its_dependencies_results(run_plan):
    plan = _plan(("A", "s-a", []), ("B", "s-b", []), ("C", "s-c", ["A"]))
    _, contexts, _, _ = await run_plan(plan)
    assert "result of A" in contexts["C"]
    assert "result of B" not in contexts["C"]
