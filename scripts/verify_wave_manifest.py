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
the conductor's six wave ids in order, and (when --expected-hash is given)
the canonical hash matches. Prints the canonical hash in all cases.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

EXPECTED_WAVE_IDS = [
    "candidate-boundary",
    "control-plane-lifecycle",
    "correctness-quality",
    "ci-enforcement",
    "browser-spine-acceptance",
    "promotion-certification",
]

DEFAULT_MANIFEST = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "build-stream"
    / "2026-09-09-testing-to-main-waves-manifest.json"
)


def canonical_hash(obj: object) -> str:
    canon = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-hash", default=None)
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

    if args.expected_hash and digest != args.expected_hash.lower():
        print(f"FAIL: expected {args.expected_hash.lower()}, got {digest}")
        return 1

    print("OK: wave manifest verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
