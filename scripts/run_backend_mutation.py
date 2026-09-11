#!/usr/bin/env python3
"""Run Istara's backend mutation gate through a macOS-safe mutmut wrapper."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import sys
from pathlib import Path


def _default_max_children() -> int:
    if platform.system() == "Darwin":
        return 1
    return max(1, min(os.cpu_count() or 1, 4))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run mutmut for the backend compute-capacity mutation gate. "
            "The wrapper disables mutmut's child-process title update, which "
            "can trigger macOS Python crash dialogs after fork."
        )
    )
    parser.add_argument(
        "--max-children",
        type=int,
        default=_default_max_children(),
        help="Maximum mutmut worker children. Defaults to 1 on macOS, up to 4 elsewhere.",
    )
    parser.add_argument(
        "mutants", nargs="*", help="Optional mutmut mutant names to rerun."
    )
    parser.add_argument(
        "--keep-mutants",
        action="store_true",
        help=(
            "Keep mutmut's generated backend/mutants tree after a successful run. "
            "By default the wrapper removes it so repository gates do not treat "
            "generated mutants as source files."
        ),
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    backend_root = repo_root / "backend"
    if not (backend_root / "pyproject.toml").exists():
        print(f"Backend pyproject not found at {backend_root}", file=sys.stderr)
        return 2

    os.chdir(backend_root)
    os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")
    os.environ.setdefault("PYTHONFAULTHANDLER", "1")

    import mutmut.__main__ as mutmut_main

    mutmut_main.setproctitle = lambda _title: None
    exit_code = 0
    try:
        result = mutmut_main._run(tuple(args.mutants), args.max_children)
        if isinstance(result, int):
            exit_code = result
    except SystemExit as exc:
        raw_code = exc.code
        if raw_code in (None, 0):
            exit_code = 0
        elif isinstance(raw_code, int):
            exit_code = raw_code
        else:
            exit_code = 1
        if exit_code:
            raise
    if exit_code == 0 and not args.keep_mutants:
        shutil.rmtree(backend_root / "mutants", ignore_errors=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
