"""Regression tests for the reversible Pi replacement candidate path."""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks
from sqlalchemy import select

from app.api.routes import autoresearch as autoresearch_route
from app.api.routes import chat as chat_route
from app.channels.base import channel_router
from app.channels.pi_local import PiLocalAdapter
from app.config import settings
from app.models.channel_message import ChannelMessage
from app.models.codebook import Codebook  # noqa: F401 - registers Project relationship.
from app.models.message import Message
from app.models.database import async_session, init_db
from app.models.project import Project
from app.models.agent import A2AMessage
from app.models.task import Task, TaskStatus  # noqa: F401 - registers Project relationship.
from app.models.telemetry_span import TelemetrySpan
from app.services import channel_service
from app.services.inbound_processor import process_inbound_channel_message


class _FakePiService:
    """Lightweight stand-in for ``PiExecutionService`` used to prove seam wiring
    (persistence, gating, governance) without spawning the real Node worker.

    The real worker + provider HTTP stack are exercised end-to-end in
    ``tests/pi_production`` instead.
    """

    def __init__(self, reply: str = "Pi handled the channel message via the real loop."):
        self.reply = reply
        self.channel_calls: list[dict] = []
        self.autoresearch_calls: list[dict] = []

    async def run_channel_turn(self, *, project_id, agent_id, system_prompt, inbound_text,
                               tool_executor, session_key=None, **_kw):
        self.channel_calls.append({"project_id": project_id, "inbound_text": inbound_text})
        return {"text": self.reply, "endpoint_id": "pi-loopback", "status": "success", "tool_calls": []}

    async def run_autoresearch_turn(self, *, project_id, agent_id, system_prompt, objective,
                                    tool_executor, loop_type, target, **_kw):
        self.autoresearch_calls.append({"project_id": project_id, "loop_type": loop_type})
        return {
            "status": "candidate_proposal",
            "loop_type": loop_type,
            "target": target,
            "project_id": project_id,
            "production_mutation_allowed": False,
            "background_task_started": False,
            "proposal": {
                "hypothesis": "Governed Pi candidate hypothesis (fake).",
                "governance_required": True,
                "report_evidence": False,
                "promotion": "blocked_pending_human_review",
            },
            "runtime": {"engine": "pi", "turn_status": "success", "tool_calls": [],
                        "endpoint_id": "pi-loopback"},
        }


@pytest.mark.asyncio
async def test_pi_candidate_chat_fails_closed_before_transport_when_registration_is_missing(
    monkeypatch,
):
    calls: list[dict] = []

    async def fake_chat_stream(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            yield {
                "tool_calls": [
                    {
                        "id": "call-1",
                        "function": {
                            "name": "list_tasks",
                            "arguments": "{}",
                        },
                    }
                ]
            }
        else:
            yield "candidate final answer"

    async def fake_execute_tool(tool_name, params, project_id, agent_id):
        return {"result": "no open tasks"}

    async def fake_record_span(*args, **kwargs):
        return None

    monkeypatch.setattr(chat_route.ollama, "chat_stream", fake_chat_stream)
    monkeypatch.setattr(chat_route, "execute_tool", fake_execute_tool)
    monkeypatch.setattr(
        chat_route,
        "ensure_pi_deepseek_registered",
        lambda: (False, "missing_keychain_secret"),
    )
    monkeypatch.setattr(
        "app.core.pi_replacement.telemetry_recorder.record_span",
        fake_record_span,
    )

    events = [
        event
        async for event in chat_route._generate_native_tools(
            [{"role": "user", "content": "show tasks"}],
            [],
            [],
            SimpleNamespace(project_id="pi-chat-project"),
            "istara-main",
            None,
            0.1,
            128,
            pi_candidate=True,
        )
    ]

    assert calls == []
    assert any('"code": "pi_registration_unavailable"' in event for event in events)
    assert any('"type": "done"' in event for event in events)


@pytest.mark.asyncio
async def test_pi_candidate_text_fallback_fails_closed_before_transport_when_registration_is_missing(
    monkeypatch,
):
    calls: list[dict] = []

    async def fake_chat_stream(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            yield 'Before tool ```json\n{"tool": "list_tasks", "params": {}}\n```'
        else:
            yield "fallback final answer"

    async def fake_execute_tool(tool_name, params, project_id, agent_id):
        return {"result": "fallback tasks"}

    monkeypatch.setattr(chat_route.ollama, "chat_stream", fake_chat_stream)
    monkeypatch.setattr(chat_route, "execute_tool", fake_execute_tool)
    monkeypatch.setattr(
        chat_route,
        "ensure_pi_deepseek_registered",
        lambda: (False, "missing_keychain_secret"),
    )

    parts: list[str] = []
    tools: list[dict] = []
    events = [
        event
        async for event in chat_route._generate_text_fallback(
            [{"role": "user", "content": "show tasks"}],
            parts,
            tools,
            SimpleNamespace(project_id="pi-fallback-project"),
            "istara-main",
            None,
            0.1,
            128,
            pi_candidate=True,
        )
    ]

    assert calls == []
    assert any('"code": "pi_registration_unavailable"' in event for event in events)
    assert tools == []


@pytest.mark.asyncio
async def test_pi_candidate_registered_text_fallback_uses_the_pinned_deepseek_model(monkeypatch):
    calls: list[dict] = []

    async def fake_chat_stream(**kwargs):
        calls.append(kwargs)
        yield "registered candidate response"

    async def fake_record_span(*args, **kwargs):
        return None

    monkeypatch.setattr(chat_route.ollama, "chat_stream", fake_chat_stream)
    monkeypatch.setattr(chat_route, "ensure_pi_deepseek_registered", lambda: (True, "registered"))
    monkeypatch.setattr(
        "app.core.pi_replacement.telemetry_recorder.record_span",
        fake_record_span,
    )

    events = [
        event
        async for event in chat_route._generate_text_fallback(
            [{"role": "user", "content": "hello"}], [], [],
            SimpleNamespace(project_id="pi-registered-project"), "istara-main", None,
            0.1, 128, pi_candidate=True,
        )
    ]

    assert len(calls) == 1
    assert calls[0]["model"] == settings.pi_replacement_deepseek_model
    assert calls[0]["strict_model_routing"] is True
    assert any("registered candidate response" in event for event in events)


@pytest.mark.asyncio
async def test_pi_candidate_text_fallback_finishes_chat_metrics(monkeypatch):
    metrics: list[object] = []

    class FakeMetrics:
        def __init__(self, *, project_id, agent_id):
            self.project_id = project_id
            self.agent_id = agent_id
            self.registration_status = ""
            self.inputs: list[list[dict]] = []
            self.chunks: list[str] = []
            self.finished: list[dict] = []
            metrics.append(self)

        def observe_input(self, messages):
            self.inputs.append(messages)

        def observe_chunk(self, chunk):
            self.chunks.append(chunk)

        async def finish(self, **kwargs):
            self.finished.append(kwargs)

    async def fake_chat_stream(**kwargs):
        yield "registered candidate response"

    monkeypatch.setattr(chat_route, "PiChatRunMetrics", FakeMetrics)
    monkeypatch.setattr(chat_route.ollama, "chat_stream", fake_chat_stream)
    monkeypatch.setattr(chat_route, "ensure_pi_deepseek_registered", lambda: (True, "registered"))

    events = [
        event
        async for event in chat_route._generate_text_fallback(
            [{"role": "user", "content": "hello"}], [], [],
            SimpleNamespace(project_id="pi-fallback-metrics-project"), "istara-main", None,
            0.1, 128, pi_candidate=True,
        )
    ]

    assert any("registered candidate response" in event for event in events)
    assert len(metrics) == 1
    assert metrics[0].registration_status == "registered"
    assert metrics[0].inputs == [[{"role": "user", "content": "hello"}]]
    assert metrics[0].chunks == ["registered candidate response"]
    assert metrics[0].finished == [{}]


@pytest.mark.asyncio
async def test_pi_candidate_chat_route_header_selects_pi_and_persists_done_sse(
    monkeypatch,
):
    await init_db()
    project_id = str(uuid.uuid4())
    calls: list[dict] = []

    async def fake_chat_stream(**kwargs):
        calls.append(kwargs)
        yield "route final answer"

    async def fake_record_span(*args, **kwargs):
        return None

    async def fake_retrieve_context(*args, **kwargs):
        return SimpleNamespace(retrieved=[])

    async def fake_compose_dynamic_prompt(*args, **kwargs):
        return "Pi route test identity"

    monkeypatch.setattr(chat_route.ollama, "chat_stream", fake_chat_stream)
    monkeypatch.setattr(chat_route, "retrieve_context", fake_retrieve_context)
    monkeypatch.setattr(chat_route, "compose_dynamic_prompt", fake_compose_dynamic_prompt)
    monkeypatch.setattr(chat_route, "ensure_pi_deepseek_registered", lambda: (False, "missing_keychain_secret"))
    monkeypatch.setattr("app.core.pi_replacement.telemetry_recorder.record_span", fake_record_span)

    async with async_session() as db:
        project = Project(id=project_id, name="Pi Chat Route Project")
        db.add(project)
        await db.commit()

        async def fake_get_visible_project_or_404(*args, **kwargs):
            return project

        monkeypatch.setattr(chat_route, "get_visible_project_or_404", fake_get_visible_project_or_404)
        response = await chat_route.chat(
            chat_route.ChatRequest(project_id=project_id, message="route pi"),
            SimpleNamespace(headers={"x-istara-agent-engine": "pi"}),
            db,
        )

    raw_parts: list[str] = []
    async for chunk in response.body_iterator:
        raw_parts.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
    raw = "".join(raw_parts)

    assert calls == []
    assert '"code": "pi_registration_unavailable"' in raw
    assert '"type": "done"' in raw

    async with async_session() as db:
        assistant = await db.scalar(
            select(Message).where(
                Message.project_id == project_id,
                Message.role == "assistant",
                Message.content == "route final answer",
            )
        )
        assert assistant is None


@pytest.mark.asyncio
async def test_pi_local_channel_adapter_routes_through_inbound_processor(monkeypatch):
    await init_db()
    project_id = f"pi-local-channel-{uuid.uuid4()}"

    monkeypatch.setattr("app.core.pi_runtime.seams._service", _FakePiService())

    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi Local Channel Project"))
        await db.commit()
        instance = await channel_service.create_channel_instance(
            db,
            platform="pi_local",
            name="Pi Local",
            config={"enabled": True},
            project_id=project_id,
        )
        result = await channel_service.start_channel_instance(
            db,
            instance.id,
            project_id=project_id,
        )

    assert result["status"] == "started"
    adapter = channel_router.get(instance.id)
    assert isinstance(adapter, PiLocalAdapter)

    channel_router.set_handler(process_inbound_channel_message)
    await adapter.inject(sender_id="participant-1", text="hello pi candidate")

    assert adapter.sent_messages
    assert adapter.sent_messages[0].metadata["pi_replacement"] is True

    async with async_session() as db:
        inbound = await db.get(ChannelMessage, adapter.sent_messages[0].metadata["inbound_message_id"])
        assert inbound is not None
        assert inbound.project_id == project_id
        assert json.loads(inbound.metadata_json)["pi_candidate"] is True

    async with async_session() as db:
        await channel_service.stop_project_channel_instances(db, project_id)


@pytest.mark.asyncio
async def test_pi_local_channel_drops_stopped_injection_and_unregisters_ownership(monkeypatch):
    await init_db()
    project_id = f"pi-local-stop-{uuid.uuid4()}"

    monkeypatch.setattr("app.core.pi_runtime.seams._service", _FakePiService())

    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi Local Stop Project"))
        await db.commit()
        instance = await channel_service.create_channel_instance(
            db,
            platform="pi_local",
            name="Pi Local Stop",
            config={"enabled": True},
            project_id=project_id,
        )
        await channel_service.start_channel_instance(db, instance.id, project_id=project_id)

    adapter = channel_router.get(instance.id)
    assert isinstance(adapter, PiLocalAdapter)
    channel_router.set_handler(process_inbound_channel_message)
    async with async_session() as db:
        assert await channel_service.stop_project_channel_instances(db, project_id) == 1

    await adapter.inject(sender_id="participant-1", text="must be dropped after stop")

    assert channel_router.get(instance.id) is None
    assert adapter.is_running is False
    assert adapter._callback is None
    assert adapter.sent_messages == []
    async with async_session() as db:
        messages = (await db.execute(
            select(ChannelMessage).where(ChannelMessage.channel_instance_id == instance.id)
        )).scalars().all()
    assert messages == []


@pytest.mark.asyncio
async def test_pi_local_channel_inbound_cannot_cross_project_boundary(monkeypatch):
    await init_db()
    project_a = f"pi-local-a-{uuid.uuid4()}"
    project_b = f"pi-local-b-{uuid.uuid4()}"

    monkeypatch.setattr("app.core.pi_runtime.seams._service", _FakePiService())

    async with async_session() as db:
        db.add_all([
            Project(id=project_a, name="Pi Local Project A"),
            Project(id=project_b, name="Pi Local Project B"),
        ])
        await db.commit()
        instance = await channel_service.create_channel_instance(
            db,
            platform="pi_local",
            name="Pi Local Project A",
            config={"enabled": True},
            project_id=project_a,
        )
        await channel_service.start_channel_instance(db, instance.id, project_id=project_a)

    adapter = channel_router.get(instance.id)
    assert isinstance(adapter, PiLocalAdapter)
    channel_router.set_handler(process_inbound_channel_message)
    await adapter.inject(
        sender_id="participant-a",
        text="project A only",
        metadata={"project_id": project_b},
    )
    assert len(adapter.sent_messages) == 1
    pi_response = adapter.sent_messages[0]
    assert pi_response.metadata["pi_replacement"] is True

    async with async_session() as db:
        project_a_messages = (await db.execute(
            select(ChannelMessage).where(ChannelMessage.project_id == project_a)
        )).scalars().all()
        project_b_messages = (await db.execute(
            select(ChannelMessage).where(ChannelMessage.project_id == project_b)
        )).scalars().all()
        project_b_spans = (await db.execute(
            select(TelemetrySpan).where(TelemetrySpan.project_id == project_b)
        )).scalars().all()
        response_inbound = await db.get(
            ChannelMessage,
            pi_response.metadata["inbound_message_id"],
        )
        await channel_service.stop_project_channel_instances(db, project_a)

    # Project A holds exactly one inbound message plus the persisted Pi reply;
    # project B (the spoofed metadata target) sees nothing — scope comes from the
    # instance, never from model-supplied metadata.
    inbound_a = [m for m in project_a_messages if m.direction == "inbound"]
    outbound_a = [m for m in project_a_messages if m.direction == "outbound"]
    assert len(inbound_a) == 1
    assert len(outbound_a) == 1
    assert response_inbound is not None
    assert response_inbound.id == inbound_a[0].id
    assert response_inbound.project_id == project_a
    assert project_b_messages == []
    assert project_b_spans == []


@pytest.mark.asyncio
async def test_pi_exercisers_deleted_have_no_surviving_caller():
    """Plan C D-C6: the credential-free research/memory/steering exercisers and
    the canned channel response are deleted — no code path may call them."""
    import app.core.pi_replacement as pr

    for gone in (
        "write_pi_source_evidence_chain",
        "exercise_pi_done_report_gate",
        "record_pi_memory_governance_fanout",
        "exercise_pi_steering_interrupt_probe",
        "exercise_pi_production_readiness",
        "build_pi_channel_response",
    ):
        assert not hasattr(pr, gone), f"exerciser {gone} still present"


@pytest.mark.asyncio
async def test_pi_governed_autoresearch_returns_candidate_only_and_starts_no_loop(monkeypatch):
    """The governed Pi autoresearch seam (non-dry-run) yields a candidate
    proposal only: no background loop, no promotion, human governance required
    (AC-5). Replaces the deleted readiness exerciser with a route-level proof."""
    added: list[object] = []

    async def fake_project_scope(*args, **kwargs):
        return "pi-governed-autoresearch"

    monkeypatch.setattr(settings, "autoresearch_enabled", True)
    monkeypatch.setattr(autoresearch_route, "_require_active_project_scope", fake_project_scope)
    monkeypatch.setattr(autoresearch_route, "_get_engine", lambda: SimpleNamespace(is_running=False))
    monkeypatch.setattr("app.core.pi_runtime.seams._service", _FakePiService())

    background_tasks = BackgroundTasks()
    background_tasks.add_task = lambda fn, *args, **kwargs: added.append((fn, args, kwargs))
    result = await autoresearch_route.start_experiment(
        autoresearch_route.StartExperimentRequest(
            loop_type="model_temp",
            target="pi-governed-benchmark",
            max_iterations=3,
            project_id="pi-governed-autoresearch",
            dry_run=False,
        ),
        SimpleNamespace(headers={"x-istara-agent-engine": "pi"}),
        background_tasks,
        None,
    )

    assert result["status"] == "candidate_proposal"
    assert result["production_mutation_allowed"] is False
    assert result["background_task_started"] is False
    assert result["proposal"]["governance_required"] is True
    assert result["proposal"]["report_evidence"] is False
    assert result["proposal"]["promotion"] == "blocked_pending_human_review"
    assert result["max_iterations"] == 3
    # The legacy runner loop was never scheduled — governed mode is turn-only.
    assert added == []


@pytest.mark.asyncio
async def test_pi_a2a_route_persists_candidate_telemetry(monkeypatch):
    await init_db()
    project_id = str(uuid.uuid4())

    async def fake_authorize_a2a_request(request):
        return {"id": "pi-a2a-user", "username": "pi-a2a-user", "role": "admin"}

    async def fake_authorize_project_scope(*args, **kwargs):
        return None

    async def fake_record_a2a_event(*args, **kwargs):
        return None

    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": "pi-a2a-1",
            "method": "tasks/send",
            "params": {
                "from": "agent-a",
                "to": "istara-main",
                "message": {
                    "text": "credential-free Pi A2A task",
                    "metadata": {"project_id": project_id, "pi_candidate": True},
                },
            },
        }
    ).encode()

    async def fake_body():
        return body

    monkeypatch.setattr("app.api.routes.a2a._authorize_a2a_request", fake_authorize_a2a_request)
    monkeypatch.setattr("app.api.routes.a2a._authorize_project_scope", fake_authorize_project_scope)
    monkeypatch.setattr("app.api.routes.a2a._record_a2a_event", fake_record_a2a_event)

    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi A2A Project"))
        await db.commit()

    result = await __import__("app.api.routes.a2a", fromlist=["a2a_jsonrpc"]).a2a_jsonrpc(
        SimpleNamespace(
            headers={"x-istara-agent-engine": "pi", "content-length": str(len(body))},
            body=fake_body,
            state=SimpleNamespace(),
            client=SimpleNamespace(host="127.0.0.1"),
            url=SimpleNamespace(path="/api/a2a"),
        )
    )

    assert result["result"]["status"] == "submitted"
    async with async_session() as db:
        span = await db.scalar(
            select(TelemetrySpan).where(
                TelemetrySpan.project_id == project_id,
                TelemetrySpan.operation == "pi_candidate_a2a_tasks_send",
                TelemetrySpan.event_kind == "a2a_jsonrpc",
            )
        )
        assert span is not None
        assert "agent-a->istara-main" in span.route_id


@pytest.mark.asyncio
async def test_pi_a2a_scope_denial_submits_no_work_or_candidate_telemetry(monkeypatch):
    await init_db()
    project_id = str(uuid.uuid4())

    async def fake_authorize_a2a_request(request):
        return {"id": "unauthorized-pi-user", "username": "unauthorized", "role": "researcher"}

    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": f"pi-a2a-denied-{uuid.uuid4()}",
            "method": "tasks/send",
            "params": {
                "from": "agent-a",
                "to": "istara-main",
                "message": {
                    "text": "Pi work must not submit outside project scope",
                    "metadata": {"project_id": project_id, "pi_candidate": True},
                },
            },
        }
    ).encode()

    async def fake_body():
        return body

    monkeypatch.setattr(settings, "team_mode", True)
    monkeypatch.setattr("app.api.routes.a2a._authorize_a2a_request", fake_authorize_a2a_request)
    async with async_session() as db:
        db.add(Project(id=project_id, name="Pi A2A Denied Project"))
        await db.commit()

    result = await __import__("app.api.routes.a2a", fromlist=["a2a_jsonrpc"]).a2a_jsonrpc(
        SimpleNamespace(
            headers={"x-istara-agent-engine": "pi", "content-length": str(len(body))},
            body=fake_body,
            state=SimpleNamespace(user={"id": "unauthorized-pi-user", "role": "researcher"}),
            client=SimpleNamespace(host="127.0.0.1"),
            url=SimpleNamespace(path="/api/a2a"),
        )
    )

    assert result.status_code == 404
    denial = json.loads(result.body)
    assert denial["error"]["code"] == -32043
    assert denial["id"].startswith("pi-a2a-denied-")
    async with async_session() as db:
        candidate_spans = (await db.execute(
            select(TelemetrySpan).where(
                TelemetrySpan.project_id == project_id,
                TelemetrySpan.operation == "pi_candidate_a2a_tasks_send",
            )
        )).scalars().all()
        submitted_work = (await db.execute(
            select(A2AMessage).where(A2AMessage.project_id == project_id)
        )).scalars().all()

    assert candidate_spans == []
    assert submitted_work == []


@pytest.mark.asyncio
async def test_pi_autoresearch_dry_run_does_not_start_background_loop(monkeypatch):
    added: list[object] = []

    async def fake_project_scope(*args, **kwargs):
        return "pi-autoresearch-project"

    async def fake_record_span(*args, **kwargs):
        return None

    monkeypatch.setattr(settings, "autoresearch_enabled", True)
    monkeypatch.setattr(autoresearch_route, "_require_active_project_scope", fake_project_scope)
    monkeypatch.setattr(autoresearch_route, "_get_engine", lambda: SimpleNamespace(is_running=False))
    monkeypatch.setattr("app.core.pi_replacement.telemetry_recorder.record_span", fake_record_span)

    background_tasks = BackgroundTasks()
    background_tasks.add_task = lambda fn, *args, **kwargs: added.append((fn, args, kwargs))
    result = await autoresearch_route.start_experiment(
        autoresearch_route.StartExperimentRequest(
            loop_type="model_temp",
            target="pi-replacement-benchmark",
            max_iterations=3,
            project_id="pi-autoresearch-project",
            dry_run=True,
        ),
        SimpleNamespace(headers={"x-istara-agent-engine": "pi"}),
        background_tasks,
        None,
    )

    assert result["status"] == "dry_run"
    assert result["production_mutation_allowed"] is False
    assert result["background_task_started"] is False
    assert result["proposal"]["report_evidence"] is False
    assert added == []
