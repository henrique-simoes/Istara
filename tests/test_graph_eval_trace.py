"""G1 evidence-graph traceability: every seeded fault shows up in the metric meant to catch it.

Plan: docs/build-stream/2026-09-26-graph-quality-measurement.md (acceptance 1). The fixture is a
small, correct graph (two documents, units, nuggets quoting them, a fact, an insight and a
recommendation, grounding and coding edges); each test breaks one thing and checks that only the
metric for that fault moves.
"""

from __future__ import annotations

import copy
from types import SimpleNamespace as Row

from app.evals.graph_eval import GraphSnapshot, find_cycles, normalise, trace_metrics

P = "proj-g1"
DOC_A = "Interviewer: Where do receipts go?\n\nP1: The receipt is in my apron pocket, then the van."
DOC_B = "P2: Payroll runs Thursday night and client money lands on Friday."


def _edge(src_type, src, rel, tgt_type, tgt, project=P):
    return Row(
        project_id=project,
        source_type=src_type,
        source_id=src,
        relation=rel,
        target_type=tgt_type,
        target_id=tgt,
    )


def _rows():
    return {
        "documents": [Row(id="doc-a", content_text=DOC_A), Row(id="doc-b", content_text=DOC_B)],
        "units": [
            Row(id="u1", source_text="The receipt is in my apron pocket, then the van."),
            Row(id="u2", source_text=DOC_B.removeprefix("P2: ")),
        ],
        "nuggets": [
            Row(id="n1", text="The receipt is in my apron pocket, then the van."),
            Row(id="n2", text="Payroll runs Thursday night"),
        ],
        "facts": [Row(id="f1", nugget_ids='["n1", "n2"]')],
        "insights": [Row(id="i1", fact_ids='["f1"]')],
        "recommendations": [Row(id="r1", insight_ids='["i1"]')],
        "code_applications": [Row(evidence_unit_id="u1", source_text="apron pocket")],
        "edges": [
            _edge("document", "doc-a", "contains", "evidence_unit", "u1"),
            _edge("document", "doc-b", "contains", "evidence_unit", "u2"),
            _edge("nugget", "n1", "grounded_in", "evidence_unit", "u1"),
            _edge("nugget", "n2", "grounded_in", "evidence_unit", "u2"),
        ],
    }


def _metrics(rows):
    return trace_metrics(GraphSnapshot(rows), P)


def test_a_correct_graph_traces_fully():
    m = _metrics(_rows())
    assert m["nugget_span_fidelity"]["share"] == 1.0
    assert m["nugget_grounded"]["share"] == 1.0
    assert m["code_application_quote_fidelity"]["share"] == 1.0
    assert m["link_validity"]["share"] == 1.0
    assert m["edge_validity"]["share"] == 1.0
    assert m["chain_completeness"]["recommendations"]["share"] == 1.0
    assert m["cycles"] == 0


def test_a_paraphrased_nugget_loses_span_fidelity():
    rows = _rows()
    rows["nuggets"][1].text = "Payroll happens late in the week"
    m = _metrics(rows)
    assert m["nugget_span_fidelity"]["share"] == 0.5
    # Its grounded_in unit still quotes the source, so the chain stays traceable.
    assert m["nugget_grounded"]["share"] == 1.0


def test_a_deleted_unit_breaks_grounding_and_edge_validity():
    rows = _rows()
    rows["units"] = rows["units"][:1]
    m = _metrics(rows)
    assert m["nugget_grounded"]["share"] == 0.5
    assert m["edge_validity"]["share"] < 1.0


def test_a_dangling_id_breaks_link_validity_and_an_ungrounded_chain_breaks_completeness():
    rows = _rows()
    rows["facts"][0].nugget_ids = '["missing-nugget"]'
    m = _metrics(rows)
    assert m["link_validity"]["share"] < 1.0
    assert m["chain_completeness"]["facts"]["share"] == 0.0
    assert m["chain_completeness"]["recommendations"]["share"] == 0.0


def test_a_cross_project_edge_is_invalid():
    rows = _rows()
    stray = _edge("nugget", "n1", "grounded_in", "evidence_unit", "u2", project="other")
    rows["edges"].append(stray)
    assert _metrics(rows)["edge_validity"]["share"] < 1.0


def test_a_quote_that_is_not_in_its_unit_is_caught():
    rows = _rows()
    rows["code_applications"][0].source_text = "shoebox under the counter"
    assert _metrics(rows)["code_application_quote_fidelity"]["share"] == 0.0


def test_a_cycle_is_counted():
    rows = copy.deepcopy(_rows())
    rows["edges"].append(_edge("evidence_unit", "u1", "derived_from", "nugget", "n1"))
    assert _metrics(rows)["cycles"] == 1
    assert find_cycles([("a", "b"), ("b", "c")]) == 0


def test_containment_ignores_case_and_whitespace_runs():
    assert normalise("The  receipt\nis") == "the receipt is"
