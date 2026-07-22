"""W1 contract-complete coverage (F-W1-4).

Replaces the earlier self-consistent W1 smoke tests with proofs of the actual
production contracts from the master plan (§4, §5) and the W1 review findings:

* all five dispatcher verbs exist and route to the selected engine seam;
* both engine seams are real (Pi through the supervised faux-worker runtime,
  legacy through the bound real-plane executor) and Pi-only gaps fail typed
  instead of silently switching engines;
* engine precedence is per-call override > request header > project setting >
  configured default, wired into the verbs;
* ``TurnParams`` is forwarded unchanged to the selected engine seam;
* the Pi model catalog covers its three sources (static settings, read-only
  LLMServer projection, local serving) with capability-filtered, fail-closed
  selection and no ComputeRegistry or donor dependency;
* structured output is a forced tool call with Python revalidation, exactly
  one bounded repair, and a typed fail-closed failure — never an error-shaped
  result and never free-form JSON text accepted as structured;
* every dispatch persists exactly one durable ledger row with exact-vs-
  estimated semantics, including exception paths;
* the worker protocol version matches on both sides and a mismatched peer is
  rejected at handshake;
* the W1 wave leaves the armed 87-site count-to-zero ratchet unchanged;
* same-model donor isolation holds (static plane guard here; the behavioral
  bidirectional proof lives in ``test_same_model_donor_isolation.py`` and runs
  in the same ladder).

All verification here is faux/loopback/static: no live model activity and no
external traffic.
"""

from __future__ import annotations

import ast
import json
import re
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.agentic import dispatcher as dispatcher_module
from app.core.agentic import legacy as legacy_module
from app.core.agentic.dispatcher import AgenticDispatcher
from app.core.agentic.types import AgenticDispatchError, EnsembleResult, TurnParams
from app.core.pi_runtime.endpoints import PiEndpointResolutionError, PiRuntimeTurnError
from app.core.pi_runtime.model_manager import PiModelManager
from app.core.pi_runtime.supervisor import PiRuntimeSupervisor, PiWorkerError
from app.models.agentic_usage import AgenticUsageRow
from app.models.database import async_session, init_db
from app.models.project import Project
from tests.pi_production.harness import faux_service, final_text, requires_node, tool_call

REPO_ROOT = Path(__file__).resolve().parents[2]

STRUCTURED_SCHEMA = {
    "type": "object",
    "properties": {"accepted": {"type": "boolean"}},
    "required": ["accepted"],
}


# ── helpers ─────────────────────────────────────────────────────────────


class _RecordingLegacyExecutor:
    """Legacy engine seam spy: records the verb/kwargs and returns an outcome."""

    def __init__(self, outcome: dict | None = None) -> None:
        self.calls: list[dict] = []
        self._outcome = outcome or {
            "text": "legacy-done",
            "status": "success",
            "stop_reason": "stop",
            "endpoint_id": "legacy-node-1",
            "usage": {"input_tokens": 11, "output_tokens": 7, "cost_usd": 0.001},
        }

    async def __call__(self, **kwargs):
        self.calls.append(kwargs)
        verb = kwargs.get("verb")
        if verb == "embed":
            return {"embeddings": [[0.1, 0.2]], "usage": {"estimate": False}, "status": "success"}
        if verb == "ensemble":
            return {
                "samples": [dict(self._outcome), dict(self._outcome)],
                "endpoint_ids": ["legacy", "legacy"],
                "usage": {"input_tokens": 22, "output_tokens": 14},
                "status": "success",
            }
        return dict(self._outcome)


class _RaisingLegacyExecutor:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    async def __call__(self, **kwargs):
        raise self._exc


class _StubPiService:
    """Pi seam stub capturing every run_* invocation for routing/param proofs."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def _record(self, method: str, kwargs: dict) -> dict:
        self.calls.append((method, kwargs))
        return {
            "text": "pi-done",
            "value": {"accepted": True},
            "status": "success",
            "stop_reason": "stop",
            "endpoint_id": "pi-stub",
            "usage": {"input": 5, "output": 3, "cost": {"total": 0.0004}},
        }

    def run_chat_turn(self, **kwargs):
        self.calls.append(("run_chat_turn", kwargs))

        async def _events():
            yield {"type": "content", "text": "pi-done"}
            yield {
                "type": "done",
                "usage": {"input": 5, "output": 3, "cost": {"total": 0.0004}},
                "stop_reason": "stop",
                "endpoint_id": "pi-stub",
            }

        return _events()

    async def run_completion(self, **kwargs):
        return self._record("run_completion", kwargs)

    async def run_structured(self, **kwargs):
        return self._record("run_structured", kwargs)

    async def run_react(self, **kwargs):
        return self._record("run_react", kwargs)

    async def run_ensemble(self, **kwargs):
        self.calls.append(("run_ensemble", kwargs))
        return {
            "samples": [
                {"text": "s1", "status": "success", "endpoint_id": "pi-a", "usage": {"input": 1, "output": 1}},
                {"text": "s2", "status": "success", "endpoint_id": "pi-b", "usage": {"input": 1, "output": 1}},
            ],
            "endpoint_ids": ["pi-a", "pi-b"],
            "usage": {"input": 2, "output": 2},
            "status": "success",
        }


@pytest.fixture
async def usage_db():
    await init_db()
    # W2: route-level tests earlier in the suite legitimately persist ledger
    # rows through the dispatcher (chat_turn via the chat/design-chat routes)
    # without this fixture, so isolation must clean BEFORE the test as well,
    # not only after it.
    async with async_session() as session:
        await session.execute(AgenticUsageRow.__table__.delete())
        await session.commit()
    try:
        yield
    finally:
        async with async_session() as session:
            await session.execute(AgenticUsageRow.__table__.delete())
            await session.commit()


async def _ledger_rows(**filters) -> list[AgenticUsageRow]:
    async with async_session() as session:
        stmt = select(AgenticUsageRow)
        for key, value in filters.items():
            stmt = stmt.where(getattr(AgenticUsageRow, key) == value)
        return list((await session.execute(stmt)).scalars())


def _request_with_header(value: str) -> SimpleNamespace:
    return SimpleNamespace(headers={"x-istara-agent-engine": value})


def _completion_kwargs(purpose: str) -> dict:
    return {
        "purpose": purpose,
        "project_id": "p1",
        "system": "system",
        "messages": [{"role": "user", "content": "hello"}],
        "params": TurnParams(),
    }


# ── five verbs + both real engine seams ─────────────────────────────────


def test_dispatcher_exposes_exactly_the_five_contract_verbs():
    for verb in ("chat_turn", "completion", "structured", "ensemble", "embed"):
        assert callable(getattr(AgenticDispatcher, verb, None)), f"missing verb {verb}"


def test_production_singleton_binds_both_real_engine_seams():
    """The module singleton mirrors the ollama/llm_router idiom: a real
    PiExecutionService and the REAL legacy-plane executor — never None, never a
    placeholder."""
    from app.core.pi_runtime.engine import PiExecutionService

    singleton = dispatcher_module.agentic
    assert isinstance(singleton._pi, PiExecutionService)
    assert singleton._legacy is legacy_module.legacy_executor


async def test_every_verb_routes_to_the_pi_seam_and_records_one_row(usage_db):
    service = _StubPiService()
    dispatcher = AgenticDispatcher(pi_service=service, legacy_executor=_RecordingLegacyExecutor())
    tag = uuid.uuid4().hex[:8]

    result = await dispatcher.chat_turn(
        project_id="p1", agent_id="a1", session_key="s1", system_prompt="sys",
        messages=[], user_text="hi", engine="pi",
    )
    assert result.text == "pi-done"

    await dispatcher.completion(**_completion_kwargs(f"w1.verbs.completion.{tag}"), engine="pi")
    structured = await dispatcher.structured(
        purpose=f"w1.verbs.structured.{tag}", project_id="p1", system="sys",
        messages=[{"role": "user", "content": "go"}], schema=STRUCTURED_SCHEMA,
        params=TurnParams(), engine="pi",
    )
    assert structured.value == {"accepted": True}

    ensemble = await dispatcher.ensemble(
        purpose=f"w1.verbs.ensemble.{tag}", project_id="p1",
        messages=[{"role": "user", "content": "go"}], n=2, distinct=True, engine="pi",
    )
    assert isinstance(ensemble, EnsembleResult)
    assert ensemble.endpoint_ids == ["pi-a", "pi-b"]

    methods = [method for method, _ in service.calls]
    assert methods == ["run_chat_turn", "run_completion", "run_structured", "run_ensemble"]
    # Exactly one ledger row per dispatch, whatever the verb.
    for purpose in (f"w1.verbs.completion.{tag}", f"w1.verbs.structured.{tag}", f"w1.verbs.ensemble.{tag}"):
        assert len(await _ledger_rows(purpose=purpose)) == 1
    assert len(await _ledger_rows(purpose="chat_turn")) == 1


async def test_every_verb_routes_to_the_legacy_seam_and_records_one_row(usage_db):
    legacy = _RecordingLegacyExecutor()
    dispatcher = AgenticDispatcher(pi_service=_StubPiService(), legacy_executor=legacy)
    tag = uuid.uuid4().hex[:8]

    await dispatcher.chat_turn(
        project_id="p1", agent_id="a1", session_key="s1", system_prompt="sys",
        messages=[], user_text="hi", engine="legacy",
    )
    await dispatcher.completion(**_completion_kwargs(f"w1.verbs.legacy.completion.{tag}"), engine="legacy")
    await dispatcher.structured(
        purpose=f"w1.verbs.legacy.structured.{tag}", project_id="p1", system="sys",
        messages=[{"role": "user", "content": "go"}], schema=STRUCTURED_SCHEMA,
        params=TurnParams(), engine="legacy",
    )
    ensemble = await dispatcher.ensemble(
        purpose=f"w1.verbs.legacy.ensemble.{tag}", project_id="p1",
        messages=[{"role": "user", "content": "go"}], n=2, engine="legacy",
    )
    assert [sample.text for sample in ensemble.samples] == ["legacy-done", "legacy-done"]
    vectors = await dispatcher.embed(texts=["hello"], project_id="p1", engine="legacy")
    assert vectors == [[0.1, 0.2]]

    verbs = [call["verb"] for call in legacy.calls]
    assert verbs == ["chat_turn", "completion", "structured", "ensemble", "embed"]
    for purpose in (
        f"w1.verbs.legacy.completion.{tag}",
        f"w1.verbs.legacy.structured.{tag}",
        f"w1.verbs.legacy.ensemble.{tag}",
        "chat_turn",
        "embed",
    ):
        assert len(await _ledger_rows(purpose=purpose)) == 1


async def test_pi_embed_routes_through_the_w8_gateway(usage_db):
    """W8: a Pi-selected embed dispatches through the EmbeddingsGateway and
    records its one ledger row; a gateway failure propagates typed and never
    leaks onto the legacy plane."""
    legacy = _RecordingLegacyExecutor()

    class _StubGateway:
        def __init__(self) -> None:
            self.calls: list[tuple[list[str], str | None]] = []

        async def embed(self, texts, *, model=None):
            self.calls.append((list(texts), model))
            return {
                "embeddings": [[0.3, 0.4]],
                "endpoint_id": "pi-local-ollama",
                "model": model or "nomic-embed-text",
                "usage": {"estimate": False},
                "status": "success",
            }

    gateway = _StubGateway()
    dispatcher = AgenticDispatcher(
        pi_service=_StubPiService(), legacy_executor=legacy, embeddings_gateway=gateway
    )
    vectors = await dispatcher.embed(texts=["hello"], project_id="p1", engine="pi")
    assert vectors == [[0.3, 0.4]]
    assert gateway.calls == [(["hello"], None)]
    assert legacy.calls == [], "a Pi embed must never execute on the legacy plane"
    rows = await _ledger_rows(purpose="embed")
    assert len(rows) == 1
    assert rows[0].engine == "pi"
    assert rows[0].outcome == "success"
    assert rows[0].endpoint_id == "pi-local-ollama"


@requires_node
async def test_completion_pi_seam_drives_the_real_supervised_worker(usage_db):
    """Pi seam end-to-end: a real supervised worker (faux provider) serves the
    turn and exactly one ledger row is persisted for the dispatch."""
    supervisor = PiRuntimeSupervisor()
    service = faux_service([{"text": "done", "stop_reason": "stop"}], supervisor)
    purpose = f"w1.verbs.{uuid.uuid4().hex[:8]}"
    try:
        result = await AgenticDispatcher(pi_service=service).completion(
            purpose=purpose, project_id="p1", system="system",
            messages=[{"role": "user", "content": "hello"}], params=TurnParams(), engine="pi",
        )
    finally:
        await supervisor.shutdown()
    assert result.text == "done"
    assert result.endpoint_id == "pi-faux"
    rows = await _ledger_rows(purpose=purpose)
    assert len(rows) == 1
    assert rows[0].engine == "pi"
    assert rows[0].outcome == "success"


async def test_completion_legacy_seam_executes_the_bound_executor(usage_db):
    """Legacy seam: the bound executor is invoked byte-compatibly and its
    provider-reported usage lands exact (estimate=0) in the ledger row."""
    legacy = _RecordingLegacyExecutor()
    purpose = f"w1.legacy.{uuid.uuid4().hex[:8]}"
    result = await AgenticDispatcher(legacy_executor=legacy).completion(
        purpose=purpose, project_id="p1", system="system",
        messages=[{"role": "user", "content": "hello"}], params=TurnParams(model="m1"), engine="legacy",
    )
    assert result.text == "legacy-done"
    assert legacy.calls and legacy.calls[0]["verb"] == "completion"
    rows = await _ledger_rows(purpose=purpose)
    assert len(rows) == 1
    row = rows[0]
    assert row.engine == "legacy"
    assert row.input_tokens == 11 and row.output_tokens == 7
    assert row.estimate == 0  # provider-reported usage is exact, never estimated


# ── precedence resolution ────────────────────────────────────────────────


def test_engine_precedence_is_override_then_request_then_project_then_default(monkeypatch):
    dispatcher = AgenticDispatcher(pi_service=_StubPiService(), legacy_executor=_RecordingLegacyExecutor())
    monkeypatch.setattr("app.core.agentic.dispatcher.settings.agentic_engine_default", "pi", raising=False)

    # Per-call override always wins.
    assert dispatcher.resolve_engine(engine="legacy", request=_request_with_header("pi"), project_engine="pi") == "legacy"
    assert dispatcher.resolve_engine(engine="pi", request=_request_with_header("legacy"), project_engine="legacy") == "pi"
    # Request header beats project setting and default.
    assert dispatcher.resolve_engine(request=_request_with_header("pi"), project_engine="legacy") == "pi"
    assert dispatcher.resolve_engine(request=_request_with_header("deepseek-pi"), project_engine="legacy") == "pi"
    assert dispatcher.resolve_engine(request=_request_with_header("legacy"), project_engine="pi") == "legacy"
    # Project setting beats the configured default.
    assert dispatcher.resolve_engine(project_engine="pi") == "pi"
    assert dispatcher.resolve_engine(project_engine="legacy") == "legacy"
    # Configured default is the last resort.
    assert dispatcher.resolve_engine() == "pi"
    monkeypatch.setattr("app.core.agentic.dispatcher.settings.agentic_engine_default", "legacy", raising=False)
    assert dispatcher.resolve_engine() == "legacy"
    # Unknown/absent values never silently select Pi.
    assert dispatcher.resolve_engine(request=_request_with_header("gpt-4o")) == "legacy"


async def test_verbs_read_the_persisted_project_engine_setting(usage_db):
    """Level-3 precedence is real: the project's persisted agentic_engine column
    selects the engine when no per-call override or header is present, and the
    request header still beats it."""
    project_id = f"w1-precedence-{uuid.uuid4().hex[:8]}"
    async with async_session() as session:
        session.add(Project(id=project_id, name="W1 precedence", agentic_engine="pi"))
        await session.commit()
    service = _StubPiService()
    legacy = _RecordingLegacyExecutor()
    dispatcher = AgenticDispatcher(pi_service=service, legacy_executor=legacy)
    try:
        await dispatcher.completion(**_completion_kwargs("w1.precedence.project") | {"project_id": project_id})
        assert service.calls and service.calls[0][0] == "run_completion"
        assert legacy.calls == []

        await dispatcher.completion(
            **(_completion_kwargs("w1.precedence.header") | {"project_id": project_id}),
            request=_request_with_header("legacy"),
        )
        assert legacy.calls and legacy.calls[0]["verb"] == "completion"
    finally:
        async with async_session() as session:
            row = await session.get(Project, project_id)
            if row is not None:
                await session.delete(row)
            await session.commit()


# ── parameter forwarding ─────────────────────────────────────────────────


async def test_turn_params_are_forwarded_unchanged_to_both_engine_seams():
    service = _StubPiService()
    legacy = _RecordingLegacyExecutor()
    params = TurnParams(model="deepseek-v4-pro", temperature=0.2, max_tokens=512,
                        thinking_mode="high", min_context=32768, timeout_s=45.0,
                        max_turns=5, require_vision=True)
    dispatcher = AgenticDispatcher(pi_service=service, legacy_executor=legacy)

    await dispatcher.completion(purpose="w1.params", project_id="p1", system="s",
                                messages=[{"role": "user", "content": "hi"}], params=params, engine="pi")
    assert service.calls[0][1]["params"] is params

    await dispatcher.structured(purpose="w1.params", project_id="p1", system="s",
                                messages=[{"role": "user", "content": "hi"}],
                                schema=STRUCTURED_SCHEMA, params=params, engine="pi")
    assert service.calls[1][1]["params"] is params

    await dispatcher.react(purpose="w1.params", project_id="p1", agent_id="a1", session_key="s1",
                           system="s", messages=[], user_text="go", tool_executor=None,
                           tool_names=["search_documents"], params=params, engine="pi")
    assert service.calls[2][1]["params"] is params

    await dispatcher.chat_turn(project_id="p1", agent_id="a1", session_key="s1", system_prompt="s",
                               messages=[], user_text="hi", params=params, engine="pi")
    assert service.calls[3][1]["params"] is params

    await dispatcher.ensemble(purpose="w1.params", project_id="p1",
                              messages=[{"role": "user", "content": "hi"}], n=2, params=params, engine="pi")
    assert service.calls[4][1]["params"] is params

    await dispatcher.completion(purpose="w1.params.legacy", project_id="p1", system="s",
                                messages=[{"role": "user", "content": "hi"}], params=params, engine="legacy")
    assert legacy.calls[0]["params"] is params


# ── typed structured failure (forced tool call contract) ────────────────


@requires_node
async def test_structured_valid_forced_capture_returns_the_object():
    supervisor = PiRuntimeSupervisor()
    service = faux_service([tool_call("emit_structured_output", {"accepted": True})], supervisor)
    try:
        result = await service.run_structured(
            purpose="w1.structured.ok", project_id="p1", agent_id="a1", system="sys",
            messages=[{"role": "user", "content": "go"}], schema=STRUCTURED_SCHEMA, params=TurnParams(),
        )
    finally:
        await supervisor.shutdown()
    assert result["status"] == "success"
    assert result["value"] == {"accepted": True}


@requires_node
async def test_structured_free_form_json_text_is_never_accepted_and_fails_typed():
    """Free-form JSON text — even schema-valid text — is not structured output:
    the missing forced call triggers exactly one bounded repair, then a typed
    fail-closed error."""
    supervisor = PiRuntimeSupervisor()
    service = faux_service([final_text('{"accepted": true}'), final_text('{"accepted": true}')], supervisor)
    try:
        with pytest.raises(PiRuntimeTurnError, match="structured_output_missing"):
            await service.run_structured(
                purpose="w1.structured.freeform", project_id="p1", agent_id="a1", system="sys",
                messages=[{"role": "user", "content": "go"}], schema=STRUCTURED_SCHEMA, params=TurnParams(),
            )
    finally:
        await supervisor.shutdown()


async def test_structured_second_invalid_capture_raises_typed_failure():
    """One bounded repair, then a typed failure — never an error-shaped
    StructuredResult returned as if it were a success. (The worker-side
    capture path is proven by the valid-forced-capture test; pi-ai rejects
    schema-violating arguments before capture, so the captured-invalid path is
    driven at the Python revalidation boundary — the authoritative contract.)"""
    from app.core.pi_runtime.engine import PiExecutionService

    class InvalidTwiceService(PiExecutionService):
        def __init__(self) -> None:
            self.calls = 0

        async def _collect_turn(self, **kwargs):
            self.calls += 1
            return {
                "text": "",
                "tool_calls": [],
                "status": "success",
                "usage": {},
                "stop_reason": "toolUse",
                "endpoint_id": "pi-faux",
                "structured": {"wrong": True},  # fails the original schema
                "error": None,
            }

    service = InvalidTwiceService()
    with pytest.raises(PiRuntimeTurnError, match="structured_output_invalid"):
        await service.run_structured(
            purpose="w1.structured.invalid", project_id="p1", agent_id="a1", system="sys",
            messages=[{"role": "user", "content": "go"}], schema=STRUCTURED_SCHEMA, params=TurnParams(),
        )
    assert service.calls == 2, "exactly one bounded repair, never an unbounded retry loop"


@requires_node
async def test_structured_unsupported_schema_fails_before_any_model_call():
    supervisor = PiRuntimeSupervisor()
    service = faux_service([tool_call("emit_structured_output", {"accepted": True})], supervisor)
    try:
        with pytest.raises(PiRuntimeTurnError, match="structured_output_schema_unsupported"):
            await service.run_structured(
                purpose="w1.structured.unsupported", project_id="p1", agent_id="a1", system="sys",
                messages=[{"role": "user", "content": "go"}],
                schema={"type": "object", "properties": {"a": {"$ref": "#/definitions/x"}}},
                params=TurnParams(),
            )
    finally:
        await supervisor.shutdown()
    assert supervisor.is_running is False, "an unsupported schema must never reach the worker"


# ── ledger persistence ───────────────────────────────────────────────────


async def test_exception_path_persists_exactly_one_error_row(usage_db):
    """A raising engine executor still produces its one durable row: zeroed
    accounting, outcome=error, exception type preserved."""
    purpose = f"w1.ledger.exc.{uuid.uuid4().hex[:8]}"
    dispatcher = AgenticDispatcher(
        pi_service=_StubPiService(), legacy_executor=_RaisingLegacyExecutor(RuntimeError("kaput"))
    )
    with pytest.raises(RuntimeError, match="kaput"):
        await dispatcher.completion(
            purpose=purpose, project_id="p1", system="s",
            messages=[{"role": "user", "content": "hi"}], params=TurnParams(), engine="legacy",
        )
    rows = await _ledger_rows(purpose=purpose)
    assert len(rows) == 1
    assert rows[0].outcome == "error"
    assert rows[0].error_type == "RuntimeError"
    assert rows[0].input_tokens == 0 and rows[0].output_tokens == 0


async def test_legacy_absent_provider_usage_is_estimated_and_flagged(usage_db):
    """Only absent legacy provider usage is estimated with the existing token
    counter and flagged estimate=1 — exact and estimated numbers never mix."""
    legacy = _RecordingLegacyExecutor(outcome={"text": "legacy-done", "status": "success"})
    purpose = f"w1.ledger.estimate.{uuid.uuid4().hex[:8]}"
    await AgenticDispatcher(legacy_executor=legacy).completion(
        purpose=purpose, project_id="p1", system="system",
        messages=[{"role": "user", "content": "hello world"}], params=TurnParams(), engine="legacy",
    )
    rows = await _ledger_rows(purpose=purpose)
    assert len(rows) == 1
    row = rows[0]
    assert row.estimate == 1
    assert row.input_tokens > 0  # estimated with the existing count_tokens estimator
    assert row.outcome == "success"


# ── protocol mismatch ────────────────────────────────────────────────────


def test_protocol_version_matches_on_both_sides():
    python_source = (REPO_ROOT / "backend/app/core/pi_runtime/protocol.py").read_text(encoding="utf-8")
    worker_source = (REPO_ROOT / "pi-runtime/src/protocol.mjs").read_text(encoding="utf-8")
    py_version = int(re.search(r"PROTOCOL_VERSION\s*=\s*(\d+)", python_source).group(1))
    js_version = int(re.search(r"PROTOCOL_VERSION\s*=\s*(\d+)", worker_source).group(1))
    assert py_version == js_version, (
        f"protocol skew: Python speaks v{py_version}, the worker speaks v{js_version}"
    )
    assert py_version >= 2, "the forced structured-output contract requires protocol v2"


@requires_node
async def test_worker_with_mismatched_ready_version_is_rejected(tmp_path):
    """Both-side validation: a worker answering `ready` with a different
    protocol version is never used and is reclaimed."""
    from app.core.pi_runtime.protocol import PROTOCOL_VERSION

    wrong = PROTOCOL_VERSION + 1
    fake = tmp_path / "fake_worker.mjs"
    fake.write_text(
        "let buf='';process.stdin.on('data',(c)=>{buf+=c;if(buf.includes('\\n')){"
        f"process.stdout.write(JSON.stringify({{v:{wrong},type:'ready',protocol_version:{wrong},seq:1}})+'\\n');"
        "process.stdin.pause();}});\n",
        encoding="utf-8",
    )
    supervisor = PiRuntimeSupervisor(worker_entry=fake, handshake_timeout=5.0)
    with pytest.raises(PiWorkerError, match="protocol_version_mismatch"):
        await supervisor.ensure_started()
    assert supervisor.is_running is False


@requires_node
async def test_worker_handshake_fatal_is_rejected_typed(tmp_path):
    """A worker that rejects OUR hello with a fatal (its own version check)
    fails the handshake typed, never silently ready."""
    from app.core.pi_runtime.protocol import PROTOCOL_VERSION

    fake = tmp_path / "fake_worker.mjs"
    fake.write_text(
        "let buf='';process.stdin.on('data',(c)=>{buf+=c;if(buf.includes('\\n')){"
        f"process.stdout.write(JSON.stringify({{v:{PROTOCOL_VERSION},type:'fatal',error:'protocol_version_mismatch',seq:1}})+'\\n');"
        "process.stdin.pause();}});\n",
        encoding="utf-8",
    )
    supervisor = PiRuntimeSupervisor(worker_entry=fake, handshake_timeout=5.0)
    with pytest.raises(PiWorkerError, match="protocol_version_mismatch"):
        await supervisor.ensure_started()
    assert supervisor.is_running is False


# ── armed ratchet stays consistent and only ratchets downward ─────────────


def test_ratchet_is_consistent_and_only_ratchets_down():
    """W1 armed the ratchet at 87 and migrated zero sites. Each later wave may
    only lower it (never raise it) and must keep the count-to-zero contract
    internally consistent. W2 (complete) migrated all 9 interactive surfaces
    (4 one-shot completions, 4 streaming ReAct loops, browser tool); W3
    migrated the 8 research-spine + steering sites (agent_research L1/L2/L3/L5,
    self_check L6, agent_execution L7, agent_lifecycle L10); W8 migrated all
    17 embed sites (embeddings.py/validation.py wrappers now route through
    agentic.embed), so the current floor is 53."""
    from tests.pi_migration.test_count_to_zero import EXPECTED_PRODUCT_SITES, check_count_to_zero

    assert EXPECTED_PRODUCT_SITES <= 87, "the ratchet must never migrate sites back onto the legacy plane"
    assert EXPECTED_PRODUCT_SITES == 53, "W8 migrated the 17 embed sites: ratchet floor is 53"
    check_count_to_zero()  # raises RuntimeError naming every violation


# ── same-model donor isolation (static plane guard) ─────────────────────


def test_pi_model_plane_has_no_compute_registry_dependency():
    """The dispatcher, ledger, and Pi catalog must never import or reference the
    donor plane (docstrings excluded — code only)."""
    guarded = [
        "backend/app/core/agentic/dispatcher.py",
        "backend/app/core/agentic/types.py",
        "backend/app/core/agentic/usage_ledger.py",
        "backend/app/core/pi_runtime/model_manager.py",
        "backend/app/core/pi_runtime/endpoints.py",
    ]
    banned = re.compile(r"compute_registry|compute_node|ComputeRegistry|ComputeNode")
    for rel in guarded:
        source = (REPO_ROOT / rel).read_text(encoding="utf-8")
        tree = ast.parse(source)
        # Skip string literals (docstrings may NAME the invariant they guard).
        string_lines: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for line in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                    string_lines.add(line)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = getattr(node, "module", "") or ",".join(alias.name for alias in node.names)
                assert not banned.search(module), f"{rel} imports the donor plane: {module}"
        for lineno, line in enumerate(source.splitlines(), start=1):
            if lineno in string_lines or line.strip().startswith("#"):
                continue
            assert not re.search(r"\bcompute_registry\b|\bComputeRegistry\b", line), (
                f"{rel}:{lineno} references the donor plane"
            )


# ── Pi model catalog sources + capabilities ──────────────────────────────


def _resolved(endpoint_id: str, *, model: str = "m", context_window: int = 0,
              supports_vision: bool = False, kind: str = "remote") -> "ResolvedPiEndpoint":
    from app.core.pi_runtime.endpoints import ResolvedPiEndpoint

    return ResolvedPiEndpoint(
        endpoint_id=endpoint_id, provider_kind="openai_compat", base_url="http://127.0.0.1:9/v1",
        model=model, api_key="k", timeout_ms=30000, max_retries=0,
        context_window=context_window, supports_vision=supports_vision, kind=kind,
    )


def test_catalog_covers_static_settings_endpoints_with_capabilities():
    """Source 1: settings endpoints + the built-in default, with the capability
    subset (context window, vision) carried into the identity view."""
    from app.config import PiApiEndpoint
    from app.core.pi_runtime.endpoints import DEFAULT_ENDPOINT_ID, PiEndpointResolver

    resolver = PiEndpointResolver([
        PiApiEndpoint(
            endpoint_id="pi-cfg-1", provider_kind="openai_compat",
            base_url="http://127.0.0.1:9/v1", model="cfg-model", keychain_service="svc",
            context_window=65536, supports_vision=True,
        )
    ])
    manager = PiModelManager(resolver=resolver, include_local=False)
    info = {item.endpoint_id: item for item in manager.catalog()}
    assert "pi-cfg-1" in info
    assert DEFAULT_ENDPOINT_ID in info
    assert info["pi-cfg-1"].context_window == 65536
    assert info["pi-cfg-1"].supports_vision is True


def test_catalog_covers_local_serving_as_kind_local():
    """Source 3: Ollama / LM Studio OpenAI-compatible /v1 serving, kind=local,
    resolvable without any registry or donor involvement."""
    from app.core.pi_runtime.endpoints import PiEndpointResolver

    manager = PiModelManager(resolver=PiEndpointResolver([]))
    info = {item.endpoint_id: item for item in manager.catalog()}
    assert info["pi-local-ollama"].kind == "local"
    assert info["pi-local-lmstudio"].kind == "local"
    resolved = manager.resolve(endpoint_id="pi-local-ollama")
    assert resolved.endpoint_id == "pi-local-ollama"
    assert resolved.base_url.endswith("/v1")


def test_capability_filters_and_exact_identity_are_fail_closed():
    """Selection is exact-identity or capability-filtered, never donor-style
    scoring; capability admission fails closed."""
    manager = PiModelManager(endpoints=[
        _resolved("pi-small", model="small", context_window=8192),
        _resolved("pi-vision", model="vision-m", context_window=131072, supports_vision=True),
    ])
    # Vision admission skips non-vision entries.
    assert manager.resolve(require_vision=True).endpoint_id == "pi-vision"
    # Context admission skips small-context entries.
    assert manager.resolve(min_context=32768).endpoint_id == "pi-vision"
    # Exact model identity.
    assert manager.resolve(model="small").endpoint_id == "pi-small"
    # Exact endpoint pin with a model mismatch fails typed.
    with pytest.raises(PiEndpointResolutionError, match="model_mismatch"):
        manager.resolve(endpoint_id="pi-small", model="other")
    # Unsatisfiable capability requirements fail closed.
    with pytest.raises(PiEndpointResolutionError):
        manager.resolve(min_context=1_000_000)
    with pytest.raises(PiEndpointResolutionError, match="capability_missing:vision"):
        manager.resolve(endpoint_id="pi-small", require_vision=True)
    # Distinct selection never silently reuses one identity as two.
    distinct = manager.resolve_distinct(2)
    assert {item.endpoint_id for item in distinct} == {"pi-small", "pi-vision"}
    with pytest.raises(PiEndpointResolutionError, match="insufficient_distinct"):
        manager.resolve_distinct(2, exclude=("pi-vision",))
    with pytest.raises(PiEndpointResolutionError, match="insufficient_distinct"):
        PiModelManager(endpoints=[]).resolve_distinct(2)


async def test_llm_server_rows_project_read_only_and_relays_never_do(usage_db):
    """Source 2: persisted LLMServer rows project one-directionally into the
    catalog; relay/browser donor rows are NEVER projected."""
    from app.core.pi_runtime.endpoints import PiEndpointResolver
    from app.models.llm_server import LLMServer

    server_id = f"srv-{uuid.uuid4().hex[:8]}"
    relay_id = f"relay-{uuid.uuid4().hex[:8]}"
    async with async_session() as session:
        session.add(LLMServer(
            id=server_id, name="Contract Server", provider_type="openai_compat",
            host="http://127.0.0.1:9/v1", is_local=False,
            capabilities=json.dumps({"models": ["contract-model"], "context_window": 65536, "vision": True}),
        ))
        session.add(LLMServer(
            id=relay_id, name="Relay Donor", provider_type="openai_compat",
            host="http://donor.invalid:1234/v1", is_local=False, is_relay=True,
            capabilities=json.dumps({"models": ["contract-model"]}),
        ))
        await session.commit()
    try:
        manager = PiModelManager(resolver=PiEndpointResolver([]), include_local=False)
        await manager.ensure_db_projection()
        info = {item.endpoint_id: item for item in manager.catalog()}
        projected = manager.resolve(endpoint_id=f"pi-llm-{server_id}")
        assert projected.model == "contract-model"
        assert projected.supports_vision is True
        assert projected.context_window == 65536
        assert f"pi-llm-{relay_id}" not in info, "donor capacity must never enter the Pi catalog"
        with pytest.raises(PiEndpointResolutionError):
            manager.resolve(endpoint_id=f"pi-llm-{relay_id}")
    finally:
        async with async_session() as session:
            for row_id in (server_id, relay_id):
                row = await session.get(LLMServer, row_id)
                if row is not None:
                    await session.delete(row)
            await session.commit()
