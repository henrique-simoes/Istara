"""W6 per-experiment engine selection (master plan §8 W6, finding F-W6-2).

The experiment definition gains a validated ``pi``|``legacy`` engine field at
the ``/start`` boundary (``StartExperimentRequest.engine``). The selection is
threaded into the runner via ``bind_engine`` so every migrated model call site
routes on the bound selection (``use_pi_engine``) rather than re-reading the
global ``settings.agentic_core`` flag at each site; it is persisted on the
``AutoresearchExperiment`` row and returned in ``to_dict`` for audit.

Covered here (all stubbed/static — no live model activity):

* boundary: the request validates pi|legacy (normalized) and rejects anything
  else, including the empty string;
* resolver: an explicit value validates; an unset value defaults from the
  global flag (prior behavior preserved);
* override: a bound engine overrides the global flag at the dispatch site — a
  ``pi`` experiment dispatches with the flag OFF and a ``legacy`` experiment
  stays on the legacy plane with the flag ON;
* persistence: the engine loop stamps and persists the engine, and the durable
  row round-trips it (incl. the config snapshot) and NULL for legacy rows.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

# Importing ``app.core.agentic`` transitively imports ``app.core.ollama``,
# whose module import registers the local server on the real ``llm_router``.
# That must happen before any test stubs ``app.core.llm_router.llm_router``.
import app.core.agentic  # noqa: F401
from app.api.routes.autoresearch import StartExperimentRequest
from app.core.autoresearch_engine import AutoresearchEngine
from app.core.autoresearch_runners import (
    AUTORESEARCH_ENGINES,
    BaseLoopRunner,
    normalize_engine,
    resolve_engine,
)
from app.core.autoresearch_runners.persona import PersonaRunner
from app.models.autoresearch_experiment import AutoresearchExperiment
from app.models.database import async_session, init_db
from app.models.project import Project

from pydantic import ValidationError


# ── recording stand-ins ──────────────────────────────────────────────────


class _StubAgentic:
    def __init__(self, *, text: str) -> None:
        self.calls: list[dict] = []
        self._text = text

    async def completion(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(text=self._text, status="success", usage={})


class _StubRouter:
    def __init__(self, *, text: str) -> None:
        self.calls: list[dict] = []
        self._text = text

    async def chat(self, messages=None, **kwargs):
        self.calls.append({"messages": messages, **kwargs})
        return {"message": {"content": self._text}}


# ── boundary validation ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    "value,expected",
    [(None, None), ("pi", "pi"), ("legacy", "legacy"), ("PI", "pi"), ("  legacy ", "legacy")],
)
def test_start_request_accepts_and_normalizes_valid_engine(value, expected):
    kwargs = {"loop_type": "persona", "target": "agent-x"}
    if value is not None:
        kwargs["engine"] = value
    req = StartExperimentRequest(**kwargs)
    assert req.engine == expected


@pytest.mark.parametrize("bad", ["gpt-4", "ollama", "", "pi ; legacy", "none"])
def test_start_request_rejects_invalid_engine(bad):
    with pytest.raises(ValidationError):
        StartExperimentRequest(loop_type="persona", target="agent-x", engine=bad)


def test_start_request_defaults_engine_to_none():
    req = StartExperimentRequest(loop_type="model_temp", target="skill-a")
    assert req.engine is None


# ── resolver / normalizer ────────────────────────────────────────────────


def test_normalize_engine_validates_membership():
    assert normalize_engine("pi") == "pi"
    assert normalize_engine("LEGACY") == "legacy"
    assert set(AUTORESEARCH_ENGINES) == {"pi", "legacy"}
    for bad in (None, "", "gpt", "  "):
        with pytest.raises(ValueError):
            normalize_engine(bad)


def test_resolve_engine_uses_explicit_value_over_flag(monkeypatch):
    monkeypatch.setattr("app.config.settings.agentic_core", True)
    assert resolve_engine("legacy") == "legacy"
    monkeypatch.setattr("app.config.settings.agentic_core", False)
    assert resolve_engine("pi") == "pi"


def test_resolve_engine_defaults_from_flag_when_unset(monkeypatch):
    monkeypatch.setattr("app.config.settings.agentic_core", True)
    assert resolve_engine(None) == "pi"
    assert resolve_engine("") == "pi"
    monkeypatch.setattr("app.config.settings.agentic_core", False)
    assert resolve_engine(None) == "legacy"


def test_resolve_engine_rejects_invalid_explicit_value():
    with pytest.raises(ValueError):
        resolve_engine("gpt-4")


# ── binding overrides the global flag at the dispatch site ───────────────


def test_bind_engine_overrides_flag_for_use_pi_engine(monkeypatch):
    runner = PersonaRunner()
    monkeypatch.setattr("app.config.settings.agentic_core", False)
    runner.bind_engine("pi")
    assert runner.use_pi_engine() is True  # per-experiment engine wins
    runner.bind_engine("legacy")
    assert runner.use_pi_engine() is False
    monkeypatch.setattr("app.config.settings.agentic_core", True)
    # An unbound runner still falls back to the global flag (prior behavior).
    assert PersonaRunner().use_pi_engine() is True


async def test_bound_pi_engine_routes_to_dispatcher_with_flag_off(monkeypatch):
    """The core of F-W6-2: a Pi experiment dispatches even with the flag OFF."""
    monkeypatch.setattr("app.config.settings.agentic_core", False)
    dispatcher = _StubAgentic(text="0.9")
    router = _StubRouter(text="0.1")
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher)
    monkeypatch.setattr("app.core.llm_router.llm_router", router)

    runner = PersonaRunner()
    runner.bind_project("proj-engine")
    runner.bind_engine("pi")
    score = await runner._score_response("x" * 50)

    assert score == pytest.approx(0.9)
    assert len(dispatcher.calls) == 1
    assert dispatcher.calls[0]["purpose"] == "autoresearch.persona.score"
    assert not router.calls, "legacy plane must not be touched for a pi experiment"


async def test_bound_legacy_engine_routes_to_llm_router_with_flag_on(monkeypatch):
    """The inverse: a legacy experiment stays on the legacy plane with flag ON."""
    monkeypatch.setattr("app.config.settings.agentic_core", True)
    dispatcher = _StubAgentic(text="0.9")
    router = _StubRouter(text="0.2")
    monkeypatch.setattr("app.core.agentic.agentic", dispatcher)
    monkeypatch.setattr("app.core.llm_router.llm_router", router)

    runner = PersonaRunner()
    runner.bind_engine("legacy")
    score = await runner._score_response("x" * 50)

    assert score == pytest.approx(0.2)
    assert len(router.calls) == 1
    assert not dispatcher.calls, "dispatcher must not be touched for a legacy experiment"


# ── run_loop threads + persists the engine ───────────────────────────────


class _EngineFakeRunner(BaseLoopRunner):
    loop_type = "model_temp"
    needs_persona_lock = False

    def __init__(self) -> None:
        self.engine_during_hypothesize: str | None = None

    async def measure_baseline(self, target):
        return 0.5

    async def measure(self, target):
        return 0.9

    async def hypothesize(self, target, current_score, history):
        # Record the effective engine the runner sees mid-loop.
        self.engine_during_hypothesize = self.engine
        return "hypothesis", {"description": "bump"}

    async def apply_mutation(self, target, mutation):
        async def _revert():
            return None

        return _revert


async def _run_one(monkeypatch, *, engine, flag):
    await init_db()
    from app.config import settings

    monkeypatch.setattr("app.config.settings.agentic_core", flag)
    settings.autoresearch_min_improvement_delta = 0.01
    settings.autoresearch_measurement_repeats = 1

    project_id = f"proj-engine-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Engine Select"))
        await db.commit()

    async def _allow(db, target):
        return True, ""

    persisted: list[dict] = []

    async def _fake_persist(self, experiment, project_id):
        persisted.append(experiment.copy())

    async def _noop(self, *a, **k):
        return []

    monkeypatch.setattr(
        "app.core.autoresearch_engine.check_experiment_limit", _allow
    )
    monkeypatch.setattr(AutoresearchEngine, "_persist_experiment", _fake_persist)
    monkeypatch.setattr(AutoresearchEngine, "_record_reasoning_memory", _noop)
    monkeypatch.setattr(AutoresearchEngine, "_register_improvement_proposals", _noop)

    async def _noop_telemetry(self, *a, **k):
        return None

    monkeypatch.setattr(
        AutoresearchEngine, "_record_validity_telemetry", _noop_telemetry
    )

    runner = _EngineFakeRunner()
    ar_engine = AutoresearchEngine()
    await ar_engine.run_loop(
        runner, target="skill-a", max_iterations=1, project_id=project_id, engine=engine
    )
    return runner, persisted


async def test_run_loop_threads_and_persists_explicit_engine(monkeypatch):
    # Explicit engine="pi" must win even though the global flag is OFF.
    runner, persisted = await _run_one(monkeypatch, engine="pi", flag=False)
    assert runner.engine_during_hypothesize == "pi"
    assert persisted and persisted[0]["engine"] == "pi"


async def test_run_loop_defaults_engine_from_flag(monkeypatch):
    # Unset engine + flag ON resolves to pi and is stamped on the experiment.
    runner, persisted = await _run_one(monkeypatch, engine=None, flag=True)
    assert runner.engine_during_hypothesize == "pi"
    assert persisted and persisted[0]["engine"] == "pi"
    # Unset engine + flag OFF resolves to legacy (prior behavior).
    runner2, persisted2 = await _run_one(monkeypatch, engine=None, flag=False)
    assert runner2.engine_during_hypothesize == "legacy"
    assert persisted2 and persisted2[0]["engine"] == "legacy"


# ── durable persistence + serialization ──────────────────────────────────


async def test_persist_experiment_writes_engine_column_and_snapshot(monkeypatch):
    await init_db()
    project_id = f"proj-persist-{uuid.uuid4().hex[:8]}"
    async with async_session() as db:
        db.add(Project(id=project_id, name="Persist Engine"))
        await db.commit()

    exp_id = str(uuid.uuid4())
    experiment = {
        "id": exp_id,
        "loop_type": "persona",
        "target_name": "agent-x",
        "engine": "pi",
        "status": "proposal_ready",
        "measurement_repeats": 1,
    }
    await AutoresearchEngine()._persist_experiment(experiment, project_id)

    reloaded = await AutoresearchEngine().get_experiment(exp_id)
    assert reloaded is not None
    assert reloaded["engine"] == "pi"
    assert reloaded["config_snapshot"]["engine"] == "pi"


async def test_experiment_to_dict_exposes_engine_and_allows_null():
    await init_db()
    row = AutoresearchExperiment(
        id=str(uuid.uuid4()),
        loop_type="model_temp",
        target_name="skill-a",
        engine=None,  # a pre-W6 row has an unknown engine
    )
    assert "engine" in row.to_dict()
    assert row.to_dict()["engine"] is None


# ── migration presence ───────────────────────────────────────────────────


def test_migration_025_adds_engine_column():
    from pathlib import Path

    migration = (
        Path(__file__).resolve().parents[2]
        / "backend/alembic/versions/025_autoresearch_experiment_engine.py"
    )
    text = migration.read_text(encoding="utf-8")
    assert 'down_revision = "024_project_agentic_engine"' in text
    assert "autoresearch_experiments" in text
    assert '"engine"' in text
