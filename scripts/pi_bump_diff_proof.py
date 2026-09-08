#!/usr/bin/env python3
"""Routine pi-ai/pi-agent-core bump diff-proof and release gate.

Build-stream: docs/build-stream/2026-09-08-pi-capability-inheritance.md
(master plan §5.6 routine-bump contract, W6.1 diff-proof, §8 change
classification taxonomy, AC-10/AC-11; authority doc:
docs/architecture/pi-compatibility-authority.md).

A pi version bump must be a controlled maintenance action, never repository
archaeology. This script makes the pre-bump proof and the post-bump gate
mechanical:

``proof``
    Installs the candidate versions of ``@earendil-works/pi-ai`` and
    ``@earendil-works/pi-agent-core`` into a scratch directory (npm, network
    required), diffs every CONSUMED dist surface against the currently
    installed pin, and walks both registries (provider/model inventory,
    optional ``--expect-model`` assertions). Every changed surface is
    reported with a §8 classification — ``unclassified`` by default — and a
    single unclassified (or ``blocked``) change FAILS the gate: the bump
    must then be split out (DEC-O4) or the fixtures updated deliberately
    with the classification cited in the ledger.

``verify-report``
    Re-checks a previously written proof report: passes only when every
    changed surface carries a gate-passing classification
    (``intended-upstream`` or ``istara-fix``). This is the durable,
    offline, CI-side form of the gate.

``verify``
    Post-bump offline acceptance: both bundled surfaces agree with each
    other and with ``tests/pi_migration/test_version_provenance.py``
    EXPECTED_PINS on package.json pins, lockfile resolution, and the
    actually-installed node_modules versions, and the catalog projection's
    ``__provenance.pi_ai_version`` equals the pin (a bump without
    regeneration fails here, AC-5).

Exit codes:
    0  gate passed
    1  gate failed (unclassified/blocked diff, inventory regression, or
       provenance mismatch)
    2  usage error
    3  not_runnable — node/npm unavailable, network install failed, or a
       required artifact is missing; callers must treat this as an explicit
       typed outcome, never a silent skip.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SURFACES_ROOTS = (
    ("pi-runtime", REPO_ROOT / "pi-runtime"),
    ("labs/pi-replacement", REPO_ROOT / "labs" / "pi-replacement"),
)
PROVENANCE_TEST = REPO_ROOT / "tests" / "pi_migration" / "test_version_provenance.py"
CATALOG_PATH = REPO_ROOT / "backend" / "app" / "core" / "pi_runtime" / "data" / "pi_models_catalog.json"

PIN_PACKAGES = ("@earendil-works/pi-ai", "@earendil-works/pi-agent-core")

# Dist surfaces the worker/projection actually consume (provider.mjs imports
# plus the registry model-data files the catalog generator reads). A change
# here is a WIRE- or REGISTRY-behavior change and must be classified (§8)
# before a pin advances — W6.1.
CONSUMED_SURFACES = (
    "pi-ai/dist/providers/all.js",
    "pi-ai/dist/models.js",
    "pi-ai/dist/api/openai-completions.js",
    "pi-ai/dist/api/openai-responses.js",
    "pi-ai/dist/api/anthropic-messages.js",
    "pi-ai/dist/api/openai-codex-responses.js",
)
# Registry content: the generated data modules (pi-ai's models.js shims import
# ./data/<provider>.json) drive the catalog projection, so any change is a
# catalog-diff event even when the resolver files are identical.
REGISTRY_SURFACE_GLOBS = (
    "pi-ai/dist/providers/*.models.js",
    "pi-ai/dist/providers/data/*.json",
)

VALID_CLASSES = ("intended-upstream", "istara-fix", "blocked")
GATE_PASSING_CLASSES = ("intended-upstream", "istara-fix")


def _not_runnable(reason: str) -> int:
    print(f"not_runnable: {reason}", file=sys.stderr)
    return 3


def _fail(reason: str) -> int:
    print(f"gate-failed: {reason}", file=sys.stderr)
    return 1


def _read_pin(surface_root: Path, package: str) -> str | None:
    try:
        manifest = json.loads((surface_root / "package.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return (manifest.get("dependencies") or {}).get(package)


def _expected_pins() -> dict[str, str]:
    """Parse EXPECTED_PINS from the version-provenance source of truth."""
    text = PROVENANCE_TEST.read_text(encoding="utf-8")
    start = text.index("EXPECTED_PINS = {")
    end = text.index("}", start)
    block = text[start:end]
    pins: dict[str, str] = {}
    for line in block.splitlines()[1:]:
        line = line.strip().rstrip(",")
        if not line or line.startswith("#") or '":' not in line:
            continue
        name, value = line.split('":', 1)
        pins[name.strip().strip('"')] = value.strip().strip('"')
    return pins


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _surface_files(pi_ai_dist: Path) -> list[str]:
    """Explicit consumed surfaces plus every registry model-data module."""
    files = list(CONSUMED_SURFACES)
    for pattern in REGISTRY_SURFACE_GLOBS:
        for path in sorted(pi_ai_dist.glob(pattern.replace("pi-ai/dist/", ""))):
            rel = f"pi-ai/dist/{path.relative_to(pi_ai_dist)}"
            if rel not in files:
                files.append(rel)
    return files


def compare_trees(old_base: Path, new_base: Path) -> list[dict]:
    """Diff every consumed surface between two package trees.

    Each surface's parent package dir is resolved under
    ``<base>/node_modules/@earendil-works``. Returns per-surface entries:
    identical surfaces carry no classification; changed/missing ones default
    to ``unclassified``.
    """
    ns = "@earendil-works"
    old_ns = old_base / "node_modules" / ns
    new_ns = new_base / "node_modules" / ns
    # The surface list is fixed by the resolver's imports; the *.models.js
    # glob is expanded over whichever tree exists (candidate preferred).
    glob_base = new_ns if new_ns.exists() else old_ns
    entries: list[dict] = []
    for rel in _surface_files(glob_base / "pi-ai" / "dist"):
        old_file = old_ns / rel
        new_file = new_ns / rel
        if not old_file.exists() and not new_file.exists():
            entries.append({"surface": rel, "status": "missing-both", "classification": "unclassified"})
            continue
        if not old_file.exists() or not new_file.exists():
            entries.append({
                "surface": rel,
                "status": "removed" if not new_file.exists() else "added",
                "classification": "unclassified",
                "old_sha256": _sha256(old_file) if old_file.exists() else None,
                "new_sha256": _sha256(new_file) if new_file.exists() else None,
            })
            continue
        if old_file.read_bytes() == new_file.read_bytes():
            entries.append({
                "surface": rel,
                "status": "identical",
                "classification": None,
                "sha256": _sha256(new_file),
            })
        else:
            entries.append({
                "surface": rel,
                "status": "changed",
                "classification": "unclassified",
                "old_sha256": _sha256(old_file),
                "new_sha256": _sha256(new_file),
            })
    return entries


REGISTRY_PROBE = """
import { getBuiltinProviders, getBuiltinModels } from "@earendil-works/pi-ai/providers/all";
const inventory = {};
for (const provider of getBuiltinProviders().slice().sort()) {
    inventory[provider] = getBuiltinModels(provider).map((record) => record.id).sort();
}
process.stdout.write(JSON.stringify({ inventory }));
"""


def registry_probe(tree_base: Path) -> dict:
    """Walk the registry of the pi-ai copy installed under ``tree_base``."""
    probe = subprocess.run(
        ["node", "--input-type=module", "-e", REGISTRY_PROBE],
        cwd=str(tree_base),
        capture_output=True,
        text=True,
    )
    if probe.returncode != 0:
        raise RuntimeError((probe.stderr or probe.stdout).strip()[-500:] or "registry probe failed")
    return json.loads(probe.stdout)


def inventory_delta(old_probe: dict, new_probe: dict) -> dict:
    old_inv = old_probe.get("inventory", {})
    new_inv = new_probe.get("inventory", {})
    added_providers = sorted(set(new_inv) - set(old_inv))
    removed_providers = sorted(set(old_inv) - set(new_inv))
    model_deltas = {}
    for provider in sorted(set(old_inv) & set(new_inv)):
        added = sorted(set(new_inv[provider]) - set(old_inv[provider]))
        removed = sorted(set(old_inv[provider]) - set(new_inv[provider]))
        if added or removed:
            model_deltas[provider] = {"added": added, "removed": removed}
    return {
        "providers_added": added_providers,
        "providers_removed": removed_providers,
        "model_deltas": model_deltas,
        "total_models_old": sum(len(v) for v in old_inv.values()),
        "total_models_new": sum(len(v) for v in new_inv.values()),
    }


def apply_classifications(entries: list[dict], class_args: list[str]) -> None:
    for arg in class_args:
        if "=" not in arg:
            raise SystemExit(f"usage error: --classify expects SURFACE=CLASS, got {arg!r}")
        surface, classification = arg.split("=", 1)
        if classification not in VALID_CLASSES:
            raise SystemExit(
                f"usage error: classification {classification!r} not in {VALID_CLASSES} (§8 taxonomy)"
            )
        matches = [entry for entry in entries if entry["surface"] == surface]
        if not matches:
            raise SystemExit(f"usage error: --classify surface {surface!r} is not in the diff")
        if matches[0]["status"] == "identical":
            raise SystemExit(f"usage error: surface {surface!r} is identical; nothing to classify")
        matches[0]["classification"] = classification


def apply_removal_classifications(inventory: dict, class_args: list[str]) -> None:
    """Attach §8 classifications to registry removals (G7: deletions cannot
    pass *unnoticed* — they must be classified, not silently tolerated)."""
    recorded = inventory.setdefault("removal_classifications", [])
    for arg in class_args:
        if "=" not in arg:
            raise SystemExit(f"usage error: --classify-removal expects PROVIDER[/MODEL]=CLASS, got {arg!r}")
        key, classification = arg.split("=", 1)
        if classification not in VALID_CLASSES:
            raise SystemExit(
                f"usage error: classification {classification!r} not in {VALID_CLASSES} (§8 taxonomy)"
            )
        provider, _, model = key.partition("/")
        in_deltas = provider in inventory.get("model_deltas", {}) and (
            not model or model in inventory["model_deltas"][provider].get("removed", [])
        )
        in_providers = not model and provider in inventory.get("providers_removed", [])
        if not (in_deltas or in_providers):
            raise SystemExit(f"usage error: --classify-removal {key!r} is not in the measured inventory delta")
        recorded.append({"provider": provider, "model": model or None, "classification": classification})


def gate_result(entries: list[dict], inventory: dict | None, expect_models: list[str], new_probe: dict | None) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    non_identical = [e for e in entries if e["status"] != "identical"]
    missing_both = sorted(e["surface"] for e in non_identical if e["status"] == "missing-both")
    for surface in missing_both:
        reasons.append(f"{surface} absent from BOTH trees: consumed-surface list does not match reality (W6.1)")
    unclassified = sorted(e["surface"] for e in non_identical if e["classification"] == "unclassified")
    if unclassified:
        reasons.append(f"{len(unclassified)} changed surface(s) unclassified (§8): {', '.join(sorted(unclassified))}")
    blocked = sorted(e["surface"] for e in non_identical if e["classification"] == "blocked")
    for surface in blocked:
        reasons.append(f"{surface} classified blocked: do not ship; split into its own task (§8)")
    if inventory is not None:
        recorded = {
            (item["provider"], item.get("model")): item["classification"]
            for item in inventory.get("removal_classifications", [])
        }

        def removal_class(provider: str, model: str | None) -> str:
            # A provider-wide classification covers its per-model removals.
            return recorded.get((provider, model)) or recorded.get((provider, None)) or "unclassified"

        unclassified_removals: list[str] = []
        for provider in inventory["providers_removed"]:
            if removal_class(provider, None) == "unclassified":
                unclassified_removals.append(provider)
            elif removal_class(provider, None) == "blocked":
                reasons.append(f"provider {provider} removal classified blocked: do not ship (§8)")
        for provider, delta in inventory["model_deltas"].items():
            for model in delta["removed"]:
                classification = removal_class(provider, model)
                if classification == "unclassified":
                    unclassified_removals.append(f"{provider}/{model}")
                elif classification == "blocked":
                    reasons.append(f"model {provider}/{model} removal classified blocked: do not ship (§8)")
        if unclassified_removals:
            reasons.append(
                f"{len(unclassified_removals)} registry removal(s) unclassified (§8, G7): "
                f"{', '.join(sorted(set(unclassified_removals)))}"
            )
    # Live expect-model checks run only with a live probe; verify-report
    # relies on the report's recorded expect_models entries instead.
    if new_probe is not None:
        for spec in expect_models:
            provider, _, model = spec.partition("/")
            if model not in new_probe.get("inventory", {}).get(provider, []):
                reasons.append(f"--expect-model {spec}: absent from candidate registry")
    return (not reasons, reasons)


def cmd_proof(args: argparse.Namespace) -> int:
    if shutil.which("node") is None:
        return _not_runnable("node executable not on PATH")
    if shutil.which("npm") is None:
        return _not_runnable("npm executable not on PATH")
    pin = _read_pin(REPO_ROOT / "pi-runtime", PIN_PACKAGES[0])
    if not pin:
        return _not_runnable("pi-runtime/package.json does not pin @earendil-works/pi-ai")
    if not (REPO_ROOT / "pi-runtime" / "node_modules" / PIN_PACKAGES[0]).exists():
        return _not_runnable("pi-runtime/node_modules/@earendil-works/pi-ai not installed (run npm ci)")

    scratch = Path(args.scratch_dir) if args.scratch_dir else Path(tempfile.mkdtemp(prefix="pi-bump-"))
    scratch.mkdir(parents=True, exist_ok=True)
    (scratch / "package.json").write_text(json.dumps({"name": "pi-bump-proof", "private": True, "version": "0.0.0"}), encoding="utf-8")
    spec = [f"{pkg}@{args.candidate}" for pkg in PIN_PACKAGES]
    print(f"installing candidate into scratch: {' '.join(spec)}")
    install = subprocess.run(
        ["npm", "install", "--no-audit", "--no-fund", "--prefix", str(scratch), *spec],
        capture_output=True,
        text=True,
    )
    if install.returncode != 0:
        if not args.keep_scratch:
            shutil.rmtree(scratch, ignore_errors=True)
        return _not_runnable(f"npm install of {' '.join(spec)} failed (network required): {install.stderr.strip()[-300:]}")

    try:
        entries = compare_trees(REPO_ROOT / "pi-runtime", scratch)
        old_probe = registry_probe(REPO_ROOT / "pi-runtime")
        new_probe = registry_probe(scratch)
    except RuntimeError as error:
        if not args.keep_scratch:
            shutil.rmtree(scratch, ignore_errors=True)
        return _not_runnable(f"registry probe failed: {error}")

    inventory = inventory_delta(old_probe, new_probe)
    apply_classifications(entries, args.classify or [])
    apply_removal_classifications(inventory, args.classify_removal or [])
    passed, reasons = gate_result(entries, inventory, args.expect_model or [], new_probe)

    report = {
        "schema": "pi-bump-diff-proof/1",
        "installed_pin": pin,
        "candidate": args.candidate,
        "surfaces": entries,
        "registry_inventory_delta": inventory,
        "expect_models": [
            {
                "model": spec,
                "present": spec.partition("/")[2] in new_probe.get("inventory", {}).get(spec.partition("/")[0], []),
            }
            for spec in (args.expect_model or [])
        ],
        "gate_passed": passed,
        "gate_reasons": reasons,
    }
    text = json.dumps(report, indent=2, sort_keys=False)
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(text + "\n", encoding="utf-8")
        print(f"report written: {report_path}")
    print(text)
    changed = [e for e in entries if e["status"] != "identical"]
    print(f"summary: {len(changed)} changed surface(s), gate {'PASSED' if passed else 'FAILED'}")
    if not args.keep_scratch:
        shutil.rmtree(scratch, ignore_errors=True)
    else:
        print(f"scratch kept: {scratch}")
    return 0 if passed else 1


def cmd_verify_report(args: argparse.Namespace) -> int:
    try:
        report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return _not_runnable(f"cannot read report {args.report}: {error}")
    entries = report.get("surfaces")
    if not isinstance(entries, list):
        return _not_runnable(f"report {args.report} has no surfaces list")
    inventory = report.get("registry_inventory_delta")
    if not isinstance(inventory, dict):
        return _not_runnable(f"report {args.report} has no registry_inventory_delta")
    expect = [entry["model"] for entry in report.get("expect_models", [])]
    passed, reasons = gate_result(entries, inventory, expect, None)
    # A recorded expect-model that was measured absent is a recorded failure.
    for entry in report.get("expect_models", []):
        if entry.get("present") is False:
            reasons.append(f"recorded expect-model absent: {entry['model']}")
            passed = False
    for reason in reasons:
        print(f"gate-failed: {reason}", file=sys.stderr)
    print(f"verify-report: {len([e for e in entries if e['status'] != 'identical'])} changed surface(s), gate {'PASSED' if passed else 'FAILED'}")
    return 0 if passed else 1


def cmd_verify(args: argparse.Namespace) -> int:
    """Offline post-bump acceptance across both bundled surfaces."""
    pins = _expected_pins()
    if not pins:
        return _not_runnable("EXPECTED_PINS not parseable from tests/pi_migration/test_version_provenance.py")
    reasons: list[str] = []
    for label, root in SURFACES_ROOTS:
        for package in PIN_PACKAGES:
            manifest_pin = _read_pin(root, package)
            if manifest_pin != pins[package]:
                reasons.append(f"{label}/package.json pins {package}={manifest_pin!r}, expected {pins[package]!r}")
            lock_path = root / "package-lock.json"
            try:
                lock = json.loads(lock_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                reasons.append(f"{label}/package-lock.json unreadable")
                continue
            locked = ((lock.get("packages") or {}).get(f"node_modules/{package}") or {}).get("version")
            if locked != pins[package]:
                reasons.append(f"{label} lockfile resolves {package}={locked!r}, expected {pins[package]!r}")
            installed = root / "node_modules" / package / "package.json"
            if installed.exists():
                try:
                    installed_version = json.loads(installed.read_text(encoding="utf-8")).get("version")
                except (OSError, json.JSONDecodeError):
                    installed_version = None
                if installed_version != pins[package]:
                    reasons.append(
                        f"{label} installed {package}={installed_version!r}, expected {pins[package]!r} "
                        "(node_modules drifted from the pin; run npm ci)"
                    )
            else:
                print(f"note: {label} has no installed {package} (surface not built); installed-version check skipped")
    try:
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        provenance_version = (catalog.get("__provenance") or {}).get("pi_ai_version")
        if provenance_version != pins[PIN_PACKAGES[0]]:
            reasons.append(
                f"catalog __provenance.pi_ai_version={provenance_version!r}, expected {pins[PIN_PACKAGES[0]]!r} "
                "(bump without regeneration — run scripts/generate_pi_catalog.py)"
            )
    except (OSError, json.JSONDecodeError) as error:
        reasons.append(f"catalog projection unreadable: {error}")
    for reason in reasons:
        print(f"gate-failed: {reason}", file=sys.stderr)
    print(f"verify: pins={pins} gate {'PASSED' if not reasons else 'FAILED'}")
    return 0 if not reasons else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    proof = sub.add_parser("proof", help="diff-proof the candidate against the installed pin (W6.1; network required)")
    proof.add_argument("candidate", help="candidate version, e.g. 0.85.1")
    proof.add_argument("--report", help="write the machine-readable report JSON to this path")
    proof.add_argument("--classify", action="append", metavar="SURFACE=CLASS",
                       help=f"classify a changed surface (§8 classes: {', '.join(VALID_CLASSES)}); repeatable")
    proof.add_argument("--classify-removal", action="append", metavar="PROVIDER[/MODEL]=CLASS",
                       help="classify a registry provider/model removal (G7); repeatable")
    proof.add_argument("--expect-model", action="append", metavar="PROVIDER/MODEL",
                       help="assert a model is present in the candidate registry (e.g. zai/glm-5.3-flash); repeatable")
    proof.add_argument("--scratch-dir", help="use this scratch dir instead of a temp dir (kept on failure)")
    proof.add_argument("--keep-scratch", action="store_true", help="keep the scratch install for inspection")

    verify_report = sub.add_parser("verify-report", help="re-check a written proof report (offline gate)")
    verify_report.add_argument("report", help="path to a proof report JSON")

    verify = sub.add_parser("verify", help="post-bump offline acceptance: pins, lockfiles, installed modules, catalog provenance")

    args = parser.parse_args(argv)
    if args.command == "proof":
        return cmd_proof(args)
    if args.command == "verify-report":
        return cmd_verify_report(args)
    return cmd_verify(args)


if __name__ == "__main__":
    raise SystemExit(main())
