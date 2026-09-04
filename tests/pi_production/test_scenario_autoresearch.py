"""Production scenario 10 (autoresearch.governed_experiment.slice) — the governed
Pi autoresearch mode on ``/autoresearch/start`` runs one bounded real Pi turn and
returns a candidate proposal only: no background loop, no promotion, no mutation.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks
from sqlalchemy import select

from app.api.routes import autoresearch as autoresearch_route
from app.config import settings
from app.core.pi_runtime import seams
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor
from app.models.database import async_session, init_db
from app.models.project import Project

from .harness import faux_service, final_text, requires_node

pytestmark = requires_node


@pytest.mark.asyncio
async def test_scenario10_governed_autoresearch_candidate_only_no_loop(monkeypatch):
    await init_db()
    project_id = f"pi-prod-s10-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi Production Scenario 10"))
        await db.commit()

    hypothesis = (
        "Lowering extraction temperature to 0.3 should raise coding reliability."
    )
    sup = PiRuntimeSupervisor()
    monkeypatch.setattr(seams, "_service", faux_service([final_text(hypothesis)], sup))

    added: list[object] = []

    async def fake_scope(*args, **kwargs):
        return project_id

    monkeypatch.setattr(settings, "autoresearch_enabled", True)
    monkeypatch.setattr(autoresearch_route, "_require_active_project_scope", fake_scope)
    monkeypatch.setattr(
        autoresearch_route, "_get_engine", lambda: SimpleNamespace(is_running=False)
    )

    background_tasks = BackgroundTasks()
    background_tasks.add_task = lambda fn, *a, **k: added.append((fn, a, k))

    try:
        result = await autoresearch_route.start_experiment(
            autoresearch_route.StartExperimentRequest(
                loop_type="model_temp",
                target="extraction",
                max_iterations=5,
                project_id=project_id,
                dry_run=False,
            ),
            SimpleNamespace(headers={"x-istara-agent-engine": "pi"}),
            background_tasks,
            None,
        )
    finally:
        await sup.shutdown()

    assert result["status"] == "candidate_proposal"
    assert result["proposal"]["hypothesis"] == hypothesis  # from the real Pi turn
    assert result["proposal"]["governance_required"] is True
    assert result["proposal"]["report_evidence"] is False
    assert result["proposal"]["promotion"] == "blocked_pending_human_review"
    assert result["production_mutation_allowed"] is False
    assert result["background_task_started"] is False
    assert result["runtime"]["engine"] == "pi"
    # No legacy runner loop was scheduled.
    assert added == []
    assert sup.is_running is False
