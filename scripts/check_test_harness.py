#!/usr/bin/env python3
"""Verify Istara's test harness still matches current production contracts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_PYTEST_MARKERS = {
    "acceptance",
    "agentic_eval",
    "benchmark",
    "contract",
    "e2e",
    "live_llm",
    "mutation",
    "security",
    "simulation",
    "ui",
}

REQUIRED_SIMULATION_SCENARIOS = {
    "70-research-integrity",
    "71-plan-and-execute",
    "72-circuit-breaker-health",
    "73-a2a-debate-and-reports",
    "76-long-horizon-trajectory",
}

REQUIRED_AGENTIC_CONTRACTS = {
    "autoresearch",
    "reasoning_bank",
    "memento_skills_and_agent_creation",
    "hyperagent_meta_tuning",
    "dgmh_archive_evolution",
    "ensemble_llm_orchestration",
    "tool_calling_react",
    "acceptance_ui_simulation",
}

REQUIRED_FRONTEND_MUTATION_DEPS = {
    "@stryker-mutator/core",
    "@stryker-mutator/vitest-runner",
    "vitest",
}


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [ROOT / line for line in result.stdout.splitlines() if line.strip()]


def check_no_committed_live_llm_secrets(issues: list[str]) -> None:
    secret_fragments = [
        "AI" + "za",
        "sk" + "-lm-",
        "J4K" + "WKasP",
        "PzY" + "MJjpkYyo7",
    ]
    for path in tracked_files():
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for fragment in secret_fragments:
            if fragment in text:
                issues.append(
                    f"{path.relative_to(ROOT)}: contains a live LLM secret-like fragment"
                )


def check_pytest_markers(issues: list[str]) -> None:
    pytest_ini = read("pytest.ini")
    for marker in sorted(REQUIRED_PYTEST_MARKERS):
        if f"{marker}:" not in pytest_ini:
            issues.append(f"pytest.ini: missing registered marker `{marker}`")
    if "addopts = --strict-markers" not in pytest_ini:
        issues.append("pytest.ini: strict marker validation is not enabled")


def check_llm_profiles(issues: list[str]) -> None:
    config = read("tests/llm_test_config.py")
    script = read("scripts/test_llm_integration.py")
    required = {
        "Gemini OpenAI base": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "Gemini test model": "gemini-3.1-flash-lite-preview",
        "secondary base": "http://10.0.10.142:1234",
        "secondary model": "qwen3.6-35b-a3b@q5_k_xl",
        "endpoint helper": "openai_compatible_endpoint",
        "profile matrix": "LIVE_LLM_PROFILES",
        "primary retry budget": "PRIMARY_LIVE_LLM_MAX_ATTEMPTS = 5",
        "Gemini-first helper": "post_live_llm_chat_completion",
    }
    for label, snippet in required.items():
        if snippet not in config:
            issues.append(f"tests/llm_test_config.py: missing {label}")
    if "post_live_llm_chat_completion" not in script:
        issues.append(
            "scripts/test_llm_integration.py: must exercise the Gemini-first fallback helper"
        )
    forbidden_endpoint_snippets = ["/api/tags", "/output_schema"]
    combined = config + script
    for snippet in forbidden_endpoint_snippets:
        if snippet in combined:
            issues.append(
                f"LLM test harness still references stale endpoint `{snippet}`"
            )


def check_simulation_runner(issues: list[str]) -> None:
    runner = read("tests/simulation/run.mjs")
    client = read("tests/simulation/lib/api-client.mjs")
    marathon = read("scripts/marathon/run-cycle.mjs")
    scenario_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "tests" / "simulation" / "scenarios").glob("*.mjs"))
    )
    simulation_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            *sorted((ROOT / "tests" / "simulation" / "lib").glob("*.mjs")),
            *sorted((ROOT / "tests" / "simulation" / "scenarios").glob("*.mjs")),
        ]
    )
    for scenario in sorted(REQUIRED_SIMULATION_SCENARIOS):
        if f'"{scenario}"' not in runner:
            issues.append(f"tests/simulation/run.mjs: missing scenario `{scenario}`")
    if "process.env.ISTARA_API_URL" not in runner:
        issues.append(
            "tests/simulation/run.mjs: API base must be environment-configurable"
        )
    if "process.env.ISTARA_FRONTEND_URL" not in runner:
        issues.append(
            "tests/simulation/run.mjs: frontend base must be environment-configurable"
        )
    if "istara_tour_completed_" not in runner:
        issues.append(
            "tests/simulation/run.mjs: authenticated regression runs must mark guided tour complete"
        )
    if "ISTARA_FIXED_LLM_TEST_MODEL" not in simulation_sources:
        issues.append(
            "tests/simulation: model/session scenario must honor the fixed live-test LLM model"
        )
    if "networkidle" in simulation_sources:
        issues.append(
            "tests/simulation: scenarios must not wait for networkidle in the realtime authenticated UI"
        )
    if "http://localhost:3000" in scenario_sources:
        issues.append(
            "tests/simulation/scenarios: scenarios must use ctx.frontendUrl instead of hardcoded localhost"
        )
    for snippet in ("setAuthToken", "authHeaders", "ISTARA_TEST_AUTH_TOKEN"):
        if snippet not in client:
            issues.append(f"tests/simulation/lib/api-client.mjs: missing `{snippet}`")
    if 'headers: authHeaders({ "Content-Type": "application/json" })' not in client:
        issues.append(
            "tests/simulation/lib/api-client.mjs: chat client must send auth headers"
        )
    if "headers: authHeaders()" not in client:
        issues.append(
            "tests/simulation/lib/api-client.mjs: upload client must send auth headers"
        )
    if "process.env.ISTARA_API_URL" not in marathon:
        issues.append(
            "scripts/marathon/run-cycle.mjs: API base must be environment-configurable"
        )
    if "headers: authHeaders()" not in marathon:
        issues.append(
            "scripts/marathon/run-cycle.mjs: protected probes must send auth headers"
        )


def check_agentic_eval_contract(issues: list[str]) -> None:
    path = ROOT / "tests" / "agentic_eval_contract.json"
    if not path.exists():
        issues.append(
            "tests/agentic_eval_contract.json: missing agentic eval contract manifest"
        )
        return
    manifest = json.loads(path.read_text(encoding="utf-8"))
    contracts = {item.get("id") for item in manifest.get("contracts", [])}
    missing = sorted(REQUIRED_AGENTIC_CONTRACTS - contracts)
    if missing:
        issues.append(f"tests/agentic_eval_contract.json: missing contracts {missing}")
    for contract in manifest.get("contracts", []):
        if not contract.get("eval_metrics"):
            issues.append(
                f"tests/agentic_eval_contract.json: {contract.get('id')} has no metrics"
            )
        if not contract.get("unit_tests") and not contract.get("simulation_scenarios"):
            issues.append(
                f"tests/agentic_eval_contract.json: {contract.get('id')} has no test evidence"
            )


def check_ci_governance(issues: list[str]) -> None:
    ci = read(".github/workflows/ci.yml")
    if "python scripts/check_test_harness.py" not in ci:
        issues.append(".github/workflows/ci.yml: missing test harness governance step")
    if "tests/test_agentic_eval_contract.py" not in ci:
        issues.append(
            ".github/workflows/ci.yml: missing agentic eval contract smoke test"
        )
    governance = read("scripts/check_ci_governance.py")
    if "check_test_harness.py" not in governance:
        issues.append("scripts/check_ci_governance.py: missing test harness self-check")


def check_mutation_property_harness(issues: list[str]) -> None:
    backend_pyproject = read("backend/pyproject.toml")
    for snippet in (
        "hypothesis",
        "mutmut",
        "[tool.mutmut]",
        "paths_to_mutate",
        "app/core/compute_capacity.py",
    ):
        if snippet not in backend_pyproject:
            issues.append(f"backend/pyproject.toml: missing mutation/property snippet `{snippet}`")
    if not (ROOT / "tests" / "test_property_contracts.py").exists():
        issues.append("tests/test_property_contracts.py: missing Hypothesis property tests")
    if not (ROOT / "backend" / "tests" / "test_compute_capacity_properties.py").exists():
        issues.append(
            "backend/tests/test_compute_capacity_properties.py: missing mutmut-local property tests"
        )

    frontend_package = json.loads(read("frontend/package.json"))
    dev_deps = set(frontend_package.get("devDependencies", {}))
    missing_deps = sorted(REQUIRED_FRONTEND_MUTATION_DEPS - dev_deps)
    if missing_deps:
        issues.append(f"frontend/package.json: missing mutation test dev deps {missing_deps}")
    scripts = frontend_package.get("scripts", {})
    for name in ("test:unit", "test:mutation"):
        if name not in scripts:
            issues.append(f"frontend/package.json: missing `{name}` script")
    for relative_path in (
        "scripts/run_backend_mutation.py",
        "frontend/vitest.config.ts",
        "frontend/stryker.config.json",
        "frontend/src/lib/runtimeConfig.test.ts",
    ):
        if not (ROOT / relative_path).exists():
            issues.append(f"{relative_path}: missing executable mutation harness file")

    ci = read(".github/workflows/ci.yml")
    for snippet in (
        "pytest ../tests/test_property_contracts.py -q",
        "python ../scripts/run_backend_mutation.py",
        "npm run test:unit",
        "npm run test:mutation",
    ):
        if snippet not in ci:
            issues.append(f".github/workflows/ci.yml: missing executable test gate `{snippet}`")


def main() -> int:
    issues: list[str] = []
    check_no_committed_live_llm_secrets(issues)
    check_pytest_markers(issues)
    check_llm_profiles(issues)
    check_simulation_runner(issues)
    check_agentic_eval_contract(issues)
    check_ci_governance(issues)
    check_mutation_property_harness(issues)

    if issues:
        print("Test harness governance check failed:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print("Test harness governance check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
