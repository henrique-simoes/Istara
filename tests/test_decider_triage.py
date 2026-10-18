"""Decision-model triage at the Research Spine seam (CF-SPEC-1, Phase 4).

The guard test is the point: a trusted decider that flags every application must leave every
acceptance, reliability, reconciliation and review state, and the run's kappa and matrix, exactly as
the coding run committed them. Triage only records verdicts and marks items for priority review.
"""

import json
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.core.decider.access as access
import app.models.database as database
from app.core.assurance import ProjectAssurance
from app.core.decider.contract import DecisionOutcome
from app.core.decision.labels import LABEL_MAPPING_VERSION
from app.core.decision.sampling import scope_key
from app.models.code_application import CodeApplication
from app.models.decision_trajectory import DecisionTrajectory, DecisionTrustEvaluation
from app.models.research_validity import CodingRun, EvidenceUnit
from app.services import decider_triage
from app.services.decision_trajectories import label_after_reconciliation, routed_triage

POLICY = ProjectAssurance("decision_models", decider_endpoint_ids=("kev",))
STATE_FIELDS = ("promotion_status", "reliability_status", "reconciliation_status", "review_status")


class FakeDecider:
    """Answers by the coder's quote: quote -> (forward distribution, reversed distribution)."""

    def __init__(self, answers):
        self.answers = answers

    async def decide(self, state, questions):
        forward, reversed_ = self.answers[state["coder_quote"]]
        return DecisionOutcome(
            status="ok",
            endpoint_id="kev",
            requested_model="kev-4b",
            served_model="kev-4b",
            answers={"relation": forward, "relation__reversed": reversed_},
        )


def _dist(supports, contradicts, says_nothing):
    return {"supports": supports, "contradicts": contradicts, "says_nothing": says_nothing}


@pytest.fixture
async def maker(monkeypatch, tmp_path):
    # A file, not :memory:: triage opens concurrent sessions, and every :memory: connection would
    # get its own empty database.
    database.register_models()
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path / 'triage.db'}", connect_args={"timeout": 30}
    )
    async with engine.begin() as conn:
        await conn.run_sync(database.Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(database, "async_session", factory)
    yield factory
    await engine.dispose()


async def _seed(factory, quotes, statuses=("accepted", "needs_reconciliation")):
    run_id = str(uuid.uuid4())
    async with factory() as session:
        session.add(
            CodingRun(
                id=run_id,
                project_id="p1",
                status="completed",
                kappa=0.71,
                matrix_json=json.dumps({"u1": {"a": "pain"}}),
                promotion_status="accepted",
            )
        )
        for index, quote in enumerate(quotes):
            unit_id = str(uuid.uuid4())
            session.add(
                EvidenceUnit(
                    id=unit_id,
                    project_id="p1",
                    stable_id=f"u{index}",
                    source_text=f"Participant said: {quote} and more context.",
                )
            )
            status = statuses[index % len(statuses)]
            session.add(
                CodeApplication(
                    id=f"ca-{index}",
                    project_id="p1",
                    code_id="pain_point",
                    evidence_unit_id=unit_id,
                    coding_run_id=run_id,
                    source_text=quote,
                    promotion_status=status,
                    reliability_status=status,
                    reconciliation_status="unreconciled",
                    review_status="pending",
                )
            )
        await session.commit()
    return run_id


async def _trust(factory, temperature=1.0):
    key = scope_key(
        project_id="p1",
        provider="kev",
        served_model="kev-4b",
        question_set_id=decider_triage.QUESTION_SET_ID,
        question_set_version=decider_triage.QUESTION_SET_VERSION,
        task_family=decider_triage.TASK_FAMILY,
        language=decider_triage.UNDETERMINED_LANGUAGE,
        label_mapping_version=LABEL_MAPPING_VERSION,
    )
    async with factory() as session:
        session.add(
            DecisionTrustEvaluation(
                scope_key=key,
                trusted=True,
                metrics_json=json.dumps({"median_temperature": temperature}),
            )
        )
        await session.commit()


def _use(monkeypatch, decider):
    async def fake_open(endpoint_id, project_id, **kwargs):
        return decider

    monkeypatch.setattr(access, "open_decider", fake_open)


async def _snapshot(factory, run_id):
    async with factory() as session:
        apps = (await session.execute(select(CodeApplication))).scalars().all()
        run = await session.get(CodingRun, run_id)
        return (
            {a.id: tuple(getattr(a, f) for f in STATE_FIELDS) for a in apps},
            (run.kappa, run.matrix_json, run.promotion_status, run.status),
        )


async def test_guard_triage_never_changes_spine_state(maker, monkeypatch):
    quotes = [f"quote {i}" for i in range(6)]
    run_id = await _seed(maker, quotes)
    await _trust(maker)
    flag_all = {q: (_dist(0.01, 0.01, 0.98), _dist(0.01, 0.01, 0.98)) for q in quotes}
    _use(monkeypatch, FakeDecider(flag_all))
    before = await _snapshot(maker, run_id)
    summary = await decider_triage.triage_coding_run("p1", run_id, policy=POLICY)
    assert summary["counts"] == {"flag": 6}
    assert await _snapshot(maker, run_id) == before


async def test_untrusted_scope_is_shadow_and_never_shown(maker, monkeypatch):
    run_id = await _seed(maker, ["q"])
    _use(monkeypatch, FakeDecider({"q": (_dist(0.0, 0.0, 1.0), _dist(0.0, 0.0, 1.0))}))
    summary = await decider_triage.triage_coding_run("p1", run_id, policy=POLICY)
    assert summary["counts"] == {"shadow": 1}, summary
    async with maker() as session:
        row = (await session.execute(select(DecisionTrajectory))).scalars().one()
        assert row.action == "shadow" and not row.routed and row.order_flip_agree is True
        assert await routed_triage(session, "p1", ["ca-0"]) == {}


async def test_trusted_actions_follow_tau_and_order_flip(maker, monkeypatch):
    answers = {
        "clear support": (_dist(0.97, 0.01, 0.02), _dist(0.96, 0.02, 0.02)),
        "unsupported": (_dist(0.02, 0.03, 0.95), _dist(0.03, 0.02, 0.95)),
        "uncertain": (_dist(0.6, 0.1, 0.3), _dist(0.62, 0.1, 0.28)),
        "position bias": (_dist(0.7, 0.1, 0.2), _dist(0.2, 0.1, 0.7)),
    }
    run_id = await _seed(maker, list(answers))
    await _trust(maker)
    _use(monkeypatch, FakeDecider(answers))
    summary = await decider_triage.triage_coding_run("p1", run_id, policy=POLICY)
    assert "error" not in summary["counts"], summary
    async with maker() as session:
        rows = (await session.execute(select(DecisionTrajectory))).scalars().all()
        by_app = {r.subject_id: r for r in rows}
        actions = {app_id: by_app[app_id].action for app_id in by_app}
        assert actions == {"ca-0": "none", "ca-1": "flag", "ca-2": "abstain", "ca-3": "abstain"}
        assert by_app["ca-3"].order_flip_agree is False
        assert by_app["ca-0"].tau == pytest.approx(0.9) and not by_app["ca-0"].routed
        shown = await routed_triage(session, "p1", ["ca-0", "ca-1", "ca-2", "ca-3"])
    assert set(shown) == {"ca-1", "ca-2", "ca-3"}
    assert shown["ca-1"]["action"] == "flag" and shown["ca-1"]["top_outcome"] == "says_nothing"


async def test_inactive_modes_and_the_per_run_bound(maker, monkeypatch):
    run_id = await _seed(maker, ["a", "b", "c"])
    _use(monkeypatch, FakeDecider({q: (_dist(1, 0, 0), _dist(1, 0, 0)) for q in "abc"}))
    for policy in (ProjectAssurance("llm_judges", decider_endpoint_ids=("kev",)), ProjectAssurance()):
        summary = await decider_triage.triage_coding_run("p1", run_id, policy=policy)
        assert summary.get("inactive") is True
    bounded = await decider_triage.triage_coding_run("p1", run_id, policy=POLICY, max_items=2)
    assert bounded["skipped"] == 1 and bounded["counts"] == {"shadow": 2}


async def test_reconciliation_labels_only_human_reviews(maker, monkeypatch):
    run_id = await _seed(maker, ["q"])
    _use(monkeypatch, FakeDecider({"q": (_dist(0.9, 0.05, 0.05), _dist(0.9, 0.05, 0.05))}))
    await decider_triage.triage_coding_run("p1", run_id, policy=POLICY)

    class Decision:
        def __init__(self, source):
            self.id, self.project_id, self.code_application_id = "rd-1", "p1", "ca-0"
            self.decision_type, self.source = "rejected", source

    assert await label_after_reconciliation(Decision("synthetic_benchmark")) == 0
    assert await label_after_reconciliation(Decision("human_review")) == 1
    async with maker() as session:
        row = (await session.execute(select(DecisionTrajectory))).scalars().one()
    assert row.human_label == 0 and row.label_decision_id == "rd-1"


async def test_safe_hook_never_raises(monkeypatch):
    async def boom(*args, **kwargs):
        raise RuntimeError("decider exploded")

    monkeypatch.setattr(decider_triage, "triage_coding_run", boom)
    assert await decider_triage.triage_coding_run_safely("p1", "run") is None
