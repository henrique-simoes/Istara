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
    }
    for label, snippet in required.items():
        if snippet not in config:
            issues.append(f"tests/llm_test_config.py: missing {label}")
    if "LIVE_LLM_PROFILES" not in script or "get_profile_api_key" not in script:
        issues.append(
            "scripts/test_llm_integration.py: must exercise the shared LLM profile matrix"
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


def main() -> int:
    issues: list[str] = []
    check_no_committed_live_llm_secrets(issues)
    check_pytest_markers(issues)
    check_llm_profiles(issues)
    check_simulation_runner(issues)
    check_agentic_eval_contract(issues)
    check_ci_governance(issues)

    if issues:
        print("Test harness governance check failed:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    print("Test harness governance check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
