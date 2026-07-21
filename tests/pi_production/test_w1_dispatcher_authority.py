"""W1 authority/API gap regressions (F-W1-1).

Covers the immediate seams the fix changed: five-verb dispatcher with
header -> project -> default engine precedence, the real byte-compatible
legacy executor binding, PiModelManager catalog sources and capability
admission, PiExecutionService TurnParams forwarding, and fail-closed
negatives. Non-faux seams use real ResolvedPiEndpoint payloads, the real
project-settings DB seam, and the real legacy plane signature (stubbed at
the ``app.core.ollama.ollama`` boundary, never at the dispatcher).
"""

from __future__ import annotations

import uuid

import pytest

from app.config import settings
from app.core.agentic.dispatcher import AgenticDispatcher, agentic
from app.core.agentic.legacy import legacy_executor
from app.core.agentic.types import AgenticDispatchError, TurnParams
from app.core.pi_runtime.endpoints import (
    PiEndpointResolutionError,
    ResolvedPiEndpoint,
)
from app.core.pi_runtime.engine import PiExecutionService, _bind_payload
from app.core.pi_runtime.model_manager import PiModelManager
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor
from tests.pi_production.harness import faux_endpoint, final_text


def _isolated(manager: PiModelManager) -> PiModelManager:
    """Pin the catalog to its explicit entries (skip the DB projection)."""
    manager._db_projected = True
    return manager


def _real_endpoint(**overrides) -> ResolvedPiEndpoint:
    base = dict(
        endpoint_id="pi-real-a",
        provider_kind="openai_compat",
        base_url="https://provider.invalid/v1",
        model="real-model-a",
        api_key="secret-a",
        timeout_ms=30_000,
        max_retries=0,
        cost_input_per_mtok=1.0,
        cost_output_per_mtok=2.0,
        cost_cache_read_per_mtok=0.1,
    )
    base.update(overrides)
    return ResolvedPiEndpoint(**base)


class _Request:
    def __init__(self, headers: dict[str, str]) -> None:
        self.headers = headers


# ── engine resolution precedence ────────────────────────────────────────
def test_resolve_engine_precedence_explicit_header_project_default(monkeypatch):
    dispatcher = AgenticDispatcher()

    async def fake_project_engine(project_id):
        return {"p-pi": "pi", "p-legacy": "legacy"}.get(project_id)

    monkeypatch.setattr(dispatcher, "_project_engine", fake_project_engine)
    # 1. explicit per-call override wins over everything
    assert dispatcher.resolve_engine(engine="pi", project_engine="legacy") == "pi"
    # 2. request header beats the project setting
    request = _Request({settings.pi_replacement_request_header: "pi"})
    assert dispatcher.resolve_engine(request=request, project_engine="legacy") == "pi"
    # 3. project setting beats the global default
    assert dispatcher.resolve_engine(project_engine="pi") == "pi"
    assert dispatcher.resolve_engine(project_engine="legacy") == "legacy"
    # 4. global default is the last resort
    monkeypatch.setattr(settings, "agentic_engine_default", "legacy")
    assert dispatcher.resolve_engine() == "legacy"
    monkeypatch.setattr(settings, "agentic_engine_default", "pi")
    assert dispatcher.resolve_engine() == "pi"


@pytest.mark.asyncio
async def test_project_setting_column_drives_resolution_via_real_db():
    """The persisted projects.agentic_engine column is honored (level 3)."""
    from app.models.database import async_session, init_db
    from app.models.project import Project

    await init_db()
    project_id = f"test-engine-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="engine-precedence", agentic_engine="pi"))
        await db.commit()
    try:
        dispatcher = AgenticDispatcher()
        assert await dispatcher._resolve(project_id=project_id, engine=None, request=None) == "pi"
        # Header still outranks the project setting.
        request = _Request({settings.pi_replacement_request_header: "legacy"})
        assert await dispatcher._resolve(project_id=project_id, engine=None, request=request) == "legacy"
        # Unknown projects fall through to the default without failing.
        assert await dispatcher._resolve(project_id="no-such-project", engine=None, request=None) == (
            "pi" if settings.agentic_engine_default.strip().lower() in {"pi", "pi-candidate", "pi-replacement", "deepseek-pi"} else "legacy"
        )
    finally:
        async with async_session() as db:
            # Raw cleanup: the shared dev DB schema may lag the ORM (stale
            # columns on related tables make relationship cascades fail).
            from sqlalchemy import text

            await db.execute(text("DELETE FROM projects WHERE id = :id"), {"id": project_id})
            await db.commit()


# ── real legacy executor binding ─────────────────────────────────────────
def test_singleton_binds_real_legacy_executor():
    assert agentic._legacy is legacy_executor
    assert AgenticDispatcher()._legacy is legacy_executor


class _LegacyPlaneStub:
    """Stands at the app.core.ollama.ollama boundary (the real signature)."""

    def __init__(self) -> None:
        self.chat_calls: list[dict] = []
        self.embed_calls: list[dict] = []

    async def chat(self, messages, **kwargs):
        self.chat_calls.append({"messages": messages, **kwargs})
        return {
            "message": {"content": "legacy text", "tool_calls": []},
            "prompt_eval_count": 11,
            "eval_count": 7,
            "done_reason": "stop",
        }

    async def embed_batch(self, texts, **kwargs):
        self.embed_calls.append({"texts": texts, **kwargs})
        return [[0.1, 0.2]] * len(texts)


@pytest.mark.asyncio
async def test_legacy_completion_forwards_all_turn_params_byte_compatibly(monkeypatch):
    stub = _LegacyPlaneStub()
    monkeypatch.setattr("app.core.ollama.ollama", stub)
    params = TurnParams(model="m1", temperature=0.2, max_tokens=64, thinking_mode="low",
                        min_context=8192, timeout_s=5.0, max_turns=3, require_vision=True)
    outcome = await legacy_executor(
        "completion", purpose="p", project_id="proj-1", agent_id="a", system="sys",
        messages=[{"role": "user", "content": "hi"}], params=params,
    )
    call = stub.chat_calls[0]
    assert call["model"] == "m1"
    assert call["temperature"] == 0.2
    assert call["max_tokens"] == 64
    assert call["thinking_mode"] == "low"
    assert call["min_context"] == 8192
    assert call["project_id"] == "proj-1"
    assert call["system"] == "sys"
    assert outcome["text"] == "legacy text"
    # Provider-reported usage stays exact, never silently estimated.
    assert outcome["usage"] == {"input_tokens": 11, "output_tokens": 7, "total_tokens": 18, "estimate": False}


@pytest.mark.asyncio
async def test_legacy_structured_uses_schema_adapter_and_parses(monkeypatch):
    stub = _LegacyPlaneStub()

    async def chat(messages, **kwargs):
        stub.chat_calls.append(kwargs)
        return {"message": {"content": '{"accepted": true}'}, "prompt_eval_count": 1, "eval_count": 1}

    stub.chat = chat
    monkeypatch.setattr("app.core.ollama.ollama", stub)
    outcome = await legacy_executor(
        "structured", purpose="debate synthesis!", project_id="p", agent_id="a", system=None,
        messages=[{"role": "user", "content": "go"}],
        schema={"type": "object", "required": ["accepted"]}, params=TurnParams(),
    )
    response_format = stub.chat_calls[0]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "debate_synthesis"
    assert outcome["value"] == {"accepted": True}


@pytest.mark.asyncio
async def test_legacy_embed_uses_legacy_embed_path(monkeypatch):
    stub = _LegacyPlaneStub()
    monkeypatch.setattr("app.core.ollama.ollama", stub)
    outcome = await legacy_executor("embed", texts=["a", "b"], project_id="p", params=TurnParams(model="emb"))
    assert stub.embed_calls[0]["texts"] == ["a", "b"]
    assert stub.embed_calls[0]["model"] == "emb"
    assert outcome["embeddings"] == [[0.1, 0.2], [0.1, 0.2]]


@pytest.mark.asyncio
async def test_legacy_unknown_verb_fails_closed():
    with pytest.raises(AgenticDispatchError, match="legacy_verb_unknown"):
        await legacy_executor("summarize", params=TurnParams())


# ── dispatcher verbs ─────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_chat_turn_pi_streams_and_records_one_row(monkeypatch):
    supervisor = PiRuntimeSupervisor()
    endpoint = faux_endpoint([final_text("streamed answer")])
    service = PiExecutionService(supervisor=supervisor, model_manager=_isolated(PiModelManager(endpoints=[endpoint])))
    recorded = []

    async def capture(**kwargs):
        recorded.append(kwargs)

    monkeypatch.setattr("app.core.agentic.dispatcher.record_agentic_usage", capture)
    streamed = []
    try:
        result = await AgenticDispatcher(pi_service=service).chat_turn(
            project_id="p1", agent_id="istara-main", session_key=None, system_prompt="sys",
            messages=[{"role": "user", "content": "earlier"}], user_text="hello",
            params=TurnParams(endpoint_id=endpoint.endpoint_id), stream_cb=streamed.append, engine="pi",
        )
    finally:
        await supervisor.shutdown()
    assert result.text == "streamed answer"
    assert result.endpoint_id == endpoint.endpoint_id
    assert any(event["type"] == "content" for event in streamed)
    assert len(recorded) == 1 and recorded[0]["engine"] == "pi" and recorded[0]["purpose"] == "chat_turn"


@pytest.mark.asyncio
async def test_embed_pi_fails_closed_and_never_falls_back(monkeypatch):
    legacy_calls = []

    async def legacy_spy(verb, **kwargs):
        legacy_calls.append(verb)
        return {"embeddings": [[1.0]]}

    async def no_op(**kwargs):
        return None

    monkeypatch.setattr("app.core.agentic.dispatcher.record_agentic_usage", no_op)
    dispatcher = AgenticDispatcher(legacy_executor=legacy_spy)
    with pytest.raises(AgenticDispatchError, match="pi_embed_gateway_unavailable"):
        await dispatcher.embed(texts=["x"], project_id="p1", engine="pi")
    assert legacy_calls == []  # no silent engine switch
    # The legacy engine embeds through the real bound executor path.
    vectors = await dispatcher.embed(texts=["x"], project_id="p1", engine="legacy")
    assert vectors == [[1.0]] and legacy_calls == ["embed"]


@pytest.mark.asyncio
async def test_ensemble_pi_distinct_endpoints_and_fail_closed(monkeypatch):
    supervisor = PiRuntimeSupervisor()
    ep_a = faux_endpoint([final_text("answer A")], endpoint_id="pi-faux-a")
    ep_b = faux_endpoint([final_text("answer B")], endpoint_id="pi-faux-b")
    manager = _isolated(PiModelManager(endpoints=[ep_a, ep_b]))
    service = PiExecutionService(supervisor=supervisor, model_manager=manager)

    async def no_op(**kwargs):
        return None

    monkeypatch.setattr("app.core.agentic.dispatcher.record_agentic_usage", no_op)
    try:
        result = await AgenticDispatcher(pi_service=service).ensemble(
            purpose="w1.ensemble", project_id="p1",
            messages=[{"role": "user", "content": "go"}], n=2, distinct=True, engine="pi",
        )
        assert {sample.endpoint_id for sample in result.samples} == {"pi-faux-a", "pi-faux-b"}
        assert {sample.text for sample in result.samples} == {"answer A", "answer B"}
        # Fail-closed: fewer distinct endpoints than requested never reuses one.
        with pytest.raises(PiEndpointResolutionError, match="insufficient_distinct"):
            await AgenticDispatcher(pi_service=service).ensemble(
                purpose="w1.ensemble", project_id="p1",
                messages=[{"role": "user", "content": "go"}], n=3, distinct=True, engine="pi",
            )
    finally:
        await supervisor.shutdown()


# ── PiModelManager: catalog sources and capability admission ─────────────
def test_catalog_sources_static_and_local_without_registry():
    import inspect

    import app.core.pi_runtime.model_manager as mm

    assert "compute_registry" not in inspect.getsource(mm).lower()
    manager = PiModelManager()
    ids = {info.endpoint_id for info in manager.catalog()}
    assert "pi-deepseek-default" in ids
    assert "pi-local-ollama" in ids and "pi-local-lmstudio" in ids
    kinds = {info.endpoint_id: info.kind for info in manager.catalog()}
    assert kinds["pi-local-ollama"] == "local"
    # Local entries materialize without any Keychain/secret dependency.
    local = manager.resolve(endpoint_id="pi-local-ollama")
    assert local.kind == "local" and local.base_url.endswith("/v1") and local.api_key


def test_capability_filtering_and_admission_fail_closed():
    vision = _real_endpoint(endpoint_id="pi-vision", model="m-vision", supports_vision=True, context_window=128_000)
    text_only = _real_endpoint(endpoint_id="pi-text", model="m-text", supports_vision=False, context_window=8_000)
    manager = _isolated(PiModelManager(endpoints=[text_only, vision]))
    # require_vision selects the vision-capable endpoint.
    assert manager.resolve(require_vision=True).endpoint_id == "pi-vision"
    # min_context admission selects the large-context endpoint.
    assert manager.resolve(min_context=32_000).endpoint_id == "pi-vision"
    # Explicit endpoint below the required capabilities fails closed.
    with pytest.raises(PiEndpointResolutionError, match="capability_missing:vision"):
        manager.resolve(endpoint_id="pi-text", require_vision=True)
    with pytest.raises(PiEndpointResolutionError, match="capability_missing:context"):
        manager.resolve(endpoint_id="pi-text", min_context=32_000)
    # No matching candidate fails closed.
    with pytest.raises(PiEndpointResolutionError, match="no_matching_pi_endpoint"):
        manager.resolve(model="does-not-exist")
    # Distinct selection honors capability filters too.
    with pytest.raises(PiEndpointResolutionError, match="insufficient_distinct"):
        manager.resolve_distinct(2, require_vision=True)


@pytest.mark.asyncio
async def test_llm_server_projection_excludes_donor_rows():
    """Persisted LLMServer rows project read-only; relay donors never do."""
    from app.core.field_encryption import encrypt_field
    from app.models.database import async_session, init_db
    from app.models.llm_server import LLMServer

    await init_db()
    keep_id = f"test-proj-{uuid.uuid4().hex[:8]}"
    relay_id = f"test-relay-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        db.add(LLMServer(id=keep_id, name="Proj", provider_type="openai_compat",
                         host="https://llm.invalid/v1", api_key=encrypt_field("proj-key"),
                         is_local=False, is_relay=False,
                         capabilities='{"models": ["proj-model"], "context_window": 64000, "vision": true}'))
        db.add(LLMServer(id=relay_id, name="Relay", provider_type="openai_compat",
                         host="https://donor.invalid/v1", is_relay=True))
        await db.commit()
    manager = PiModelManager()
    try:
        await manager.ensure_db_projection()
        ids = {info.endpoint_id for info in manager.catalog()}
        assert f"pi-llm-{keep_id}" in ids
        assert f"pi-llm-{relay_id}" not in ids
        resolved = manager.resolve(endpoint_id=f"pi-llm-{keep_id}")
        assert resolved.model == "proj-model"
        assert resolved.api_key == "proj-key"
        assert resolved.supports_vision and resolved.context_window == 64_000
        # Identity isolation: telemetry exposes ids/kinds, never URLs/keys.
        assert resolved.telemetry_identity() == {
            "endpoint_id": f"pi-llm-{keep_id}", "provider_kind": "openai_compat", "model": "proj-model"
        }
    finally:
        manager._entries.pop(f"pi-llm-{keep_id}", None)
        async with async_session() as db:
            from sqlalchemy import text

            await db.execute(
                text("DELETE FROM llm_servers WHERE id IN (:a, :b)"), {"a": keep_id, "b": relay_id}
            )
            await db.commit()


# ── TurnParams forwarding through the engine ─────────────────────────────
def test_bind_payload_forwards_turn_params_on_real_endpoint():
    params = TurnParams(temperature=0.2, max_tokens=64, thinking_mode="low", timeout_s=5.0)
    payload = _bind_payload(_real_endpoint(), params)
    assert payload["params"] == {
        "temperature": 0.2, "max_tokens": 64, "thinking_level": "low", "timeout_ms": 5000
    }
    # Pricing identity stays intact on the non-faux path.
    assert payload["pricing"]["input_per_mtok"] == 1.0
    # No params set -> no params key (worker/endpoint defaults rule).
    assert "params" not in _bind_payload(_real_endpoint(), TurnParams())


@pytest.mark.asyncio
async def test_engine_forwards_params_to_bind_and_turn_frames():
    supervisor = PiRuntimeSupervisor()
    endpoint = faux_endpoint([final_text("ok")])
    service = PiExecutionService(supervisor=supervisor, model_manager=_isolated(PiModelManager(endpoints=[endpoint])))
    sent: list[dict] = []
    original_send = supervisor._send

    async def spy_send(frame):
        sent.append(frame)
        await original_send(frame)

    supervisor._send = spy_send  # type: ignore[method-assign]
    try:
        result = await service.run_completion(
            purpose="w1.params", project_id="p1", agent_id="a", system="sys",
            messages=[{"role": "user", "content": "hi"}],
            params=TurnParams(temperature=0.3, max_tokens=32, thinking_mode="minimal",
                              timeout_s=4.0, max_turns=2, endpoint_id=endpoint.endpoint_id),
        )
    finally:
        await supervisor.shutdown()
    assert result["status"] == "success"
    bind = next(frame for frame in sent if frame["type"] == "provider.bind")
    assert bind["endpoint"]["params"] == {
        "temperature": 0.3, "max_tokens": 32, "thinking_level": "minimal", "timeout_ms": 4000
    }
    prompt = next(frame for frame in sent if frame["type"] == "turn.prompt")
    assert prompt.get("max_turns") == 2


@pytest.mark.asyncio
async def test_engine_model_and_capability_admission_via_model_manager():
    supervisor = PiRuntimeSupervisor()
    ep_a = faux_endpoint([final_text("from A")], endpoint_id="pi-faux-a")
    ep_b = faux_endpoint([final_text("from B")], endpoint_id="pi-faux-b")
    manager = _isolated(PiModelManager(endpoints=[ep_a, ep_b]))
    service = PiExecutionService(supervisor=supervisor, model_manager=manager)
    try:
        # model= selects the matching catalog endpoint (both are stub-model here,
        # so selection falls to the first entry; a mismatch must fail closed).
        with pytest.raises(PiEndpointResolutionError, match="no_matching_pi_endpoint"):
            await service.run_completion(
                purpose="w1.admit", project_id="p1", agent_id="a", system="sys",
                messages=[{"role": "user", "content": "hi"}], params=TurnParams(model="absent-model"),
            )
        # min_context admission fails closed before any worker frame is sent
        # (no catalog candidate satisfies the filter).
        with pytest.raises(PiEndpointResolutionError, match="no_matching_pi_endpoint"):
            await service.run_completion(
                purpose="w1.admit", project_id="p1", agent_id="a", system="sys",
                messages=[{"role": "user", "content": "hi"}], params=TurnParams(min_context=999_999),
            )
        result = await service.run_completion(
            purpose="w1.admit", project_id="p1", agent_id="a", system="sys",
            messages=[{"role": "user", "content": "hi"}], params=TurnParams(model="stub-model"),
        )
        assert result["status"] == "success" and result["text"] == "from A"
    finally:
        await supervisor.shutdown()


@pytest.mark.asyncio
async def test_react_hard_turn_budget_default(monkeypatch):
    """run_react defaults to an 8-turn budget (legacy MAX_TOOL_ITERATIONS parity)."""
    supervisor = PiRuntimeSupervisor()
    endpoint = faux_endpoint([final_text("done")])
    service = PiExecutionService(supervisor=supervisor, model_manager=_isolated(PiModelManager(endpoints=[endpoint])))
    sent: list[dict] = []
    original_send = supervisor._send

    async def spy_send(frame):
        sent.append(frame)
        await original_send(frame)

    supervisor._send = spy_send  # type: ignore[method-assign]

    async def tool_executor(name, args, project_id, agent_id):
        return {"result": "ok"}

    try:
        await service.run_react(
            purpose="w1.react", project_id="p1", agent_id="a", session_key=None, system="sys",
            messages=[], user_text="go", tool_executor=tool_executor,
            tool_names=["search_memory"], params=TurnParams(endpoint_id=endpoint.endpoint_id),
        )
    finally:
        await supervisor.shutdown()
    prompt = next(frame for frame in sent if frame["type"] == "turn.prompt")
    assert prompt.get("max_turns") == 8
