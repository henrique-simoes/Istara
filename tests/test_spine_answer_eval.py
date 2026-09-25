"""Measurement 4 grades retrieved chunks against the corpus the product ingested.

``answer_eval`` scores context precision and validates its judges on chunk relevance from the
span-graded qrels. It found a chunk's corpus file by path suffix only, and a file uploaded through
the product is stored under the upload directory by its file name, so every uploaded chunk graded 0.
"""

from __future__ import annotations

import json


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
