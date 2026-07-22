"""W5 contract coverage — Discover-skill migration (master plan §8 W5).

The nine legacy ``ollama.chat`` call sites across the Discover skills route
through the AgenticDispatcher. W9 retired the ``agentic_core`` feature-flag
gate and the preserved legacy ``ollama.chat`` branch: the dispatcher path is
now the only path.

* ``channel_deployment.py`` — ``plan`` (completion → ``skill.discover_plan``),
  ``_analyze`` (structured → ``skill.discover_analyze``,
  ``DEPLOYMENT_ANALYSIS_SCHEMA``);
* ``contextual_inquiry.py`` — ``plan`` (completion), ``execute``
  (structured, ``CONTEXTUAL_INQUIRY_SCHEMA``);
* ``diary_studies.py`` — ``plan`` (completion), ``execute``
  (structured, ``DIARY_ANALYSIS_SCHEMA``);
* ``user_interviews.py`` — ``plan`` (completion), ``execute`` transcript
  analysis (structured, ``TRANSCRIPT_ANALYSIS_SCHEMA``) and cross-interview
  synthesis (structured, ``SYNTHESIS_SCHEMA``).

Covered here (all stubbed/static — no live model activity):

* static: each migrated function carries the dispatcher path with the
  planned purpose slug;
* behavior: the dispatcher stub records the right verb, purpose, project
  scope, params, and schema; the downstream behavior (return shape,
  candidate marking, fallback on structured failure) is unchanged.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DISCOVER = REPO_ROOT / "backend/app/skills/discover"

SPINE_PHASES = {
    "intent", "context", "plan", "tool_selection", "execution",
    "recovery", "grounding", "synthesis", "review", "governance",
}


# ── helpers ─────────────────────────────────────────────────────────────


def _function_source(module_file: str, function_name: str) -> str:
    text = (DISCOVER / module_file).read_text(encoding="utf-8")
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return ast.get_source_segment(text, node) or ""
    raise AssertionError(f"{function_name} not found in {module_file}")


class _StubAgentic:
    """Recording stand-in for the ``agentic`` dispatcher singleton."""

    def __init__(self, *, text: str = "dispatcher text", value: dict | None = None,
                 status: str = "success") -> None:
        self.calls: list[tuple[str, dict]] = []
        self._text = text
        self._value = value
        self._status = status

    async def completion(self, **kwargs):
        self.calls.append(("completion", kwargs))
        return SimpleNamespace(text=self._text, status=self._status, usage={})

    async def structured(self, **kwargs):
        self.calls.append(("structured", kwargs))
        return SimpleNamespace(
            text=self._text, status=self._status, usage={}, value=self._value
        )


@pytest.fixture
def _agentic_core_on(monkeypatch):
    monkeypatch.setattr("app.config.settings.agentic_core", True)


def _skill_input(**overrides):
    from app.skills.base import SkillInput

    kwargs = {"project_id": "p1", "parameters": {}, "user_context": "",
              "project_context": "", "company_context": ""}
    kwargs.update(overrides)
    return SkillInput(**kwargs)


# ── static: dispatcher paths present with the planned purpose slugs ──────


def test_w5_discover_sites_carry_dispatcher_path():
    plan = _function_source("channel_deployment.py", "plan")
    assert "agentic.completion" in plan
    assert "skill.discover_plan" in plan

    analyze = _function_source("channel_deployment.py", "_analyze")
    assert "agentic.structured" in analyze
    assert "skill.discover_analyze" in analyze and "DEPLOYMENT_ANALYSIS_SCHEMA" in analyze

    ci_plan = _function_source("contextual_inquiry.py", "plan")
    assert "agentic.completion" in ci_plan
    assert "skill.discover_plan" in ci_plan

    ci_exec = _function_source("contextual_inquiry.py", "execute")
    assert "agentic.structured" in ci_exec
    assert "skill.discover_analyze" in ci_exec and "CONTEXTUAL_INQUIRY_SCHEMA" in ci_exec

    diary_plan = _function_source("diary_studies.py", "plan")
    assert "agentic.completion" in diary_plan
    assert "skill.discover_plan" in diary_plan

    diary_exec = _function_source("diary_studies.py", "execute")
    assert "agentic.structured" in diary_exec
    assert "skill.discover_analyze" in diary_exec and "DIARY_ANALYSIS_SCHEMA" in diary_exec

    ui_plan = _function_source("user_interviews.py", "plan")
    assert "agentic.completion" in ui_plan
    assert "skill.discover_plan" in ui_plan

    ui_exec = _function_source("user_interviews.py", "execute")
    assert ui_exec.count("agentic.structured") == 2, "analysis + synthesis sites"
    assert ui_exec.count('purpose="skill.discover_analyze"') == 2
    assert "TRANSCRIPT_ANALYSIS_SCHEMA" in ui_exec and "SYNTHESIS_SCHEMA" in ui_exec


# ── channel_deployment ────────────────────────────────────────────────────


def _channel_skill():
    from app.skills.discover.channel_deployment import ChannelResearchDeploymentSkill

    return ChannelResearchDeploymentSkill()


async def test_channel_plan_flag_on_dispatches_completion(monkeypatch, _agentic_core_on):
    dispatcher_stub = _StubAgentic(text='{"channel_strategy": "telegram"}')

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    result = await _channel_skill().plan(_skill_input())

    method, kwargs = dispatcher_stub.calls[0]
    assert method == "completion"
    assert kwargs["purpose"] == "skill.discover_plan"
    assert kwargs["project_id"] == "p1"
    assert kwargs["params"].temperature == 0.7
    assert kwargs["spine_phase"] == "plan" and kwargs["spine_phase"] in SPINE_PHASES
    assert result["channel_strategy"] == "telegram"


async def test_channel_analyze_flag_on_dispatches_structured(monkeypatch, _agentic_core_on):
    from app.skills.discover.channel_deployment import DEPLOYMENT_ANALYSIS_SCHEMA

    dispatcher_stub = _StubAgentic(value={
        "candidate_nuggets": [{"text": "dispatcher nugget", "confidence": "high"}],
        "candidate_insights": [{"text": "insight", "confidence": "medium", "impact": "high"}],
        "candidate_recommendations": [{"text": "rec", "priority": "high", "effort": "low"}],
    })

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    output = await _channel_skill().execute(_skill_input(
        parameters={"mode": "analyze", "deployment_name": "onboarding",
                    "deployment_type": "survey", "responses": [{"answer": "a"}]},
    ))

    method, kwargs = dispatcher_stub.calls[0]
    assert method == "structured"
    assert kwargs["purpose"] == "skill.discover_analyze"
    assert kwargs["project_id"] == "p1"
    assert kwargs["schema"] is DEPLOYMENT_ANALYSIS_SCHEMA
    assert kwargs["params"].temperature == 0.3
    assert kwargs["spine_phase"] == "synthesis" and kwargs["spine_phase"] in SPINE_PHASES
    assert output.nuggets[0]["text"] == "dispatcher nugget"
    assert output.nuggets[0]["artifact_state"] == "candidate_atom"
    assert output.insights[0]["artifact_state"] == "candidate_insight"
    assert output.recommendations[0]["artifact_state"] == "candidate_recommendation"


async def test_channel_analyze_flag_on_structured_failure_keeps_raw_fallback(
    monkeypatch, _agentic_core_on
):
    dispatcher_stub = _StubAgentic(text="not json at all", value=None, status="error")

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    output = await _channel_skill().execute(_skill_input(
        parameters={"mode": "analyze", "deployment_name": "onboarding",
                    "deployment_type": "interview", "responses": [{"answer": "a"}]},
    ))

    artifact = json.loads(output.artifacts["deployment_analysis.json"])
    assert artifact["raw_analysis"] == "not json at all", "parse-failure path preserved"
    assert output.nuggets == []


# ── contextual_inquiry ────────────────────────────────────────────────────


def _ci_skill():
    from app.skills.discover.contextual_inquiry import ContextualInquirySkill

    return ContextualInquirySkill()


async def test_contextual_inquiry_plan_flag_on_dispatches_completion(monkeypatch, _agentic_core_on):
    dispatcher_stub = _StubAgentic(text="dispatcher markdown plan")

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    result = await _ci_skill().plan(_skill_input())

    method, kwargs = dispatcher_stub.calls[0]
    assert method == "completion"
    assert kwargs["purpose"] == "skill.discover_plan"
    assert kwargs["project_id"] == "p1"
    assert kwargs["params"].temperature == 0.7
    assert result["plan"] == "dispatcher markdown plan"


async def test_contextual_inquiry_execute_flag_on_dispatches_structured(
    monkeypatch, _agentic_core_on
):
    from app.skills.discover.contextual_inquiry import CONTEXTUAL_INQUIRY_SCHEMA

    dispatcher_stub = _StubAgentic(value={
        "nuggets": [{"text": "dispatcher observation", "tags": ["workflow"]}],
        "summary": "dispatcher summary",
    })

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    output = await _ci_skill().execute(_skill_input(user_context="observation notes"))

    method, kwargs = dispatcher_stub.calls[0]
    assert method == "structured"
    assert kwargs["purpose"] == "skill.discover_analyze"
    assert kwargs["project_id"] == "p1"
    assert kwargs["schema"] is CONTEXTUAL_INQUIRY_SCHEMA
    assert kwargs["params"].temperature == 0.3
    assert output.summary == "dispatcher summary"
    assert output.nuggets[0]["text"] == "dispatcher observation"


async def test_contextual_inquiry_execute_flag_on_structured_failure_keeps_empty_fallback(
    monkeypatch, _agentic_core_on
):
    dispatcher_stub = _StubAgentic(value=None, status="error")

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    output = await _ci_skill().execute(_skill_input(user_context="observation notes"))

    assert output.nuggets == [], "parse-failure path yields no nuggets"
    assert "Found 0 nuggets" in output.summary


# ── diary_studies ─────────────────────────────────────────────────────────


def _diary_skill():
    from app.skills.discover.diary_studies import DiaryStudiesSkill

    return DiaryStudiesSkill()


async def test_diary_plan_flag_on_dispatches_completion(monkeypatch, _agentic_core_on):
    dispatcher_stub = _StubAgentic(text="dispatcher diary plan")

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    result = await _diary_skill().plan(_skill_input())

    method, kwargs = dispatcher_stub.calls[0]
    assert method == "completion"
    assert kwargs["purpose"] == "skill.discover_plan"
    assert kwargs["project_id"] == "p1"
    assert kwargs["params"].temperature == 0.7
    assert result["plan"] == "dispatcher diary plan"


async def test_diary_execute_flag_on_dispatches_structured(monkeypatch, _agentic_core_on):
    from app.skills.discover.diary_studies import DIARY_ANALYSIS_SCHEMA

    dispatcher_stub = _StubAgentic(value={
        "nuggets": [{"text": "dispatcher diary nugget", "day": "3", "tags": ["habit"]}],
        "summary": "dispatcher diary summary",
    })

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    output = await _diary_skill().execute(_skill_input(user_context="day 1: ..."))

    method, kwargs = dispatcher_stub.calls[0]
    assert method == "structured"
    assert kwargs["purpose"] == "skill.discover_analyze"
    assert kwargs["project_id"] == "p1"
    assert kwargs["schema"] is DIARY_ANALYSIS_SCHEMA
    assert kwargs["params"].temperature == 0.3
    assert output.summary == "dispatcher diary summary"
    assert output.nuggets[0]["text"] == "dispatcher diary nugget"


# ── user_interviews ───────────────────────────────────────────────────────


def _ui_skill():
    from app.skills.discover.user_interviews import UserInterviewsSkill

    return UserInterviewsSkill()


async def test_interviews_plan_flag_on_dispatches_completion(monkeypatch, _agentic_core_on):
    dispatcher_stub = _StubAgentic(text="dispatcher interview guide")

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    result = await _ui_skill().plan(_skill_input())

    method, kwargs = dispatcher_stub.calls[0]
    assert method == "completion"
    assert kwargs["purpose"] == "skill.discover_plan"
    assert kwargs["project_id"] == "p1"
    assert kwargs["params"].temperature == 0.7
    assert result["guide"] == "dispatcher interview guide"


async def test_interviews_execute_single_transcript_flag_on_dispatches_structured(
    monkeypatch, _agentic_core_on
):
    from app.skills.discover.user_interviews import TRANSCRIPT_ANALYSIS_SCHEMA

    dispatcher_stub = _StubAgentic(value={
        "nuggets": [{"text": "dispatcher quote", "location": "00:12", "tags": ["trust"]}],
    })

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    output = await _ui_skill().execute(_skill_input(user_context="interview transcript"))

    assert len(dispatcher_stub.calls) == 1, "single transcript — no synthesis call"
    method, kwargs = dispatcher_stub.calls[0]
    assert method == "structured"
    assert kwargs["purpose"] == "skill.discover_analyze"
    assert kwargs["project_id"] == "p1"
    assert kwargs["schema"] is TRANSCRIPT_ANALYSIS_SCHEMA
    assert kwargs["params"].temperature == 0.3
    assert output.nuggets[0]["text"] == "dispatcher quote"
    assert "synthesis.json" not in output.artifacts


def _two_transcripts(tmp_path: Path) -> list[str]:
    files = []
    for name in ("t1.txt", "t2.txt"):
        path = tmp_path / name
        path.write_text(f"transcript body for {name}", encoding="utf-8")
        files.append(str(path))
    return files


def _fake_process_file(path):
    return SimpleNamespace(error=None, chunks=[SimpleNamespace(text=f"text of {path}")])


async def test_interviews_synthesis_flag_on_dispatches_structured(
    monkeypatch, _agentic_core_on, tmp_path
):
    from app.skills.discover.user_interviews import SYNTHESIS_SCHEMA, TRANSCRIPT_ANALYSIS_SCHEMA

    dispatcher_stub = _StubAgentic()

    async def _structured(**kwargs):
        dispatcher_stub.calls.append(("structured", kwargs))
        if kwargs["schema"] is SYNTHESIS_SCHEMA:
            value = {
                "facts": [{"text": "dispatcher fact", "evidence_count": 2, "sources": []}],
                "insights": [{"text": "dispatcher insight", "confidence": "high"}],
                "recommendations": [{"text": "dispatcher rec", "priority": "critical", "effort": "high"}],
                "research_gaps": [{"description": "dispatcher gap", "suggested_method": "diary study"}],
            }
        else:
            value = {"nuggets": [{"text": "quote", "location": "", "tags": []}]}
        return SimpleNamespace(text="", status="success", usage={}, value=value)

    dispatcher_stub.structured = _structured

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    monkeypatch.setattr("app.skills.discover.user_interviews.process_file", _fake_process_file)

    output = await _ui_skill().execute(_skill_input(files=_two_transcripts(tmp_path)))

    assert len(dispatcher_stub.calls) == 3, "two transcript analyses + one synthesis"
    schemas = [kwargs["schema"] for _, kwargs in dispatcher_stub.calls]
    assert schemas[:2] == [TRANSCRIPT_ANALYSIS_SCHEMA, TRANSCRIPT_ANALYSIS_SCHEMA]
    assert schemas[2] is SYNTHESIS_SCHEMA
    for _, kwargs in dispatcher_stub.calls:
        assert kwargs["purpose"] == "skill.discover_analyze"
        assert kwargs["project_id"] == "p1"
        assert kwargs["params"].temperature == 0.3
    assert output.facts[0]["text"] == "dispatcher fact"
    assert output.insights[0]["text"] == "dispatcher insight"
    assert output.insights[0]["confidence"] == "high"
    assert output.recommendations[0]["priority"] == "critical"
    assert any("dispatcher gap" in s for s in output.suggestions)
    synthesis_artifact = json.loads(output.artifacts["synthesis.json"])
    assert synthesis_artifact["facts"][0]["text"] == "dispatcher fact"


async def test_interviews_synthesis_flag_on_structured_failure_keeps_raw_fallback(
    monkeypatch, _agentic_core_on, tmp_path
):
    from app.skills.discover.user_interviews import SYNTHESIS_SCHEMA

    dispatcher_stub = _StubAgentic()

    async def _structured(**kwargs):
        dispatcher_stub.calls.append(("structured", kwargs))
        if kwargs["schema"] is SYNTHESIS_SCHEMA:
            return SimpleNamespace(text="not json", status="error", usage={}, value=None)
        return SimpleNamespace(
            text="", status="success", usage={},
            value={"nuggets": [{"text": "quote", "location": "", "tags": []}]},
        )

    dispatcher_stub.structured = _structured

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    monkeypatch.setattr("app.skills.discover.user_interviews.process_file", _fake_process_file)

    output = await _ui_skill().execute(_skill_input(files=_two_transcripts(tmp_path)))

    synthesis_artifact = json.loads(output.artifacts["synthesis.json"])
    assert synthesis_artifact == {"raw_synthesis": "not json"}, "parse-failure path preserved"
    assert output.facts == [] and output.insights == [] and output.recommendations == []


# ── raise-path: Pi engine fail-closed errors degrade, never escape ──────
# F-W5-2: on the Pi engine the dispatcher RAISES PiRuntimeTurnError instead of
# returning status != "success". Every Discover structured site must catch
# that and route to its exact existing degraded-output fallback.


def _raising_dispatcher(dispatcher_stub, *, raise_for=None):
    """Make a _StubAgentic raise PiRuntimeTurnError like the Pi fail-closed path.

    ``raise_for`` optionally limits raising to calls whose schema is in the set;
    other calls keep the stub's normal behavior.
    """
    from app.core.pi_runtime.endpoints import PiRuntimeTurnError

    real_structured = dispatcher_stub.structured

    async def _structured(**kwargs):
        if raise_for is None or kwargs.get("schema") in raise_for:
            dispatcher_stub.calls.append(("structured", kwargs))
            raise PiRuntimeTurnError("error", "invalid structured output")
        return await real_structured(**kwargs)

    dispatcher_stub.structured = _structured
    return dispatcher_stub


async def test_channel_analyze_flag_on_structured_raise_keeps_raw_fallback(
    monkeypatch, _agentic_core_on
):
    dispatcher_stub = _raising_dispatcher(_StubAgentic())

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    output = await _channel_skill().execute(_skill_input(
        parameters={"mode": "analyze", "deployment_name": "onboarding",
                    "deployment_type": "interview", "responses": [{"answer": "a"}]},
    ))

    assert len(dispatcher_stub.calls) == 1
    artifact = json.loads(output.artifacts["deployment_analysis.json"])
    assert artifact["raw_analysis"] == "", "raised structured call must degrade to raw_analysis"
    assert output.nuggets == []


async def test_contextual_inquiry_execute_flag_on_structured_raise_keeps_empty_fallback(
    monkeypatch, _agentic_core_on
):
    dispatcher_stub = _raising_dispatcher(_StubAgentic())

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    output = await _ci_skill().execute(_skill_input(user_context="observation notes"))

    assert len(dispatcher_stub.calls) == 1
    assert output.nuggets == [], "raised structured call must degrade to empty analysis"
    assert "Found 0 nuggets" in output.summary


async def test_diary_execute_flag_on_structured_raise_keeps_empty_fallback(
    monkeypatch, _agentic_core_on
):
    dispatcher_stub = _raising_dispatcher(_StubAgentic())

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    output = await _diary_skill().execute(_skill_input(user_context="day 1: ..."))

    assert len(dispatcher_stub.calls) == 1
    assert output.success is True
    assert output.nuggets == [], "raised structured call must degrade to empty analysis"


async def test_interviews_execute_flag_on_structured_raise_keeps_raw_analysis(
    monkeypatch, _agentic_core_on
):
    dispatcher_stub = _raising_dispatcher(_StubAgentic())

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    output = await _ui_skill().execute(_skill_input(user_context="interview transcript"))

    assert len(dispatcher_stub.calls) == 1, "single transcript — no synthesis call"
    assert output.success is True
    assert output.nuggets == [], "raised structured call must degrade to raw_analysis"
    analyses_artifact = json.loads(output.artifacts["analysis.json"])
    assert analyses_artifact[0]["raw_analysis"] == ""


async def test_interviews_synthesis_flag_on_structured_raise_keeps_raw_fallback(
    monkeypatch, _agentic_core_on, tmp_path
):
    from app.skills.discover.user_interviews import SYNTHESIS_SCHEMA

    dispatcher_stub = _StubAgentic(
        value={"nuggets": [{"text": "quote", "location": "", "tags": []}]}
    )
    # raise only for the synthesis call; the per-transcript analyses succeed.
    # A list (not a set) — JSON-schema dicts are unhashable, and the helper's
    # ``schema in raise_for`` membership check matches by equality.
    _raising_dispatcher(dispatcher_stub, raise_for=[SYNTHESIS_SCHEMA])

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)
    monkeypatch.setattr("app.skills.discover.user_interviews.process_file", _fake_process_file)

    output = await _ui_skill().execute(_skill_input(files=_two_transcripts(tmp_path)))

    assert len(dispatcher_stub.calls) == 3, "two transcript analyses + one synthesis"
    synthesis_artifact = json.loads(output.artifacts["synthesis.json"])
    assert synthesis_artifact == {"raw_synthesis": ""}, "raised synthesis must degrade"
    assert output.facts == [] and output.insights == [] and output.recommendations == []
