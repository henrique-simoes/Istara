"""W5 contract coverage — intercoder skill migration (master plan §8 W5).

The five LLM call sites in ``app/skills/intercoder.py``
(``KappaIntercoderSkill.plan`` plus the four coding steps in ``execute`` —
Coder A, Coder B, reconciliation, theme extraction) route through the
AgenticDispatcher — ``completion`` → ``skill.kappa_plan``, ``structured`` →
``skill.kappa_code_a`` / ``skill.kappa_code_b`` / ``skill.kappa_reconcile`` /
``skill.kappa_themes``. W9 removed the ``agentic_core`` feature-flag gate and
the legacy ``ollama.chat`` fallthrough branches: the dispatcher path is now
the only path.

Covered here (all stubbed/static — no live model activity):

* static: each migrated function carries the dispatcher path with the
  planned purpose slugs, and no legacy ``ollama.chat`` branch remains;
* behavior: the dispatcher stub records each call (verb, purpose,
  project scope) and downstream behavior (kappa math, reconciliation
  application, parse-failure fallback) is unchanged.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

# Import-order guard: this suite imports app.skills.intercoder inside test
# bodies. That module sits on a latent module-level import cycle
# (research_validity -> skills.intercoder -> skill_factory -> file_processor
# -> embeddings -> pi_runtime.engine -> telemetry -> research_validity) that
# only resolves when the dispatcher plane (app.core.agentic) has been
# initialized first in the process. The cycle is pre-existing architecture
# debt outside this wave's files; initializing the plane here keeps a
# standalone run of this file green.
import app.core.agentic  # noqa: F401

REPO_ROOT = Path(__file__).resolve().parents[2]
INTERCODER = REPO_ROOT / "backend/app/skills/intercoder.py"

SPINE_PHASES = {
    "intent", "context", "plan", "tool_selection", "execution",
    "recovery", "grounding", "synthesis", "review", "governance",
}

ALLOWED_SCHEMA_KEYS = {
    "type", "properties", "required", "items", "enum", "const",
    "additionalProperties", "description",
}


# ── helpers ─────────────────────────────────────────────────────────────


def _function_source(function_name: str) -> str:
    text = INTERCODER.read_text(encoding="utf-8")
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return ast.get_source_segment(text, node) or ""
    raise AssertionError(f"{function_name} not found in {INTERCODER}")


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

    def __init__(self, *, text: str = "dispatcher text", values: dict | None = None,
                 statuses: dict | None = None) -> None:
        self.calls: list[tuple[str, dict]] = []
        self._text = text
        self._values = values or {}
        self._statuses = statuses or {}

    async def completion(self, **kwargs):
        self.calls.append(("completion", kwargs))
        return SimpleNamespace(text=self._text, status="success", usage={})

    async def structured(self, **kwargs):
        self.calls.append(("structured", kwargs))
        purpose = kwargs.get("purpose")
        return SimpleNamespace(
            text="",
            value=self._values.get(purpose, {}),
            status=self._statuses.get(purpose, "success"),
            usage={},
        )


@pytest.fixture
def _agentic_core_on(monkeypatch):
    monkeypatch.setattr("app.config.settings.agentic_core", True)


def _skill():
    from app.skills.intercoder import KappaIntercoderSkill

    return KappaIntercoderSkill()


def _skill_input(**overrides):
    from app.skills.base import SkillInput

    kwargs = {"project_id": "p1", "user_context": "Interview transcript: users discuss onboarding and export speed."}
    kwargs.update(overrides)
    return SkillInput(**kwargs)


# ── shared payload shapes ────────────────────────────────────────────────

CODER_A_DATA = {
    "codebook": [{"code": "ux", "definition": "usability concerns"}],
    "coding_results": [
        {"item_id": "seg_1", "text": "the onboarding flow was confusing", "source": "i1.txt", "codes": ["ux"]},
        {"item_id": "seg_2", "text": "export took forever to finish", "source": "i1.txt", "codes": ["perf"]},
    ],
}

CODER_B_DATA_DISAGREE = {
    "coding_results": [
        {"item_id": "seg_1", "codes": ["ux"]},
        {"item_id": "seg_2", "codes": ["speed"]},
    ],
}

CODER_B_DATA_AGREE = {
    "coding_results": [
        {"item_id": "seg_1", "codes": ["ux"]},
        {"item_id": "seg_2", "codes": ["perf"]},
    ],
}

RECONCILE_DATA = {
    "reconciled": [
        {"item_id": "seg_2", "final_codes": ["perf"], "rationale": "performance complaint"},
    ],
    "codebook_refinements": [
        {"code": "perf", "issue": "ambiguous label", "refined_definition": "latency/speed complaints"},
    ],
    "themes": [
        {"name": "Performance", "definition": "speed concerns", "codes": ["perf"],
         "prevalence": "minor", "description": "Users mention slowness."},
    ],
}

THEMES_DATA = {
    "themes": [
        {"name": "Usability", "definition": "ease-of-use concerns", "codes": ["ux"],
         "prevalence": "dominant", "description": "Users struggle with onboarding."},
    ],
}


# ── static: dispatcher paths present, legacy branches removed (W9) ──────


def test_w5_plan_carries_dispatcher_path():
    plan = _function_source("plan")
    assert "agentic.completion" in plan
    assert 'purpose="skill.kappa_plan"' in plan
    assert "agentic_core" not in plan, "W9 removed the feature-flag gate"
    assert "ollama.chat" not in plan, "W9 removed the legacy branch"


def test_w5_execute_carries_structured_paths():
    execute = _function_source("execute")
    assert execute.count("agentic.structured") == 4
    for purpose in (
        "skill.kappa_code_a", "skill.kappa_code_b",
        "skill.kappa_reconcile", "skill.kappa_themes",
    ):
        assert f'purpose="{purpose}"' in execute
    assert "agentic_core" not in execute, "W9 removed the feature-flag gate"
    assert "ollama.chat" not in execute, "W9 removed the legacy branches"


def test_w5_schemas_stay_inside_pi_forced_tool_subset():
    from app.skills import intercoder

    for schema in (
        intercoder._CODER_A_SCHEMA, intercoder._CODER_B_SCHEMA,
        intercoder._RECONCILIATION_SCHEMA, intercoder._THEMES_SCHEMA,
    ):
        assert schema.get("type") == "object"
        _check_schema_subset(schema)


# ── behavior: plan ───────────────────────────────────────────────────────


async def test_plan_flag_on_dispatches_skill_kappa_plan(monkeypatch, _agentic_core_on):
    dispatcher_stub = _StubAgentic(text="dispatcher plan")

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    result = await _skill().plan(_skill_input())

    method, kwargs = dispatcher_stub.calls[0]
    assert method == "completion"
    assert kwargs["purpose"] == "skill.kappa_plan"
    assert kwargs["project_id"] == "p1"
    assert kwargs["params"].temperature == 0.7
    assert kwargs["spine_phase"] in SPINE_PHASES
    assert result == {"skill": "kappa-thematic-analysis", "plan": "dispatcher plan"}


# ── behavior: execute — disagreement path (reconcile) ───────────────────


async def test_execute_flag_on_dispatches_structured_calls_and_reconciles(monkeypatch, _agentic_core_on):
    dispatcher_stub = _StubAgentic(values={
        "skill.kappa_code_a": CODER_A_DATA,
        "skill.kappa_code_b": CODER_B_DATA_DISAGREE,
        "skill.kappa_reconcile": RECONCILE_DATA,
    })

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    output = await _skill().execute(_skill_input())

    assert [method for method, _ in dispatcher_stub.calls] == ["structured"] * 3
    purposes = [kwargs["purpose"] for _, kwargs in dispatcher_stub.calls]
    assert purposes == ["skill.kappa_code_a", "skill.kappa_code_b", "skill.kappa_reconcile"]
    for _, kwargs in dispatcher_stub.calls:
        assert kwargs["project_id"] == "p1"
        assert kwargs["params"].temperature == 0.3
        assert kwargs["spine_phase"] in SPINE_PHASES
        assert kwargs["schema"]["type"] == "object"

    # Downstream behavior unchanged: kappa math + reconciliation application.
    assert output.success
    assert len(output.nuggets) == 2
    seg_2 = next(n for n in output.nuggets if "export" in n["text"])
    assert seg_2["tags"] == ["perf"]
    assert "Cohen's Kappa" in output.insights[0]["text"]
    theme_insights = [i for i in output.insights if i["text"].startswith("Theme: Performance")]
    assert theme_insights, "themes from the reconciliation call must surface as insights"


# ── behavior: execute — all-agreed path (theme extraction) ──────────────


async def test_execute_flag_on_all_agreed_dispatches_kappa_themes(monkeypatch, _agentic_core_on):
    dispatcher_stub = _StubAgentic(values={
        "skill.kappa_code_a": CODER_A_DATA,
        "skill.kappa_code_b": CODER_B_DATA_AGREE,
        "skill.kappa_themes": THEMES_DATA,
    })

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    output = await _skill().execute(_skill_input())

    purposes = [kwargs["purpose"] for _, kwargs in dispatcher_stub.calls]
    assert purposes == ["skill.kappa_code_a", "skill.kappa_code_b", "skill.kappa_themes"]
    assert output.success
    theme_insights = [i for i in output.insights if i["text"].startswith("Theme: Usability")]
    assert theme_insights, "theme-extraction call must feed the insights list"


# ── behavior: parse-failure fallback mirrors the legacy path ─────────────


async def test_execute_flag_on_failed_coder_a_returns_failure_output(monkeypatch, _agentic_core_on):
    dispatcher_stub = _StubAgentic(
        values={"skill.kappa_code_a": {}},
        statuses={"skill.kappa_code_a": "error"},
    )

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    output = await _skill().execute(_skill_input())

    assert not output.success, "empty Coder A value must mirror the legacy parse-failure path"
    assert output.summary == "Coder A produced no coding results."
    assert len(dispatcher_stub.calls) == 1, "pipeline must stop after the failed first pass"


# ── raise-path: Pi engine fail-closed errors degrade, never escape ──────
# F-W5-2: on the Pi engine the dispatcher RAISES PiRuntimeTurnError (repair=False
# gives no bounded retry) instead of returning status != "success"; the
# status=error stubs above never exercise that path. Each intercoder structured
# site must catch the raise and route to its exact existing degraded fallback.


def _raising_dispatcher(dispatcher_stub, *, raise_for):
    """Make a _StubAgentic raise PiRuntimeTurnError like the Pi fail-closed path.

    ``raise_for`` is the set of purposes whose structured call raises; other
    calls keep the stub's normal recording behavior.
    """
    from app.core.pi_runtime.endpoints import PiRuntimeTurnError

    real_structured = dispatcher_stub.structured

    async def _structured(**kwargs):
        if kwargs.get("purpose") in raise_for:
            dispatcher_stub.calls.append(("structured", kwargs))
            raise PiRuntimeTurnError("error", "invalid structured output")
        return await real_structured(**kwargs)

    dispatcher_stub.structured = _structured
    return dispatcher_stub


async def test_execute_flag_on_coder_a_raise_returns_failure_output(monkeypatch, _agentic_core_on):
    dispatcher_stub = _raising_dispatcher(_StubAgentic(), raise_for={"skill.kappa_code_a"})

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    output = await _skill().execute(_skill_input())

    assert not output.success, "raised Coder A must mirror the empty-coding path, not escape"
    assert output.summary == "Coder A produced no coding results."
    assert len(dispatcher_stub.calls) == 1, "pipeline must stop after the raised first pass"


async def test_execute_flag_on_coder_b_raise_degrades_to_union_coding(monkeypatch, _agentic_core_on):
    dispatcher_stub = _raising_dispatcher(
        _StubAgentic(values={"skill.kappa_code_a": CODER_A_DATA}),
        raise_for={"skill.kappa_code_b"},
    )

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    output = await _skill().execute(_skill_input())

    # Coder B raise → empty B coding → every segment disagrees → reconcile path
    # (default reconcile is empty) → union codes kept; the skill still completes.
    assert output.success, "raised Coder B must degrade, not escape"
    assert len(output.nuggets) == 2
    seg_2 = next(n for n in output.nuggets if "export" in n["text"])
    assert seg_2["tags"] == ["perf"], "empty Coder B leaves Coder A's union codes"
    purposes = [kwargs["purpose"] for _, kwargs in dispatcher_stub.calls]
    assert purposes == ["skill.kappa_code_a", "skill.kappa_code_b", "skill.kappa_reconcile"]


async def test_execute_flag_on_reconcile_raise_keeps_union_codes(monkeypatch, _agentic_core_on):
    dispatcher_stub = _raising_dispatcher(
        _StubAgentic(values={
            "skill.kappa_code_a": CODER_A_DATA,
            "skill.kappa_code_b": CODER_B_DATA_DISAGREE,
        }),
        raise_for={"skill.kappa_reconcile"},
    )

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    output = await _skill().execute(_skill_input())

    # Reconciliation raise → empty reconcile → unreconciled codes keep the
    # coder union and no themes surface, but the analysis still completes.
    assert output.success, "raised reconciliation must degrade, not escape"
    seg_2 = next(n for n in output.nuggets if "export" in n["text"])
    assert set(seg_2["tags"]) == {"perf", "speed"}, "unreconciled disagreement keeps the union"
    assert not any(i["text"].startswith("Theme:") for i in output.insights)
    purposes = [kwargs["purpose"] for _, kwargs in dispatcher_stub.calls]
    assert purposes == ["skill.kappa_code_a", "skill.kappa_code_b", "skill.kappa_reconcile"]


async def test_execute_flag_on_all_agreed_themes_raise_keeps_no_themes(monkeypatch, _agentic_core_on):
    dispatcher_stub = _raising_dispatcher(
        _StubAgentic(values={
            "skill.kappa_code_a": CODER_A_DATA,
            "skill.kappa_code_b": CODER_B_DATA_AGREE,
        }),
        raise_for={"skill.kappa_themes"},
    )

    monkeypatch.setattr("app.core.agentic.agentic", dispatcher_stub)

    output = await _skill().execute(_skill_input())

    # All-agreed path → theme extraction raises → no-themes fallback; kappa
    # results still surface and the skill completes.
    assert output.success, "raised theme extraction must degrade, not escape"
    assert not any(i["text"].startswith("Theme:") for i in output.insights)
    purposes = [kwargs["purpose"] for _, kwargs in dispatcher_stub.calls]
    assert purposes == ["skill.kappa_code_a", "skill.kappa_code_b", "skill.kappa_themes"]
