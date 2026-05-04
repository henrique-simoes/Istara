#!/usr/bin/env python3
"""Run blocking Ruff checks on changed backend Python files.

The full backend Ruff baseline is still being paid down. This gate prevents new
or touched Python files from adding lint/format debt while the legacy sweep
remains non-blocking.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _valid_revision(revision: str) -> bool:
    if not revision or set(revision) == {"0"}:
        return False
    return _git("rev-parse", "--verify", f"{revision}^{{commit}}").returncode == 0


def _changed_python_files(base: str, head: str) -> list[str]:
    if not _valid_revision(base):
        base = "HEAD~1"
    if not _valid_revision(head):
        head = "HEAD"

    result = _git("diff", "--name-only", "--diff-filter=ACMR", base, head)
    if result.returncode != 0:
        print(result.stderr.strip() or "Unable to determine changed files.", file=sys.stderr)
        return []

    files = []
    for raw_path in result.stdout.splitlines():
        path = raw_path.strip()
        if (
            path.startswith("backend/")
            and path.endswith(".py")
            and not path.startswith("backend/alembic/")
            and (ROOT / path).exists()
        ):
            files.append(path)
    return files


def _run(label: str, command: list[str]) -> int:
    print(f"{label}: {' '.join(command)}")
    return subprocess.run(command, cwd=ROOT, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="HEAD~1")
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()

    files = _changed_python_files(args.base, args.head)
    if not files:
        print("No changed backend Python files to lint.")
        return 0

    print("Changed backend Python files:")
    for path in files:
        print(f"  - {path}")

    config = str(ROOT / "backend" / "pyproject.toml")
    ruff = [sys.executable, "-m", "ruff"]
    lint_status = _run("Ruff lint", [*ruff, "check", "--config", config, *files])
    format_status = _run("Ruff format", [*ruff, "format", "--check", "--config", config, *files])
    return lint_status or format_status


if __name__ == "__main__":
    raise SystemExit(main())
