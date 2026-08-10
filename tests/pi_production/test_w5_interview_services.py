"""W5 contract coverage — interview services migration (master plan §8 W5).

The three ``llm_router.chat`` call sites in the interview/deployment services
(``adaptive_interview.generate_clarification``,
``adaptive_interview._is_saturated``,
``deployment_service._generate_adaptive_followup``) route through the
AgenticDispatcher — ``completion`` → ``channel.clarify`` /
``channel.saturation`` / ``channel.followup``. W9 retired the
``agentic_core`` feature-flag gate and the preserved legacy
``llm_router.chat`` branch: the dispatcher path is now the only path.

Covered here (all stubbed/static — no live model activity):

* static: each migrated function carries the dispatcher path with the right
  purpose slug;
* behavior: the dispatcher records the call (verb, purpose, project scope,
  messages) and the NONE/SATURATED sentinel handling downstream is
  unchanged.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services import adaptive_interview, deployment_service

REPO_ROOT = Path(__file__).resolve().parents[2]
ADAPTIVE_INTERVIEW = REPO_ROOT / "backend/app/services/adaptive_interview.py"
DEPLOYMENT_SERVICE = REPO_ROOT / "backend/app/services/deployment_service.py"


# ── helpers ─────────────────────────────────────────────────────────────


def _function_source(path: Path, function_name: str) -> str:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return ast.get_source_segment(text, node) or ""
    raise AssertionError(f"{function_name} not found in {path}")


class _StubAgentic:
    """Recording stand-in for the ``agentic`` dispatcher singleton."""

    def __init__(self, *, text: str = "dispatcher reply") -> None:
        self.calls: list[tuple[str, dict]] = []
        self._text = text

    async def completion(self, **kwargs):
        self.calls.append(("completion", kwargs))
        return SimpleNamespace(text=self._text, status="success", usage={})


@pytest.fixture
def _agentic_core_on(monkeypatch):
    monkeypatch.setattr("app.config.settings.agentic_core", True)


def _deployment(**overrides) -> SimpleNamespace:
    deployment = SimpleNamespace(
        config_json=json.dumps({"max_followups": 3, "research_goals": "Understand onboarding"}),
        questions_json=json.dumps([{"text": "How was onboarding?"}]),
        deployment_type="interview",
        project_id="p1",
    )
    for key, value in overrides.items():
        setattr(deployment, key, value)
    return deployment


# ── static: dispatcher path present ──────────────────────────────────────


def test_w5_interview_functions_carry_dispatcher_path():
    clarify = _function_source(ADAPTIVE_INTERVIEW, "generate_clarification")
    assert "agentic.completion" in clarify
    assert '"channel.clarify"' in clarify

    saturation = _function_source(ADAPTIVE_INTERVIEW, "_is_saturated")
    assert "agentic.completion" in saturation
    assert '"channel.saturation"' in saturation

    followup = _function_source(DEPLOYMENT_SERVICE, "_generate_adaptive_followup")
    assert "agentic.completion" in followup
    assert '"channel.followup"' in followup


# ── behavior: generate_clarification (channel.clarify) ───────────────────


async def test_generate_clarification_flag_on_dispatches_channel_clarify(
    monkeypatch, _agentic_core_on
):
    dispatcher_stub = _StubAgentic(text="What part was confusing?")
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    result = await adaptive_interview.generate_clarification(
        SimpleNamespace(), "it was confusing", project_id="p1"
    )

    assert result == "What part was confusing?"
    method, kwargs = dispatcher_stub.calls[0]
    assert method == "completion"
    assert kwargs["purpose"] == "channel.clarify"
    assert kwargs["project_id"] == "p1"
    assert kwargs["system"] is None
    assert len(kwargs["messages"]) == 1
    assert "it was confusing" in kwargs["messages"][0]["content"]


async def test_generate_clarification_flag_on_none_sentinel_unchanged(
    monkeypatch, _agentic_core_on
):
    dispatcher_stub = _StubAgentic(text="NONE")
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    result = await adaptive_interview.generate_clarification(
        SimpleNamespace(), "all clear", project_id="p1"
    )

    assert result is None, "dispatcher NONE reply must hit the same sentinel check"


async def test_generate_clarification_flag_on_empty_project_scope(monkeypatch, _agentic_core_on):
    dispatcher_stub = _StubAgentic(text="follow-up?")
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    await adaptive_interview.generate_clarification(SimpleNamespace(), "vague answer")

    _, kwargs = dispatcher_stub.calls[0]
    assert kwargs["project_id"] == "", "None project scope maps to the empty string"


# ── behavior: _is_saturated (channel.saturation) ─────────────────────────


async def test_is_saturated_flag_on_dispatches_channel_saturation(monkeypatch, _agentic_core_on):
    # NB: the check is the substring test ``"SATURATED" in content``,
    # which also matches "NOT_SATURATED" — use a reply without the substring
    # to exercise the not-saturated path.
    dispatcher_stub = _StubAgentic(text="still adding new information")
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    config = {"saturation_check_llm": True}
    result = await adaptive_interview._is_saturated("new detail here", config, project_id="p1")

    assert result is False, "a reply without the SATURATED substring is not saturated"
    method, kwargs = dispatcher_stub.calls[0]
    assert method == "completion"
    assert kwargs["purpose"] == "channel.saturation"
    assert kwargs["project_id"] == "p1"
    assert "new detail here" in kwargs["messages"][0]["content"]


async def test_is_saturated_flag_on_saturated_sentinel_unchanged(monkeypatch, _agentic_core_on):
    dispatcher_stub = _StubAgentic(text="SATURATED")
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    config = {"saturation_check_llm": True}
    result = await adaptive_interview._is_saturated("repeating myself", config, project_id="p1")

    assert result is True, "dispatcher SATURATED reply must hit the same sentinel check"


# ── behavior: _generate_adaptive_followup (channel.followup) ─────────────


async def test_adaptive_followup_flag_on_dispatches_channel_followup(
    monkeypatch, _agentic_core_on
):
    dispatcher_stub = _StubAgentic(text="Which step confused you?")
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    conversation = SimpleNamespace(current_question_index=1)
    result = await deployment_service._generate_adaptive_followup(
        None, _deployment(), conversation, "it was confusing"
    )

    assert result == "Which step confused you?"
    method, kwargs = dispatcher_stub.calls[0]
    assert method == "completion"
    assert kwargs["purpose"] == "channel.followup"
    assert kwargs["project_id"] == "p1", "project scope comes from the deployment"
    assert kwargs["system"] is None
    assert "it was confusing" in kwargs["messages"][0]["content"]


async def test_adaptive_followup_flag_on_none_sentinel_unchanged(monkeypatch, _agentic_core_on):
    dispatcher_stub = _StubAgentic(text="NONE")
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    conversation = SimpleNamespace(current_question_index=1)
    result = await deployment_service._generate_adaptive_followup(
        None, _deployment(), conversation, "all clear"
    )

    assert result is None, "dispatcher NONE reply must hit the same sentinel check"


async def test_adaptive_followup_max_followups_cap_precedes_llm(monkeypatch, _agentic_core_on):
    dispatcher_stub = _StubAgentic()
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    # 1 scripted question + 3 follow-ups already asked == max_followups cap hit.
    conversation = SimpleNamespace(current_question_index=4)
    result = await deployment_service._generate_adaptive_followup(
        None, _deployment(), conversation, "anything"
    )

    assert result is None
    assert dispatcher_stub.calls == [], (
        "the follow-up cap must short-circuit before any LLM call"
    )
