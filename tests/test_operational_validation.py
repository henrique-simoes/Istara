"""Operational validation under each assurance mode (CF-SPEC-1, Phase 3).

LLM validation functions and the decider client are replaced by recording fakes, so each test
asserts exactly which evaluators ran. ``decision_models`` and ``none`` must make no LLM-as-judge call;
``both`` keeps both halves side by side; ``auto`` without a policy behaves as before modes existed.
"""

import json
import random
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.core.adaptive_validation as adaptive
import app.core.decider.access as access
import app.models.database as database
import app.services.operational_validation as ov
from app.core.assurance import ProjectAssurance
from app.core.decider.contract import DecisionOutcome
from app.core.decider.registry import DeciderUnavailableError
from app.models.decision_trajectory import DecisionTrajectory, DecisionTrustEvaluation


class Recorder:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []
        self.outcomes: list[tuple] = []
        self.human: list[tuple] = []


def _fake_validation(recorder: Recorder, agreement: float = 0.8, fail: bool = False):
    def make(name):
        async def fn(**kwargs):
            recorder.calls.append((name, kwargs))
            if fail:
                raise RuntimeError("provider down")
            return SimpleNamespace(
                method=name,
                consensus=SimpleNamespace(
                    agreement_score=agreement, kappa=0.4, cosine_sim=0.9, confidence="medium"
                ),
                best_response="best",
                responses=["a", "b", "c"],
                metadata={"route_evidence": [], "models_used": ["m1"]},
            )

        return fn

    return {name: make(name) for name in adaptive.AVAILABLE_METHODS}


class FakeDecider:
    def __init__(self, endpoint_id: str, p: float):
        self.endpoint_id = endpoint_id
        self.p = p
        self.states: list = []

    async def decide(self, state, questions):
        self.states.append(state)
        return DecisionOutcome(
            status="ok",
            endpoint_id=self.endpoint_id,
            requested_model="kev-4b",
            served_model="kev-4b",
            answers={"acceptable": {"true": self.p, "false": 1.0 - self.p}},
            usage={"input_tokens": 50},
            latency_s=0.2,
        )


@pytest.fixture
async def env(monkeypatch):
    recorder = Recorder()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(DecisionTrajectory.__table__.create)
        await conn.run_sync(DecisionTrustEvaluation.__table__.create)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(database, "async_session", maker)
    monkeypatch.setattr(ov, "_validation_functions", lambda: _fake_validation(recorder))

    async def no_counts(self, *args):
        return {}

    async def compute_default(project_id):
        return "self_moa"

    async def record_outcome(self, *args):
        recorder.outcomes.append(args)

    async def record_human_outcome(self, *args):
        recorder.human.append(args)

    monkeypatch.setattr(adaptive.AdaptiveSelector, "_human_counts", no_counts)
    monkeypatch.setattr(adaptive, "_compute_aware_default_method", compute_default)
    monkeypatch.setattr(adaptive.AdaptiveSelector, "record_outcome", record_outcome)
    monkeypatch.setattr(adaptive.AdaptiveSelector, "record_human_outcome", record_human_outcome)

    deciders = {"kev": FakeDecider("kev", 0.85)}

    async def fake_open(endpoint_id, project_id, **kwargs):
        if endpoint_id not in deciders:
            raise DeciderUnavailableError("unknown_endpoint")
        return deciders[endpoint_id]

    monkeypatch.setattr(access, "open_decider", fake_open)
    yield SimpleNamespace(recorder=recorder, maker=maker, deciders=deciders)
    await engine.dispose()


async def _run(policy, **kwargs):
    return await ov.run_operational_validation(
        project_id="p1",
        skill_name="interview-synthesis",
        agent_id="istara-main",
        task_id="t1",
        task_text="Synthesize the interviews",
        candidate="Users struggle with onboarding.",
        policy=policy,
        **kwargs,
    )


async def test_decision_models_mode_makes_no_llm_judge_call(env):
    result = await _run(ProjectAssurance("decision_models", decider_endpoint_ids=("kev",)))
    assert env.recorder.calls == [] and env.recorder.outcomes == []
    assert result.validation_method == "decision_models" and result.consensus_score is None
    assert result.hook_payload is None
    [verdict] = result.deciders
    assert verdict["status"] == "ok" and verdict["p_acceptable"] == 0.85
    assert verdict["action"] == "shadow" and verdict["scope_trusted"] is False
    payload = result.result()
    assert payload["assurance_mode"] == "decision_models" and payload["llm"] is None
    assert env.deciders["kev"].states[0]["candidate_output"] == "Users struggle with onboarding."
    async with env.maker() as session:
        row = (await session.execute(select(DecisionTrajectory))).scalars().one()
    assert row.subject_kind == "task_output" and row.subject_id == "t1"
    assert row.question_set_id == "operational-output" and row.action == "shadow"


async def test_none_mode_runs_nothing_and_marks_the_task_unvalidated(env):
    result = await _run(ProjectAssurance("none", decider_endpoint_ids=("kev",)))
    assert env.recorder.calls == [] and result.deciders == []
    assert result.should_record
    task = SimpleNamespace(validation_method=None, validation_result=None, consensus_score=0.7)
    result.apply_to(task)
    assert task.validation_method == "unvalidated" and task.consensus_score is None
    stored = json.loads(task.validation_result)
    assert stored["status"] == "unvalidated" and stored["unvalidated_reason"] == "assurance_disabled"


async def test_decision_models_without_endpoints_is_explicitly_unvalidated(env):
    result = await _run(ProjectAssurance("decision_models"))
    assert env.recorder.calls == [] and result.should_record
    assert result.result()["unvalidated_reason"] == "no_decider_configured"


async def test_both_keeps_llm_and_decider_results_side_by_side(env):
    policy = ProjectAssurance(
        "both", llm_method="full_ensemble", llm_judges=5, decider_endpoint_ids=("kev", "missing")
    )
    result = await _run(policy)
    [(name, kwargs)] = env.recorder.calls
    assert name == "full_ensemble" and kwargs["min_responses"] == 5
    payload = result.result()
    assert payload["llm"]["actual_method"] == "full_ensemble"
    assert payload["agreement_score"] == 0.8  # older readers keep their top-level keys
    statuses = {d["endpoint_id"]: d["status"] for d in payload["deciders"]}
    assert statuses == {"kev": "ok", "missing": "not_runnable"}
    assert result.validation_method == "full_ensemble" and result.hook_payload is not None


async def test_auto_without_policy_behaves_as_before(env, monkeypatch):
    async def no_policy(project_id):
        return ProjectAssurance()

    monkeypatch.setattr(ov, "load_project_assurance", no_policy)
    result = await _run(None)
    [(name, _)] = env.recorder.calls
    assert name == "self_moa" and result.deciders == []
    assert env.recorder.outcomes[0][3] == "self_moa"
    assert result.result()["actual_method"] == "self_moa"


async def test_failed_llm_run_in_auto_leaves_the_task_untouched(env, monkeypatch):
    monkeypatch.setattr(
        ov, "_validation_functions", lambda: _fake_validation(env.recorder, fail=True)
    )
    result = await _run(ProjectAssurance())
    assert not result.should_record


async def test_task_review_labels_decider_trajectories_and_teaches_the_selector(env):
    await _run(ProjectAssurance("both", decider_endpoint_ids=("kev",)))
    event = SimpleNamespace(
        id="rev-1",
        outcome="needs_revision",
        project_id="p1",
        task_id="t1",
        skill_name="interview-synthesis",
        agent_id="istara-main",
        validation_method="self_moa",
        consensus_score=0.8,
    )
    await ov.record_assurance_review_signals(event)
    async with env.maker() as session:
        row = (await session.execute(select(DecisionTrajectory))).scalars().one()
    assert row.human_label == 0 and row.label_decision_id == "rev-1"
    # Self-MoA passed (0.8) an output the researcher sent back: it disagreed with the human.
    assert env.recorder.human == [("p1", "interview-synthesis", "istara-main", "self_moa", False)]

    env.recorder.human.clear()
    system = SimpleNamespace(**{**vars(event), "id": "rev-2", "outcome": "system_failed"})
    await ov.record_assurance_review_signals(system)
    assert env.recorder.human == []


async def test_selector_learns_only_from_human_outcomes_within_the_mode(monkeypatch):
    async def counts(self, *args):
        return {"self_moa": (5, 30), "full_ensemble": (30, 5)}

    async def compute_default(project_id):
        return "self_moa"

    monkeypatch.setattr(adaptive.AdaptiveSelector, "_human_counts", counts)
    monkeypatch.setattr(adaptive, "_compute_aware_default_method", compute_default)
    selector = adaptive.AdaptiveSelector()
    rng = random.Random(1)
    picks = [await selector.select_method("p1", rng=rng) for _ in range(50)]
    assert picks.count("full_ensemble") >= 48
    only = await selector.select_method("p1", allowed=["dual_run"], rng=rng)
    assert only == "dual_run"
    restricted = await selector.select_method("p1", allowed=["self_moa", "dual_run"], rng=rng)
    assert restricted == "self_moa"


async def test_evaluation_skill_skips_llm_judges_when_the_mode_excludes_them(monkeypatch):
    from unittest.mock import AsyncMock

    import app.skills.evaluation_skill as evaluation
    from app.skills.base import SkillInput

    async def decision_only(project_id):
        return ProjectAssurance("decision_models", decider_endpoint_ids=("kev",))

    adversarial = AsyncMock()
    ensemble = AsyncMock()
    monkeypatch.setattr(evaluation, "_project_assurance", decision_only)
    monkeypatch.setattr("app.core.validation.adversarial_review", adversarial)
    monkeypatch.setattr("app.core.validation.full_ensemble", ensemble)
    output = await evaluation.EvaluationSkill().execute(
        SkillInput(project_id="p1", user_context="Research output")
    )
    assert output.success and adversarial.await_count == 0 and ensemble.await_count == 0
    assert "Assurance mode**: decision_models" in output.artifacts["evaluation_report.md"]
