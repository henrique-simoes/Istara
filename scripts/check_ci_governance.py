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
        "release security readiness": "python scripts/security_release_readiness.py",
        "test harness governance": "python scripts/check_test_harness.py",
        "security scorecard artifact": "istara-security-scorecard",
        "production rehearsal": "python ../scripts/production_rehearsal.py --json",
        "agentic eval contract smoke tests": "tests/test_agentic_eval_contract.py",
        "project-scope harness smoke tests": "tests/test_harness_project_scope_contracts.py",
        "marathon integrity smoke tests": "tests/test_marathon_config_integrity.py",
        "property-based contract tests": "pytest ../tests/test_property_contracts.py -q",
        "relay test harness job": "working-directory: relay",
        "relay unit test gate": "npm test",
        "simulation static test gate": "npm run test:static",
        "real-user benchmark static gate": "npm run check",
        "backend mutation gate": "python ../scripts/run_backend_mutation.py",
        "governed evolution regression tests": (
            "pytest ../tests/test_improvement_governance.py ../tests/test_compute.py -q"
        ),
        "governed surface compile check": (
            "python -m compileall -q app ../scripts/production_rehearsal.py"
        ),
        "security benchmark compile check": "../scripts/security_benchmark.py",
        "release security readiness compile check": "../scripts/security_release_readiness.py",
        "test harness compile check": "../scripts/check_test_harness.py",
        "backend mutation wrapper compile check": "../scripts/run_backend_mutation.py",
        "changed-file Ruff gate": "python ../scripts/check_ruff_changed.py",
        "frontend unit test gate": "npm run test:unit",
        "frontend mutation test gate": "npm run test:mutation",
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
        "release security readiness release trigger": "scripts/security_release_readiness.py",
        "active agent contract release trigger": "AGENTS.md",
        "documentation map release trigger": "DOCUMENTATION.md",
        "security benchmark docs release trigger": "security/*",
        "testing strategy release trigger": "testing/*",
        "artifact attestation action": "actions/attest-build-provenance",
        "attestation permission": "attestations: write",
        "OIDC attestation permission": "id-token: write",
    },
    ".github/workflows/scorecard.yml": {
        "OpenSSF Scorecard action": "ossf/scorecard-action",
        "Scorecard SARIF upload": "github/codeql-action/upload-sarif",
        "read-only contents permission": "contents: read",
        "security-events permission": "security-events: write",
        "OIDC permission": "id-token: write",
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
        "release security readiness release prep": "python scripts/security_release_readiness.py",
        "production rehearsal release prep": "python scripts/production_rehearsal.py --json",
    },
    "scripts/install-istara.sh": {
        "Node 24 install requirement": "Node.js 24 or newer",
        "Node 24 detection": "-ge 24",
        "Node 24 Homebrew fallback": "node@24",
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
    "scripts/check_feature_obligations.py": {
        "fail-closed unknown path handling": "unknown_paths",
        "stable JSON obligation report": "json-out",
        "single-authority registry load": "feature_coverage.yml",
        "consulted capability registry": "runtime_capabilities.json",
        "test ownership validation": "missing_test_ownership",
    },
    "scripts/check_workflow_contracts.py": {
        "testing branch trigger check": "branches",
        "human-gate environment check": "environment",
        "no auto-merge check": "auto-merge",
    },
    "scripts/check_qa_capabilities.py": {
        "capability declaration validation": "surfaces",
        "deterministic obligation rule": "deterministic",
        "spine touch rule": "spine_touch",
    },
    "qa/runtime_capabilities.json": {
        "capability schema version": "\"version\": 1",
        "provider embedding surface": "provider.embedding",
        "research spine surface": "research.spine",
    },
    "qa/scripts/seed_synthetic.py": {
        "provisional-only stamp": "is_qa_provisional",
        "promotion gate block": "promotion_blocked",
        "safe run id validation": "SAFE_RUN_ID",
    },
    "qa/scripts/reset_qa.py": {
        "confirmation token contract": "RESET-ISTARA-QA-RUN",
        "protected folder refusal": "Model_Finetuning",
        "unique project naming": "istara-qa-",
    },
    "qa/scripts/scan_qa_artifacts.py": {
        "private endpoint patterns": "PRIVATE_PATTERNS",
        "secret pattern scan": "SECRET_PATTERNS",
        "clean result contract": "clean",
    },
    "qa/scripts/audit_qa.py": {
        "provenance evidence": "provenance",
        "redaction evidence": "redaction",
        "audit pass contract": "audit_pass",
    },
    "qa/scripts/provider_contracts.py": {
        "exact chat identity": "ChatIdentity",
        "no-fallback rule": "assert_no_fallback",
        "vector-space invariant": "vector_space_invariant",
    },
    "qa/corpora/manifest.json": {
        "canonical synthetic slices": "coding-reliability",
        "graph synthesis slice": "graph-synthesis",
        "low consensus slice": "low-consensus-review",
    },
    "docker-compose.qa.yml": {
        "unique project naming": "istara-qa-${QA_RUN_ID",
        "contract profile": "- contract",
        "live profile gate": "QA_LIVE_PROVIDER_TARGET",
    },
    "scripts/istara-qa.sh": {
        "render command": "cmd_render",
        "reset command": "cmd_reset",
        "no model services default": "ollama",
    },
    ".github/workflows/qa-artifact.yml": {
        "testing branch trigger": "branches: [testing]",
        "immutable digest tag": "qa-run-$",
        "evidence manifest": "qa-artifact-manifest.json",
        "no auto PR": "promote-testing.yml",
    },
    ".github/workflows/promote-testing.yml": {
        "manual dispatch only": "workflow_dispatch",
        "protected environment": "environment: testing-promotion",
        "anti-replay SHA check": "source SHA changed",
        "never auto-merge": "gh pr create",
    },
    "tests/test_feature_obligations.py": {
        "fail-closed unknown path test": "unknown_path_fails_closed",
        "registered CI path test": "registered_ci_path_selects_obligations",
        "capability spine test": "capability_surface_triggers_spine_obligation",
    },
    "tests/test_qa_stack_contract.py": {
        "no fixed container name test": "test_qa_compose_has_no_fixed_container_name",
        "profile render test": "test_qa_profile_renders",
        "base compose render test": "test_base_compose_renders_after_qa_hardening_fix",
    },
    "tests/test_qa_reset_seed.py": {
        "reset confirmation test": "test_reset_requires_confirmation_token",
        "seed provisional test": "test_seed_plan_is_provisional_and_blocks_promotion",
        "safe project naming test": "test_project_name_is_namespaced_and_safe",
    },
    "tests/test_qa_artifacts.py": {
        "redaction detection test": "test_scan_text_detects_private_endpoints_and_secrets",
        "audit pass contract test": "test_audit_run_requires_seed_manifest_and_clean_redaction",
    },
    "tests/test_provider_contracts.py": {
        "no fallback test": "test_no_fallback_is_fail_closed",
        "vector invariant test": "test_vector_space_invariant_violation_fails_closed",
    },
    "tests/test_qa_capabilities.py": {
        "capabilities clean validation": "test_capabilities_validate_clean",
        "spine touch obligation test": "test_capabilities_spine_touch_requires_synthetic_provisional",
    },
    "tests/test_synthetic_provisional_boundary.py": {
        "provisional boundary test": "test_synthetic_rows_are_always_provisional",
        "report gate exclusion test": "test_report_gate_excludes_provisional_artifacts",
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
        "project-scope harness audit": "check_project_scope_harness",
        "marathon config integrity audit": "check_marathon_config_integrity",
        "JavaScript harness static audit": "check_js_static_harness",
        "agentic eval manifest audit": "check_agentic_eval_contract",
        "mutation property harness audit": "check_mutation_property_harness",
        "QA obligation harness audit": "check_qa_obligation_harness",
    },
    "testing/TESTING_STRATEGY.md": {
        "pytest strict marker strategy": "--strict-markers",
        "Private main live LLM profile": "google/gemma-4-e4b",
        "mutation testing strategy": "mutation testing",
        "agentic eval contract strategy": "agentic eval contract",
    },
    "scripts/security_benchmark.py": {
        "benchmark evaluator": "def evaluate_matrix",
        "changed path file input": "changed-paths-file",
        "release threshold": "minimum_score_percent",
    },
    "scripts/security_release_readiness.py": {
        "readiness evaluator": "def evaluate_readiness",
        "Better Auth readiness": "better-auth",
        "OpenSSF readiness": "openssf scorecard",
        "attestation readiness": "attest-build-provenance",
    },
    "SECURITY.md": {
        "vulnerability disclosure": "Reporting a Vulnerability",
        "incident response": "Incident Response",
        "log redaction policy": "Logs are treated as sensitive data",
    },
    "security/RELEASE_SECURITY_READINESS.md": {
        "Better Auth mapping": "Better Auth",
        "OWASP ASVS mapping": "OWASP ASVS",
        "NIST identity mapping": "NIST SP 800-63",
        "WebAuthn mapping": "W3C WebAuthn",
        "supply-chain mapping": "OpenSSF Scorecard",
        "LLM single-model guard": "must not autoload multiple heavy models",
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
        "legacy Compass entrypoint release trigger": "AGENT_ENTRYPOINT.md",
        "legacy Claude wrapper release trigger": "CLAUDE.md",
        "legacy Compass COMPLETE_SYSTEM release trigger": "COMPLETE_SYSTEM.md",
        "legacy Gemini wrapper release trigger": "GEMINI.md",
        "legacy Qwen wrapper release trigger": "QWEN.md",
        "legacy Compass guide release trigger": "SYSTEM_INTEGRITY_GUIDE.md",
        "legacy system prompt release trigger": "SYSTEM_PROMPT.md",
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
    "scripts/install-istara.sh": {
        "Node 20 fallback": "node@20",
        "Node 22 fallback": "node@22",
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
