"""Measurement 4 grades retrieved chunks against the corpus the product ingested.

``answer_eval`` scores context precision and validates its judges on chunk relevance from the
span-graded qrels. It found a chunk's corpus file by path suffix only, and a file uploaded through
the product is stored under the upload directory by its file name, so every uploaded chunk graded 0.
"""

from __future__ import annotations

import json

import pytest


def _qrels(tmp_path):
    from app.evals.retrieval_eval import Qrels

    corpus = tmp_path / "corpus"
    (corpus / "sources" / "interviews").mkdir(parents=True)
    (corpus / "sources" / "interviews" / "p01.md").write_text(
        "## Exchange 1\n\nP1: I phone every client on Friday afternoon.\n", encoding="utf-8"
    )
    data = {
        "version": 1,
        "name": "t",
        "corpus": str(corpus),
        "corpus_glob": "sources/**/*",
        "theme_banks": {},
        "questions": [
            {
                "id": "q1",
                "style": "lexical",
                "theme": None,
                "text": "phone Friday",
                "targets": ["I phone every client on Friday afternoon."],
                "related_theme": None,
                "related": [],
            }
        ],
    }
    path = tmp_path / "q.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return Qrels.load(path)


def test_an_uploaded_file_maps_to_its_corpus_file(tmp_path):
    from app.evals.answer_eval import corpus_path_for

    qrels = _qrels(tmp_path)
    assert corpus_path_for(qrels, "/repo/tests/corpus/sources/interviews/p01.md") == (
        "sources/interviews/p01.md"
    )
    assert corpus_path_for(qrels, "/app/data/uploads/proj-1/p01.md") == "sources/interviews/p01.md"
    assert corpus_path_for(qrels, "/app/data/uploads/proj-1/other.md") is None


def test_an_uploaded_answer_chunk_gets_its_grade(tmp_path):
    from app.evals.answer_eval import corpus_path_for
    from app.evals.retrieval_eval import span_grade

    qrels = _qrels(tmp_path)
    chunk = "P1: I phone every client on Friday afternoon."
    rel = corpus_path_for(qrels, "/app/data/uploads/proj-1/p01.md")
    start = qrels.files[rel].find(chunk)
    assert span_grade(qrels, qrels.questions[0], rel, start, start + len(chunk)) == 2


def test_an_upload_stored_under_a_generated_name_maps_by_its_text(tmp_path):
    """Uploads are stored as ``<uuid>.md``: neither the path nor the name identifies the file."""
    from app.evals.answer_eval import corpus_path_for

    qrels = _qrels(tmp_path)
    chunk = "P1: I phone every client on Friday afternoon."
    source = "/app/data/uploads/proj-1/3f2a9c1e-6b1d-4a5e-9a51-2d1e0c7b9f10.md"
    assert corpus_path_for(qrels, source) is None
    assert corpus_path_for(qrels, source, chunk) == "sources/interviews/p01.md"
    assert corpus_path_for(qrels, source, "text that is in no corpus file") is None


def test_token_only_usage_is_priced_from_the_endpoint_rates(monkeypatch):
    """A chat turn reports tokens but no cost; the spend cap must still see it."""
    from app.config import PiApiEndpoint, settings
    from app.evals.answer_eval import usage_cost

    endpoint = PiApiEndpoint(
        endpoint_id="pi-priced",
        base_url="https://example.invalid/v1",
        model="m",
        keychain_service="svc",
        cost_input_per_mtok=0.1,
        cost_output_per_mtok=0.2,
    )
    monkeypatch.setattr(settings, "pi_api_endpoints", [endpoint])
    usage = {"input_tokens": 1_000_000, "output_tokens": 500_000}
    assert usage_cost("pi-priced", usage) == pytest.approx(0.2)
    assert usage_cost("pi-priced", {"cost_usd": 0.05}) == pytest.approx(0.05)
    assert usage_cost("pi-unknown", usage) == 0.0


def test_the_cli_stops_the_pi_worker_while_its_event_loop_still_runs(monkeypatch, tmp_path):
    # The dispatcher starts a Pi worker child. Left running, its pipes were torn down after
    # asyncio.run had closed the loop: "RuntimeError: Event loop is closed" on every live run.
    import asyncio

    from app.core import pi_runtime
    from app.evals import answer_eval

    loop_closed_at_shutdown: list[bool] = []

    async def _run(**kwargs):
        return {"questions": 0}

    async def _shutdown():
        loop_closed_at_shutdown.append(asyncio.get_running_loop().is_closed())

    monkeypatch.setattr(answer_eval, "run", _run)
    monkeypatch.setattr(pi_runtime, "shutdown_supervisor", _shutdown)
    out = tmp_path / "report.json"
    argv = ["--project-id", "p", "--generator", "a", "--judges", "b", "--out", str(out)]
    assert answer_eval.main(argv) == 0
    assert loop_closed_at_shutdown == [False]
    assert json.loads(out.read_text(encoding="utf-8")) == {"questions": 0}


def test_the_w3_harness_stops_the_pi_worker_while_its_event_loop_still_runs(monkeypatch, tmp_path):
    # Same defect in the live coding-run harness (qa/scripts/w3_live_ensemble.py), seen on the
    # live lane on 2026-09-26.
    import asyncio
    import sys

    from qa.scripts import w3_live_ensemble

    from app.core import pi_runtime

    loop_closed_at_shutdown: list[bool] = []

    async def _amain(args):
        return {"stages": {}}

    async def _shutdown():
        loop_closed_at_shutdown.append(asyncio.get_running_loop().is_closed())

    monkeypatch.setattr(w3_live_ensemble, "amain", _amain)
    monkeypatch.setattr(pi_runtime, "shutdown_supervisor", _shutdown)
    monkeypatch.setattr(sys, "argv", ["w3", "--stages", "E", "--out", str(tmp_path / "w3.json")])
    w3_live_ensemble.main()
    assert loop_closed_at_shutdown == [False]


def test_the_unreconciled_report_probe_is_judged_whichever_stage_runs_first():
    # Live lane, 2026-09-26: stages A-E in one call computed E after C, and P5 (a report refused
    # while applications are unreconciled) was left without a verdict although C had proven it.
    from qa.scripts import w3_live_ensemble

    gate_before = {"report_allowed": False, "reason": "Task has 9 unreconciled applications."}
    artifact = {
        "stages": {
            "C": {"gate_before": gate_before},
            "E": {
                "ok": True,
                "probes": [
                    {"id": "P1-missing-coder", "pass": True},
                    {"id": "P5-unreconciled-report", "note": "stage C"},
                ],
            },
        }
    }
    w3_live_ensemble.record_unreconciled_report_probe(artifact)
    p5 = artifact["stages"]["E"]["probes"][1]
    assert p5["pass"] is True and p5["gate_before"] == gate_before

    allowed = {
        "stages": {
            "C": {"gate_before": {"report_allowed": True}},
            "E": {"probes": [{"id": "P5-unreconciled-report"}]},
        }
    }
    w3_live_ensemble.record_unreconciled_report_probe(allowed)
    assert allowed["stages"]["E"]["probes"][0]["pass"] is False

    without_c = {"stages": {"E": {"probes": [{"id": "P5-unreconciled-report"}]}}}
    w3_live_ensemble.record_unreconciled_report_probe(without_c)
    assert "pass" not in without_c["stages"]["E"]["probes"][0]


# ── M4 v2 judge validation (DEC-14, pre-registered 2026-09-26) ──


def test_v2_planted_claims_hold_at_least_fifty_items_of_five_kinds():
    from app.evals.answer_eval import planted_claim_items
    from app.evals.retrieval_eval import DEFAULT_QRELS, Qrels

    qrels = Qrels.load(DEFAULT_QRELS)
    items = planted_claim_items(qrels, n=20, seed=20260926)
    kinds = {item["kind"] for item in items}
    assert len(items) >= 50
    assert kinds == {"verbatim", "first_sentence", "other_theme", "number_altered", "negated"}
    for item in items:
        if item["kind"] in ("verbatim", "first_sentence"):
            assert item["label"] is True and item["claim"] in item["context"]
        else:
            assert item["label"] is False and item["claim"] not in item["context"]


def test_v2_relevance_items_are_balanced_and_true_by_construction():
    from app.evals.answer_eval import construction_relevance_items
    from app.evals.retrieval_eval import DEFAULT_QRELS, Qrels

    qrels = Qrels.load(DEFAULT_QRELS)
    items = construction_relevance_items(qrels, n=20, seed=20260926)
    positives = [i for i in items if i["label"]]
    negatives = [i for i in items if not i["label"]]
    assert len(positives) == 20 and len(negatives) == 40
    by_text = {q.text: q for q in qrels.questions}
    for item in items:
        targets = by_text[item["question"]].targets
        assert any(t in item["passage"] for t in targets) is item["label"], item["kind"]
    assert {i["kind"] for i in negatives} == {"other_theme", "same_theme_related"}


class _FakeJudges:
    """A judge that is exact on claims and on 'contains the answer', and always says '1' on the
    three-level grade (so it fails the v1 relevance rule by construction)."""

    def __init__(self, qrels):
        self.judges = ["judge-a"]
        self._targets = {q.text: q.targets for q in qrels.questions}

    async def verify(self, judge, context, claims):
        return [claim in context for claim in claims]

    async def relevance(self, judge, question, chunk):
        return 1

    async def answer_bearing(self, judge, question, chunk):
        return any(t in chunk for t in self._targets.get(question, ()))


async def test_v2_trusts_a_judge_on_the_task_it_performs_and_reports_the_v1_rule():
    from app.evals.answer_eval import validate_judges
    from app.evals.retrieval_eval import DEFAULT_QRELS, Qrels

    qrels = Qrels.load(DEFAULT_QRELS)
    question = qrels.questions[0]
    run_pairs = [(question, "unrelated text", 0), (question, question.targets[0], 2)] * 6
    report = await validate_judges(_FakeJudges(qrels), qrels, run_pairs, seed=20260926)
    judge = report["judges"]["judge-a"]
    assert report["protocol"] == "v2"
    assert judge["claims"]["n"] >= 50 and judge["claims"]["kappa"] == 1.0
    assert judge["relevance_binary"]["kappa"] == 1.0 and judge["relevance_binary"]["n"] == 60
    assert judge["trusted"] is True
    assert judge["v1"]["trusted"] is False  # its 0/1/2 grades never match the qrels
