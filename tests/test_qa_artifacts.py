"""QA artifact redaction + audit contract tests."""

from __future__ import annotations

import json
from pathlib import Path

from qa.scripts.audit_qa import audit_run
from qa.scripts.scan_qa_artifacts import scan_path, scan_run, scan_text


def test_scan_text_detects_private_endpoints_and_secrets(tmp_path):
    text = (
        "backend ready at http://192.168.1.50:8000 with token sk-test123456789 "
        "and connection postgresql://user:pass@10.0.0.5/db and jwt eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    )
    hits = scan_text(text)
    labels = {h["pattern"] for h in hits}
    assert "private-ipv4" in labels
    assert "connection-string" in labels
    assert "bearer-token" in labels or "jwt" in labels or "api-key" in labels


def test_scan_text_clean(tmp_path):
    assert scan_text("all public and clean output") == []


def test_scan_path_reports_missing_file():
    report = scan_path(Path("/nonexistent/qa/file.json"))
    assert report["exists"] is False
    assert report["hits"] == []


def test_scan_run_clean_directory(tmp_path):
    (tmp_path / "evidence.json").write_text('{"source_sha": "abc", "pass": true}', encoding="utf-8")
    report = scan_run(tmp_path)
    assert report["files_scanned"] == 1
    assert report["clean"] is True


def test_scan_run_detects_secret(tmp_path):
    (tmp_path / "log.txt").write_text("token=sk-abcdef1234567890 leaked", encoding="utf-8")
    report = scan_run(tmp_path)
    assert report["clean"] is False
    assert report["hit_count"] >= 1


def test_audit_run_requires_seed_manifest_and_clean_redaction(tmp_path):
    # no seed manifest -> audit fails
    report = audit_run(tmp_path)
    assert report["audit_pass"] is False
    assert report["provenance"]["seed_manifest_present"] is False

    # with seed manifest + clean artifacts -> pass
    (tmp_path / "seed_manifest.json").write_text(
        json.dumps({"run_id": "r1", "is_qa_provisional": True}), encoding="utf-8"
    )
    (tmp_path / "evidence.json").write_text('{"ok": true}', encoding="utf-8")
    report = audit_run(tmp_path, source_sha="abc123", image_digest="sha256:deadbeef")
    assert report["audit_pass"] is True
    assert report["source_sha"] == "abc123"
    assert report["image_digest"] == "sha256:deadbeef"


def test_audit_run_fails_on_secret_in_artifacts(tmp_path):
    (tmp_path / "seed_manifest.json").write_text(
        json.dumps({"run_id": "r1", "is_qa_provisional": True}), encoding="utf-8"
    )
    (tmp_path / "log.txt").write_text("Bearer sk-abcdef1234567890", encoding="utf-8")
    report = audit_run(tmp_path)
    assert report["audit_pass"] is False
