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
from dataclasses import replace

import pytest

from app.config import settings
from app.core.agentic.dispatcher import AgenticDispatcher, agentic
from app.core.pi_replacement import PI_ENGINE_VALUES
from app.core.agentic.legacy import legacy_executor
from app.core.agentic.types import AgenticDispatchError, TurnParams
from app.core.pi_runtime.endpoints import (
    PiEndpointResolutionError,
    ResolvedPiEndpoint,
)
from app.core.pi_runtime.engine import PiExecutionService, _bind_payload
from app.core.pi_runtime.model_manager import PiModelManager
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor
from tests.pi_production.harness import faux_endpoint, final_text, tool_call


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


def test_dispatcher_exposes_its_engine_owned_pi_model_manager():
    """Selection callers must be able to reuse the dispatch authority."""
    manager = _isolated(PiModelManager(endpoints=[]))
    service = PiExecutionService(model_manager=manager)

    dispatcher = AgenticDispatcher(pi_service=service)
    assert dispatcher.model_manager() is manager
    assert dispatcher.pi_execution_service() is service


@pytest.mark.parametrize("alias", sorted(PI_ENGINE_VALUES))
@pytest.mark.asyncio
async def test_explicit_pi_aliases_normalize_at_both_dispatcher_boundaries(alias):
    """Every supported Pi spelling must select the Pi provider path."""
    dispatcher = AgenticDispatcher()

    assert dispatcher.resolve_engine(engine=alias) == "pi"
    assert await dispatcher._resolve(project_id="project-1", engine=alias, request=None) == "pi"


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


class _ProviderAuthorityStub:
    def __init__(self, samples: list[dict] | None = None) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.samples = samples or []

    async def run_completion(self, **kwargs):
        self.calls.append(("completion", kwargs))
        return {
            "text": "managed text",
            "usage": {"input_tokens": 11, "output_tokens": 7, "total_tokens": 18},
            "stop_reason": "stop",
            "tool_calls": [],
            "status": "success",
            "endpoint_id": "pi-managed-a",
            "model": "m1",
        }

    async def run_structured(self, **kwargs):
        self.calls.append(("structured", kwargs))
        return {
            "text": "",
            "value": {"accepted": True},
            "usage": {},
            "stop_reason": "stop",
            "tool_calls": [],
            "status": "success",
            "endpoint_id": "pi-managed-a",
            "model": "m1",
        }

    async def run_ensemble(self, **kwargs):
        self.calls.append(("ensemble", kwargs))
        samples = self.samples[: kwargs["n"]]
        return {
            "samples": samples,
            "endpoint_ids": [sample["endpoint_id"] for sample in samples],
            "usage": {},
            "status": "success" if all(sample["status"] == "success" for sample in samples) else "error",
        }


class _DistinctLegacyServer:
    def __init__(
        self, node_id: str, model: str, text: str, *, healthy: bool = True, fail: bool = False
    ) -> None:
        self.node_id = node_id
        self.name = node_id
        self.loaded_models = [model]
        self.is_healthy = healthy
        self.fail = fail
        self.calls: list[dict] = []
        self._text = text

    async def chat(self, messages, **kwargs):
        self.calls.append({"messages": messages, **kwargs})
        if self.fail:
            raise RuntimeError("legacy test server failed")
        return {
            "message": {"content": self._text},
            "prompt_eval_count": 2,
            "eval_count": 1,
            "_istara_route": {"node_id": self.node_id, "model": self.loaded_models[0]},
        }


@pytest.mark.asyncio
async def test_legacy_completion_preserves_loop_choice_but_uses_pi_provider_authority():
    stub = _ProviderAuthorityStub()
    params = TurnParams(model="m1", temperature=0.2, max_tokens=64, thinking_mode="low",
                        min_context=8192, timeout_s=5.0, max_turns=3, require_vision=True)
    outcome = await legacy_executor(
        "completion", purpose="p", project_id="proj-1", agent_id="a", system="sys",
        messages=[{"role": "user", "content": "hi"}], params=params,
        provider_service=stub,
    )
    method, call = stub.calls[0]
    assert method == "completion"
    assert call["params"] is params
    assert call["project_id"] == "proj-1"
    assert call["system"] == "sys"
    assert outcome["text"] == "managed text"
    assert outcome["endpoint_id"] == "pi-managed-a"


@pytest.mark.asyncio
async def test_legacy_structured_uses_pi_provider_authority():
    stub = _ProviderAuthorityStub()
    outcome = await legacy_executor(
        "structured", purpose="debate synthesis!", project_id="p", agent_id="a", system=None,
        messages=[{"role": "user", "content": "go"}],
        schema={"type": "object", "required": ["accepted"]}, params=TurnParams(),
        provider_service=stub,
    )
    method, call = stub.calls[0]
    assert method == "structured"
    assert call["purpose"] == "debate synthesis!"
    assert outcome["value"] == {"accepted": True}


@pytest.mark.asyncio
async def test_legacy_embed_uses_pi_managed_gateway():
    calls = []

    class _Gateway:
        async def embed(self, texts, *, model=None):
            calls.append({"texts": texts, "model": model})
            return {"embeddings": [[0.1, 0.2]] * len(texts), "status": "success"}

    outcome = await legacy_executor(
        "embed", texts=["a", "b"], project_id="p", params=TurnParams(model="emb"),
        embeddings_gateway=_Gateway(), provider_service=_ProviderAuthorityStub(),
    )
    assert calls == [{"texts": ["a", "b"], "model": "emb"}]
    assert outcome["embeddings"] == [[0.1, 0.2], [0.1, 0.2]]


@pytest.mark.asyncio
async def test_legacy_unknown_verb_fails_closed():
    with pytest.raises(AgenticDispatchError, match="legacy_verb_unknown"):
        await legacy_executor("summarize", params=TurnParams())


@pytest.mark.asyncio
async def test_legacy_mode_ensemble_uses_pi_identity_authority_and_preserves_models(monkeypatch):
    samples = [
        {"text": f"answer-{name}", "status": "success", "usage": {},
         "endpoint_id": f"pi-{name}", "model": f"model-{name}"}
        for name in ("a", "b", "c")
    ]
    service = _ProviderAuthorityStub(samples)
    dispatcher = AgenticDispatcher(pi_service=service)

    async def no_op_record(**kwargs):
        return None

    monkeypatch.setattr(dispatcher, "_record_outcome", no_op_record)
    result = await dispatcher.ensemble(
        purpose="w7.legacy.distinct", project_id="p1",
        messages=[{"role": "user", "content": "go"}], n=4, minimum_n=3,
        distinct=True, system="sys", params=TurnParams(), engine="legacy",
    )

    method, call = service.calls[0]
    assert method == "ensemble"
    assert call["n"] == 3 and call["distinct"] is True
    assert result.endpoint_ids == ["pi-a", "pi-b", "pi-c"]
    assert {sample.model for sample in result.samples} == {
        "model-a", "model-b", "model-c"
    }


@pytest.mark.asyncio
async def test_pi_mode_forwards_governed_minimum_width_to_pi_service():
    """Pi receives the minimum width when ``n`` includes a legacy spare."""
    samples = [
        {"text": f"answer-{name}", "status": "success", "usage": {},
         "endpoint_id": f"pi-{name}", "model": f"model-{name}"}
        for name in ("a", "b", "c")
    ]
    service = _ProviderAuthorityStub(samples)
    dispatcher = AgenticDispatcher(pi_service=service)

    result = await dispatcher.ensemble(
        purpose="w1.pi.minimum-width", project_id="p1",
        messages=[{"role": "user", "content": "go"}], n=4, minimum_n=3,
        distinct=True, system="sys", params=TurnParams(), engine="pi",
    )

    method, call = service.calls[0]
    assert method == "ensemble"
    assert call["n"] == 4 and call["minimum_n"] == 3
    assert result.endpoint_ids == ["pi-a", "pi-b", "pi-c"]


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
async def test_chat_turn_preserves_provider_served_model_identity(monkeypatch):
    """A streamed Pi terminal receipt must reach the public TurnResult/ledger."""

    class _StreamingService:
        async def run_chat_turn(self, **kwargs):  # noqa: ANN001
            yield {"type": "content", "text": "hello"}
            yield {
                "type": "done",
                "usage": {"input_tokens": 1, "output_tokens": 1},
                "stop_reason": "stop",
                "endpoint_id": "managed-endpoint",
                "model": "configured-model",
                "served_model": "provider-served-model",
            }

    recorded = []

    async def capture(**kwargs):  # noqa: ANN001
        recorded.append(kwargs)

    monkeypatch.setattr("app.core.agentic.dispatcher.record_agentic_usage", capture)
    result = await AgenticDispatcher(pi_service=_StreamingService()).chat_turn(
        project_id="p1",
        agent_id="istara-main",
        session_key=None,
        system_prompt="sys",
        messages=[],
        user_text="hello",
        params=TurnParams(model="configured-model"),
        engine="pi",
    )

    assert result.model == "configured-model"
    assert result.served_model == "provider-served-model"
    assert recorded[0]["model"] == "provider-served-model"


@pytest.mark.asyncio
async def test_legacy_and_pi_chat_choices_share_real_pi_manager(monkeypatch):
    """Both chat choices route through one Pi manager-owned endpoint identity."""

    supervisor = PiRuntimeSupervisor()
    endpoint = replace(
        faux_endpoint([final_text("shared reply")], endpoint_id="pi-shared-chat"),
        model="shared-chat-model",
    )
    manager = _isolated(PiModelManager(endpoints=[endpoint], include_local=False))
    service = PiExecutionService(supervisor=supervisor, model_manager=manager)

    async def no_op(**kwargs):  # noqa: ANN001
        return None

    monkeypatch.setattr("app.core.agentic.dispatcher.record_agentic_usage", no_op)
    try:
        results = {}
        for engine in ("legacy", "pi"):
            results[engine] = await AgenticDispatcher(pi_service=service).chat_turn(
                project_id="p1",
                agent_id="istara-main",
                session_key=None,
                system_prompt="sys",
                messages=[],
                user_text="hello",
                params=TurnParams(endpoint_id=endpoint.endpoint_id),
                engine=engine,
            )
    finally:
        await supervisor.shutdown()

    for result in results.values():
        assert result.status == "success"
        assert result.endpoint_id == endpoint.endpoint_id
        assert result.model == endpoint.model
        # The deterministic faux provider does not emit provider-response
        # identity; this test proves shared Pi admission/authority only. The
        # separate streamed-receipt test above covers propagation when a
        # provider supplies the explicit identity.
        assert result.served_model is None
        assert result.text == "shared reply"


@pytest.mark.asyncio
async def test_structured_uses_explicit_request_scoped_pi_service(monkeypatch):
    """The Research Spine can pin its selected service without losing dispatch accounting."""

    class _StructuredService:
        def __init__(self):
            self.calls = []

        async def run_structured(self, **kwargs):  # noqa: ANN001
            self.calls.append(kwargs)
            return {
                "text": "",
                "value": {"ok": True},
                "status": "success",
                "usage": {},
                "stop_reason": "stop",
                "endpoint_id": "scoped-endpoint",
                "model": "scoped-model",
            }

    async def no_op(**kwargs):  # noqa: ANN001
        return None

    monkeypatch.setattr("app.core.agentic.dispatcher.record_agentic_usage", no_op)
    default_service = _StructuredService()
    scoped_service = _StructuredService()
    result = await AgenticDispatcher(pi_service=default_service).structured(
        purpose="w1.scoped-structured",
        project_id="p1",
        system="system",
        messages=[{"role": "user", "content": "code"}],
        schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
        params=TurnParams(endpoint_id="scoped-endpoint", model="scoped-model"),
        engine="pi",
        pi_service=scoped_service,
    )

    assert result.endpoint_id == "scoped-endpoint"
    assert len(scoped_service.calls) == 1
    assert default_service.calls == []


@pytest.mark.asyncio
async def test_embed_pi_routes_through_gateway_and_never_falls_back(monkeypatch):
    legacy_calls = []

    async def legacy_spy(verb, **kwargs):
        legacy_calls.append(verb)
        return {"embeddings": [[1.0]]}

    async def no_op(**kwargs):
        return None

    monkeypatch.setattr("app.core.agentic.dispatcher.record_agentic_usage", no_op)
    gateway_calls = []

    class _StubGateway:
        async def embed(self, texts, *, model=None):
            gateway_calls.append(list(texts))
            return {
                "embeddings": [[2.0]],
                "endpoint_id": "pi-local-ollama",
                "usage": {"estimate": False},
                "status": "success",
            }

    dispatcher = AgenticDispatcher(legacy_executor=legacy_spy, embeddings_gateway=_StubGateway())
    # Embeddings have no agent loop: both selections use the one Pi-managed
    # gateway and never reopen the legacy ComputeRegistry provider plane.
    vectors = await dispatcher.embed(texts=["x"], project_id="p1", engine="pi")
    assert vectors == [[2.0]] and gateway_calls == [["x"]]
    assert legacy_calls == []  # no silent engine switch
    vectors = await dispatcher.embed(texts=["x"], project_id="p1", engine="legacy")
    assert vectors == [[2.0]] and gateway_calls == [["x"], ["x"]]
    assert legacy_calls == []


@pytest.mark.asyncio
async def test_ensemble_pi_distinct_endpoints_and_fail_closed(monkeypatch):
    supervisor = PiRuntimeSupervisor()
    ep_a = replace(
        faux_endpoint([final_text("answer A")], endpoint_id="pi-faux-a"),
        model="model-a",
    )
    ep_b = replace(
        faux_endpoint([final_text("answer B")], endpoint_id="pi-faux-b"),
        model="model-b",
    )
    manager = _isolated(PiModelManager(endpoints=[ep_a, ep_b]))
    selection_calls = []
    original_resolve_distinct = manager.resolve_distinct

    def record_project_scope(n, **kwargs):
        selection_calls.append({"n": n, **kwargs})
        return original_resolve_distinct(n, **kwargs)

    manager.resolve_distinct = record_project_scope  # type: ignore[method-assign]
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
        assert selection_calls[0]["project_id"] == "p1"
        assert {sample.text for sample in result.samples} == {"answer A", "answer B"}
        # Fail-closed: fewer distinct endpoints than requested never reuses one.
        with pytest.raises(PiEndpointResolutionError, match="insufficient_distinct"):
            await AgenticDispatcher(pi_service=service).ensemble(
                purpose="w1.ensemble", project_id="p1",
                messages=[{"role": "user", "content": "go"}], n=3, distinct=True, engine="pi",
            )
    finally:
        await supervisor.shutdown()


@pytest.mark.asyncio
async def test_legacy_and_pi_ensemble_choices_share_real_pi_manager(monkeypatch):
    """Both loop choices must use the same manager-owned rater identities.

    The legacy choice preserves Istara's surrounding loop semantics, but it
    must not reopen the removed ComputeRegistry/provider path.  Exercising both
    choices against one real ``PiExecutionService`` and one real
    ``PiModelManager`` makes that authority boundary observable instead of
    proving it only with a provider stub.
    """
    supervisor = PiRuntimeSupervisor()
    endpoints = [
        replace(
            faux_endpoint([final_text(f"answer-{name}")], endpoint_id=f"pi-shared-{name}"),
            model=f"shared-model-{name}",
        )
        for name in ("a", "b", "c")
    ]
    manager = _isolated(PiModelManager(endpoints=endpoints, include_local=False))
    service = PiExecutionService(supervisor=supervisor, model_manager=manager)

    async def no_op(**kwargs):
        return None

    monkeypatch.setattr("app.core.agentic.dispatcher.record_agentic_usage", no_op)
    try:
        results = {}
        for engine in ("legacy", "pi"):
            results[engine] = await AgenticDispatcher(pi_service=service).ensemble(
                purpose=f"w1.shared-manager.{engine}",
                project_id="p1",
                messages=[{"role": "user", "content": "compare"}],
                n=3,
                distinct=True,
                engine=engine,
            )
    finally:
        await supervisor.shutdown()

    expected_endpoints = {"pi-shared-a", "pi-shared-b", "pi-shared-c"}
    expected_models = {"shared-model-a", "shared-model-b", "shared-model-c"}
    for result in results.values():
        assert result.status == "success"
        assert set(result.endpoint_ids) == expected_endpoints
        assert {sample.model for sample in result.samples} == expected_models


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
        telemetry_identity = resolved.telemetry_identity()
        assert telemetry_identity == {
            "endpoint_id": f"pi-llm-{keep_id}",
            "provider_kind": "openai_compat",
            "model": "proj-model",
            "provider_account_handle": resolved.provider_account_handle,
        }
        assert resolved.provider_account_handle
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
async def test_engine_provider_turn_returns_raw_tool_call_without_executing_it():
    supervisor = PiRuntimeSupervisor()
    endpoint = faux_endpoint(
        [tool_call("search_documents", {"query": "bias"})],
        endpoint_id="pi-provider-only",
    )
    service = PiExecutionService(
        supervisor=supervisor,
        model_manager=_isolated(PiModelManager(endpoints=[endpoint])),
    )
    try:
        result = await service.run_provider_turn(
            purpose="w1.legacy-provider-turn",
            project_id="p1",
            agent_id="legacy",
            system="sys",
            messages=[{"role": "user", "content": "inspect"}],
            tools=[{
                "name": "search_documents",
                "description": "Search documents",
                "parameters": {"type": "object", "properties": {}},
            }],
            params=TurnParams(endpoint_id=endpoint.endpoint_id),
        )
    finally:
        await supervisor.shutdown()
    assert result["status"] == "success"
    assert result["tool_calls"] == [
        {
            "id": result["tool_calls"][0]["id"],
            "type": "function",
            "function": {
                "name": "search_documents",
                "arguments": '{"query":"bias"}',
            },
        }
    ]


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
