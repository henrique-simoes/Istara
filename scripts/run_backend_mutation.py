#!/usr/bin/env python3
"""Run Istara's backend mutation gate through a macOS-safe mutmut wrapper."""

from __future__ import annotations

import argparse
import os
import platform
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
    parser.add_argument("mutants", nargs="*", help="Optional mutmut mutant names to rerun.")
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
    mutmut_main._run(tuple(args.mutants), args.max_children)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
