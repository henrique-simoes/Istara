"""Tests for project-scoped agent learning memory."""

import uuid

import pytest

from app.core.agent_learning import AgentLearning, agent_learning
from app.core.self_evolution import self_evolution
from app.models.database import async_session, init_db


@pytest.mark.asyncio
async def test_agent_learning_requires_project_scope_for_storage_and_lookup():
    await init_db()
    agent_id = f"learning-agent-{uuid.uuid4().hex[:8]}"

    await agent_learning.record_error_learning(
        agent_id=agent_id,
        error_message="shared timeout while parsing transcript",
        resolution="retry with smaller chunks",
    )
    assert await agent_learning.get_relevant_learnings(agent_id, project_id="project-a") == []

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

    async with async_session() as db:
        project_a = AgentLearning(
            agent_id=agent_id,
            category="workflow_pattern",
            trigger="summarize interview snippets",
            resolution="use tagged evidence before synthesis",
            learning="Summarize only after project evidence has been tagged.",
            confidence=90,
            times_applied=3,
            times_successful=3,
            project_id="project-a",
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
            project_id="project-b",
        )
        db.add_all([project_a, project_b])
        await db.commit()
        await db.refresh(project_b)
        project_b_id = project_b.id

    project_a_candidates = await self_evolution.scan_for_promotions(
        agent_id,
        project_id="project-a",
    )
    project_b_candidates = await self_evolution.scan_for_promotions(
        agent_id,
        project_id="project-b",
    )

    assert [candidate["project_id"] for candidate in project_a_candidates] == ["project-a"]
    assert project_a_candidates[0]["learning"] == "Summarize only after project evidence has been tagged."
    assert [candidate["project_id"] for candidate in project_b_candidates] == ["project-b"]
    assert project_b_candidates[0]["learning"] == "This learning belongs to another project."
    assert await self_evolution.scan_for_promotions(agent_id) == []

    mismatch = await self_evolution.promote_learning(
        agent_id,
        project_b_id,
        project_id="project-a",
    )
    assert mismatch == {"success": False, "error": "Learning not found for project"}


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
