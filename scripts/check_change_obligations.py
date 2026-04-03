#!/usr/bin/env python3
"""Enforce repository governance rules for changed files in CI."""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TECH_REQUIRED_PATTERNS = [
    ".github/workflows/*.yml",
    "scripts/set-version.sh",
    "backend/app/api/routes/updates.py",
    "backend/app/core/*.py",
    "backend/app/models/*.py",
    "backend/app/services/*.py",
    "backend/app/mcp/*.py",
    "backend/app/channels/*.py",
    "desktop/src-tauri/src/*.rs",
    "relay/*.mjs",
    "relay/lib/*.mjs",
    "installer/**/*",
]

TEST_REQUIRED_PATTERNS = [
    "backend/app/api/routes/*.py",
    "backend/app/core/*.py",
    "backend/app/services/*.py",
    "backend/app/models/*.py",
    "backend/app/channels/*.py",
    "backend/app/mcp/*.py",
    "backend/app/skills/*.py",
    "backend/app/skills/definitions/*.json",
    "frontend/src/components/**/*.tsx",
    "frontend/src/stores/*.ts",
    "frontend/src/lib/api.ts",
    "frontend/src/lib/types.ts",
]

PERSONA_REQUIRED_PATTERNS = [
    "backend/app/skills/definitions/*.json",
    "skills/**/*.md",
    "backend/app/core/agent*.py",
    "backend/app/core/task_router.py",
    "backend/app/services/agent_*.py",
    "backend/app/api/routes/agents.py",
    "backend/app/api/routes/skills.py",
    "backend/app/api/routes/interfaces.py",
    "backend/app/api/routes/integrations.py",
    "backend/app/api/routes/channels.py",
    "backend/app/api/routes/deployments.py",
    "backend/app/api/routes/surveys.py",
    "backend/app/api/routes/loops.py",
    "backend/app/api/routes/autoresearch.py",
    "backend/app/api/routes/mcp.py",
    "backend/app/api/routes/laws.py",
]


def run_git_diff(base: str, head: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}..{head}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def matches_any(path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()

    changed = run_git_diff(args.base, args.head)
    if not changed:
        print("No changed files detected.")
        return 0

    changed_set = set(changed)
    issues: list[str] = []

    tech_triggers = sorted(path for path in changed if matches_any(path, TECH_REQUIRED_PATTERNS))
    test_triggers = sorted(path for path in changed if matches_any(path, TEST_REQUIRED_PATTERNS))
    persona_triggers = sorted(path for path in changed if matches_any(path, PERSONA_REQUIRED_PATTERNS))

    tech_changed = "Tech.md" in changed_set
    tests_changed = any(path.startswith("tests/") for path in changed)
    personas_changed = any(path.startswith("backend/app/agents/personas/") for path in changed)

    if tech_triggers and not tech_changed:
        issues.append(
            "Tech.md must be updated when architecture/process/release-sensitive files change.\n"
            f"Triggered by: {', '.join(tech_triggers[:8])}"
        )

    if test_triggers and not tests_changed:
        issues.append(
            "Tests must be updated for changed product behavior.\n"
            f"Triggered by: {', '.join(test_triggers[:8])}"
        )

    if persona_triggers and not personas_changed:
        issues.append(
            "Relevant persona files must be updated when Istara-agent-facing capabilities change.\n"
            f"Triggered by: {', '.join(persona_triggers[:8])}"
        )

    if issues:
        print("Change-governance check failed:\n")
        for issue in issues:
            print(f"- {issue}\n")
        print("See SYSTEM_PROMPT.md, SYSTEM_CHANGE_MATRIX.md, and CHANGE_CHECKLIST.md.")
        return 1

    print("Change-governance check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
