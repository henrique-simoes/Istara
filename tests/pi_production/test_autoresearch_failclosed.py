"""H-9 (routes + chat): typed 503s and fail-closed chat persistence.

* The governed autoresearch route must translate ``PiWorkerError`` /
  ``TimeoutError`` into a typed 503 — never an uncaught 500.
* A failed Pi chat turn must NOT persist an assistant message built from a
  failed or partially-streamed turn (fail-closed contract); a successful Pi
  turn still persists exactly one assistant message.

Both seams are driven with deterministic fakes; no node worker is spawned.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import select

from app.api.routes import autoresearch as autoresearch_route
from app.api.routes import chat as chat_route
from app.config import settings
from app.core.pi_runtime import seams
from app.core.pi_runtime.supervisor import PiWorkerError
from app.models.database import async_session, init_db
from app.models.message import Message
from app.models.project import Project


# ── autoresearch route: typed 503 on worker failure ─────────────────────────
class _FailingAutoresearchService:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def run_autoresearch_turn(self, **kwargs):
        raise self._exc


@pytest.mark.parametrize(
    "exc",
    [
        PiWorkerError("worker_not_started"),
        TimeoutError("run timed out"),
    ],
    ids=["pi_worker_error", "timeout"],
)
@pytest.mark.asyncio
async def test_autoresearch_route_returns_typed_503_on_worker_failure(monkeypatch, exc):
    await init_db()
    project_id = f"pi-h9-auto-{uuid.uuid4()}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi H-9 autoresearch"))
        await db.commit()

    async def fake_scope(*args, **kwargs):
        return project_id

    monkeypatch.setattr(seams, "_service", _FailingAutoresearchService(exc))
    monkeypatch.setattr(settings, "autoresearch_enabled", True)
    monkeypatch.setattr(autoresearch_route, "_require_active_project_scope", fake_scope)
    monkeypatch.setattr(autoresearch_route, "_get_engine", lambda: SimpleNamespace(is_running=False))

    added: list[object] = []
    background_tasks = BackgroundTasks()
    background_tasks.add_task = lambda fn, *a, **k: added.append((fn, a, k))

    with pytest.raises(HTTPException) as excinfo:
        await autoresearch_route.start_experiment(
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

    assert excinfo.value.status_code == 503
    assert "Pi runtime worker unavailable" in str(excinfo.value.detail)
    assert added == []  # no legacy loop scheduled, no candidate proposal returned


# ── chat: failed Pi turn persists no assistant message ──────────────────────
class _StubPiChatService:
    def __init__(self, events: list[dict]) -> None:
        self._events = events

    def steering_binding(self, *, agent_id, project_id):
        return None

    async def run_chat_turn(self, **kwargs):
        for event in self._events:
            yield event


class _FakeMetrics:
    def __init__(self, *, project_id, agent_id):
        self.finished: list[dict] = []

    def observe_input(self, messages):
        pass

    def observe_chunk(self, chunk):
        pass

    def observe_tool_call(self):
        pass

    async def finish(self, **kwargs):
        self.finished.append(kwargs)


async def _run_pi_chat(monkeypatch, project_id: str, events: list[dict]) -> str:
    """Drive the real chat route's SSE stream with a scripted Pi service."""

    async def fake_retrieve_context(*args, **kwargs):
        return SimpleNamespace(retrieved=[])

    async def fake_compose_dynamic_prompt(*args, **kwargs):
        return "Pi route test identity"

    async def fake_record_span(*args, **kwargs):
        return None

    monkeypatch.setattr(chat_route, "retrieve_context", fake_retrieve_context)
    monkeypatch.setattr(chat_route, "compose_dynamic_prompt", fake_compose_dynamic_prompt)
    monkeypatch.setattr(chat_route, "ensure_pi_deepseek_registered", lambda: (True, "registered"))
    monkeypatch.setattr(chat_route, "PiChatRunMetrics", _FakeMetrics)
    monkeypatch.setattr(chat_route, "_pi_execution_service", _StubPiChatService(events))
    monkeypatch.setattr("app.core.pi_replacement.telemetry_recorder.record_span", fake_record_span)
    # Keep the post-save DAG compaction task out of the deterministic stream.
    monkeypatch.setattr(chat_route.settings, "dag_enabled", False)

    async with async_session() as db:
        project = Project(id=project_id, name="Pi H-9 chat")
        db.add(project)
        await db.commit()

        async def fake_get_visible_project_or_404(*args, **kwargs):
            return project

        monkeypatch.setattr(chat_route, "get_visible_project_or_404", fake_get_visible_project_or_404)
        response = await chat_route.chat(
            chat_route.ChatRequest(project_id=project_id, message="hello pi"),
            SimpleNamespace(headers={"x-istara-agent-engine": "pi"}),
            db,
        )

    raw_parts: list[str] = []
    async for chunk in response.body_iterator:
        raw_parts.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
    return "".join(raw_parts)


async def _assistant_messages(project_id: str) -> list[Message]:
    async with async_session() as db:
        return (
            await db.execute(
                select(Message).where(
                    Message.project_id == project_id,
                    Message.role == "assistant",
                )
            )
        ).scalars().all()


@pytest.mark.asyncio
async def test_failed_pi_chat_turn_persists_no_assistant_message(monkeypatch):
    """A turn that streamed partial text then errored persists nothing."""
    await init_db()
    project_id = uuid.uuid4().hex

    raw = await _run_pi_chat(
        monkeypatch,
        project_id,
        [
            {"type": "content", "text": "partial answer before failure"},
            {"type": "error", "error": "run_failed"},
        ],
    )

    assert '"type": "error"' in raw
    assert '"type": "done"' in raw
    assert '"message_id": null' in raw
    assert await _assistant_messages(project_id) == []


@pytest.mark.asyncio
async def test_successful_pi_chat_turn_still_persists_assistant_message(monkeypatch):
    """Control: the fail-closed guard must not block successful Pi turns."""
    await init_db()
    project_id = uuid.uuid4().hex

    raw = await _run_pi_chat(
        monkeypatch,
        project_id,
        [
            {"type": "content", "text": "pi answer"},
            {"type": "done"},
        ],
    )

    assert '"type": "done"' in raw
    assert '"message_id": null' not in raw
    rows = await _assistant_messages(project_id)
    assert [row.content for row in rows] == ["pi answer"]
