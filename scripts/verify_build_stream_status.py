#!/usr/bin/env python3
"""Fail closed when a Build Stream lifecycle status block contradicts its roadmap."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

STATUS_RE = re.compile(r"<!-- STATUS BLOCK -->\s*```yaml\n(?P<body>.*?)\n```\s*<!-- /STATUS BLOCK -->", re.S)
ROADMAP_RE = re.compile(r"^\|\s*(?P<number>\d+)\s*\|.*?\|\s*(?P<status>planned|in-progress|done)\s*\|\s*$", re.M)
KEY_RE = re.compile(r"^(?P<key>[A-Za-z_][\w-]*):", re.M)


def verify(text: str) -> list[str]:
    errors: list[str] = []
    match = STATUS_RE.search(text)
    if not match:
        return ["missing or malformed STATUS BLOCK"]
    body = match.group("body")
    keys = KEY_RE.findall(body)
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        errors.append("duplicate status keys: " + ", ".join(duplicates))

    values = dict(re.findall(r'^([A-Za-z_][\w-]*):\s*["\']?([^\n"\']+)', body, re.M))
    phase_match = re.match(r"Phase\s+(\d+)\b", values.get("phase", ""))
    active = int(phase_match.group(1)) if phase_match else None
    roadmap = [(int(m.group("number")), m.group("status")) for m in ROADMAP_RE.finditer(text)]
    if active is None:
        errors.append("status phase does not name a numbered Phase")
    elif not roadmap:
        errors.append("roadmap has no phase status rows")
    else:
        statuses = dict(roadmap)
        if statuses.get(active) != "in-progress":
            errors.append(f"active Phase {active} must be in-progress in roadmap")
        stale = [number for number, status in roadmap if number < active and status != "done"]
        future = [number for number, status in roadmap if number > active and status != "planned"]
        if stale:
            errors.append("earlier phases must be done: " + ", ".join(map(str, stale)))
        if future:
            errors.append("future phases must be planned: " + ", ".join(map(str, future)))

    stage = values.get("stage")
    next_action = values.get("next_action", "")
    if stage in {"S3-review", "S4-remediate"} and "dispatch implementation" in next_action.lower():
        errors.append("review/remediation status has stale implementation next_action")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    errors = verify(args.path.read_text(encoding="utf-8"))
    if errors:
        print("FAIL: " + "; ".join(errors))
        return 1
    print(f"OK: lifecycle status and roadmap agree: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
