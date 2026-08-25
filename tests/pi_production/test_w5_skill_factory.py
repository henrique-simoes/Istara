"""W5 contract coverage — skill factory migration (master plan §8 W5).

The five LLM call sites in ``skills/skill_factory.py`` (``plan`` plus the
4-stage execute chain: native structured → native repair → plain repair →
empty-findings repair) route through the AgenticDispatcher — ``completion`` →
``skill.plan`` / ``skill.repair_plain`` / ``skill.repair_findings``,
``structured`` (``repair=False``) → ``skill.execute`` / ``skill.repair_native``.
W9 removed the ``agentic_core`` feature-flag gate and the legacy
``ollama.chat`` fallthrough branches: the dispatcher path is now the only
path. The 4-stage fallback chain is the product's resilience contract and
must survive unchanged; only the transport under each stage changed.

Covered here (all stubbed/static — no live model activity):

* static: ``plan``/``execute`` carry the dispatcher paths with the planned
  purpose slugs and no legacy ``ollama.chat`` calls remain;
* behavior: each stage dispatches with the planned verb, purpose, and
  project scope; and the fallback chain (execute → repair_native →
  repair_plain → repair_findings) still runs in order with downstream
  normalization unchanged.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

# Import-order guard: this suite imports app.skills.skill_factory inside test
# bodies. That module sits on a latent module-level import cycle
# (research_validity -> skills.intercoder -> skill_factory -> file_processor
# -> embeddings -> pi_runtime.engine -> telemetry -> research_validity) that
# only resolves when the dispatcher plane (app.core.agentic) has been
# initialized first in the process. The cycle is pre-existing architecture
# debt outside this wave's files; initializing the plane here keeps a
# standalone run of this file green.
import app.core.agentic  # noqa: F401

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_FACTORY = REPO_ROOT / "backend/app/skills/skill_factory.py"

SPINE_PHASES = {
    "intent", "context", "plan", "tool_selection", "execution",
    "recovery", "grounding", "synthesis", "review", "governance",
}

PI_SCHEMA_KEYS = {
    "type", "properties", "required", "items", "enum", "const",
    "additionalProperties", "description",
}

FINDINGS = {
    "summary": "Onboarding friction is high.",
    "nuggets": [],
    "facts": [{"text": "Participants abandoned the first onboarding step."}],
    "insights": [],
    "recommendations": [],
    "suggestions": [],
}


# ── helpers ─────────────────────────────────────────────────────────────


def _function_source(function_name: str) -> str:
    text = SKILL_FACTORY.read_text(encoding="utf-8")
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return ast.get_source_segment(text, node) or ""
    raise AssertionError(f"{function_name} not found in {SKILL_FACTORY}")


class _StubAgentic:
    """Recording stand-in for the ``agentic`` dispatcher singleton.

    ``completion_results`` / ``structured_results`` are queued per verb so the
    4-stage fallback chain can be driven stage by stage.
    """

    def __init__(self, *, completion_results=None, structured_results=None) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._completion_results = list(completion_results or [])
        self._structured_results = list(structured_results or [])

    async def completion(self, **kwargs):
        self.calls.append(("completion", kwargs))
        result = (
            self._completion_results.pop(0)
            if self._completion_results
            else {"text": "dispatcher text", "status": "success"}
        )
        return SimpleNamespace(usage={}, **result)

    async def structured(self, **kwargs):
        self.calls.append(("structured", kwargs))
        result = (
            self._structured_results.pop(0)
            if self._structured_results
            else {"text": "", "value": {}, "status": "success"}
        )
        return SimpleNamespace(usage={}, **result)


def _make_skill():
    from app.skills.base import SkillPhase, SkillType
    from app.skills.skill_factory import create_skill

    return create_skill(
        skill_name="w5-test-skill",
        display="W5 Test Skill",
        desc="Exercises the W5 dispatcher migration.",
        phase=SkillPhase.DEFINE,
        skill_type=SkillType.MIXED,
        plan_prompt="Plan for {context}.",
        execute_prompt="Context: {context}\nData: {content}",
        output_schema='{"summary": "...", "facts": [{"text": "..."}]}',
    )


def _skill_input():
    from app.skills.base import SkillInput

    return SkillInput(project_id="p1", user_context="short research context")


@pytest.fixture
def _agentic_core_on(monkeypatch):
    monkeypatch.setattr("app.config.settings.agentic_core", True)


# ── static: dispatcher paths present, legacy branches removed (W9) ──────


def test_w5_skill_factory_carries_dispatcher_paths():
    plan_src = _function_source("plan")
    assert "agentic.completion" in plan_src and '"skill.plan"' in plan_src
    assert "agentic_core" not in plan_src, "W9 removed the feature-flag gate"
    assert "ollama.chat" not in plan_src, "W9 removed the legacy plan branch"

    exec_src = _function_source("execute")
    assert "agentic.structured" in exec_src
    assert '"skill.execute"' in exec_src
    assert '"skill.repair_native"' in exec_src
    assert "agentic.completion" in exec_src
    assert '"skill.repair_plain"' in exec_src
    assert '"skill.repair_findings"' in exec_src
    assert "repair=False" in exec_src, "structured stages must not double-repair"
    assert "agentic_core" not in exec_src, "W9 removed the feature-flag gate"
    assert "ollama.chat" not in exec_src, "W9 removed all four legacy calls"
    assert "settings.llm_provider" not in exec_src, (
        "retired classical settings must not alter the Pi-managed repair chain"
    )


# ── behavior: plan ───────────────────────────────────────────────────────


async def test_plan_flag_on_dispatches_skill_plan(monkeypatch, _agentic_core_on):
    dispatcher_stub = _StubAgentic(
        completion_results=[{"text": "dispatched plan", "status": "success"}]
    )
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    result = await _make_skill()().plan(_skill_input())

    assert result["plan"] == "dispatched plan"
    assert "fallback" not in result
    method, kwargs = dispatcher_stub.calls[0]
    assert method == "completion"
    assert kwargs["purpose"] == "skill.plan"
    assert kwargs["project_id"] == "p1"
    assert kwargs["system"] is None
    assert "Plan for" in kwargs["messages"][0]["content"]
    assert kwargs["params"].temperature == 0.7
    assert kwargs["params"].thinking_mode == "off"
    assert kwargs["spine_phase"] == "plan" and kwargs["spine_phase"] in SPINE_PHASES


# ── behavior: execute ────────────────────────────────────────────────────


async def test_execute_flag_on_dispatches_skill_execute(monkeypatch, _agentic_core_on):
    dispatcher_stub = _StubAgentic(
        structured_results=[
            {"text": json.dumps(FINDINGS), "value": FINDINGS, "status": "success"}
        ]
    )
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    output = await _make_skill()().execute(_skill_input())

    assert output.success is True
    assert output.summary == FINDINGS["summary"]
    assert output.facts[0]["text"] == FINDINGS["facts"][0]["text"]
    assert len(dispatcher_stub.calls) == 1, "valid structured output needs no repair stage"
    method, kwargs = dispatcher_stub.calls[0]
    assert method == "structured"
    assert kwargs["purpose"] == "skill.execute"
    assert kwargs["project_id"] == "p1"
    assert kwargs["repair"] is False, "the Pi engine must not double-repair inside the chain"
    assert "UX Research Auditor" in kwargs["system"]
    assert kwargs["params"].temperature == 0.2
    assert kwargs["params"].thinking_mode == "off"
    assert kwargs["params"].max_tokens is not None
    assert kwargs["spine_phase"] == "execution" and kwargs["spine_phase"] in SPINE_PHASES
    schema = kwargs["schema"]
    assert schema["type"] == "object", "Pi forced-tool root must be an object"
    assert set(schema) <= PI_SCHEMA_KEYS
    for prop in schema.get("properties", {}).values():
        assert set(prop) <= PI_SCHEMA_KEYS and "type" in prop


async def test_execute_flag_on_preserves_four_stage_fallback_chain(monkeypatch, _agentic_core_on):
    monkeypatch.setattr("app.config.settings.llm_provider", "ollama")
    dispatcher_stub = _StubAgentic(
        structured_results=[
            # skill.execute: no parsed value and non-JSON text → repair stage 1
            {"text": "prose, not JSON", "value": {}, "status": "success"},
            # skill.repair_native: still unusable → repair stage 2
            {"text": "still prose", "value": {}, "status": "success"},
        ],
        completion_results=[
            # skill.repair_plain: valid JSON but zero findings → repair stage 3
            {"text": json.dumps({"summary": "Recovered but empty."}), "status": "success"},
            # skill.repair_findings: valid JSON with findings → chain ends
            {"text": json.dumps(FINDINGS), "status": "success"},
        ],
    )
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    output = await _make_skill()().execute(_skill_input())

    assert output.success is True
    assert output.json_success is True
    assert output.summary == FINDINGS["summary"]
    assert output.facts[0]["text"] == FINDINGS["facts"][0]["text"]
    assert [method for method, _ in dispatcher_stub.calls] == [
        "structured",
        "structured",
        "completion",
        "completion",
    ], "the 4-stage fallback chain order is the resilience contract"
    assert [kwargs["purpose"] for _, kwargs in dispatcher_stub.calls] == [
        "skill.execute",
        "skill.repair_native",
        "skill.repair_plain",
        "skill.repair_findings",
    ]
    assert all(kwargs["project_id"] == "p1" for _, kwargs in dispatcher_stub.calls)
    for method, kwargs in dispatcher_stub.calls:
        if method == "structured":
            assert kwargs["repair"] is False
        assert kwargs["spine_phase"] in SPINE_PHASES


async def test_execute_flag_on_primary_structured_raise_still_walks_fallback_chain(
    monkeypatch, _agentic_core_on
):
    """F-W5-1: on the Pi engine, run_structured(repair=False) RAISES
    PiRuntimeTurnError on the first invalid structured output instead of
    returning status != "success". The primary skill.execute call must catch
    that and still walk the repair chain — the resilience contract."""
    from app.core.pi_runtime.endpoints import PiRuntimeTurnError

    monkeypatch.setattr("app.config.settings.llm_provider", "ollama")
    dispatcher_stub = _StubAgentic(
        structured_results=[
            # skill.repair_native: still unusable → repair stage 2
            {"text": "still prose", "value": {}, "status": "success"},
        ],
        completion_results=[
            # skill.repair_plain: valid JSON with findings → chain ends
            {"text": json.dumps(FINDINGS), "status": "success"},
        ],
    )

    real_structured = dispatcher_stub.structured

    async def _raising_structured(**kwargs):
        if kwargs.get("purpose") == "skill.execute":
            dispatcher_stub.calls.append(("structured", kwargs))
            raise PiRuntimeTurnError("error", "invalid structured output")
        return await real_structured(**kwargs)

    dispatcher_stub.structured = _raising_structured
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    output = await _make_skill()().execute(_skill_input())

    assert output.success is True
    assert output.json_success is True
    assert output.summary == FINDINGS["summary"]
    assert output.facts[0]["text"] == FINDINGS["facts"][0]["text"]
    assert [method for method, _ in dispatcher_stub.calls] == [
        "structured",
        "structured",
        "completion",
    ], "a raised primary structured call must fall into the repair chain"
    assert [kwargs["purpose"] for _, kwargs in dispatcher_stub.calls] == [
        "skill.execute",
        "skill.repair_native",
        "skill.repair_plain",
    ]
    assert all(kwargs["project_id"] == "p1" for _, kwargs in dispatcher_stub.calls)
