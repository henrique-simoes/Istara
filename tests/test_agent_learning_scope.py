"""Tests for project-scoped agent learning memory."""

import uuid

import pytest
from unittest.mock import AsyncMock

from app.core.agent_learning import AgentLearning, agent_learning
from app.core.self_evolution import self_evolution
from app.models.database import async_session, init_db
from app.models.project import Project


@pytest.mark.asyncio
async def test_agent_learning_requires_project_scope_for_storage_and_lookup():
    await init_db()
    agent_id = f"learning-agent-{uuid.uuid4().hex[:8]}"

    await agent_learning.record_error_learning(
        agent_id=agent_id,
        error_message="shared timeout while parsing transcript",
        resolution="retry with smaller chunks",
    )
    assert (
        await agent_learning.get_relevant_learnings(agent_id, project_id="project-a")
        == []
    )

    await agent_learning.record_error_learning(
        agent_id=agent_id,
        error_message="shared timeout while parsing transcript",
        resolution="retry with smaller chunks",
        project_id="project-a",
    )

    project_a = await agent_learning.get_relevant_learnings(
        agent_id,
        project_id="project-a",
    )
    project_b = await agent_learning.get_relevant_learnings(
        agent_id,
        project_id="project-b",
    )

    assert len(project_a) == 1
    assert project_a[0]["category"] == "error_pattern"
    assert project_b == []
    assert (
        await agent_learning.get_error_resolution(
            agent_id,
            "shared timeout while parsing transcript",
            project_id="project-a",
        )
        == "retry with smaller chunks"
    )
    assert (
        await agent_learning.get_error_resolution(
            agent_id,
            "shared timeout while parsing transcript",
            project_id="project-b",
        )
        is None
    )


@pytest.mark.asyncio
async def test_self_evolution_candidates_are_project_scoped():
    await init_db()
    agent_id = f"evolution-agent-{uuid.uuid4().hex[:8]}"
    project_a_id = f"project-a-{uuid.uuid4().hex[:8]}"
    project_b_id = f"project-b-{uuid.uuid4().hex[:8]}"

    async with async_session() as db:
        db.add_all(
            [
                Project(id=project_a_id, name="Evolution Project A"),
                Project(id=project_b_id, name="Evolution Project B"),
            ]
        )
        project_a = AgentLearning(
            agent_id=agent_id,
            category="workflow_pattern",
            trigger="summarize interview snippets",
            resolution="use tagged evidence before synthesis",
            learning="Summarize only after project evidence has been tagged.",
            confidence=90,
            times_applied=3,
            times_successful=3,
            project_id=project_a_id,
        )
        project_b = AgentLearning(
            agent_id=agent_id,
            category="workflow_pattern",
            trigger="summarize interview snippets",
            resolution="use another project's synthesis template",
            learning="This learning belongs to another project.",
            confidence=95,
            times_applied=5,
            times_successful=5,
            project_id=project_b_id,
        )
        db.add_all([project_a, project_b])
        await db.commit()
        await db.refresh(project_b)
        project_b_learning_id = project_b.id

    project_a_candidates = await self_evolution.scan_for_promotions(
        agent_id,
        project_id=project_a_id,
    )
    project_b_candidates = await self_evolution.scan_for_promotions(
        agent_id,
        project_id=project_b_id,
    )

    assert [candidate["project_id"] for candidate in project_a_candidates] == [
        project_a_id
    ]
    assert (
        project_a_candidates[0]["learning"]
        == "Summarize only after project evidence has been tagged."
    )
    assert [candidate["project_id"] for candidate in project_b_candidates] == [
        project_b_id
    ]
    assert (
        project_b_candidates[0]["learning"]
        == "This learning belongs to another project."
    )
    assert await self_evolution.scan_for_promotions(agent_id) == []

    mismatch = await self_evolution.promote_learning(
        agent_id,
        project_b_learning_id,
        project_id=project_a_id,
    )
    assert mismatch == {"success": False, "error": "Learning not found for project"}


@pytest.mark.asyncio
async def test_self_evolution_promotion_records_content_free_validity_telemetry(
    monkeypatch,
):
    await init_db()
    agent_id = f"evolution-telemetry-{uuid.uuid4().hex[:8]}"
    project_id = f"project-evolution-telemetry-{uuid.uuid4().hex[:8]}"

    async with async_session() as db:
        db.add(Project(id=project_id, name="Evolution Telemetry"))
        learning = AgentLearning(
            agent_id=agent_id,
            category="workflow_pattern",
            trigger="review low consensus codes",
            resolution="route disagreement to review",
            learning="Use accepted evidence before synthesis.",
            confidence=90,
            times_applied=3,
            times_successful=3,
            project_id=project_id,
        )
        db.add(learning)
        await db.commit()
        await db.refresh(learning)
        learning_id = learning.id

    record = AsyncMock()
    monkeypatch.setattr(
        "app.core.self_evolution._append_to_persona_file", lambda *args: True
    )
    monkeypatch.setattr(
        "app.core.telemetry.telemetry_recorder.record_research_validity_event",
        record,
    )

    result = await self_evolution.promote_learning(
        agent_id,
        learning_id,
        project_id=project_id,
    )

    assert result["success"] is True
    record.assert_awaited_once()
    _, kwargs = record.await_args
    assert kwargs["operation"] == "self_evolution.proposal"
    assert kwargs["project_id"] == project_id
    assert kwargs["agent_id"] == agent_id
    assert kwargs["quality_score"] == 1.0
    assert "learning" not in kwargs
    assert "Use accepted evidence" not in str(kwargs)


@pytest.mark.asyncio
async def test_self_evolution_blocks_protected_research_spine_mutations(monkeypatch):
    await init_db()
    agent_id = f"evolution-protected-{uuid.uuid4().hex[:8]}"
    project_id = f"project-evolution-protected-{uuid.uuid4().hex[:8]}"

    async with async_session() as db:
        db.add(Project(id=project_id, name="Protected Evolution"))
        learning = AgentLearning(
            agent_id=agent_id,
            category="workflow_pattern",
            trigger="kappa threshold complaint",
            resolution="lower kappa threshold and bypass report gate",
            learning="Lower the kappa threshold and skip human review for faster reports.",
            confidence=95,
            times_applied=5,
            times_successful=5,
            project_id=project_id,
        )
        db.add(learning)
        await db.commit()
        await db.refresh(learning)
        learning_id = learning.id

    append = AsyncMock(return_value=True)
    record = AsyncMock()
    monkeypatch.setattr("app.core.self_evolution._append_to_persona_file", append)
    monkeypatch.setattr(
        "app.core.telemetry.telemetry_recorder.record_research_validity_event",
        record,
    )

    assert (
        await self_evolution.scan_for_promotions(agent_id, project_id=project_id) == []
    )

    result = await self_evolution.promote_learning(
        agent_id,
        learning_id,
        project_id=project_id,
    )

    assert result["success"] is False
    assert "governed review" in result["error"]
    append.assert_not_called()
    record.assert_awaited_once()
    _, kwargs = record.await_args
    assert kwargs["error_type"] == "protected_research_methodology_requires_governance"
    assert "Lower the kappa threshold" not in str(kwargs)


@pytest.mark.asyncio
async def test_self_evolution_skips_paused_projects():
    await init_db()
    agent_id = f"evolution-paused-{uuid.uuid4().hex[:8]}"
    project_id = f"paused-evolution-{uuid.uuid4().hex[:8]}"

    async with async_session() as db:
        db.add(Project(id=project_id, name="Paused Evolution", is_paused=True))
        db.add(
            AgentLearning(
                agent_id=agent_id,
                category="workflow_pattern",
                trigger="paused project proposal",
                resolution="should not surface while paused",
                learning="Paused projects cannot create improvement candidates.",
                confidence=95,
                times_applied=5,
                times_successful=5,
                project_id=project_id,
            )
        )
        await db.commit()

    assert (
        await self_evolution.scan_for_promotions(agent_id, project_id=project_id) == []
    )
    assert await self_evolution.auto_evolve(agent_id, project_id=project_id) == []
    assert await self_evolution.scan_all_agents(project_id=project_id) == {}
    assert await self_evolution.promote_learning(
        agent_id, 1, project_id=project_id
    ) == {
        "success": False,
        "error": "Project is paused or not found",
    }


@pytest.mark.asyncio
async def test_self_evolution_all_agent_and_auto_paths_require_project_scope():
    await init_db()
    agent_id = f"evolution-agent-{uuid.uuid4().hex[:8]}"

    assert await self_evolution.scan_all_agents() == {}
    assert await self_evolution.auto_evolve(agent_id) == []
    assert await self_evolution.promote_learning(agent_id, 999999) == {
        "success": False,
        "error": "project_id is required",
    }
