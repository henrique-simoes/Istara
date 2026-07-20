#!/usr/bin/env python3
"""Pi migration inventory — deterministic scanner for legacy-plane call sites.

Walks ``backend/app/`` (excluding ``tests/``) and regex-matches direct
invocations of the legacy compute plane (``ollama.*`` / ``llm_router.*`` /
``compute_registry.*`` aliases, direct per-node dispatch, and the
browser-service ``ChatOpenAI`` bypass).

Output rows: ``{file, line, pattern, snippet}``. Deterministic sort order.
Always exits 0 — the ratchet test (``tests/pi_migration/test_count_to_zero.py``)
owns pass/fail semantics.

Usage:
    python scripts/pi_migration_inventory.py [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_ROOT = REPO_ROOT / "backend" / "app"
EXCLUDED_DIRS = {"tests", "__pycache__"}

# Verbatim from docs/build-stream/plans/2026-07-20-pi-full-replacement-master-plan.md §4.1
PATTERNS = [
    r"\bollama\.chat(_stream)?\(",
    r"\bllm_router\.chat\(",
    r"\bcompute_registry\.chat(_stream)?\(",
    r"\.node\.chat\(",  # direct per-node dispatch (validation, dual-coder)
    r"\bserver\.chat\(",
    r"\bollama\.embed(_batch)?\(",
    r"\bllm_router\.embed_batch\(",
    r"\bChatOpenAI\(",  # browser_service bypass
]

_COMPILED = [re.compile(pattern) for pattern in PATTERNS]


def iter_python_files(root: Path) -> list[Path]:
    """Return all .py files under root, skipping excluded dirs, sorted."""
    files: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        files.append(path)
    return sorted(files)


def scan(root: Path = SCAN_ROOT) -> list[dict]:
    """Scan root for legacy-plane call sites; return sorted inventory rows."""
    rows: list[dict] = []
    for path in iter_python_files(root):
        rel = path.relative_to(REPO_ROOT).as_posix()
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(lines, start=1):
            for pattern, compiled in zip(PATTERNS, _COMPILED):
                if compiled.search(line):
                    rows.append(
                        {
                            "file": rel,
                            "line": lineno,
                            "pattern": pattern,
                            "snippet": line.strip(),
                        }
                    )
    rows.sort(key=lambda row: (row["file"], row["line"], row["pattern"]))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the inventory as a JSON array of {file, line, pattern, snippet} rows.",
    )
    args = parser.parse_args()

    rows = scan()
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        for row in rows:
            print(f"{row['file']}:{row['line']}: {row['pattern']}  {row['snippet']}")
        print(f"\n{len(rows)} legacy-plane call site(s) found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
