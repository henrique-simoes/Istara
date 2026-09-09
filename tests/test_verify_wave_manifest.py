from __future__ import annotations

import copy
import json
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
