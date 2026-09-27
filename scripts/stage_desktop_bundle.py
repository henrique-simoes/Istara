#!/usr/bin/env python3
"""Stage the source the desktop app installs on first run, before ``tauri build``.

The desktop app copies ``<resources>/istara`` into its data folder on first run
(``desktop/src-tauri/src/first_run.rs``). The release workflow used to copy the source into the
built ``.app`` after the build, which broke the code signature, left the updater archive without
it, and on Windows and Linux never reached the installer at all. Staging it into
``desktop/src-tauri/istara/`` first lets Tauri bundle it as a resource on every platform, inside
the signed bundle and the updater archive.

    python scripts/stage_desktop_bundle.py [--out desktop/src-tauri/istara]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "desktop" / "src-tauri" / "istara"

TREES = ("backend", "frontend", "relay")
FILES = ("VERSION", ".env.example", "istara.sh")
# Tracked files that are research or model artefacts, never application source.
SKIP_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".gguf", ".safetensors", ".pt", ".pth"}


def tracked_files() -> list[str]:
    """Exactly the files git tracks under the shipped trees: never a local .env, database,
    virtualenv, build output or untracked scratch file."""
    listing = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "--", *TREES, *FILES],
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8")
    return sorted(
        path
        for path in listing.split("\0")
        if path and Path(path).suffix not in SKIP_SUFFIXES and (ROOT / path).is_file()
    )


def stage(out: Path) -> dict:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    files = tracked_files()
    for relative in files:
        target = out / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    return {
        "out": str(out),
        "files": len(files),
        "bytes": sum((out / f).stat().st_size for f in files),
        "has_backend_app": (out / "backend" / "app" / "main.py").exists(),
        "has_version": (out / "VERSION").exists(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    report = stage(args.out.resolve())
    print(f"Staged {report['files']} files ({report['bytes'] / 1e6:.1f} MB) into {report['out']}")
    if not (report["has_backend_app"] and report["has_version"]):
        print("Staged bundle is missing backend/app/main.py or VERSION", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
