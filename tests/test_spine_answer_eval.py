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
