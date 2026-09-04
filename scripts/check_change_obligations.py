#!/usr/bin/env python3
"""Enforce repository governance rules for changed files in CI."""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TECH_REQUIRED_PATTERNS = [
    ".github/workflows/*.yml",
    "security/*.md",
    "security/*.json",
    "scripts/check_change_obligations.py",
    "scripts/check_ci_governance.py",
    "scripts/check_integrity.py",
    "scripts/check_test_harness.py",
    "scripts/security_benchmark.py",
    "scripts/production_rehearsal.py",
    "testing/TESTING_STRATEGY.md",
    "testing/feature_coverage.yml",
    "scripts/check_feature_obligations.py",
    "scripts/check_workflow_contracts.py",
    "scripts/check_qa_capabilities.py",
    "scripts/istara-qa.sh",
    "docker-compose.yml",
    "docker-compose.qa.yml",
    "qa/**",
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
    "frontend/src/lib/dgmhArchive*.ts",
    "frontend/src/lib/improvementGovernance*.ts",
    "frontend/src/lib/reasoningBank*.ts",
    "scripts/production_rehearsal.py",
    "scripts/check_ci_governance.py",
    "scripts/check_test_harness.py",
    "scripts/security_benchmark.py",
    "scripts/check_feature_obligations.py",
    "scripts/check_workflow_contracts.py",
    "scripts/check_qa_capabilities.py",
    "scripts/istara-qa.sh",
    "docker-compose.yml",
    "docker-compose.qa.yml",
    "qa/**",
    "tests/agentic_eval_contract.json",
    "tests/llm_test_config.py",
    "tests/simulation/run.mjs",
    "tests/simulation/lib/*.mjs",
    "testing/TESTING_STRATEGY.md",
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

GOVERNED_EVOLUTION_PATTERNS = [
    "backend/app/api/routes/autoresearch.py",
    "backend/app/api/routes/dgmh_archive.py",
    "backend/app/api/routes/improvement_governance.py",
    "backend/app/api/routes/meta_hyperagent.py",
    "backend/app/api/routes/reasoning_bank.py",
    "backend/app/core/autoresearch*.py",
    "backend/app/core/autoresearch_runners/*.py",
    "backend/app/core/compute_capacity.py",
    "backend/app/core/compute_registry.py",
    "backend/app/core/dgmh_archive.py",
    "backend/app/core/improvement_governance*.py",
    "backend/app/core/meta_hyperagent.py",
    "backend/app/core/reasoning_bank.py",
    "backend/app/core/sandbox_evaluation.py",
    "backend/app/models/autoresearch_experiment.py",
    "backend/app/models/dgmh_archive.py",
    "backend/app/models/improvement_governance.py",
    "backend/app/models/reasoning_memory.py",
    "frontend/src/components/autoresearch/*.tsx",
    "frontend/src/components/autoresearch/**/*.tsx",
    "frontend/src/components/settings/GovernedEvolutionView.tsx",
    "frontend/src/lib/dgmhArchive*.ts",
    "frontend/src/lib/improvementGovernance*.ts",
    "frontend/src/lib/reasoningBank*.ts",
    "scripts/production_rehearsal.py",
    "tests/agentic_eval_contract.json",
]

GOVERNED_EVOLUTION_TEST_FILES = {
    "tests/agentic_eval_contract.json",
    "tests/test_agentic_eval_contract.py",
    "tests/test_autoresearch.py",
    "tests/test_compute.py",
    "tests/test_dgmh_archive.py",
    "tests/test_improvement_governance.py",
    "tests/test_meta_hyperagent.py",
    "tests/test_reasoning_bank.py",
    "tests/test_research_integrity.py",
    "tests/test_harness_config.py",
}

SECURITY_BENCHMARK_PATTERNS = [
    "backend/app/api/routes/auth.py",
    "backend/app/api/routes/webauthn.py",
    "backend/app/api/routes/connections.py",
    "backend/app/api/routes/mcp.py",
    "backend/app/core/pi_runtime/endpoints.py",
    "backend/app/core/pi_runtime/model_manager.py",
    "backend/app/api/routes/webhooks.py",
    "backend/app/core/auth*.py",
    "backend/app/core/security*.py",
    "backend/app/core/auth_sessions.py",
    "backend/app/core/auth_cookies.py",
    "backend/app/core/auth_origins.py",
    "backend/app/core/permissions.py",
    "backend/app/core/field_encryption.py",
    "backend/app/core/connection_string.py",
    "backend/app/core/compute_registry.py",
    "backend/app/core/compute_capacity.py",
    "backend/app/core/improvement_governance*.py",
    "backend/app/core/meta_hyperagent.py",
    "backend/app/core/reasoning_bank.py",
    "backend/app/core/sandbox_evaluation.py",
    "backend/app/mcp/*.py",
    "backend/app/models/user.py",
    "backend/app/models/*auth*.py",
    "backend/app/models/*webauthn*.py",
    "backend/app/models/*recovery*.py",
    "backend/alembic/versions/*auth*.py",
    "backend/alembic/versions/*webauthn*.py",
    "backend/alembic/versions/*recovery*.py",
    "frontend/src/stores/authStore.ts",
    "frontend/src/components/auth/*.tsx",
    "frontend/src/components/auth/**/*.tsx",
    "frontend/src/components/common/UserManagement.tsx",
    "frontend/src/components/settings/PasskeyManager.tsx",
    "frontend/src/components/settings/TOTPManager.tsx",
    "scripts/security_benchmark.py",
    "security/*.md",
    "security/*.json",
]

SECURITY_BENCHMARK_FILES = {
    "security/SECURITY_BENCHMARK.md",
    "security/control_matrix.json",
    "scripts/security_benchmark.py",
    "tests/test_security_benchmark.py",
}


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

    tech_triggers = sorted(
        path for path in changed if matches_any(path, TECH_REQUIRED_PATTERNS)
    )
    test_triggers = sorted(
        path for path in changed if matches_any(path, TEST_REQUIRED_PATTERNS)
    )
    persona_triggers = sorted(
        path for path in changed if matches_any(path, PERSONA_REQUIRED_PATTERNS)
    )
    governed_triggers = sorted(
        path for path in changed if matches_any(path, GOVERNED_EVOLUTION_PATTERNS)
    )
    security_triggers = sorted(
        path for path in changed if matches_any(path, SECURITY_BENCHMARK_PATTERNS)
    )

    tech_changed = "Tech.md" in changed_set
    tests_changed = any(path.startswith("tests/") for path in changed)
    governed_tests_changed = bool(
        changed_set.intersection(GOVERNED_EVOLUTION_TEST_FILES)
    )
    security_benchmark_changed = bool(
        changed_set.intersection(SECURITY_BENCHMARK_FILES)
    )
    personas_changed = any(
        path.startswith("backend/app/agents/personas/") for path in changed
    )

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

    if governed_triggers and not governed_tests_changed:
        issues.append(
            "Governed evolution changes must update the dedicated autoresearch, "
            "ReasoningBank, DGM-H, improvement governance, or compute tests.\n"
            f"Triggered by: {', '.join(governed_triggers[:8])}"
        )

    if security_triggers and not security_benchmark_changed:
        issues.append(
            "Auth/security-sensitive changes must update or explicitly revalidate the "
            "security benchmark package (`security/`, `scripts/security_benchmark.py`, "
            "or `tests/test_security_benchmark.py`).\n"
            f"Triggered by: {', '.join(security_triggers[:8])}"
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
        print(
            "See AGENTS.md, SYSTEM_CHANGE_MATRIX.md, CHANGE_CHECKLIST.md, and Tech.md."
        )
        return 1

    print("Change-governance check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
