"""H-13: REAL ASGI coverage for the Pi engine path (CF-SPEC-7 correction).

The CF-SPEC-7 review packet previously claimed "real ASGI routes" coverage while
the evidence was direct route-function invocation. This module is the correction:
every request here goes through ``httpx.ASGITransport`` against the real FastAPI
``app`` — so the full middleware stack (SecurityAuthMiddleware JWT enforcement,
audit logging, security headers), routing, request validation, and the SSE
``StreamingResponse`` are exercised over real HTTP semantics, while the turn
itself is driven by the real spawned pi-agent-core node worker on a scripted
``faux`` provider (zero network, zero ComputeRegistry, deterministic).

Deliberate, documented substitution boundary (nothing else is faked):

* the Keychain-backed default-endpoint registration check
  (``ensure_pi_deepseek_registered``) is stubbed to "resolved" so the route
  reaches the Pi path — endpoint *resolution* itself is real: the chat route's
  own ``PiExecutionService`` is replaced by a harness service whose resolver
  returns the faux endpoint (same pattern as every ``tests/pi_production``
  scenario);
* ``retrieve_context`` (RAG embeddings) and ``compose_dynamic_prompt`` (persona
  prompt-RAG) are pinned to no-ops because they would attempt the configured
  embedding endpoint — forbidden here (no network/LLM calls). Both degrade
  gracefully in production and are orthogonal to the Pi engine path under test;
  the protected research-spine contract block, message persistence, session
  handling, and the canonical tool authority round-trip all run for real.

The SSE envelope (``chunk``/``tool_call``/``done``/``error``) asserted here is
the byte-compatible contract the W2 dispatcher migration must preserve
(master plan §8 "SSE contract").
"""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.routes import autoresearch as autoresearch_route
from app.api.routes import chat as chat_route
from app.config import settings
from app.core.auth import create_token
from app.core.pi_runtime import seams
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor
from app.core.rag import RAGContext
from app.main import app
from app.models.database import async_session, init_db
from app.models.message import Message
from app.models.project import Project
from app.models.task import Task

from .harness import error_after_partial, faux_service, final_text, requires_node, tool_call

_PI_HEADERS = {"x-istara-agent-engine": "pi"}


def _sse_events(body: str) -> list[dict]:
    """Parse a ``text/event-stream`` body into its JSON event payloads."""
    events = []
    for block in body.split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: "):]))
    return events


def _auth_headers() -> dict[str, str]:
    token = create_token("pi-asgi-admin", "pi-asgi-admin", "admin", mfa_verified=True)
    return {"Authorization": f"Bearer {token}"}


def _pin_no_network_prompt_seams(monkeypatch) -> None:
    """Pin the two prompt-assembly seams that would attempt the embedding
    endpoint, keeping the whole test at zero network (see module docstring)."""

    async def _no_rag(*args, **kwargs) -> RAGContext:
        return RAGContext(query="", retrieved=[], context_text="")

    async def _no_identity(*args, **kwargs) -> str:
        return ""

    monkeypatch.setattr(chat_route, "retrieve_context", _no_rag)
    monkeypatch.setattr(chat_route, "compose_dynamic_prompt", _no_identity)


@requires_node
@pytest.mark.asyncio
async def test_chat_pi_turn_streams_sse_over_real_asgi(monkeypatch):
    """POST /api/chat (Pi-selected) streams the real worker turn over real ASGI.

    Auth (team-mode JWT through the middleware), routing, the SSE
    ``StreamingResponse``, the canonical tool authority round-trip, and
    assistant-message persistence are all real; only the provider is scripted.
    """
    await init_db()
    monkeypatch.setattr(settings, "team_mode", True)
    monkeypatch.setattr(settings, "jwt_secret", "pi-asgi-test-secret")
    _pin_no_network_prompt_seams(monkeypatch)
    monkeypatch.setattr(
        chat_route, "ensure_pi_deepseek_registered", lambda: (True, "resolved_private_endpoint")
    )

    project_id = f"pi-asgi-chat-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi ASGI chat"))
        await db.commit()

    reply_text = "Task created through the real Pi worker over real ASGI."
    sup = PiRuntimeSupervisor()
    monkeypatch.setattr(
        chat_route,
        "_pi_execution_service",
        faux_service(
            [
                tool_call("create_task", {"title": "Pi ASGI task", "priority": "high"}),
                final_text(reply_text),
            ],
            sup,
        ),
    )

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/chat",
                json={"message": "Please open a task for the accessibility pass.", "project_id": project_id},
                headers={**_auth_headers(), **_PI_HEADERS},
            )
    finally:
        await sup.shutdown()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _sse_events(response.text)
    assert events, "expected SSE events over the real ASGI stream"
    # Pin the byte-compatible envelope: chunk / tool_call / done (master plan §8).
    for event in events:
        assert event["type"] in {"chunk", "tool_call", "done", "error"}
        assert "type" in event

    chunks = [e for e in events if e["type"] == "chunk"]
    assert "".join(e["content"] for e in chunks) == reply_text

    tool_events = [e for e in events if e["type"] == "tool_call"]
    assert [e["tool"] for e in tool_events] == ["create_task"]
    assert tool_events[0]["params"] == {"title": "Pi ASGI task", "priority": "high"}

    assert not [e for e in events if e["type"] == "error"]
    done = events[-1]
    assert done["type"] == "done"
    assert done["message_id"]
    assert done["sources"] == []
    assert done["tools_used"] == ["create_task"]

    # The real canonical tool executed under the authenticated project scope,
    # and the route persisted the assistant message — over real HTTP semantics.
    async with async_session() as db:
        tasks = (await db.execute(select(Task).where(Task.project_id == project_id))).scalars().all()
        assert [t.title for t in tasks] == ["Pi ASGI task"]
        assistant = (
            await db.execute(
                select(Message).where(Message.project_id == project_id, Message.role == "assistant")
            )
        ).scalars().all()
        assert [m.content for m in assistant] == [reply_text]
        assert assistant[0].id == done["message_id"]

    assert sup.is_running is False


@pytest.mark.asyncio
async def test_chat_pi_turn_requires_auth_over_asgi(monkeypatch):
    """The same Pi-selected chat request without a token is rejected by the real
    auth middleware (team mode) before any route or worker code runs."""
    await init_db()
    monkeypatch.setattr(settings, "team_mode", True)
    monkeypatch.setattr(settings, "jwt_secret", "pi-asgi-test-secret")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/chat",
            json={"message": "hello", "project_id": "pi-asgi-unauth"},
            headers=_PI_HEADERS,
        )
    assert response.status_code == 401


@requires_node
@pytest.mark.asyncio
async def test_autoresearch_governed_turn_fails_closed_over_real_asgi(monkeypatch):
    """HTTP-level fail-closed seam: a governed autoresearch turn that reaches a
    real ``run.failed`` after partial streamed output returns a typed 503 over
    real ASGI — never a fabricated candidate proposal (RF3-2)."""
    await init_db()
    monkeypatch.setattr(settings, "team_mode", True)
    monkeypatch.setattr(settings, "jwt_secret", "pi-asgi-test-secret")
    monkeypatch.setattr(settings, "autoresearch_enabled", True)

    project_id = f"pi-asgi-auto-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi ASGI autoresearch"))
        await db.commit()

    async def _fake_scope(*args, **kwargs):
        return project_id

    monkeypatch.setattr(autoresearch_route, "_require_active_project_scope", _fake_scope)
    monkeypatch.setattr(autoresearch_route, "_get_engine", lambda: SimpleNamespace(is_running=False))

    sup = PiRuntimeSupervisor()
    monkeypatch.setattr(
        seams,
        "_service",
        faux_service([error_after_partial("Partial hypothesis before failure.")], sup),
    )

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post(
                "/api/autoresearch/start",
                json={
                    "loop_type": "model_temp",
                    "target": "extraction",
                    "max_iterations": 5,
                    "project_id": project_id,
                    "dry_run": False,
                },
                headers={**_auth_headers(), **_PI_HEADERS},
            )
    finally:
        await sup.shutdown()

    assert response.status_code == 503
    assert "Pi runtime turn failed" in response.json()["detail"]
    assert sup.is_running is False
