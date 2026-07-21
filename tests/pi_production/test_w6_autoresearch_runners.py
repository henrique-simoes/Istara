"""W6 contract coverage — autoresearch-runner migration (master plan §8 W6).

The 14 ``llm_router.chat`` call sites across the six autoresearch loop runners
(``model_temp``, ``persona``, ``question_bank``, ``rag_params``,
``skill_prompt``, ``ui_sim``) route through the AgenticDispatcher —
``completion`` → ``autoresearch.<runner>.<step>`` — gated on the
``agentic_core`` feature flag, with the legacy ``llm_router.chat`` branch
preserved alongside for ``agentic_core=False``.

Two design decisions from the plan are covered explicitly:

* ``model_temp`` sweeping — under the Pi engine the (model, temperature) grid
  is built from the PiModelManager catalog (not the legacy ``llm_router``
  model list), and a sweep that cannot span two distinct models records
  ``sweep_truncated`` rather than silently narrowing;
* ``rag_params`` embedding-skip — the ``_llm_hypothesis`` chat call migrates,
  but the ``_score_single_query`` retrieval-eval embedding stays on the legacy
  plane (never routed through ``agentic.embed``) until the W8 gateway.

Covered here (all stubbed/static — no live model activity):

* static: each migrated function carries both the dispatcher path (flag on,
  right purpose slug, valid spine phase) and the preserved legacy branch;
* ratchet: the count-to-zero ratchet stays green at 70 (legacy branch
  preserved, not retired);
* behavior (flag off): the legacy plane is used exactly as before and the
  dispatcher is never touched;
* behavior (flag on): the dispatcher records the call (right verb, purpose,
  project scope, spine phase) and the legacy plane is never touched.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

# Importing ``app.core.agentic`` transitively imports ``app.core.ollama``,
# whose module import registers the local server on the real ``llm_router``.
# That must happen before any test stubs ``app.core.llm_router.llm_router``.
import app.core.agentic  # noqa: F401
from app.core.autoresearch_runners.model_temp import TEMPERATURES, ModelTempRunner

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNERS = REPO_ROOT / "backend/app/core/autoresearch_runners"

SPINE_PHASES = {
    "intent", "context", "plan", "tool_selection", "execution",
    "recovery", "grounding", "synthesis", "review", "governance",
}

# (module, function, purpose slug) for every migrated chat site.
MIGRATED_SITES = [
    ("model_temp", "_evaluate_skill", "autoresearch.model_temp.evaluate"),
    ("model_temp", "_score_output", "autoresearch.model_temp.score"),
    ("persona", "hypothesize", "autoresearch.persona.hypothesize"),
    ("persona", "_evaluate_agent", "autoresearch.persona.evaluate"),
    ("persona", "_score_response", "autoresearch.persona.score"),
    ("question_bank", "hypothesize", "autoresearch.question_bank.hypothesize"),
    ("question_bank", "_evaluate_questions", "autoresearch.question_bank.evaluate"),
    ("question_bank", "_score_responses", "autoresearch.question_bank.score"),
    ("rag_params", "_llm_hypothesis", "autoresearch.rag_params.hypothesize"),
    ("skill_prompt", "hypothesize", "autoresearch.skill_prompt.hypothesize"),
    ("skill_prompt", "_single_eval", "autoresearch.skill_prompt.evaluate"),
    ("skill_prompt", "_score_output", "autoresearch.skill_prompt.score"),
    ("ui_sim", "hypothesize", "autoresearch.ui_sim.hypothesize"),
    ("ui_sim", "_evaluate_component", "autoresearch.ui_sim.evaluate"),
]


# ── helpers ─────────────────────────────────────────────────────────────


def _function_source(module: str, function_name: str) -> str:
    path = RUNNERS / f"{module}.py"
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return ast.get_source_segment(text, node) or ""
    raise AssertionError(f"{function_name} not found in {path}")


class _StubAgentic:
    """Recording stand-in for the ``agentic`` dispatcher singleton."""

    def __init__(self, *, text: str = "dispatcher text", status: str = "success") -> None:
        self.calls: list[tuple[str, dict]] = []
        self._text = text
        self._status = status

    async def completion(self, **kwargs):
        self.calls.append(("completion", kwargs))
        return SimpleNamespace(text=self._text, status=self._status, usage={})

    async def embed(self, **kwargs):  # pragma: no cover - must never be reached in W6
        self.calls.append(("embed", kwargs))
        raise AssertionError("W6 must not route embeddings through the dispatcher")


class _StubRouter:
    """Recording stand-in for the legacy ``llm_router`` singleton."""

    def __init__(self, *, text: str = "legacy text", models=None) -> None:
        self.calls: list[dict] = []
        self._text = text
        self._models = models or []

    async def chat(self, messages=None, **kwargs):
        self.calls.append({"messages": messages, **kwargs})
        return {"message": {"content": self._text}}

    async def list_models(self):
        return list(self._models)


class _FakeManager:
    """Stand-in for PiModelManager exposing only ``catalog()``."""

    def __init__(self, models: list[str]) -> None:
        self._models = models

    def catalog(self):
        return [SimpleNamespace(model=m, endpoint_id=f"ep-{m}") for m in self._models]


@pytest.fixture
def _flag_on(monkeypatch):
    monkeypatch.setattr("app.config.settings.agentic_core", True)


@pytest.fixture
def _flag_off(monkeypatch):
    monkeypatch.setattr("app.config.settings.agentic_core", False)


# ── static: both paths present, ratchet green ───────────────────────────


def test_w6_ratchet_stays_green_at_70():
    """The legacy branch is preserved, so the 14 sites stay allowlisted."""
    from tests.pi_migration.test_count_to_zero import EXPECTED_PRODUCT_SITES, check_count_to_zero

    assert EXPECTED_PRODUCT_SITES == 70
    check_count_to_zero()


@pytest.mark.parametrize("module,function,purpose", MIGRATED_SITES)
def test_w6_site_carries_dispatcher_and_preserved_legacy_branch(module, function, purpose):
    src = _function_source(module, function)
    assert "settings.agentic_core" in src, f"{module}.{function} missing feature-flag gate"
    assert "agentic.completion" in src, f"{module}.{function} missing dispatcher path"
    assert purpose in src, f"{module}.{function} missing purpose slug {purpose!r}"
    assert "llm_router.chat" in src, f"{module}.{function} must preserve the legacy branch"
    assert any(f'spine_phase="{phase}"' in src for phase in SPINE_PHASES), (
        f"{module}.{function} must tag a valid spine phase"
    )


# ── model_temp sweeping decision (master plan §8 W6) ─────────────────────


async def test_model_temp_pi_sweep_uses_catalog_and_filters_embeddings(_flag_on, monkeypatch):
    monkeypatch.setattr(
        "app.core.pi_runtime.model_manager.PiModelManager",
        lambda *a, **k: _FakeManager(["m-alpha", "m-beta", "nomic-embed-text"]),
    )
    runner = ModelTempRunner()
    grid = await runner._build_grid()

    assert {model for model, _ in grid} == {"m-alpha", "m-beta"}  # embed filtered out
    assert len(grid) == 2 * len(TEMPERATURES)
    assert runner._sweep_truncated is False


async def test_model_temp_pi_sweep_degenerate_records_truncated(_flag_on, monkeypatch):
    monkeypatch.setattr(
        "app.core.pi_runtime.model_manager.PiModelManager",
        lambda *a, **k: _FakeManager(["only-one"]),
    )
    runner = ModelTempRunner()
    grid = await runner._build_grid()

    assert {model for model, _ in grid} == {"only-one"}
    assert runner._sweep_truncated is True


async def test_model_temp_pi_sweep_empty_catalog_records_truncated(_flag_on, monkeypatch):
    monkeypatch.setattr(
        "app.core.pi_runtime.model_manager.PiModelManager",
        lambda *a, **k: _FakeManager([]),
    )
    runner = ModelTempRunner()
    grid = await runner._build_grid()

    assert grid == []
    assert runner._sweep_truncated is True


async def test_model_temp_legacy_sweep_uses_llm_router(_flag_off, monkeypatch):
    router = _StubRouter(models=[{"name": "a"}, {"name": "b"}, {"name": "x-embed"}])
    monkeypatch.setattr("app.core.llm_router.llm_router", router)
    # PiModelManager must NOT be consulted on the legacy engine.
    monkeypatch.setattr(
        "app.core.pi_runtime.model_manager.PiModelManager",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("catalog must not be used")),
    )
    runner = ModelTempRunner()
    grid = await runner._build_grid()

    assert {model for model, _ in grid} == {"a", "b"}  # embed filtered
    assert runner._sweep_truncated is False


# ── behavior: score site dispatches / falls back to legacy ───────────────


async def test_model_temp_score_dispatches_when_flag_on(_flag_on, monkeypatch):
    dispatcher = _StubAgentic(text="0.85")
    router = _StubRouter(text="0.11")
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher)
    monkeypatch.setattr("app.core.llm_router.llm_router", router)

    runner = ModelTempRunner()
    runner.bind_project("proj-w6")
    score = await runner._score_output("x" * 50, "skill-a")

    assert score == pytest.approx(0.85)
    assert len(dispatcher.calls) == 1
    verb, kwargs = dispatcher.calls[0]
    assert verb == "completion"
    assert kwargs["purpose"] == "autoresearch.model_temp.score"
    assert kwargs["project_id"] == "proj-w6"
    assert kwargs["spine_phase"] in SPINE_PHASES
    assert not router.calls, "legacy plane must not be touched when the flag is on"


async def test_model_temp_score_uses_legacy_when_flag_off(_flag_off, monkeypatch):
    dispatcher = _StubAgentic()
    router = _StubRouter(text="0.42")
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher)
    monkeypatch.setattr("app.core.llm_router.llm_router", router)

    runner = ModelTempRunner()  # no bind_project — legacy path never needs it
    score = await runner._score_output("x" * 50, "skill-a")

    assert score == pytest.approx(0.42)
    assert len(router.calls) == 1
    assert not dispatcher.calls, "dispatcher must not be touched when the flag is off"


async def test_model_temp_evaluate_forwards_candidate_model_when_flag_on(_flag_on, monkeypatch):
    """The Pi path must carry the swept candidate model in TurnParams."""
    dispatcher = _StubAgentic(text="sample output text")
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher)

    class _Defn:
        data = {"execute_prompt": "You are a UX skill."}

    monkeypatch.setattr(
        "app.skills.skill_manager.skill_manager", SimpleNamespace(get=lambda name: _Defn())
    )
    # Score step returns a constant so we isolate the evaluate dispatch.
    async def _fixed_score(self, output, skill_name):
        return 0.5

    monkeypatch.setattr(ModelTempRunner, "_score_output", _fixed_score)
    async def _noop_record(self, *a, **k):
        return None

    monkeypatch.setattr(ModelTempRunner, "_record_stats", _noop_record)

    runner = ModelTempRunner()
    runner.bind_project("proj-w6")
    await runner._evaluate_skill("skill-a", model="candidate-model", temperature=0.9)

    evaluate_calls = [c for c in dispatcher.calls if c[1]["purpose"] == "autoresearch.model_temp.evaluate"]
    assert len(evaluate_calls) == 1
    params = evaluate_calls[0][1]["params"]
    assert params.model == "candidate-model"
    assert params.temperature == 0.9


# ── rag_params embedding-skip decision (master plan §8 W6) ───────────────


def test_rag_params_hypothesis_migrates_but_embedding_stays_legacy():
    hypo = _function_source("rag_params", "_llm_hypothesis")
    assert "agentic.completion" in hypo
    assert "autoresearch.rag_params.hypothesize" in hypo
    assert "llm_router.chat" in hypo  # legacy branch preserved

    score_query = _function_source("rag_params", "_score_single_query")
    assert "embed_text" in score_query, "retrieval-eval embedding must stay on the legacy plane"
    assert "agentic.embed" not in score_query, "W6 must not route embeddings through the dispatcher"
    assert "W8" in score_query, "the deliberate embed-skip must be documented in-line"
