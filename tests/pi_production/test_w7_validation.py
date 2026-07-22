"""W7 contract coverage — validation/consensus/dual-coder migration (master plan §8 W7).

The seven chat call sites in ``app/core/validation.py`` (``dual_run``,
``full_ensemble``, ``self_moa`` ensembles; ``adversarial_review`` and
``debate_rounds`` completions), ``app/core/validation_executor.py``
(LLM-as-judge), and ``app/services/research_validity_service.py``
(dual-coder) route through the AgenticDispatcher — ``ensemble`` →
``validation.dual_run`` / ``validation.full_ensemble`` / ``validation.self_moa``,
``completion`` → ``validation.adversarial`` / ``validation.debate``,
``structured`` → ``validation.judge`` / ``validity.coder`` — gated on the
``agentic_core`` feature flag, with the legacy ``llm_router`` / ``server`` /
``compute_registry`` / ``coder.node`` branches preserved alongside for
``agentic_core=False``. ``validation.py:_get_embeddings`` stays legacy until
W8 and is not covered here.

Covered here (all stubbed/static — no live model activity):

* static: each migrated function carries both the dispatcher path (flag on)
  and the preserved legacy branch, with the planned purpose slugs; the judge
  schema and the coding schema stay inside the Pi forced-tool subset;
* behavior (flag off): the legacy stubs drive every site and the dispatcher
  stub is never touched — including the validation_executor judge, whose
  ``message.content`` bug fix is proven by the legacy branch now scoring;
* behavior (flag on): the dispatcher stub records each call (verb, purpose,
  params, endpoint pinning), the legacy stubs are never called, and the
  fail-closed ``distinct=True`` rule degrades down the existing chain
  (dual_run → self_moa; full_ensemble → dual_run; dual-coder → blocked
  coding run) instead of fabricating diversity from fewer endpoints.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATION = REPO_ROOT / "backend/app/core/validation.py"
VALIDATION_EXECUTOR = REPO_ROOT / "backend/app/core/validation_executor.py"
VALIDITY_SERVICE = REPO_ROOT / "backend/app/services/research_validity_service.py"

SPINE_PHASES = {
    "intent", "context", "plan", "tool_selection", "execution",
    "recovery", "grounding", "synthesis", "review", "governance",
}

ALLOWED_SCHEMA_KEYS = {
    "type", "properties", "required", "items", "enum", "const",
    "additionalProperties", "description",
}


# ── helpers ─────────────────────────────────────────────────────────────


def _function_source(path: Path, function_name: str) -> str:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return ast.get_source_segment(text, node) or ""
    raise AssertionError(f"{function_name} not found in {path}")


def _check_schema_subset(node, path: str = "$") -> None:
    """Recursively assert a schema stays inside the Pi forced-tool subset."""
    if not isinstance(node, dict):
        return
    extra = set(node) - ALLOWED_SCHEMA_KEYS
    assert not extra, f"{path}: disallowed schema keys {extra}"
    if "additionalProperties" in node:
        assert isinstance(node["additionalProperties"], bool), f"{path}.additionalProperties must be bool"
    for key, value in node.get("properties", {}).items():
        _check_schema_subset(value, f"{path}.properties.{key}")
    if "items" in node:
        _check_schema_subset(node["items"], f"{path}.items")


class _StubAgentic:
    """Recording stand-in for the ``agentic`` dispatcher singleton."""

    def __init__(self, *, texts: list[str] | None = None, value: dict | None = None,
                 raise_on: dict | None = None, fail_samples: bool = False) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._texts = list(texts) if texts is not None else None
        self._value = value if value is not None else {}
        self._raise_on = raise_on or {}
        self._fail_samples = fail_samples

    def _next_text(self) -> str:
        return self._texts.pop(0) if self._texts else "dispatcher text"

    async def completion(self, **kwargs):
        self.calls.append(("completion", kwargs))
        if "completion" in self._raise_on:
            raise self._raise_on["completion"]
        if len(self.calls) in self._raise_on.get("completion_calls", set()):
            raise RuntimeError("scripted completion failure")
        return SimpleNamespace(
            text=self._next_text(), status="success", usage={},
            stop_reason="stop", endpoint_id=f"ep-{len(self.calls)}", tool_calls=[],
        )

    async def ensemble(self, **kwargs):
        self.calls.append(("ensemble", kwargs))
        if "ensemble" in self._raise_on:
            raise self._raise_on["ensemble"]
        n = kwargs.get("n") or 1
        samples = [
            SimpleNamespace(
                text="" if self._fail_samples else self._next_text(),
                status="error" if self._fail_samples else "success",
                usage={}, stop_reason="stop",
                endpoint_id=f"ep-{index}", tool_calls=[],
            )
            for index in range(n)
        ]
        return SimpleNamespace(
            samples=samples,
            endpoint_ids=[f"ep-{index}" for index in range(n)],
            usage={}, status="error" if self._fail_samples else "success",
        )

    async def structured(self, **kwargs):
        self.calls.append(("structured", kwargs))
        if "structured" in self._raise_on:
            raise self._raise_on["structured"]
        return SimpleNamespace(
            text="", value=self._value, status="success", usage={},
            stop_reason="stop", endpoint_id="ep-structured", tool_calls=[],
        )


class _StubLlmRouter:
    """Legacy stand-in for ``llm_router`` returning queued response texts."""

    def __init__(self, texts: list[str] | None = None, servers: list | None = None) -> None:
        self.calls: list[dict] = []
        self._texts = list(texts) if texts is not None else ["legacy text"]
        self._servers = servers or []

    def _sorted_servers(self, **kwargs):
        return self._servers

    async def chat(self, messages=None, **kwargs):
        self.calls.append({"messages": messages, **kwargs})
        content = self._texts.pop(0) if self._texts else "legacy text"
        return {"message": {"content": content}}


class _StubServer:
    """Legacy stand-in for one healthy routed server."""

    def __init__(self, name: str, text: str) -> None:
        self.name = name
        self.is_healthy = True
        self.loaded_models = [f"model-{name}"]
        self._text = text
        self.calls: list[dict] = []

    async def chat(self, messages=None, **kwargs):
        self.calls.append({"messages": messages, **kwargs})
        return {"message": {"content": self._text}}


@pytest.fixture
def _agentic_core_on(monkeypatch):
    monkeypatch.setattr("app.config.settings.agentic_core", True)


@pytest.fixture
def _agentic_core_off(monkeypatch):
    monkeypatch.setattr("app.config.settings.agentic_core", False)


@pytest.fixture
def _no_embeddings(monkeypatch):
    async def _embed(texts, project_id=None):
        return []

    monkeypatch.setattr("app.core.validation._get_embeddings", _embed)


# ── static: both paths present with planned purpose slugs ────────────────


def test_w7_validation_functions_carry_dispatcher_path_and_preserved_legacy_branch():
    expected = {
        "dual_run": ("_dispatch_ensemble", 'purpose="validation.dual_run"', "server.chat"),
        "full_ensemble": ("_dispatch_ensemble", 'purpose="validation.full_ensemble"', "server.chat"),
        "self_moa": ("_dispatch_ensemble", 'purpose="validation.self_moa"', "llm_router.chat"),
        "adversarial_review": ("agentic.completion", 'purpose="validation.adversarial"', "llm_router.chat"),
        "debate_rounds": ("agentic.completion", 'purpose="validation.debate"', "llm_router.chat"),
    }
    for function_name, (verb, purpose, legacy_call) in expected.items():
        source = _function_source(VALIDATION, function_name)
        assert "agentic_core" in source, f"{function_name}: missing flag gate"
        assert verb in source, f"{function_name}: missing {verb}"
        assert purpose in source, f"{function_name}: missing {purpose}"
        assert legacy_call in source, f"{function_name}: legacy branch must be preserved alongside"
    helper = _function_source(VALIDATION, "_dispatch_ensemble")
    assert "agentic.ensemble" in helper, "the ensemble sites must dispatch via agentic.ensemble"


def test_w7_executor_judge_carries_structured_path_legacy_branch_and_bug_fix():
    source = _function_source(VALIDATION_EXECUTOR, "_adversarial_review")
    assert "agentic_core" in source and "agentic.structured" in source
    assert 'purpose="validation.judge"' in source
    assert "compute_registry.chat" in source, "legacy branch must be preserved alongside"
    assert 'result.get("message", {}).get("content", "")' in source, (
        "the message.content bug fix must be present (registry never returns top-level content)"
    )


def test_w7_validity_dual_coder_carries_pi_paths_and_preserved_legacy_branch():
    runner = _function_source(VALIDITY_SERVICE, "_pi_coder_runner")
    assert "agentic.structured" in runner and 'purpose="validity.coder"' in runner
    assert "endpoint_id" in runner, "the coder's exact Pi endpoint identity must be pinned"
    selection = _function_source(VALIDITY_SERVICE, "_select_pi_coders")
    assert "resolve_distinct" in selection
    legacy = _function_source(VALIDITY_SERVICE, "_default_coder_runner")
    assert "coder.node.chat" in legacy, "legacy runner must be preserved alongside"
    orchestration = _function_source(VALIDITY_SERVICE, "run_independent_coding_run")
    assert "_use_pi_coding_plane" in orchestration and "_select_pi_coders" in orchestration
    assert "_select_project_coders" in orchestration, "legacy selection must be preserved alongside"


def test_w7_schemas_stay_inside_pi_forced_tool_subset():
    from app.core import validation_executor
    from app.services import research_validity_service

    for schema in (validation_executor._JUDGE_SCHEMA, research_validity_service.CODING_RESPONSE_SCHEMA):
        assert schema.get("type") == "object"
        _check_schema_subset(schema)


# ── behavior: dual_run ───────────────────────────────────────────────────


async def test_dual_run_flag_on_dispatches_distinct_ensemble(
    monkeypatch, _agentic_core_on, _no_embeddings
):
    dispatcher_stub = _StubAgentic(texts=["resp-a", "resp-b"])
    router_stub = _StubLlmRouter()
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    monkeypatch.setattr("app.core.llm_router.llm_router", router_stub)

    from app.core.validation import dual_run

    result = await dual_run("prompt", system="sys", project_id="p1")

    assert router_stub.calls == [], "flag on must not call the legacy plane directly"
    method, kwargs = dispatcher_stub.calls[0]
    assert method == "ensemble"
    assert kwargs["purpose"] == "validation.dual_run"
    assert kwargs["n"] == 2 and kwargs["distinct"] is True
    assert kwargs["project_id"] == "p1"
    assert kwargs["spine_phase"] in SPINE_PHASES
    assert result.method == "dual_run"
    assert result.responses == ["resp-a", "resp-b"]
    assert result.metadata["endpoint_ids"] == ["ep-0", "ep-1"]


async def test_dual_run_flag_on_insufficient_distinct_endpoints_falls_back_to_self_moa(
    monkeypatch, _agentic_core_on, _no_embeddings
):
    from app.core.pi_runtime.endpoints import PiEndpointResolutionError

    dispatcher_stub = _StubAgentic(texts=["solo-a", "solo-b"])
    calls = {"n": 0}
    real_ensemble = dispatcher_stub.ensemble

    async def _ensemble(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            dispatcher_stub.calls.append(("ensemble", kwargs))
            raise PiEndpointResolutionError("insufficient_distinct_pi_endpoints")
        return await real_ensemble(**kwargs)

    dispatcher_stub.ensemble = _ensemble
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    monkeypatch.setattr("app.core.llm_router.llm_router", _StubLlmRouter())

    from app.core.validation import dual_run

    result = await dual_run("prompt", project_id="p1")

    first, second = [kwargs for method, kwargs in dispatcher_stub.calls if method == "ensemble"]
    assert first["distinct"] is True and first["n"] == 2
    assert second["purpose"] == "validation.self_moa"
    assert second["distinct"] is False and second["n"] == 2, (
        "fail-closed: degrade to the labeled single-model variation, never fabricate diversity"
    )
    assert result.method == "self_moa"
    assert result.metadata["assurance"] == "single_model_temperature_variation"


async def test_dual_run_flag_off_uses_legacy_servers(
    monkeypatch, _agentic_core_off, _no_embeddings
):
    servers = [_StubServer("a", "legacy-a"), _StubServer("b", "legacy-b")]
    router_stub = _StubLlmRouter(servers=servers)
    dispatcher_stub = _StubAgentic()
    monkeypatch.setattr("app.core.llm_router.llm_router", router_stub)
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    from app.core.validation import dual_run

    result = await dual_run("prompt", project_id="p1")

    assert dispatcher_stub.calls == [], "flag off must not touch the dispatcher"
    assert len(servers[0].calls) == 1 and len(servers[1].calls) == 1
    assert result.responses == ["legacy-a", "legacy-b"]
    assert result.metadata["servers_used"] == ["a", "b"]


# ── behavior: full_ensemble / self_moa ───────────────────────────────────


async def test_full_ensemble_flag_on_dispatches_min_responses_plus_one_distinct(
    monkeypatch, _agentic_core_on, _no_embeddings
):
    dispatcher_stub = _StubAgentic(texts=["r1", "r2", "r3", "r4"])
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    monkeypatch.setattr("app.core.llm_router.llm_router", _StubLlmRouter())

    from app.core.validation import full_ensemble

    result = await full_ensemble("prompt", min_responses=3, project_id="p1")

    method, kwargs = dispatcher_stub.calls[0]
    assert method == "ensemble"
    assert kwargs["purpose"] == "validation.full_ensemble"
    assert kwargs["n"] == 4 and kwargs["distinct"] is True
    assert result.method == "full_ensemble"
    assert result.metadata["n_responses"] == 4


async def test_full_ensemble_flag_on_insufficient_distinct_falls_back_to_dual_run(
    monkeypatch, _agentic_core_on, _no_embeddings
):
    from app.core.pi_runtime.endpoints import PiEndpointResolutionError

    dispatcher_stub = _StubAgentic(texts=["d1", "d2"])
    calls = {"n": 0}
    real_ensemble = dispatcher_stub.ensemble

    async def _ensemble(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            dispatcher_stub.calls.append(("ensemble", kwargs))
            raise PiEndpointResolutionError("insufficient_distinct_pi_endpoints")
        return await real_ensemble(**kwargs)

    dispatcher_stub.ensemble = _ensemble
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    monkeypatch.setattr("app.core.llm_router.llm_router", _StubLlmRouter())

    from app.core.validation import full_ensemble

    result = await full_ensemble("prompt", min_responses=3, project_id="p1")

    purposes = [kwargs["purpose"] for method, kwargs in dispatcher_stub.calls if method == "ensemble"]
    assert purposes == ["validation.full_ensemble", "validation.dual_run"]
    assert result.method == "dual_run", "fail-closed degradation down the existing chain"


async def test_self_moa_flag_on_dispatches_temperature_sweep_single_endpoint(
    monkeypatch, _agentic_core_on, _no_embeddings
):
    dispatcher_stub = _StubAgentic(texts=["t1", "t2", "t3"])
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    monkeypatch.setattr("app.core.llm_router.llm_router", _StubLlmRouter())

    from app.core.validation import self_moa

    result = await self_moa("prompt", n=3, project_id="p1")

    method, kwargs = dispatcher_stub.calls[0]
    assert method == "ensemble"
    assert kwargs["purpose"] == "validation.self_moa"
    assert kwargs["distinct"] is False
    assert kwargs["n"] == 3
    assert kwargs["temperatures"] == [0.3, 0.7, 1.0]
    assert result.metadata["assurance"] == "single_model_temperature_variation"
    assert result.metadata["temperatures"] == [0.3, 0.7, 1.0]


async def test_self_moa_flag_off_uses_legacy_temperature_sweep(
    monkeypatch, _agentic_core_off, _no_embeddings
):
    router_stub = _StubLlmRouter(texts=["l1", "l2", "l3"])
    dispatcher_stub = _StubAgentic()
    monkeypatch.setattr("app.core.llm_router.llm_router", router_stub)
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    from app.core.validation import self_moa

    result = await self_moa("prompt", n=3, project_id="p1")

    assert dispatcher_stub.calls == []
    assert [call["temperature"] for call in router_stub.calls] == [0.3, 0.7, 1.0]
    assert result.responses == ["l1", "l2", "l3"]


# ── behavior: adversarial_review / debate_rounds ────────────────────────


async def test_adversarial_review_flag_on_dispatches_completion(
    monkeypatch, _agentic_core_on, _no_embeddings
):
    dispatcher_stub = _StubAgentic(texts=["the critique"])
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    monkeypatch.setattr("app.core.llm_router.llm_router", _StubLlmRouter())

    from app.core.validation import adversarial_review

    result = await adversarial_review("q", "initial", system="sys", project_id="p1")

    method, kwargs = dispatcher_stub.calls[0]
    assert method == "completion"
    assert kwargs["purpose"] == "validation.adversarial"
    assert kwargs["params"].temperature == 0.3
    assert kwargs["system"] == "sys"
    assert kwargs["spine_phase"] in SPINE_PHASES
    assert result.metadata["review_text"] == "the critique"
    assert result.responses == ["initial", "the critique"]
    assert result.best_response == "initial"


async def test_adversarial_review_flag_on_dispatch_failure_returns_empty_result(
    monkeypatch, _agentic_core_on, _no_embeddings
):
    dispatcher_stub = _StubAgentic(raise_on={"completion": RuntimeError("worker down")})
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    monkeypatch.setattr("app.core.llm_router.llm_router", _StubLlmRouter())

    from app.core.validation import adversarial_review

    result = await adversarial_review("q", "initial", project_id="p1")

    assert result.responses == []
    assert result.consensus.confidence == "insufficient", (
        "dispatch failure must degrade to the existing validation-unavailable result"
    )


async def test_adversarial_review_flag_off_uses_legacy_router(
    monkeypatch, _agentic_core_off, _no_embeddings
):
    router_stub = _StubLlmRouter(texts=["legacy critique"])
    dispatcher_stub = _StubAgentic()
    monkeypatch.setattr("app.core.llm_router.llm_router", router_stub)
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    from app.core.validation import adversarial_review

    result = await adversarial_review("q", "initial", project_id="p1")

    assert dispatcher_stub.calls == []
    assert router_stub.calls[0]["temperature"] == 0.3
    assert result.metadata["review_text"] == "legacy critique"


async def test_debate_rounds_flag_on_dispatches_initial_plus_rounds(
    monkeypatch, _agentic_core_on, _no_embeddings
):
    dispatcher_stub = _StubAgentic(texts=["r0", "r1", "r2"])
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    monkeypatch.setattr("app.core.llm_router.llm_router", _StubLlmRouter())

    from app.core.validation import debate_rounds

    result = await debate_rounds("prompt", rounds=2, project_id="p1")

    completions = [kwargs for method, kwargs in dispatcher_stub.calls if method == "completion"]
    assert len(completions) == 3, "initial + 2 rounds"
    assert all(kwargs["purpose"] == "validation.debate" for kwargs in completions)
    assert completions[0]["params"].temperature == 0.7
    assert all(kwargs["params"].temperature == 0.5 for kwargs in completions[1:])
    assert result.best_response == "r2"
    assert result.metadata["rounds_completed"] == 2


async def test_debate_rounds_flag_on_round_failure_breaks_like_legacy(
    monkeypatch, _agentic_core_on, _no_embeddings
):
    dispatcher_stub = _StubAgentic(texts=["r0"])
    real_completion = dispatcher_stub.completion
    calls = {"n": 0}

    async def _completion(**kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            dispatcher_stub.calls.append(("completion", kwargs))
            raise RuntimeError("round failed")
        return await real_completion(**kwargs)

    dispatcher_stub.completion = _completion
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    monkeypatch.setattr("app.core.llm_router.llm_router", _StubLlmRouter())

    from app.core.validation import debate_rounds

    result = await debate_rounds("prompt", rounds=2, project_id="p1")

    assert result.responses == ["r0"]
    assert result.metadata["rounds_completed"] == 0
    assert result.best_response == "r0"


async def test_debate_rounds_flag_off_uses_legacy_router(
    monkeypatch, _agentic_core_off, _no_embeddings
):
    router_stub = _StubLlmRouter(texts=["l0", "l1", "l2"])
    dispatcher_stub = _StubAgentic()
    monkeypatch.setattr("app.core.llm_router.llm_router", router_stub)
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    from app.core.validation import debate_rounds

    result = await debate_rounds("prompt", rounds=2, project_id="p1")

    assert dispatcher_stub.calls == []
    assert len(router_stub.calls) == 3
    assert router_stub.calls[0]["temperature"] == 0.7
    assert [call["temperature"] for call in router_stub.calls[1:]] == [0.5, 0.5]
    assert result.best_response == "l2"


# ── behavior: validation_executor judge ──────────────────────────────────


def _executor_io():
    output = SimpleNamespace(
        nuggets=[{"text": "users struggled with invites", "tags": ["ux"]}],
        facts=[{"text": "invites are confusing"}],
        insights=[],
    )
    input_data = SimpleNamespace(project_id="p1")
    return output, input_data


async def test_judge_flag_on_dispatches_structured(monkeypatch, _agentic_core_on):
    scores = {"code_quality": 4, "evidence": 4, "chain": 4,
              "hallucination_free": 5, "depth": 4, "overall": 4}
    dispatcher_stub = _StubAgentic(value=scores)
    registry_stub = _StubLlmRouter()
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    monkeypatch.setattr("app.core.compute_registry.compute_registry", registry_stub)

    from app.core.validation_executor import ValidationExecutor

    output, input_data = _executor_io()
    result = await ValidationExecutor()._adversarial_review(output, input_data)

    assert registry_stub.calls == [], "flag on must not call the legacy plane directly"
    method, kwargs = dispatcher_stub.calls[0]
    assert method == "structured"
    assert kwargs["purpose"] == "validation.judge"
    assert kwargs["params"].temperature == 0.3
    assert kwargs["schema"]["type"] == "object"
    assert kwargs["spine_phase"] in SPINE_PHASES
    assert result.passed and result.confidence == 4 / 5
    assert result.details == scores


async def test_judge_flag_on_raise_fails_closed_as_unavailable(monkeypatch, _agentic_core_on):
    from app.core.pi_runtime.endpoints import PiRuntimeTurnError

    dispatcher_stub = _StubAgentic(
        raise_on={"structured": PiRuntimeTurnError("error", "structured_output_missing")}
    )
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    monkeypatch.setattr("app.core.compute_registry.compute_registry", _StubLlmRouter())

    from app.core.validation_executor import ValidationExecutor

    output, input_data = _executor_io()
    result = await ValidationExecutor()._adversarial_review(output, input_data)

    assert not result.passed and result.confidence == 0.0
    assert result.details == {
        "status": "unavailable",
        "reason": "judge_dispatch_failed",
        "error": "pi_runtime_turn_error:structured_output_missing",
    }


async def test_judge_flag_on_missing_verdict_fails_closed(monkeypatch, _agentic_core_on):
    dispatcher_stub = _StubAgentic(value={})
    registry_stub = _StubLlmRouter()
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    monkeypatch.setattr("app.core.compute_registry.compute_registry", registry_stub)

    from app.core.validation_executor import ValidationExecutor

    output, input_data = _executor_io()
    result = await ValidationExecutor()._adversarial_review(output, input_data)

    assert registry_stub.calls == []
    assert not result.passed and result.confidence == 0.0
    assert result.details == {
        "status": "unavailable",
        "reason": "judge_verdict_missing",
    }


async def test_judge_flag_off_reads_message_content_bug_fix(monkeypatch, _agentic_core_off):
    scores = {"code_quality": 5, "evidence": 5, "chain": 5,
              "hallucination_free": 5, "depth": 5, "overall": 5}
    registry_stub = _StubLlmRouter(texts=[json.dumps(scores)])
    dispatcher_stub = _StubAgentic()
    monkeypatch.setattr("app.core.compute_registry.compute_registry", registry_stub)
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    from app.core.validation_executor import ValidationExecutor

    output, input_data = _executor_io()
    result = await ValidationExecutor()._adversarial_review(output, input_data)

    assert dispatcher_stub.calls == [], "flag off must not touch the dispatcher"
    assert result.details == scores and result.confidence == 1.0, (
        "bug fix: the registry's message.content must actually be scored — "
        "the old top-level content read always missed and silently degraded"
    )


async def test_judge_flag_off_low_score_fails(monkeypatch, _agentic_core_off):
    scores = {"overall": 1}
    registry_stub = _StubLlmRouter(texts=[json.dumps(scores)])
    monkeypatch.setattr("app.core.compute_registry.compute_registry", registry_stub)
    monkeypatch.setattr("app.core.agentic.agentic", _StubAgentic())

    from app.core.validation_executor import ValidationExecutor

    output, input_data = _executor_io()
    result = await ValidationExecutor()._adversarial_review(output, input_data)

    assert not result.passed and result.confidence == 0.2


# ── behavior: research_validity_service dual-coder ──────────────────────


class _StubPiModelManager:
    """Catalog stand-in: N identity-distinct resolved endpoints."""

    instances: list["_StubPiModelManager"] = []

    def __init__(self, endpoints: list[SimpleNamespace] | None = None,
                 error: Exception | None = None) -> None:
        self._endpoints = endpoints or []
        self._error = error
        self.projected = False
        _StubPiModelManager.instances.append(self)

    async def ensure_db_projection(self):
        self.projected = True

    def resolve_distinct(self, n, **kwargs):
        if self._error is not None:
            raise self._error
        return self._endpoints[:n]


def _fake_endpoint(endpoint_id: str, model: str) -> SimpleNamespace:
    return SimpleNamespace(
        endpoint_id=endpoint_id, model=model, provider_kind="openai_compat",
        base_url="http://endpoint.invalid", api_key="", timeout_ms=1000, max_retries=0,
    )


async def test_select_pi_coders_maps_distinct_endpoint_identities(monkeypatch):
    manager = _StubPiModelManager(endpoints=[
        _fake_endpoint("ep-a", "model-a"),
        _fake_endpoint("ep-b", "model-b"),
        _fake_endpoint("ep-c", "model-c"),
    ])
    monkeypatch.setattr("app.core.pi_runtime.model_manager.PiModelManager", lambda: manager)

    from app.services.research_validity_service import _select_pi_coders

    coders = await _select_pi_coders(max_coders=3)

    assert manager.projected, "the read-only DB projection must run before selection"
    assert [c.coder_id for c in coders] == [
        "model-coder:ep-a", "model-coder:ep-b", "model-coder:ep-c",
    ]
    assert [c.model_name for c in coders] == ["model-a", "model-b", "model-c"]
    assert [c.node.endpoint_id for c in coders] == ["ep-a", "ep-b", "ep-c"]
    assert [c.node.node_id for c in coders] == ["ep-a", "ep-b", "ep-c"], (
        "telemetry/route getattr('node_id') must resolve to the endpoint identity"
    )


async def test_select_pi_coders_fails_closed_on_insufficient_distinct(monkeypatch):
    from app.core.pi_runtime.endpoints import PiEndpointResolutionError

    manager = _StubPiModelManager(
        error=PiEndpointResolutionError("insufficient_distinct_pi_endpoints")
    )
    monkeypatch.setattr("app.core.pi_runtime.model_manager.PiModelManager", lambda: manager)

    from app.services.research_validity_service import _select_pi_coders

    with pytest.raises(PiEndpointResolutionError):
        await _select_pi_coders(max_coders=3)


async def test_pi_coder_runner_dispatches_structured_pinned_to_endpoint(monkeypatch):
    value = {"applications": [{"evidence_unit_id": "eu-1", "codes": ["ux"],
                               "primary_code": "ux", "quote": "q", "confidence": 0.9}]}
    dispatcher_stub = _StubAgentic(value=value)
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    from app.services.research_validity_service import (
        CODING_RESPONSE_SCHEMA, CoderSpec, _pi_coder_runner,
    )

    coder = CoderSpec(
        node=SimpleNamespace(node_id="ep-a", name="ep-a", source="pi",
                             provider_type="openai_compat", endpoint_id="ep-a"),
        coder_id="model-coder:ep-a",
        model_name="model-a",
    )
    response = await _pi_coder_runner(coder, [{"role": "user", "content": "code this"}], "model-a", "p1")

    method, kwargs = dispatcher_stub.calls[0]
    assert method == "structured"
    assert kwargs["purpose"] == "validity.coder"
    assert kwargs["project_id"] == "p1"
    assert kwargs["schema"] is CODING_RESPONSE_SCHEMA
    assert kwargs["params"].temperature == 0.2
    assert kwargs["params"].model == "model-a"
    assert kwargs["params"].endpoint_id == "ep-a", "dispatch must pin the coder's exact endpoint"
    assert kwargs["spine_phase"] in SPINE_PHASES
    assert json.loads(response["message"]["content"]) == value
    route = response["_istara_route"]
    assert route["node_id"] == "ep-a" and route["node_source"] == "pi"
    assert route["model"] == "model-a" and route["outcome"] == "served"


class _RaisingDb:
    async def scalar(self, *args, **kwargs):
        raise RuntimeError("no project row")


async def test_use_pi_coding_plane_requires_flag_and_pi_engine(monkeypatch):
    from app.services.research_validity_service import _use_pi_coding_plane

    monkeypatch.setattr("app.config.settings.agentic_core", False)
    monkeypatch.setattr("app.config.settings.agentic_engine_default", "pi")
    assert await _use_pi_coding_plane(_RaisingDb(), "p1") is False

    monkeypatch.setattr("app.config.settings.agentic_core", True)
    monkeypatch.setattr("app.config.settings.agentic_engine_default", "legacy")
    assert await _use_pi_coding_plane(_RaisingDb(), "p1") is False, (
        "a legacy-resolved engine must keep the legacy coder selection"
    )

    monkeypatch.setattr("app.config.settings.agentic_engine_default", "pi")
    assert await _use_pi_coding_plane(_RaisingDb(), "p1") is True


async def _run_pi_coding_run(monkeypatch, tmp_path, *, selection_error=None, shared_model=None):
    """Shared driver: full coding run on the Pi plane with stubbed selection/dispatch.

    ``shared_model`` makes all three endpoints advertise the *same* model name
    while keeping distinct endpoint identities (W7 endpoint-identity contract).
    """
    import uuid

    from app.models.database import async_session, init_db
    from app.models.research_validity import EvidenceUnit
    from app.services import research_validity_service

    suffix = uuid.uuid4().hex[:8]
    project_id = f"proj-w7-pi-{suffix}"
    task_id = f"task-w7-pi-{suffix}"
    unit_ids = [f"eu-w7-1-{suffix}", f"eu-w7-2-{suffix}"]

    async def _plane(db, pid):
        return True

    monkeypatch.setattr(research_validity_service, "_use_pi_coding_plane", _plane)

    if selection_error is not None:
        async def _select(max_coders):
            raise selection_error

        monkeypatch.setattr(research_validity_service, "_select_pi_coders", _select)
        dispatcher_stub = None
    else:
        coders = [
            research_validity_service.CoderSpec(
                node=SimpleNamespace(
                    node_id=f"ep-{name}", name=f"ep-{name}", source="pi",
                    provider_type="openai_compat", endpoint_id=f"ep-{name}",
                ),
                coder_id=f"model-coder:ep-{name}",
                model_name=shared_model or f"model-{name}",
            )
            for name in ("a", "b", "c")
        ]

        async def _select(max_coders):
            return coders

        monkeypatch.setattr(research_validity_service, "_select_pi_coders", _select)

        async def _structured(**kwargs):
            dispatcher_stub.calls.append(("structured", kwargs))
            applications = [
                {
                    "evidence_unit_id": unit_id,
                    "codes": ["collaboration-disorientation"],
                    "primary_code": "collaboration-disorientation",
                    "quote": f"quote for {unit_id}",
                    "confidence": 0.92,
                    "rationale": "The participant is blocked by team invitation setup.",
                }
                for unit_id in unit_ids
            ]
            return SimpleNamespace(
                text="", value={"applications": applications}, status="success",
                usage={}, stop_reason="stop",
                endpoint_id=kwargs["params"].endpoint_id, tool_calls=[],
            )

        dispatcher_stub = _StubAgentic()
        dispatcher_stub.structured = _structured
        monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    class _SentinelRouter:
        def _sorted_servers(self, **kwargs):
            raise AssertionError("legacy coder selection must not run on the Pi plane")

    monkeypatch.setattr(research_validity_service, "llm_router", _SentinelRouter())

    await init_db()
    async with async_session() as db:
        for index, unit_id in enumerate(unit_ids, 1):
            db.add(
                EvidenceUnit(
                    id=unit_id,
                    project_id=project_id,
                    task_id=task_id,
                    source_id="interview-01",
                    stable_id=f"interview-01#EU-{index:04d}",
                    unit_index=index,
                    source_text=f"Participant struggled with invitation setup {index}.",
                    source_location=f"interview-01:{index}",
                )
            )
        await db.commit()

        result = await research_validity_service.run_independent_coding_run(
            db,
            project_id=project_id,
            task_id=task_id,
            evidence_unit_ids=unit_ids,
            created_by="test-researcher",
        )
    return result, dispatcher_stub


async def test_coding_run_pi_plane_distinct_endpoint_coders_accept(monkeypatch, tmp_path, _agentic_core_on):
    result, dispatcher_stub = await _run_pi_coding_run(monkeypatch, tmp_path)

    assert result["promotion_status"] == "accepted"
    assert result["kappa"] == 1.0
    assert result["rater_count"] == 3
    assert result["distinct_model_count"] == 3, (
        "three distinct Pi endpoint identities satisfy the multi-model gate"
    )
    assert result["code_application_count"] == 6
    purposes = [kwargs["purpose"] for method, kwargs in dispatcher_stub.calls]
    assert purposes == ["validity.coder"] * 3
    pinned = [kwargs["params"].endpoint_id for _, kwargs in dispatcher_stub.calls]
    assert pinned == ["ep-a", "ep-b", "ep-c"], "each coder dispatches on its own endpoint"
    assert {route["model"] for route in result["route_evidence"]} == {
        "model-a", "model-b", "model-c",
    }


async def test_coding_run_pi_plane_same_model_distinct_endpoints_accept(
    monkeypatch, tmp_path, _agentic_core_on
):
    """Three Pi endpoints serving one model remain three reliability raters."""
    result, dispatcher_stub = await _run_pi_coding_run(
        monkeypatch, tmp_path, shared_model="same-model"
    )

    assert result["promotion_status"] == "accepted"
    assert result["rater_count"] == 3
    assert result["distinct_model_count"] == 3
    assert {route["endpoint_id"] for route in result["route_evidence"]} == {
        "ep-a", "ep-b", "ep-c",
    }
    assert {route["model"] for route in result["route_evidence"]} == {"same-model"}
    assert [kwargs["params"].endpoint_id for _, kwargs in dispatcher_stub.calls] == [
        "ep-a", "ep-b", "ep-c",
    ]


async def test_coding_run_pi_plane_insufficient_distinct_blocks_fail_closed(
    monkeypatch, tmp_path, _agentic_core_on
):
    from app.core.pi_runtime.endpoints import PiEndpointResolutionError

    result, dispatcher_stub = await _run_pi_coding_run(
        monkeypatch, tmp_path,
        selection_error=PiEndpointResolutionError("insufficient_distinct_pi_endpoints"),
    )

    assert dispatcher_stub is None, "no coder dispatch may happen after fail-closed selection"
    assert result["status"] == "blocked", (
        "fewer distinct Pi endpoints than coders must hit the existing "
        "validation-unavailable handling, never fabricated diversity"
    )
    assert result["promotion_status"] == "blocked"
    assert result["code_application_count"] == 0
    failure_rows = [r for r in result["route_evidence"] if r.get("outcome") == "failed"]
    assert failure_rows and "insufficient_distinct_pi_endpoints" in failure_rows[0]["error"]
