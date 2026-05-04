#!/usr/bin/env python3
"""Verify CI/CD governance covers Istara's governed evolution contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


REQUIRED_SNIPPETS: dict[str, dict[str, str]] = {
    ".github/workflows/ci.yml": {
        "CI self-check": "python scripts/check_ci_governance.py",
        "Node 24 frontend runtime": 'node-version: "24"',
        "production rehearsal": "python ../scripts/production_rehearsal.py --json",
        "governed evolution regression tests": (
            "pytest ../tests/test_improvement_governance.py ../tests/test_compute.py -q"
        ),
        "governed surface compile check": (
            "python -m compileall -q app ../scripts/production_rehearsal.py"
        ),
        "changed-file Ruff gate": "python ../scripts/check_ruff_changed.py",
        "change obligations": "python scripts/check_change_obligations.py",
        "integrity check": "python scripts/check_integrity.py",
    },
    ".github/workflows/build-installers.yml": {
        "Node 24 installer runtime": "node-version: 24",
        "production rehearsal release trigger": "scripts/production_rehearsal.py",
        "CI governance release trigger": "scripts/check_ci_governance.py",
        "change obligation release trigger": "scripts/check_change_obligations.py",
    },
    ".nvmrc": {
        "Node 24 local runtime": "24",
    },
    ".node-version": {
        "Node 24 local runtime": "24",
    },
    "frontend/Dockerfile": {
        "Node 24 dependency image": "FROM node:24-slim AS deps",
        "Node 24 builder image": "FROM node:24-slim AS builder",
        "Node 24 runtime image": "FROM node:24-slim",
    },
    "relay/Dockerfile": {
        "Node 24 relay image": "FROM node:24-alpine",
    },
    "desktop/src/index.html": {
        "Node 24 setup wizard label": "Node.js 24",
    },
    "desktop/src-tauri/src/installer.rs": {
        "Node 24 required major": "REQUIRED_NODE_MAJOR: u32 = 24",
        "Node 24 installer version": 'NODE_VERSION: &str = "24.15.0"',
    },
    "scripts/prepare-release.sh": {
        "integrity release prep": "python scripts/check_integrity.py",
        "CI governance release prep": "python scripts/check_ci_governance.py",
        "production rehearsal release prep": "python scripts/production_rehearsal.py --json",
    },
    ".github/workflows/track-autoresearch.yml": {
        "repository checkout": "actions/checkout@v4",
        "read-only contents permission": "contents: read",
        "issue permission": "issues: write",
    },
    "scripts/check_change_obligations.py": {
        "governed evolution patterns": "GOVERNED_EVOLUTION_PATTERNS",
        "governed evolution test ownership": "GOVERNED_EVOLUTION_TEST_FILES",
        "production rehearsal obligation": "scripts/production_rehearsal.py",
        "CI governance obligation": "scripts/check_ci_governance.py",
    },
    "scripts/check_integrity.py": {
        "legacy Compass guard": "LEGACY_COMPASS_DOCS",
        "backend dependency alignment": "BACKEND_DEPENDENCY_MARKERS",
        "governed evolution Tech freshness": '"governed evolution"',
        "sandbox evaluation Tech freshness": '"sandbox evaluation"',
        "production rehearsal Tech freshness": '"production rehearsal"',
        "ReasoningBank Tech freshness": '"reasoningbank"',
        "DGM-H Tech freshness": '"dgm-h"',
        "compute capacity Tech freshness": '"compute capacity"',
    },
    "Tech.md": {
        "governed evolution documentation": "governed evolution",
        "sandbox evaluation documentation": "sandbox evaluation",
        "production rehearsal documentation": "production rehearsal",
        "ReasoningBank documentation": "reasoningbank",
        "DGM-H documentation": "dgm-h",
        "compute capacity documentation": "compute capacity",
        "route/type contract documentation": "route/type contract",
    },
}

FORBIDDEN_SNIPPETS: dict[str, dict[str, str]] = {
    ".github/workflows/ci.yml": {
        "legacy Compass doc generation": "scripts/update_agent_md.py",
        "legacy Compass AGENT doc commit": "AGENT.md COMPLETE_SYSTEM.md AGENT_ENTRYPOINT.md",
        "Node 20 frontend runtime": 'node-version: "20"',
    },
    ".github/workflows/build-installers.yml": {
        "legacy Compass doc generator release trigger": "scripts/update_agent_md.py",
        "legacy Compass AGENT release trigger": "AGENT.md",
        "legacy Compass COMPLETE_SYSTEM release trigger": "COMPLETE_SYSTEM.md",
        "legacy Compass guide release trigger": "SYSTEM_INTEGRITY_GUIDE.md",
        "Node 20 installer runtime": "node-version: 20",
    },
    "frontend/Dockerfile": {
        "Node 20 frontend image": "node:20-",
    },
    "relay/Dockerfile": {
        "Node 20 relay image": "node:20-",
    },
    "desktop/src/index.html": {
        "Node 20 setup wizard label": "Node.js 20",
    },
    "desktop/src-tauri/src/installer.rs": {
        "Node 20 installer URL": "node-v20.",
        "Node 20 install message": "Node.js 20 installed",
    },
    "scripts/prepare-release.sh": {
        "legacy Compass doc generation": "scripts/update_agent_md.py",
    },
}


def main() -> int:
    issues: list[str] = []

    for relative_path, snippets in REQUIRED_SNIPPETS.items():
        path = ROOT / relative_path
        if not path.exists():
            issues.append(f"{relative_path}: missing required governance file")
            continue

        text = path.read_text(encoding="utf-8").lower()
        for label, snippet in snippets.items():
            if snippet.lower() not in text:
                issues.append(f"{relative_path}: missing {label} (`{snippet}`)")

    for relative_path, snippets in FORBIDDEN_SNIPPETS.items():
        path = ROOT / relative_path
        if not path.exists():
            continue

        text = path.read_text(encoding="utf-8").lower()
        for label, snippet in snippets.items():
            if snippet.lower() in text:
                issues.append(f"{relative_path}: still references {label} (`{snippet}`)")

    if issues:
        print("CI/CD governance check failed:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    print("CI/CD governance check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
