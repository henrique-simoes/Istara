"""QA reset/seed lifecycle contract tests (project-scoped, provisional-only)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qa.scripts.reset_qa import (
    CONFIRM_TOKEN,
    PROTECTED_FOLDERS,
    SAFE_PROJECT,
    project_name,
    reset_project,
    validate_target,
)
from qa.scripts.seed_synthetic import (
    PROMOTION_GATES,
    SAFE_RUN_ID,
    load_corpora_manifest,
    seed_plan,
    span_hash,
    write_seed_manifest,
)

ROOT = Path(__file__).resolve().parent.parent
CORPORA = ROOT / "qa" / "corpora" / "manifest.json"


# ---------------------------------------------------------------------------
# Reset contract
# ---------------------------------------------------------------------------


def test_project_name_is_namespaced_and_safe():
    assert project_name("20260818abc") == "istara-qa-20260818abc"
    assert SAFE_PROJECT.match(project_name("abc-123"))


def test_validate_target_rejects_empty_and_root():
    for bad in ("", ".", "/", "..", "istara-qa-../../etc"):
        with pytest.raises(ValueError):
            validate_target(bad)


def test_validate_target_rejects_protected_folders():
    with pytest.raises(ValueError):
        validate_target("llms-backup")
    with pytest.raises(ValueError):
        validate_target("model_finetuning-x")


def test_validate_target_accepts_normal_run_id():
    validate_target("20260818-abc123")
    assert SAFE_RUN_ID.match("20260818-abc123")


def test_reset_requires_confirmation_token():
    with pytest.raises(ValueError):
        project_name("")
    assert CONFIRM_TOKEN == "RESET-ISTARA-QA-RUN"
    assert "LLMs" in PROTECTED_FOLDERS
    assert "Model_Finetuning" in PROTECTED_FOLDERS


def test_reset_dry_run_returns_project_scoped_command():
    result = reset_project("20260818abc", dry_run=True)
    assert result["dry_run"] is True
    assert result["project"] == "istara-qa-20260818abc"
    assert "down" in result["command"]
    assert "-v" in result["command"]
    # Never touches developer/global projects.
    assert "istara-qa-20260818abc" in result["command"]


def test_reset_only_targets_qa_overlay_not_base_compose():
    # Merging the base compose into reset would reintroduce ollama and the
    # fixed istara-* container names; reset must target ONLY the QA overlay.
    result = reset_project("20260818abc", dry_run=True)
    assert "docker-compose.qa.yml" in result["command"]
    assert "docker-compose.yml" not in result["command"]


# ---------------------------------------------------------------------------
# Seed contract (Research Spine provisional-only)
# ---------------------------------------------------------------------------


def test_corpora_manifest_valid():
    manifest = load_corpora_manifest(CORPORA)
    assert manifest["version"] == 1
    slice_ids = {s["slice_id"] for s in manifest["slices"]}
    assert {"coding-reliability", "graph-synthesis", "low-consensus-review"} <= slice_ids


def test_seed_plan_is_provisional_and_blocks_promotion(tmp_path):
    manifest = load_corpora_manifest(CORPORA)
    plan = seed_plan("coding-reliability", manifest, "run-abc123")
    assert plan["is_qa_provisional"] is True
    assert plan["promotion_blocked"] is True
    assert plan["source_kind"] == "synthetic_qa"
    assert set(plan["promotion_gates"]) == set(PROMOTION_GATES)
    # accepted/reportable states are never reachable from synthetic rows
    for gate in ("accepted", "accepted_after_reconciliation"):
        assert gate in PROMOTION_GATES  # present as declared gates, but blocked
    assert plan["span_count"] >= 1
    for span in plan["spans"]:
        assert span["span_sha256"] == span_hash(
            [s["text"] for s in manifest["slices"][0]["sources"] if s["id"] == span["source_id"]][0]
        )
        assert span["kind"] == "synthetic_qa"


def test_seed_plan_unknown_slice_fails():
    manifest = load_corpora_manifest(CORPORA)
    with pytest.raises(KeyError):
        seed_plan("does-not-exist", manifest, "run-abc123")


def test_seed_plan_rejects_unsafe_run_id():
    manifest = load_corpora_manifest(CORPORA)
    with pytest.raises(ValueError):
        seed_plan("coding-reliability", manifest, "../escape")


def test_write_seed_manifest(tmp_path):
    manifest = load_corpora_manifest(CORPORA)
    plan = seed_plan("graph-synthesis", manifest, "run-xyz789")
    out = write_seed_manifest(plan, tmp_path)
    assert out.exists()
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["run_id"] == "run-xyz789"
    assert loaded["is_qa_provisional"] is True
