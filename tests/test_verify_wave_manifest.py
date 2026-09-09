from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import scripts.verify_wave_manifest as verifier


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def test_default_hash_rejects_tampered_manifest(tmp_path, monkeypatch):
    original = json.loads(verifier.DEFAULT_MANIFEST.read_text(encoding="utf-8"))
    tampered = copy.deepcopy(original)
    tampered["waves"][0]["scope"] = ["backend"]
    candidate = tmp_path / "tampered.json"
    _write(candidate, tampered)

    monkeypatch.setattr(verifier, "CONDUCTOR_MANIFEST", candidate)
    assert verifier.main(["--manifest", str(candidate)]) == 1


def test_tracked_mirror_must_equal_conductor_manifest(tmp_path, monkeypatch):
    original = json.loads(verifier.DEFAULT_MANIFEST.read_text(encoding="utf-8"))
    conductor = copy.deepcopy(original)
    conductor["waves"][0]["instructions"] = "changed after export"
    conductor_path = tmp_path / "conductor.json"
    _write(conductor_path, conductor)

    monkeypatch.setattr(verifier, "CONDUCTOR_MANIFEST", conductor_path)
    assert verifier.main([]) == 1


def test_clean_checkout_without_conductor_manifest_verifies_pin(tmp_path):
    repo = tmp_path / "clean-checkout"
    script = repo / "scripts" / "verify_wave_manifest.py"
    manifest = (
        repo
        / "docs"
        / "build-stream"
        / "2026-09-09-testing-to-main-waves-manifest.json"
    )
    script.parent.mkdir(parents=True)
    manifest.parent.mkdir(parents=True)
    shutil.copy2(verifier.__file__, script)
    shutil.copy2(verifier.DEFAULT_MANIFEST, manifest)

    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )

    assert not (repo / ".compass-forge").exists()
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "WARNING: conductor manifest absent" in completed.stdout
    assert f"canonical_sha256={verifier.PINNED_CANONICAL_SHA256}" in completed.stdout
