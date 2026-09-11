#!/usr/bin/env python3
"""Verify the tracked testing-to-main wave manifest (M-14).

The conductor's wave manifest lives in an ignored directory
(`.compass-forge/`), so reviewers who hash the file bytes directly get a
mismatch against the task payload's pinned value. The pinned value is the
SHA-256 of the *canonical* JSON form: ``json.dumps(obj, sort_keys=True,
separators=(',', ':'))`` encoded as UTF-8. This script recomputes that form
so any agent can verify the manifest without re-deriving the recipe.

Usage:
    python scripts/verify_wave_manifest.py [--expected-hash <hex>]
        [--manifest <path>]

Exit 0 when the manifest parses, carries schema_version 1, contains exactly
the conductor's six wave ids in order, and matches the pinned canonical hash.
When the ignored conductor source manifest is present, the tracked mirror must
also equal it; clean checkouts without that local source print a warning and
skip only the mirror comparison. Prints the canonical hash in all cases.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PINNED_CANONICAL_SHA256 = (
    "8601a1fc7cc2373909234cf8bcf6534e0f8a7f7e46c731c1f4f9ad864e142c3c"
)

EXPECTED_WAVE_IDS = [
    "candidate-boundary",
    "control-plane-lifecycle",
    "correctness-quality",
    "ci-enforcement",
    "browser-spine-acceptance",
    "promotion-certification",
]

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "build-stream"
    / "2026-09-09-testing-to-main-waves-manifest.json"
)
CONDUCTOR_MANIFEST = (
    REPO_ROOT
    / ".compass-forge"
    / "conductor"
    / "testing-to-main-20260909-waves.json"
)


def canonical_hash(obj: object) -> str:
    canon = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-hash", default=PINNED_CANONICAL_SHA256)
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    try:
        obj = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot parse manifest: {exc}")
        return 1

    if obj.get("schema_version") != 1:
        print(f"FAIL: schema_version is {obj.get('schema_version')!r}, want 1")
        return 1

    wave_ids = [w.get("id") for w in obj.get("waves", [])]
    if wave_ids != EXPECTED_WAVE_IDS:
        print(f"FAIL: wave ids {wave_ids} != {EXPECTED_WAVE_IDS}")
        return 1

    digest = canonical_hash(obj)
    print(f"canonical_sha256={digest}")

    if digest != args.expected_hash.lower():
        print(f"FAIL: expected {args.expected_hash.lower()}, got {digest}")
        return 1

    try:
        tracked_obj = json.loads(DEFAULT_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot parse tracked manifest for mirror comparison: {exc}")
        return 1

    try:
        conductor_obj = json.loads(CONDUCTOR_MANIFEST.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(
            f"WARNING: conductor manifest absent at {CONDUCTOR_MANIFEST}; "
            "skipping local mirror comparison"
        )
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot parse conductor manifest for mirror comparison: {exc}")
        return 1
    else:
        if tracked_obj != conductor_obj:
            print(f"FAIL: tracked manifest differs from {CONDUCTOR_MANIFEST}")
            return 1

    print("OK: wave manifest verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
