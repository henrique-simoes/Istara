#!/usr/bin/env python3
"""Verify CI/CD governance covers Istara's governed evolution contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


REQUIRED_SNIPPETS: dict[str, dict[str, str]] = {
    ".github/workflows/ci.yml": {
        "CI self-check": "python scripts/check_ci_governance.py",
        "Node 24 frontend runtime": 'node-version: "24"',
        "security benchmark": "python scripts/security_benchmark.py --fail-on-threshold",
        "test harness governance": "python scripts/check_test_harness.py",
        "security scorecard artifact": "istara-security-scorecard",
        "production rehearsal": "python ../scripts/production_rehearsal.py --json",
        "agentic eval contract smoke tests": "tests/test_agentic_eval_contract.py",
        "governed evolution regression tests": (
            "pytest ../tests/test_improvement_governance.py ../tests/test_compute.py -q"
        ),
        "governed surface compile check": (
            "python -m compileall -q app ../scripts/production_rehearsal.py"
        ),
        "security benchmark compile check": "../scripts/security_benchmark.py",
        "test harness compile check": "../scripts/check_test_harness.py",
        "changed-file Ruff gate": "python ../scripts/check_ruff_changed.py",
        "change obligations": "python scripts/check_change_obligations.py",
        "integrity check": "python scripts/check_integrity.py",
    },
    ".github/workflows/build-installers.yml": {
        "Node 24 installer runtime": "node-version: 24",
        "production rehearsal release trigger": "scripts/production_rehearsal.py",
        "CI governance release trigger": "scripts/check_ci_governance.py",
        "test harness release trigger": "scripts/check_test_harness.py",
        "change obligation release trigger": "scripts/check_change_obligations.py",
        "security benchmark release trigger": "scripts/security_benchmark.py",
        "security benchmark docs release trigger": "security/*",
        "testing strategy release trigger": "testing/*",
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
        "test harness release prep": "python scripts/check_test_harness.py",
        "security benchmark release prep": "python scripts/security_benchmark.py --fail-on-threshold",
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
        "security benchmark patterns": "SECURITY_BENCHMARK_PATTERNS",
        "security benchmark files": "SECURITY_BENCHMARK_FILES",
        "production rehearsal obligation": "scripts/production_rehearsal.py",
        "CI governance obligation": "scripts/check_ci_governance.py",
        "test harness obligation": "scripts/check_test_harness.py",
    },
    "scripts/check_integrity.py": {
        "legacy Compass guard": "LEGACY_COMPASS_DOCS",
        "security benchmark governance doc": "SECURITY_BENCHMARK_MD",
        "backend dependency alignment": "BACKEND_DEPENDENCY_MARKERS",
        "governed evolution Tech freshness": '"governed evolution"',
        "sandbox evaluation Tech freshness": '"sandbox evaluation"',
        "production rehearsal Tech freshness": '"production rehearsal"',
        "ReasoningBank Tech freshness": '"reasoningbank"',
        "DGM-H Tech freshness": '"dgm-h"',
        "compute capacity Tech freshness": '"compute capacity"',
        "security benchmark Tech freshness": '"security benchmark"',
        "agentic eval contract Tech freshness": '"agentic eval contract"',
        "mutation testing Tech freshness": '"mutation testing"',
    },
    "scripts/check_test_harness.py": {
        "LLM profile audit": "check_llm_profiles",
        "simulation runner audit": "check_simulation_runner",
        "agentic eval manifest audit": "check_agentic_eval_contract",
    },
    "testing/TESTING_STRATEGY.md": {
        "pytest strict marker strategy": "--strict-markers",
        "Gemini live LLM profile": "gemini-3.1-flash-lite-preview",
        "LM Studio fallback profile": "qwen3.6-35b-a3b",
        "mutation testing strategy": "mutation testing",
        "agentic eval contract strategy": "agentic eval contract",
    },
    "scripts/security_benchmark.py": {
        "benchmark evaluator": "def evaluate_matrix",
        "changed path file input": "changed-paths-file",
        "release threshold": "minimum_score_percent",
    },
    "security/SECURITY_BENCHMARK.md": {
        "ASVS benchmark": "OWASP ASVS",
        "NIST identity benchmark": "NIST SP 800-63",
        "Compass Forge contract": "Compass Forge Contract",
    },
    "security/control_matrix.json": {
        "ASVS standard mapping": "owasp-asvs",
        "NIST identity mapping": "nist-800-63",
        "security trigger patterns": "changed_path_patterns",
    },
    "Tech.md": {
        "governed evolution documentation": "governed evolution",
        "sandbox evaluation documentation": "sandbox evaluation",
        "production rehearsal documentation": "production rehearsal",
        "ReasoningBank documentation": "reasoningbank",
        "DGM-H documentation": "dgm-h",
        "compute capacity documentation": "compute capacity",
        "route/type contract documentation": "route/type contract",
        "security benchmark documentation": "security benchmark",
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
                issues.append(
                    f"{relative_path}: still references {label} (`{snippet}`)"
                )

    if issues:
        print("CI/CD governance check failed:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    print("CI/CD governance check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
