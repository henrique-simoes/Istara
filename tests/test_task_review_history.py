"""Tests for preserving human review context when agent work fails."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.task import Task, TaskStatus


@pytest.mark.asyncio
async def test_custom_worker_failure_preserves_existing_human_revision_instruction(monkeypatch):
    """An orphaned custom task keeps human guidance while exposing the failure reason."""
    from app.agents import custom_worker

    class _NoProjectResult:
        @staticmethod
        def scalar_one_or_none():
            return None

    class _FakeDb:
        async def execute(self, statement):  # noqa: ANN001
            del statement
            return _NoProjectResult()

        async def commit(self) -> None:
            return None

    human_instruction = "Keep the approved quote set and repair only the unsupported pricing claim."
    task = Task(
        id="orphaned-custom-worker-review-history-task",
        project_id="missing-project",
        agent_id="custom-worker-agent",
        title="Preserve human guidance after worker failure",
        status=TaskStatus.BACKLOG,
        what_to_review=human_instruction,
    )
    worker = custom_worker.CustomAgentWorker("custom-worker-agent", "Test worker")
    monkeypatch.setattr(worker, "_update_db_state", AsyncMock())
    monkeypatch.setattr(custom_worker, "broadcast_agent_status", AsyncMock())

    await worker._execute_task(_FakeDb(), task, SimpleNamespace())

    assert task.status == TaskStatus.IN_REVIEW
    assert task.review_state == "needs_revision"
    assert task.what_to_review == human_instruction
    assert "project" in task.last_review_feedback.lower()


@pytest.mark.asyncio
async def test_custom_worker_failure_broadcasts_terminal_retry_state(monkeypatch):
    """Early worker failures must clear progress and update the live UI."""
    from app.agents import custom_worker
    from app.core.agent import agent as agent_orchestrator

    class _ProjectResult:
        @staticmethod
        def scalar_one_or_none():
            return SimpleNamespace(id="project-without-provider")

    class _FakeDb:
        async def execute(self, statement):  # noqa: ANN001
            del statement
            return _ProjectResult()

        async def commit(self) -> None:
            return None

    task = Task(
        id="custom-worker-provider-failure-task",
        project_id="project-without-provider",
        agent_id="custom-worker-agent",
        title="Expose provider failure to the live UI",
        status=TaskStatus.BACKLOG,
    )
    worker = custom_worker.CustomAgentWorker("custom-worker-agent", "Test worker")
    monkeypatch.setattr(worker, "_update_db_state", AsyncMock())
    status_mock = AsyncMock()
    progress_mock = AsyncMock()
    monkeypatch.setattr(custom_worker, "broadcast_agent_status", status_mock)
    monkeypatch.setattr(custom_worker, "broadcast_task_progress", progress_mock, raising=False)
    monkeypatch.setattr(
        agent_orchestrator,
        "_execute_task",
        AsyncMock(side_effect=RuntimeError("missing_keychain_secret")),
    )

    await worker._execute_task(_FakeDb(), task, SimpleNamespace())

    assert task.status == TaskStatus.BACKLOG
    assert task.progress == 0.0
    assert task.agent_notes == "Error: missing_keychain_secret"
    progress_mock.assert_awaited_once_with(
        task.id,
        0.0,
        "Execution failed: missing_keychain_secret",
        outcome="retry_scheduled",
        project_id=task.project_id,
    )
    assert status_mock.await_count == 2
    status_mock.assert_any_await(
        "working",
        "Test worker: Expose provider failure to the live UI",
        project_id=task.project_id,
    )
    status_mock.assert_awaited_with(
        "warning",
        "Task retry scheduled (1/3): Expose provider failure to the live UI — missing_keychain_secret",
        project_id=task.project_id,
    )


def test_review_context_does_not_mislabel_machine_feedback_as_human():
    """Machine diagnostics must not be presented to the agent as human review."""
    from app.core.agent_lifecycle import AgentLifecycleMixin

    task = Task(
        title="Retry a failed task",
        what_to_review="Re-check the cited evidence before retrying.",
        last_review_feedback="System execution failed: provider unavailable",
    )

    context = AgentLifecycleMixin()._review_context_for_prompt(task)

    assert "Last review feedback: System execution failed" in context
    assert "Last human feedback:" not in context


def test_custom_worker_backoff_window_is_timezone_safe():
    """Retry timestamps from SQLite must suppress immediate task re-picks."""
    from app.agents.custom_worker import CustomAgentWorker

    task = Task(
        title="Respect custom-worker retry backoff",
        retry_count=1,
        last_retry_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    assert CustomAgentWorker._is_in_backoff(task) is True

    task.last_retry_at = datetime.now(timezone.utc) - timedelta(seconds=6)
    assert CustomAgentWorker._is_in_backoff(task) is False


@pytest.mark.asyncio
async def test_custom_worker_pick_skips_backoff_tasks():
    """A failed task cannot starve another ready task during its backoff."""
    from app.agents.custom_worker import CustomAgentWorker

    blocked = Task(
        id="custom-worker-backoff-task",
        title="Wait for retry backoff",
        retry_count=1,
        last_retry_at=datetime.now(timezone.utc),
    )
    ready = Task(id="custom-worker-ready-task", title="Pick ready task")

    class _Scalars:
        def all(self):
            return [blocked, ready]

    class _Result:
        def scalars(self):
            return _Scalars()

    class _FakeDb:
        async def execute(self, statement):  # noqa: ANN001
            del statement
            return _Result()

    picked = await CustomAgentWorker("custom-worker-agent", "Test worker")._pick_task(_FakeDb())

    assert picked is ready


@pytest.mark.asyncio
async def test_custom_worker_failure_escalates_after_max_retries(monkeypatch):
    """Repeated custom-agent failures must reach system-failed human review."""
    from app.agents import custom_worker
    from app.core.agent import agent as agent_orchestrator
    from app.core import task_review

    class _ProjectResult:
        @staticmethod
        def scalar_one_or_none():
            return SimpleNamespace(id="project-without-provider")

    class _FakeDb:
        async def execute(self, statement):  # noqa: ANN001
            del statement
            return _ProjectResult()

        async def commit(self) -> None:
            return None

        def add(self, event):  # noqa: ANN001
            del event

    task = Task(
        id="custom-worker-max-retry-task",
        project_id="project-without-provider",
        agent_id="custom-worker-agent",
        title="Escalate repeated provider failure",
        status=TaskStatus.BACKLOG,
        max_retries=2,
        what_to_review="Keep the accepted evidence and repair only the unsupported claim.",
    )
    worker = custom_worker.CustomAgentWorker("custom-worker-agent", "Test worker")
    monkeypatch.setattr(worker, "_update_db_state", AsyncMock())
    status_mock = AsyncMock()
    progress_mock = AsyncMock()
    monkeypatch.setattr(custom_worker, "broadcast_agent_status", status_mock)
    monkeypatch.setattr(custom_worker, "broadcast_task_progress", progress_mock, raising=False)
    monkeypatch.setattr(
        agent_orchestrator,
        "_execute_task",
        AsyncMock(side_effect=RuntimeError("missing_keychain_secret")),
    )
    event = SimpleNamespace(id="system-failed-event", outcome="system_failed", quality_score=0.1)
    record_event = AsyncMock(return_value=event)
    diagnose_event = AsyncMock()
    side_effects = AsyncMock()
    monkeypatch.setattr(task_review, "record_task_review_event", record_event)
    monkeypatch.setattr(task_review, "diagnose_review_event", diagnose_event)
    monkeypatch.setattr(task_review, "record_review_side_effects", side_effects)

    db = _FakeDb()
    await worker._execute_task(db, task, SimpleNamespace())
    assert task.retry_count == 1
    assert task.last_retry_at is not None
    assert task.status == TaskStatus.BACKLOG
    assert task.progress == 0.0
    assert task.what_to_review.startswith("Keep the accepted evidence")

    await worker._execute_task(db, task, SimpleNamespace())
    assert task.retry_count == 2
    assert task.status == TaskStatus.IN_REVIEW
    assert task.review_state == "system_failed"
    assert task.progress == 1.0
    record_event.assert_awaited_once()
    diagnose_event.assert_awaited_once_with(db, event.id)
    side_effects.assert_awaited_once_with(event)
    progress_mock.assert_any_await(
        task.id,
        1.0,
        "Execution failed after 2 retries: missing_keychain_secret",
        outcome="system_failed",
        project_id=task.project_id,
    )
