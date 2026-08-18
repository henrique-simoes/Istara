"""Feature-obligation classifier contract tests (fail-closed)."""

from __future__ import annotations

import json

import pytest

from scripts.check_feature_obligations import (
    CAPABILITIES,
    REGISTRY,
    _inline_list,
    _parse_scalar,
    build_report,
    classify_path,
    load_capabilities,
    load_registry,
    parse_registry,
    path_matches,
)

REGISTRY_TEXT = (REGISTRY.parent.parent / "testing" / "feature_coverage.yml").read_text(
    encoding="utf-8"
)


# ---------------------------------------------------------------------------
# Registry parser
# ---------------------------------------------------------------------------


def test_parse_registry_schema_and_features():
    registry = parse_registry(REGISTRY_TEXT)
    assert registry["schema_version"] == 1
    assert isinstance(registry["allowlist"], list)
    assert len(registry["features"]) >= 8
    ids = {f["id"] for f in registry["features"]}
    assert {
        "ci.public-testing-branch",
        "qa.obligation-registry",
        "qa.disposable-runtime",
        "provider.llm-contracts",
        "research.spine-qa",
    } <= ids


def test_parse_registry_feature_shape():
    registry = load_registry()
    for feature in registry["features"]:
        assert feature["id"]
        assert feature["status"] in ("active", "deprecated")
        assert isinstance(feature["paths"], list) and feature["paths"]
        obligations = feature.get("obligations", {})
        assert "deterministic" in obligations
        assert isinstance(feature.get("commands", {}).get("deterministic"), list)


def test_parse_scalar_and_inline_list():
    assert _parse_scalar("true") is True
    assert _parse_scalar("false") is False
    assert _parse_scalar("1") == 1
    assert _parse_scalar("hello") == "hello"
    assert _parse_scalar('"quoted"') == "quoted"
    assert _inline_list("[a, b, c]") == ["a", "b", "c"]
    assert _inline_list("[]") == []


# ---------------------------------------------------------------------------
# Path classification and matching
# ---------------------------------------------------------------------------


def test_classify_path_zones():
    assert classify_path("backend/app/api/routes/llm_servers.py") == "source"
    assert classify_path("tests/test_feature_obligations.py") == "test"
    assert classify_path("docs/architecture/research-validity-contract.md") == "docs"
    assert classify_path(".github/workflows/ci.yml") == "workflow"
    assert classify_path("scripts/check_feature_obligations.py") == "script"
    assert classify_path("qa/runtime_capabilities.json") == "qa"
    assert classify_path("security/control_matrix.json") == "security"
    assert classify_path("testing/feature_coverage.yml") == "docs"


def test_path_matches_glob():
    assert path_matches("backend/app/core/pi_runtime/embeddings_gateway.py", "backend/app/core/pi_runtime/*.py")
    assert path_matches("qa/scripts/seed_synthetic.py", "qa/scripts/**")
    assert not path_matches("frontend/src/App.tsx", "backend/**")


# ---------------------------------------------------------------------------
# Capabilities declaration
# ---------------------------------------------------------------------------


def test_capabilities_json_loads_and_is_registered():
    caps = load_capabilities()
    assert caps["version"] == 1
    surface_ids = {s["id"] for s in caps["surfaces"]}
    assert {"provider.embedding", "provider.chat", "research.spine"} <= surface_ids
    # The capabilities file must be referenced by the registry (single authority
    # boundary: consulted, not duplicated).
    registry_text = REGISTRY_TEXT.lower()
    assert "qa/runtime_capabilities.json" in registry_text


# ---------------------------------------------------------------------------
# Classifier behavior (fail-closed)
# ---------------------------------------------------------------------------


def _report_for_paths(paths, monkeypatch):
    """Build a report for a fixed path list without running git."""
    import scripts.check_feature_obligations as module

    monkeypatch.setattr(module, "git_diff_files", lambda base, head: list(paths))
    monkeypatch.setattr(module, "git_rev_parse", lambda rev: rev)
    return build_report("BASE", "HEAD")


def test_unknown_path_fails_closed(monkeypatch):
    report = _report_for_paths(["backend/app/routes/brand_new_surface.py"], monkeypatch)
    assert report["unknown_paths"] == ["backend/app/routes/brand_new_surface.py"]
    assert report["pass"] is False


def test_registered_ci_path_selects_obligations(monkeypatch):
    report = _report_for_paths([".github/workflows/ci.yml"], monkeypatch)
    assert report["unknown_paths"] == []
    ids = [f["id"] for f in report["matched_features"]]
    assert "ci.public-testing-branch" in ids
    deterministic = report["obligations"]["deterministic"]
    assert "feature_obligations" in deterministic
    assert "workflow_contract" in deterministic
    assert report["pass"] is True


def test_qa_script_selects_runtime_obligations(monkeypatch):
    report = _report_for_paths(["docker-compose.qa.yml"], monkeypatch)
    ids = [f["id"] for f in report["matched_features"]]
    assert "qa.disposable-runtime" in ids
    assert "qa_stack_contract" in report["obligations"]["deterministic"]
    assert report["pass"] is True


def test_docs_path_does_not_fail(monkeypatch):
    report = _report_for_paths(["docs/build-stream/README.md"], monkeypatch)
    assert report["unknown_paths"] == []
    assert report["pass"] is True


def test_capability_surface_triggers_spine_obligation(monkeypatch):
    report = _report_for_paths(
        ["backend/app/services/research_validity_service.py"], monkeypatch
    )
    assert "synthetic_provisional" in report["obligations"]["deterministic"]
    assert report["spine_touched"] is True


def test_commands_are_pinned_and_reported(monkeypatch):
    report = _report_for_paths([".github/workflows/ci.yml"], monkeypatch)
    assert "check_feature_obligations" in report["commands"]
    assert any("check_feature_obligations.py" in c for c in report["commands"]["check_feature_obligations"])


def test_required_artifacts_include_scorecard_when_security(monkeypatch):
    report = _report_for_paths(["security/control_matrix.json"], monkeypatch)
    assert "security/security_scorecard.json" in report["required_artifacts"]


def test_json_report_is_stable_and_serializable(monkeypatch):
    report = _report_for_paths([".github/workflows/ci.yml"], monkeypatch)
    payload = json.dumps(report, sort_keys=True)
    assert '"schema_version": 1' in payload
    assert '"base": "BASE"' in payload
    assert '"head": "HEAD"' in payload


def test_optional_lanes_never_satisfy_deterministic(monkeypatch):
    # A live-only obligation name is never promoted into deterministic.
    report = _report_for_paths([".github/workflows/ci.yml"], monkeypatch)
    assert "authorized_live" not in report["obligations"]["deterministic"]
    assert "authorized_live" in report["obligations"]["skipped_optional_lanes"] or \
        "authorized_live" in report["obligations"]["live"]
