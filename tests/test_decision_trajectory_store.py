"""Decision trajectory persistence, human labels and stored trust (CF-SPEC-1, Phase 2).

In-memory SQLite. Trajectories hold handles and numbers only; labels come only from human review;
a scope is trusted only after a passing evaluation, otherwise it stays in shadow mode.
"""

import math
import random
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.decider.contract import DecisionOutcome
from app.models.decision_trajectory import DecisionTrajectory, DecisionTrustEvaluation
from app.services.decision_trajectories import (
    attach_human_label,
    evaluate_scope,
    record_trajectory,
    scope_is_trusted,
)

POSITIVE = frozenset({"supports"})


async def _maker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(DecisionTrajectory.__table__.create)
        await conn.run_sync(DecisionTrustEvaluation.__table__.create)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


def _outcome(p_supports: float, status: str = "ok") -> DecisionOutcome:
    rest = (1.0 - p_supports) / 2.0
    return DecisionOutcome(
        status=status,
        reason=None if status == "ok" else "timeout",
        endpoint_id="jev",
        requested_model="jev-1.13.0",
        served_model="jev-1.13.0" if status == "ok" else None,
        answers={"relation": {"supports": p_supports, "contradicts": rest, "says_nothing": rest}}
        if status == "ok"
        else {},
        usage={"input_tokens": 90},
        latency_s=0.4,
    )


async def _record(session, subject_id: str, p: float, *, routed: bool = True, status="ok"):
    return await record_trajectory(
        session,
        outcome=_outcome(p, status),
        project_id="p1",
        subject_kind="code_application",
        subject_id=subject_id,
        question_set_id="code-application-triage",
        question_set_version="1",
        question_id="relation",
        positive_outcomes=POSITIVE,
        task_family="deductive_coding",
        language="en",
        routed=routed,
    )


def _decision(subject_id: str, decision_type: str, source: str = "human_review"):
    return SimpleNamespace(
        id=f"rd-{subject_id}",
        project_id="p1",
        code_application_id=subject_id,
        decision_type=decision_type,
        source=source,
    )


async def test_trajectory_is_content_free_and_scoped():
    engine, maker = await _maker()
    try:
        async with maker() as session:
            row = await _record(session, "ca-1", 0.8)
            assert row.status == "ok" and row.served_model == "jev-1.13.0"
            assert row.raw_distribution()["supports"] == 0.8
            assert row.latency_ms == 400 and row.input_tokens == 90
            assert len(row.scope_key) == 32 and row.action == "shadow"
            text_columns = [
                c.name for c in DecisionTrajectory.__table__.columns if "text" in c.name.lower()
            ]
            assert text_columns == []
            failed = await _record(session, "ca-2", 0.5, status="not_runnable")
            assert failed.status == "not_runnable" and failed.reason == "timeout"
            assert failed.served_model == "jev-1.13.0"  # falls back to the requested identity
    finally:
        await engine.dispose()


async def test_only_human_review_labels_trajectories():
    engine, maker = await _maker()
    try:
        async with maker() as session:
            await _record(session, "ca-1", 0.9)
            await _record(session, "ca-2", 0.2)
            await _record(session, "ca-3", 0.6, status="not_runnable")
            assert await attach_human_label(session, _decision("ca-1", "accepted", "synthetic")) == 0
            assert await attach_human_label(session, _decision("ca-1", "needs_human_review")) == 0
            assert await attach_human_label(session, _decision("ca-1", "accepted")) == 1
            assert await attach_human_label(session, _decision("ca-2", "revised")) == 1
            assert await attach_human_label(session, _decision("ca-3", "accepted")) == 0
            rows = {
                r.subject_id: r
                for r in (await session.execute(select(DecisionTrajectory))).scalars().all()
            }
            assert rows["ca-1"].human_label == 1 and rows["ca-1"].label_decision_id == "rd-ca-1"
            assert rows["ca-2"].human_label == 0 and rows["ca-2"].label_mapping_version == "v1"
            assert rows["ca-3"].human_label is None
            # A second human decision does not relabel history.
            assert await attach_human_label(session, _decision("ca-1", "rejected")) == 0
    finally:
        await engine.dispose()


async def test_scope_without_evaluation_is_shadow_then_trusted_when_calibrated():
    engine, maker = await _maker()
    rng = random.Random(11)
    try:
        async with maker() as session:
            key = None
            for i in range(400):
                z = rng.gauss(0.0, 4.0)
                p = 1.0 / (1.0 + math.exp(-z))
                row = await _record(session, f"ca-{i}", p)
                key = row.scope_key
                decision_type = "accepted" if rng.random() < p else "rejected"
                await attach_human_label(session, _decision(f"ca-{i}", decision_type))
            assert await scope_is_trusted(session, key) is False
            report = await evaluate_scope(session, key)
            assert report.trusted, report.reasons
            assert await scope_is_trusted(session, key) is True
            stored = (await session.execute(select(DecisionTrustEvaluation))).scalars().one()
            assert stored.labelled_count == 400 and stored.reasons() == []
    finally:
        await engine.dispose()


async def test_unlabelled_route_items_without_known_inclusion_are_excluded():
    engine, maker = await _maker()
    try:
        async with maker() as session:
            key = None
            for i in range(30):
                row = await _record(session, f"ca-{i}", 0.9, routed=False)
                key = row.scope_key
                await attach_human_label(session, _decision(f"ca-{i}", "accepted"))
            report = await evaluate_scope(session, key)
            # Only audit-sampled ones (about 10%) count; the rest reached a human by other means.
            assert report.reasons == ["insufficient_labelled_data"]
            assert report.metrics["n"] < 30
    finally:
        await engine.dispose()
