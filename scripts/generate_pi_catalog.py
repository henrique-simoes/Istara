#!/usr/bin/env python3
"""Operator entry point for regenerating the pi-ai catalog projection.

Build-stream: docs/build-stream/2026-09-08-pi-capability-inheritance.md
(winners plan §5.1 W1.3, §5.6 routine-bump runbook, AC-5/AC-11).

The projection (``backend/app/core/pi_runtime/data/pi_models_catalog.json``)
is generated, never hand-edited. This script:

1. runs ``pi-runtime/scripts/emit-catalog.mjs`` (the only maintenance-time
   importer of the pi-ai registry outside the worker),
2. writes the projection in place (default) or regenerates to a temp dir
   (``--check``),
3. prints a drift summary against the previously committed file —
   added/removed providers and models and per-field change counts — so a
   version bump's compatibility report is the diff itself, and
4. under ``--check`` exits non-zero when the committed file is not exactly
   what the installed pi-ai pin produces (a bump without regeneration fails).

Exit codes:
    0  success (and, under --check, no drift)
    1  drift detected under --check (or emission failed)
    2  usage error
    3  not_runnable — node or the installed pi-ai package is unavailable;
       callers must treat this as an explicit typed outcome, never a silent
       skip.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
EMITTER = REPO_ROOT / "pi-runtime" / "scripts" / "emit-catalog.mjs"
CATALOG_PATH = REPO_ROOT / "backend" / "app" / "core" / "pi_runtime" / "data" / "pi_models_catalog.json"
PROVENANCE_KEY = "__provenance"
# The only intentionally non-deterministic provenance field; masked for
# byte-identical comparisons.
MASKED_PROVENANCE_FIELDS = ("emitted_at",)
_EMITTED_AT_RE = re.compile(r'("emitted_at"\s*:\s*")[^"]*(")')


def _not_runnable(reason: str) -> int:
    print(f"not_runnable: {reason}", file=sys.stderr)
    return 3


def _emit(out_path: Path) -> None:
    result = subprocess.run(
        ["node", str(EMITTER), "--out", str(out_path)],
        cwd=str(REPO_ROOT / "pi-runtime"),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr or result.stdout)
        raise SystemExit(1)


def _masked_text(path: Path) -> str:
    """Raw file bytes with emitted_at masked, for byte-identical comparison."""
    return _EMITTED_AT_RE.sub(r"\1EMITTED_AT_MASKED\2", path.read_text(encoding="utf-8"))


def _drift_summary(old: dict, new: dict) -> list[str]:
    lines: list[str] = []
    old_providers = {k: v for k, v in old.items() if not k.startswith("__")}
    new_providers = {k: v for k, v in new.items() if not k.startswith("__")}
    added_providers = sorted(set(new_providers) - set(old_providers))
    removed_providers = sorted(set(old_providers) - set(new_providers))
    if added_providers:
        lines.append(f"providers added: {len(added_providers)} ({', '.join(added_providers)})")
    if removed_providers:
        lines.append(f"providers removed: {len(removed_providers)} ({', '.join(removed_providers)})")

    field_changes: dict[str, int] = {}
    added_models = removed_models = 0
    changed_models = 0
    for provider in sorted(set(old_providers) & set(new_providers)):
        old_models = {m.get("id"): m for m in old_providers[provider]}
        new_models = {m.get("id"): m for m in new_providers[provider]}
        added_models += len(set(new_models) - set(old_models))
        removed_models += len(set(old_models) - set(new_models))
        for model_id in sorted(set(old_models) & set(new_models)):
            om, nm = old_models[model_id], new_models[model_id]
            model_changed = False
            for field in sorted(set(om) | set(nm)):
                if om.get(field) != nm.get(field):
                    field_changes[field] = field_changes.get(field, 0) + 1
                    model_changed = True
            if model_changed:
                changed_models += 1
    if added_models or removed_models or changed_models:
        lines.append(f"models added: {added_models} | removed: {removed_models} | changed: {changed_models}")
    for field, count in sorted(field_changes.items()):
        lines.append(f"field '{field}' changed in {count} model(s)")
    if not lines:
        lines.append("no drift: providers, models, and every model field identical")
    provenance_old, provenance_new = old.get(PROVENANCE_KEY) or {}, new.get(PROVENANCE_KEY) or {}
    for key in ("pi_ai_version", "pi_ai_generated_at", "model_field_set_hash", "emitter_sha256"):
        if provenance_old.get(key) != provenance_new.get(key):
            lines.append(f"provenance '{key}': {provenance_old.get(key)} -> {provenance_new.get(key)}")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--check",
        action="store_true",
        help="regenerate to a temp dir and verify the committed file is byte-identical (masking emitted_at); exit 1 on drift",
    )
    args = parser.parse_args(argv)

    if shutil.which("node") is None:
        return _not_runnable("node executable not found on PATH")
    if not EMITTER.exists():
        return _not_runnable(f"emitter missing: {EMITTER}")
    node_modules = REPO_ROOT / "pi-runtime" / "node_modules" / "@earendil-works" / "pi-ai"
    if not node_modules.exists():
        return _not_runnable("pi-runtime/node_modules/@earendil-works/pi-ai not installed (run: cd pi-runtime && npm ci)")

    if args.check:
        if not CATALOG_PATH.exists():
            return _not_runnable(f"committed catalog missing: {CATALOG_PATH}")
        with tempfile.TemporaryDirectory(prefix="pi-catalog-check-") as tmp:
            generated = Path(tmp) / "pi_models_catalog.json"
            _emit(generated)
            if _masked_text(CATALOG_PATH) == _masked_text(generated):
                print("check ok: committed catalog is byte-identical to the projection of the installed pi-ai pin (emitted_at masked)")
                return 0
            old, new = json.loads(_masked_text(CATALOG_PATH)), json.loads(_masked_text(generated))
            print("DRIFT: committed catalog is not byte-identical to the projection of the installed pi-ai pin:")
            for line in _drift_summary(old, new):
                print(f"  {line}")
            print("run: python scripts/generate_pi_catalog.py  (then review the diff as a change, not a rubber stamp)")
            return 1

    old = json.loads(_masked_text(CATALOG_PATH)) if CATALOG_PATH.exists() else {}
    _emit(CATALOG_PATH)
    new = json.loads(_masked_text(CATALOG_PATH))
    print(f"regenerated {CATALOG_PATH.relative_to(REPO_ROOT)}")
    print("drift summary vs previous committed file:")
    for line in _drift_summary(old, new):
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
