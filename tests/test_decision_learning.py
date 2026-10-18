"""The decision-model learning loop and decision-model health (CF-SPEC-1, Phase 5).

Trust is re-evaluated only when enough new human labels arrive; drift sends a trusted scope back to
shadow mode; every evaluation leaves a content-free process lesson; the health report puts decision
models and LLM judges on one error model. File-backed SQLite, no services.
"""

import json
import math
import random

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.core.reasoning_bank as reasoning_bank_module
import app.models.database as database
from app.core.decider.contract import DecisionOutcome
from app.models.decision_trajectory import DecisionTrustEvaluation
from app.models.method_metric import MethodMetric
from app.models.task import Task
from app.services import decision_learning
from app.services.decision_health import decision_model_health
from app.services.decision_trajectories import label_subject, record_trajectory


@pytest.fixture
async def maker(monkeypatch, tmp_path):
    database.register_models()
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'learning.db'}", connect_args={"timeout": 30}
    )
    async with engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(database, "async_session", factory)
    lessons = []

    async def record_memory(**kwargs):
        lessons.append(kwargs)

    monkeypatch.setattr(reasoning_bank_module.reasoning_bank, "record_memory", record_memory)
    factory.lessons = lessons
    yield factory
    await engine.dispose()


def _sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))


async def _labelled(factory, n, seed, *, subject_kind="task_output", flip_labels=False):
    rng = random.Random(seed)
    key = None
    async with factory() as session:
        for i in range(n):
            z = rng.gauss(0.0, 4.0)
            p = _sigmoid(z)
            label = int(rng.random() < p)
            if flip_labels:
                label = 1 - label
            outcome = DecisionOutcome(
                status="ok",
                endpoint_id="kev",
                requested_model="kev-4b",
                served_model="kev-4b",
                answers={"acceptable": {"true": p, "false": 1 - p}},
            )
            subject = f"{seed}-{i}"
            row = await record_trajectory(
                session,
                outcome=outcome,
                project_id="p1",
                subject_kind=subject_kind,
                subject_id=subject,
                task_id=subject,
                question_set_id="operational-output",
                question_set_version="1",
                question_id="acceptable",
                positive_outcomes=frozenset({"true"}),
                task_family="operational_validation",
                language="und",
                routed=False,  # shadow mode: blind labels (DEC-21)
            )
            key = row.scope_key
            await label_subject(
                session,
                project_id="p1",
                subject_kind=subject_kind,
                subject_id=subject,
                label=label,
                source_id=f"rev-{subject}",
            )
        await session.commit()
    return key


async def test_first_evaluation_waits_for_enough_labels_and_leaves_a_lesson(maker):
    key = await _labelled(maker, 30, seed=1)
    async with maker() as session:
        assert await decision_learning.reevaluate_scope_if_due(session, "p1", key) == "not_due"
    await _labelled(maker, 170, seed=2)
    async with maker() as session:
        assert await decision_learning.reevaluate_scope_if_due(session, "p1", key) == "evaluated"
        evaluation = (await session.execute(select(DecisionTrustEvaluation))).scalars().one()
    assert evaluation.trusted, evaluation.reasons()
    [lesson] = maker.lessons
    assert lesson["source_kind"] == "decision_review" and lesson["project_id"] == "p1"
    body = json.loads(lesson["content"])
    assert body["scope_key"] == key and body["trusted"] is True
    allowed = {"scope_key", "trusted", "effective_n", "held_out_ece", "held_out_brier", "kappa"}
    assert set(body) <= allowed | {"order_flip_rate"}
    async with maker() as session:
        assert await decision_learning.reevaluate_scope_if_due(session, "p1", key) == "not_due"


async def test_drift_returns_a_trusted_scope_to_shadow(maker):
    key = await _labelled(maker, 200, seed=3)
    async with maker() as session:
        assert await decision_learning.reevaluate_scope_if_due(session, "p1", key) == "evaluated"
    await _labelled(maker, 60, seed=4, flip_labels=True)  # the decider is now wrong
    async with maker() as session:
        assert await decision_learning.reevaluate_scope_if_due(session, "p1", key) == "drifted"
        rows = (
            await session.execute(
                select(DecisionTrustEvaluation).order_by(DecisionTrustEvaluation.evaluated_at)
            )
        ).scalars().all()
    assert rows[-1].trusted is False and rows[-1].reasons() == ["calibration_drift"]


async def test_reevaluation_hook_never_raises(monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("database gone")

    monkeypatch.setattr(database, "async_session", boom)
    assert await decision_learning.reevaluate_subject_scopes_safely("p1", "task_output", "t") == {}


async def test_health_report_puts_deciders_and_llm_judges_on_one_error_model(maker):
    await _labelled(maker, 40, seed=5)
    async with maker() as session:
        from app.models.decision_trajectory import DecisionTrajectory

        rows = (await session.execute(select(DecisionTrajectory))).scalars().all()
        for row in rows:
            agreement = 0.9 if row.human_label == 1 else 0.2
            session.add(
                Task(
                    id=row.subject_id,
                    project_id="p1",
                    title="t",
                    validation_result=json.dumps(
                        {"llm": {"actual_method": "self_moa", "agreement_score": agreement}}
                    ),
                )
            )
        session.add(
            MethodMetric(
                id="m1",
                project_id="p1",
                method="self_moa",
                human_agree_count=8,
                human_disagree_count=2,
            )
        )
        await session.commit()
        report = await decision_model_health(session, "p1")
    [scope] = report["scopes"]
    assert scope["labelled"] == 40 and scope["trusted"] is False
    assert scope["reasons"] == ["not_evaluated"]
    assert report["llm_methods"] == [
        {"method": "self_moa", "human_agree": 8, "human_disagree": 2, "human_accuracy": 0.8}
    ]
    errors = report["error_structure"]
    assert errors["evaluators"] == ["decider:kev", "llm:self_moa"]
    assert errors["accuracy_vs_human"]["llm:self_moa"] == 1.0
    assert errors["labelled_items"] == 40
    assert all(key not in json.dumps(report) for key in ("Participant", "quote"))


async def test_protected_decider_terms_need_governed_review():
    from app.core.self_evolution import _requires_governed_research_review

    assert _requires_governed_research_review("Lower the decider trust gate ECE ceiling")
    assert _requires_governed_research_review("Skip calibration for the decision model")
    assert not _requires_governed_research_review("Prefer shorter prompts for decision models")
