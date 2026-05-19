"""Tests for project-scoped agent learning memory."""

import uuid

import pytest

from app.core.agent_learning import agent_learning
from app.models.database import init_db


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
