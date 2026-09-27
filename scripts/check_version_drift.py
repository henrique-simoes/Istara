#!/usr/bin/env python3
"""VERSION must not fall behind the releases already published (D-11).

Every release-worthy merge to main is tagged ``v<CalVer>``, but VERSION only moved when someone ran
``scripts/set-version.sh``; by September it still said 2026.05.27.3 while the tags had reached
2026.09.26.6. A Docker install reads VERSION, so it showed a months-old version and its update
checker always offered an "update" to the release it was already running.

    python scripts/check_version_drift.py                          # exit 1 if VERSION < latest tag
    python scripts/check_version_drift.py --newer-than-latest-tag  # exit 0 if VERSION > latest tag
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CALVER = re.compile(r"^v?(\d{4})\.(\d{1,2})\.(\d{1,2})(?:\.(\d+))?$")


def parse(version: str) -> tuple[int, int, int, int] | None:
    match = CALVER.match(version.strip())
    if not match:
        return None
    year, month, day, build = match.groups()
    return int(year), int(month), int(day), int(build or 0)


def latest_tag() -> str | None:
    tags = subprocess.run(
        ["git", "-C", str(ROOT), "tag", "--list", "v*"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    versions = [t for t in tags if parse(t)]
    return max(versions, key=parse) if versions else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--newer-than-latest-tag", action="store_true")
    args = parser.parse_args()

    current = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if parse(current) is None:
        print(f"VERSION is not CalVer (YYYY.MM.DD[.N]): {current!r}", file=sys.stderr)
        return 1
    tag = latest_tag()
    if tag is None:
        print(f"VERSION {current}; no release tags to compare with")
        return 0
    if args.newer_than_latest_tag:
        newer = parse(current) > parse(tag)
        print(f"VERSION {current} {'>' if newer else '<='} latest tag {tag}")
        return 0 if newer else 1
    if parse(current) < parse(tag):
        print(
            f"VERSION {current} is behind the latest release {tag}. "
            f"Run scripts/set-version.sh {tag.lstrip('v')} (or a newer version) and commit.",
            file=sys.stderr,
        )
        return 1
    print(f"VERSION {current} is not behind the latest release {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
