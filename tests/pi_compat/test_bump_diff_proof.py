"""Offline unit tests for the routine-bump diff-proof gate.

Covers ``scripts/pi_bump_diff_proof.py`` (master plan W6.1 diff-proof, §8
change-classification taxonomy, AC-10/AC-11) WITHOUT network: the tree
comparison, classification gate, report verification, inventory deltas, and
the post-bump ``verify`` acceptance run against the real repository state.

Synthetic package trees replace npm installs; the network-dependent ``proof``
mode is exercised only for its typed not_runnable contract.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "pi_bump_diff_proof.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("pi_bump_diff_proof", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mod():
    return _load_module()


def _make_tree(base: Path, files: dict[str, str], version: str = "0.84.3") -> Path:
    """Synthetic @earendil-works package tree: <base>/node_modules/<ns>/..."""
    root = base / "node_modules" / "@earendil-works"
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    (base / "package.json").write_text(json.dumps({"name": "scratch", "private": True}), encoding="utf-8")
    return base


def _standard_files(marker: str = "v1") -> dict[str, str]:
    """Every explicitly consumed surface plus registry model-data modules."""
    return {
        "pi-ai/dist/providers/all.js": f"export const all = '{marker}';\n",
        "pi-ai/dist/models.js": f"export const models = '{marker}';\n",
        "pi-ai/dist/api/openai-completions.js": f"export const api = '{marker}';\n",
        "pi-ai/dist/api/openai-responses.js": f"export const api = '{marker}';\n",
        "pi-ai/dist/api/anthropic-messages.js": f"export const api = '{marker}';\n",
        "pi-ai/dist/api/openai-codex-responses.js": f"export const api = '{marker}';\n",
        "pi-ai/dist/providers/zai.models.js": f"// gen:{marker}\nimport values from './data/zai.json';\nexport const zai = values;\n",
        "pi-ai/dist/providers/data/zai.json": f"{{\"glm-{marker}\": {{}}}}\n",
        "pi-ai/dist/providers/openai-codex.models.js": f"// gen:{marker}\nimport values from './data/openai-codex.json';\nexport const codex = values;\n",
        "pi-ai/dist/providers/data/openai-codex.json": f"{{\"gpt-{marker}\": {{}}}}\n",
    }


def test_identical_trees_pass_the_gate(mod, tmp_path):
    old = _make_tree(tmp_path / "old", _standard_files())
    new = _make_tree(tmp_path / "new", _standard_files())
    entries = mod.compare_trees(old, new)
    assert entries, "consumed surfaces must be enumerated"
    assert all(e["status"] == "identical" for e in entries)
    passed, reasons = mod.gate_result(entries, None, [], None)
    assert passed, reasons


def test_changed_surface_is_unclassified_and_fails_the_gate(mod, tmp_path):
    old = _make_tree(tmp_path / "old", _standard_files("v1"))
    new = _make_tree(tmp_path / "new", _standard_files("v2"))
    entries = mod.compare_trees(old, new)
    changed = [e for e in entries if e["status"] == "changed"]
    assert {e["surface"] for e in changed} == {
        "pi-ai/dist/providers/all.js",
        "pi-ai/dist/models.js",
        "pi-ai/dist/api/openai-completions.js",
        "pi-ai/dist/api/openai-responses.js",
        "pi-ai/dist/api/anthropic-messages.js",
        "pi-ai/dist/api/openai-codex-responses.js",
        "pi-ai/dist/providers/zai.models.js",
        "pi-ai/dist/providers/data/zai.json",
        "pi-ai/dist/providers/openai-codex.models.js",
        "pi-ai/dist/providers/data/openai-codex.json",
    }
    passed, reasons = mod.gate_result(entries, None, [], None)
    assert not passed
    assert any("unclassified" in reason for reason in reasons)
    # Deliberate §8 classification flips the gate (W6.1: fixtures updated
    # deliberately, classification cited in the ledger).
    mod.apply_classifications(entries, [f"{e['surface']}=intended-upstream" for e in entries if e["status"] != "identical"])
    passed, reasons = mod.gate_result(entries, None, [], None)
    assert passed, reasons


def test_blocked_classification_never_passes_the_gate(mod, tmp_path):
    old = _make_tree(tmp_path / "old", _standard_files("v1"))
    new = _make_tree(tmp_path / "new", _standard_files("v2"))
    entries = mod.compare_trees(old, new)
    mod.apply_classifications(entries, [f"{e['surface']}=blocked" for e in entries if e["status"] != "identical"])
    passed, reasons = mod.gate_result(entries, None, [], None)
    assert not passed
    assert any("do not ship" in reason for reason in reasons)


def test_removed_surface_fails_loudly(mod, tmp_path):
    old = _make_tree(tmp_path / "old", _standard_files())
    files = _standard_files()
    del files["pi-ai/dist/api/openai-completions.js"]
    new = _make_tree(tmp_path / "new", files)
    entries = mod.compare_trees(old, new)
    removed = [e for e in entries if e["surface"] == "pi-ai/dist/api/openai-completions.js"]
    assert removed and removed[0]["status"] == "removed"
    passed, _ = mod.gate_result(entries, None, [], None)
    assert not passed  # R11: a relocated/renamed consumed surface fails at bump time


def test_inventory_delta_reports_additions_and_removals(mod):
    old_probe = {"inventory": {"zai": ["glm-5.3"], "openai": ["gpt-4"], "legacy": ["old-1"]}}
    new_probe = {"inventory": {"zai": ["glm-5.3", "glm-5.3-flash"], "openai": ["gpt-4"]}}
    delta = mod.inventory_delta(old_probe, new_probe)
    assert delta["providers_added"] == []
    assert delta["providers_removed"] == ["legacy"]
    assert delta["model_deltas"]["zai"]["added"] == ["glm-5.3-flash"]
    assert delta["total_models_old"] == 3 and delta["total_models_new"] == 3
    passed, reasons = mod.gate_result([], delta, [], None)
    assert not passed
    assert any("legacy" in reason for reason in reasons)


def test_expect_model_absent_fails_present_passes(mod):
    new_probe = {"inventory": {"zai": ["glm-5.3", "glm-5.3-flash"]}}
    passed, _ = mod.gate_result([], None, ["zai/glm-5.3-flash"], new_probe)
    assert passed
    passed, reasons = mod.gate_result([], None, ["zai/glm-9.9"], new_probe)
    assert not passed
    assert any("glm-9.9" in reason for reason in reasons)


def test_removals_are_classifiable_g7(mod):
    """Registry removals fail unclassified, pass classified, fail blocked (G7)."""
    inventory = {
        "providers_added": [], "providers_removed": ["legacy"],
        "model_deltas": {"zai": {"added": ["glm-5.3-flash"], "removed": ["old-model"]}},
        "total_models_old": 2, "total_models_new": 2,
        "removal_classifications": [],
    }
    passed, reasons = mod.gate_result([], inventory, [], None)
    assert not passed
    assert any("legacy" in r for r in reasons) and any("old-model" in r for r in reasons)
    mod.apply_removal_classifications(
        inventory, ["legacy=intended-upstream", "zai/old-model=intended-upstream"]
    )
    passed, reasons = mod.gate_result([], inventory, [], None)
    assert passed, reasons
    inventory["removal_classifications"] = [
        {"provider": "zai", "model": "old-model", "classification": "blocked"}
    ]
    passed, _ = mod.gate_result([], inventory, [], None)
    assert not passed


def test_removal_classification_rejects_unknown_keys(mod):
    inventory = {"providers_removed": [], "model_deltas": {}, "removal_classifications": []}
    with pytest.raises(SystemExit, match="not in the measured inventory delta"):
        mod.apply_removal_classifications(inventory, ["zai/never-existed=intended-upstream"])
    with pytest.raises(SystemExit, match="§8 taxonomy"):
        mod.apply_removal_classifications(inventory, ["zai=intended-unknown"])


def test_verify_report_round_trip(mod, tmp_path):
    old = _make_tree(tmp_path / "old", _standard_files("v1"))
    new = _make_tree(tmp_path / "new", _standard_files("v2"))
    entries = mod.compare_trees(old, new)
    report = {
        "schema": "pi-bump-diff-proof/1",
        "installed_pin": "0.84.3",
        "candidate": "0.85.1",
        "surfaces": entries,
        "registry_inventory_delta": mod.inventory_delta(
            {"inventory": {"zai": ["glm-5.3"]}}, {"inventory": {"zai": ["glm-5.3", "glm-5.3-flash"]}}
        ),
        "expect_models": [{"model": "zai/glm-5.3-flash", "present": True}],
        "gate_passed": None,
        "gate_reasons": [],
    }
    path = tmp_path / "report.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    def _args():
        return type("A", (), {"report": str(path)})()

    # Unclassified report fails...
    assert mod.cmd_verify_report(_args()) == 1
    # ...classify everything and it passes...
    for entry in entries:
        entry["classification"] = "intended-upstream"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    assert mod.cmd_verify_report(_args()) == 0
    # ...and a recorded absent expect-model is a recorded failure (W6.2 either-way).
    report["expect_models"] = [{"model": "zai/glm-9.9", "present": False}]
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    assert mod.cmd_verify_report(_args()) == 1


def test_proof_is_typed_not_runnable_when_npm_install_fails(mod, tmp_path, monkeypatch):
    """A failing npm install yields exit 3, never a silent skip.

    subprocess.run is faked so the test never touches the network.
    """
    failure = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="npm ERR! network offline")
    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: failure)
    scratch = tmp_path / "s"
    assert mod.cmd_proof(type("A", (), {"candidate": "0.85.1", "report": None, "classify": None,
                                        "expect_model": None, "scratch_dir": str(scratch),
                                        "keep_scratch": False})()) == 3
    assert not scratch.exists(), "failed scratch install must be cleaned up"


def test_expected_pins_parse_from_provenance_source(mod):
    pins = mod._expected_pins()
    # Tracks tests/pi_migration/test_version_provenance.py EXPECTED_PINS;
    # 0.85.1 is the wave's classified lockstep bump (diff-proof gate passed).
    assert pins == {"@earendil-works/pi-agent-core": "0.85.1", "@earendil-works/pi-ai": "0.85.1"}


def test_verify_accepts_current_repository_state(mod, capsys):
    """The wave's core contract: pin == lockfile == installed == catalog provenance.

    Skips itself when the repo has no installed node_modules (credential-free
    lane); F-23 pins the no-install behavior separately as fail-closed in
    ``test_verify_fails_closed_without_installed_modules`` — never a silent skip.
    """
    installed_any = any(
        (root / "node_modules" / "@earendil-works" / "pi-ai").exists() for _, root in mod.SURFACES_ROOTS
    )
    code = mod.cmd_verify(type("A", (), {})())
    captured = capsys.readouterr()
    if not installed_any:
        pytest.skip("not_runnable: no installed @earendil-works package in either surface")
    assert code == 0, captured.err
    assert "PASSED" in captured.out


def test_script_cli_wiring():
    """The CLI exposes proof/verify-report/verify and refuses bare invocation."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True, text=True,
        cwd=str(REPO_ROOT), check=False,
    )
    assert result.returncode == 2  # argparse required-subcommand usage error
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "verify"], capture_output=True, text=True,
        cwd=str(REPO_ROOT), check=False,
    )
    assert result.returncode in (0, 1, 3)
    if result.returncode == 3:
        assert "not_runnable" in (result.stderr + result.stdout)


# ---------------------------------------------------------------------------
# F-22/F-23 remediation pins (FIX-pi-compat-20260908-WAVE-update-and-release-proof-REVIEW-r1)
# ---------------------------------------------------------------------------


def _fake_surface(
    base: Path,
    *,
    pin: str = "0.85.1",
    resolved_ok: bool = True,
    integrity_ok: bool = True,
    installed: bool = True,
) -> Path:
    """A synthetic bundled surface: manifest pin + lockfile + optional install."""
    base.mkdir(parents=True, exist_ok=True)

    def entry(package: str, short: str) -> dict:
        resolved = (
            f"https://registry.npmjs.org/{package}/-/{short}-{pin}.tgz"
            if resolved_ok
            else "https://mirror.example.com/evil.tgz"
        )
        integrity = (
            "sha512-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="
            if integrity_ok
            else ""
        )
        return {"version": pin, "resolved": resolved, "integrity": integrity}

    (base / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "@earendil-works/pi-ai": pin,
                    "@earendil-works/pi-agent-core": pin,
                }
            }
        ),
        encoding="utf-8",
    )
    (base / "package-lock.json").write_text(
        json.dumps(
            {
                "packages": {
                    "node_modules/@earendil-works/pi-ai": entry(
                        "@earendil-works/pi-ai", "pi-ai"
                    ),
                    "node_modules/@earendil-works/pi-agent-core": entry(
                        "@earendil-works/pi-agent-core", "pi-agent-core"
                    ),
                }
            }
        ),
        encoding="utf-8",
    )
    if installed:
        for short in ("pi-ai", "pi-agent-core"):
            package_dir = base / "node_modules" / "@earendil-works" / short
            package_dir.mkdir(parents=True, exist_ok=True)
            (package_dir / "package.json").write_text(
                json.dumps({"version": pin}), encoding="utf-8"
            )
    return base


def _fake_catalog(base: Path, version: str = "0.85.1") -> Path:
    path = base / "catalog.json"
    path.write_text(
        json.dumps({"__provenance": {"pi_ai_version": version}}), encoding="utf-8"
    )
    return path


def test_provider_wide_removal_classification_expands_to_named_models(mod):
    """F-22: a blanket PROVIDER=CLASS names every covered model explicitly."""
    inventory = {
        "providers_added": [],
        "providers_removed": [],
        "model_deltas": {"zai": {"added": [], "removed": ["old-a", "old-b"]}},
        "total_models_old": 2,
        "total_models_new": 0,
        "removal_classifications": [],
    }
    mod.apply_removal_classifications(inventory, ["zai=intended-upstream"])
    rows = inventory["removal_classifications"]
    assert {(row["provider"], row["model"]) for row in rows} == {
        ("zai", "old-a"),
        ("zai", "old-b"),
    }
    assert all(row["classification"] == "intended-upstream" for row in rows)
    passed, reasons = mod.gate_result([], inventory, [], None)
    assert passed, reasons


def test_whole_provider_removal_keeps_single_null_row(mod):
    """F-22: a genuinely removed provider keeps one model:null row (no deltas)."""
    inventory = {
        "providers_added": [],
        "providers_removed": ["legacy"],
        "model_deltas": {},
        "total_models_old": 1,
        "total_models_new": 0,
        "removal_classifications": [],
    }
    mod.apply_removal_classifications(inventory, ["legacy=intended-upstream"])
    assert inventory["removal_classifications"] == [
        {"provider": "legacy", "model": None, "classification": "intended-upstream"}
    ]
    passed, reasons = mod.gate_result([], inventory, [], None)
    assert passed, reasons


def test_verify_rejects_non_upstream_lockfile_provenance(
    mod, tmp_path, monkeypatch
):
    """F-23: version-right but provenance-wrong lockfiles fail the gate."""
    surface = _fake_surface(tmp_path / "s", resolved_ok=False, integrity_ok=False)
    monkeypatch.setattr(mod, "SURFACES_ROOTS", (("fake", surface),))
    monkeypatch.setattr(mod, "CATALOG_PATH", _fake_catalog(tmp_path))
    assert mod.cmd_verify(type("A", (), {})()) == 1


def test_verify_rejects_evil_host_with_correct_tarball_name(
    mod, tmp_path, monkeypatch
):
    """F-26: an evil host serving the right tarball filename must fail.

    The pre-F-26 leg was `tarball in resolved` plus a `sha512-` prefix, so
    `https://evil.attacker.example/.../pi-ai-0.85.1.tgz` with any sha512
    string cleared the gate. The host leg is isolated here: integrity is
    valid, the filename is exactly right, only the origin is wrong.
    """
    surface = _fake_surface(tmp_path / "s")
    lock_path = surface / "package-lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    for short in ("pi-ai", "pi-agent-core"):
        key = f"node_modules/@earendil-works/{short}"
        lock["packages"][key]["resolved"] = (
            f"https://evil.attacker.example/@earendil-works/{short}/"
            f"-/{short}-0.85.1.tgz"
        )
    lock_path.write_text(json.dumps(lock), encoding="utf-8")
    monkeypatch.setattr(mod, "SURFACES_ROOTS", (("fake", surface),))
    monkeypatch.setattr(mod, "CATALOG_PATH", _fake_catalog(tmp_path))
    assert mod.cmd_verify(type("A", (), {})()) == 1


def test_verify_rejects_missing_integrity_with_upstream_host(
    mod, tmp_path, monkeypatch
):
    """F-26: the integrity leg isolated — upstream host, no sha512."""
    surface = _fake_surface(tmp_path / "s", resolved_ok=True, integrity_ok=False)
    monkeypatch.setattr(mod, "SURFACES_ROOTS", (("fake", surface),))
    monkeypatch.setattr(mod, "CATALOG_PATH", _fake_catalog(tmp_path))
    assert mod.cmd_verify(type("A", (), {})()) == 1


def test_verify_fails_closed_without_installed_modules(
    mod, tmp_path, monkeypatch, capsys
):
    """F-23: no installed tree fails the gate (run npm ci), never note+pass."""
    surface = _fake_surface(tmp_path / "s", installed=False)
    monkeypatch.setattr(mod, "SURFACES_ROOTS", (("fake", surface),))
    monkeypatch.setattr(mod, "CATALOG_PATH", _fake_catalog(tmp_path))
    assert mod.cmd_verify(type("A", (), {})()) == 1
    assert "npm ci" in capsys.readouterr().err


def test_verify_accepts_well_formed_surface(mod, tmp_path, monkeypatch, capsys):
    """F-23: a fully provenanced surface still passes (no over-tightening)."""
    surface = _fake_surface(tmp_path / "s")
    monkeypatch.setattr(mod, "SURFACES_ROOTS", (("fake", surface),))
    monkeypatch.setattr(mod, "CATALOG_PATH", _fake_catalog(tmp_path))
    assert mod.cmd_verify(type("A", (), {})()) == 0
    assert "PASSED" in capsys.readouterr().out
