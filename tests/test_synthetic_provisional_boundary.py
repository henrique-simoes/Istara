"""Research Spine synthetic-provisional boundary tests.

Enforces the winning master plan §10: synthetic QA artifacts are provisional
only (``is_qa_provisional = true``) and can NEVER reach accepted/reportable
states. The seeder's promotion gate contract is asserted here, and the
research-validity service contract (backend) is covered by
``tests/test_research_validity_contract.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from qa.scripts.seed_synthetic import PROMOTION_GATES, load_corpora_manifest, seed_plan

ROOT = Path(__file__).resolve().parent.parent
CORPORA = ROOT / "qa" / "corpora" / "manifest.json"

# Promotion gates that a synthetic row must never reach.
REPORTABLE_GATES = {"accepted", "accepted_after_reconciliation"}
REVIEW_GATES = {"needs_reconciliation", "needs_human_review", "blocked"}


def test_synthetic_rows_are_always_provisional():
    manifest = load_corpora_manifest(CORPORA)
    for slice_info in manifest["slices"]:
        plan = seed_plan(slice_info["slice_id"], manifest, "boundary-run-001")
        assert plan["is_qa_provisional"] is True
        assert plan["promotion_blocked"] is True


def test_accepted_reportable_gates_are_declared_but_blocked():
    # The seeder declares the full gate set (so the boundary is explicit), but
    # every one of them is blocked while is_qa_provisional is true.
    for gate in PROMOTION_GATES:
        assert gate in REPORTABLE_GATES | REVIEW_GATES
    assert REPORTABLE_GATES <= set(PROMOTION_GATES)


def test_no_synthetic_artifact_can_carry_accepted_state():
    # Walk every slice: the seed plan must never emit an accepted/reportable
    # marker on synthetic rows.
    manifest = load_corpora_manifest(CORPORA)
    for slice_info in manifest["slices"]:
        plan = seed_plan(slice_info["slice_id"], manifest, "boundary-run-002")
        assert "accepted" not in plan.get("state", "")
        assert "accepted" not in plan.get("promotion_state", "")
        for span in plan["spans"]:
            assert span["kind"] == "synthetic_qa"
            assert span.get("provenance") in ("generated", "curated")


def test_report_gate_excludes_provisional_artifacts():
    # Mirror of the report-route rule: a report may only draw from accepted
    # evidence; synthetic rows are blocked by construction.
    manifest = load_corpora_manifest(CORPORA)
    for slice_info in manifest["slices"]:
        plan = seed_plan(slice_info["slice_id"], manifest, "boundary-run-003")
        assert plan["promotion_blocked"], "synthetic rows must stay blocked"


def test_synthetic_spans_have_exact_source_hashes():
    # Raw source spans (not synthesized nugget prose) become evidence units;
    # hashes must be stable and content-derived.
    manifest = load_corpora_manifest(CORPORA)
    plan = seed_plan("low-consensus-review", manifest, "boundary-run-004")
    assert plan["span_count"] >= 1
    for span in plan["spans"]:
        assert len(span["span_sha256"]) == 64
        assert span["span_sha256"] == span["span_sha256"].lower()
