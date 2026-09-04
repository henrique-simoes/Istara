#!/usr/bin/env python3
"""Deterministic feature->obligation classifier (fail-closed).

Single authority: ``testing/feature_coverage.yml``. Consulted declaration:
``qa/runtime_capabilities.json``. Every changed path must be owned by a
registry entry or be on the audited mechanical allowlist; anything else is an
error, not a warning. Emits a stable JSON obligation report used by later CI
jobs and by the human-gate promotion manifest.

Stdlib only (no PyYAML dependency): the registry parser below understands the
YAML subset the registry is constrained to, and is locked by
``tests/test_feature_obligations.py``.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "testing" / "feature_coverage.yml"
CAPABILITIES = ROOT / "qa" / "runtime_capabilities.json"

# ---------------------------------------------------------------------------
# Minimal YAML-subset parser (maps, lists, scalars, comments).
# ---------------------------------------------------------------------------


def _strip_comment(line: str) -> str:
    """Strip an unquoted ``#`` comment from a line."""
    in_single = in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i]
    return line


def _parse_scalar(token: str) -> object:
    token = token.strip()
    if not token:
        return None
    if token == "[]":
        return []
    if token == "true":
        return True
    if token == "false":
        return False
    if token in ("null", "~"):
        return None
    if (token.startswith('"') and token.endswith('"')) or (
        token.startswith("'") and token.endswith("'")
    ):
        return token[1:-1]
    if re.fullmatch(r"-?\d+", token):
        return int(token)
    if re.fullmatch(r"-?\d+\.\d+", token):
        return float(token)
    return token


def _inline_list(token: str) -> list[object]:
    inner = token.strip()
    if inner.startswith("[") and inner.endswith("]"):
        inner = inner[1:-1]
    if not inner.strip():
        return []
    return [_parse_scalar(item) for item in inner.split(",")]


def parse_registry(text: str) -> dict:
    """Parse the constrained YAML subset used by testing/feature_coverage.yml."""
    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        line = _strip_comment(raw).rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        lines.append((indent, line.strip()))

    def parse_block(idx: int, indent: int) -> tuple[object, int]:
        """Parse a block at the given indent; returns (value, next_index)."""
        if idx >= len(lines):
            return None, idx
        cur_indent, cur = lines[idx]
        if cur_indent < indent:
            return None, idx
        if cur.startswith("- "):
            return _parse_list(idx, indent)
        return _parse_map(idx, indent)

    def _parse_list(idx: int, indent: int) -> tuple[list[object], int]:
        items: list[object] = []
        while idx < len(lines):
            cur_indent, cur = lines[idx]
            if cur_indent < indent:
                break
            if cur_indent != indent or not cur.startswith("- "):
                break
            body = cur[2:].strip()
            if not body:
                # nested block under the dash
                value, idx = parse_block(idx + 1, indent + 2)
                items.append(value)
            elif ":" in body and not body.startswith(("[", "'", '"')):
                # dash map: - key: value  (scalar value, optional nested block)
                key, _, rest = body.partition(":")
                key = key.strip()
                item: dict = {}
                if rest.strip():
                    item[key] = _parse_scalar(rest)
                # optional nested block under the dash map
                if (not rest.strip() or True) and idx + 1 < len(lines):
                    nxt_indent, _ = lines[idx + 1]
                    if nxt_indent > indent:
                        value, idx = parse_block(idx + 1, nxt_indent)
                        if isinstance(value, dict):
                            # merge sibling keys, preserving the scalar key
                            for k, v in value.items():
                                item.setdefault(k, v)
                        else:
                            item[key] = value
                items.append(item)
                # parse_block already advanced idx past the nested block;
                # only advance again for scalar dash items.
                if not ("nxt_indent" in locals() and nxt_indent > indent):
                    idx += 1
                continue
            else:
                items.append(_parse_scalar(body))
            idx += 1
        return items, idx

    def _parse_map(idx: int, indent: int) -> tuple[dict, int]:
        result: dict = {}
        while idx < len(lines):
            cur_indent, cur = lines[idx]
            if cur_indent < indent:
                break
            if cur_indent != indent or cur.startswith("- "):
                break
            key, sep, rest = cur.partition(":")
            if not sep:
                idx += 1
                continue
            key = key.strip()
            rest = rest.strip()
            if rest == "":
                if idx + 1 < len(lines) and lines[idx + 1][0] > indent:
                    value, idx = parse_block(idx + 1, lines[idx + 1][0])
                    result[key] = value
                else:
                    result[key] = None
                    idx += 1
            elif rest.startswith("[") and rest.endswith("]"):
                result[key] = _inline_list(rest)
                idx += 1
            else:
                result[key] = _parse_scalar(rest)
                idx += 1
        return result, idx

    value, _ = parse_block(0, 0)
    return value if isinstance(value, dict) else {}


def load_registry() -> dict:
    return parse_registry(REGISTRY.read_text(encoding="utf-8"))


def load_capabilities() -> dict:
    return json.loads(CAPABILITIES.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Path classification and matching
# ---------------------------------------------------------------------------


def classify_path(path: str) -> str:
    """Classify a changed path into a coarse zone."""
    p = PurePosixPath(path)
    parts = p.parts
    if path.startswith("docs/"):
        return "docs"
    if path.startswith("tests/") or path.startswith("backend/tests/"):
        return "test"
    if path.startswith(".github/"):
        return "workflow"
    if path.startswith("scripts/"):
        return "script"
    if path.startswith("qa/"):
        return "qa"
    if path.startswith("backend/"):
        return "source"
    if path.startswith("frontend/"):
        return "source"
    if path.startswith("relay/"):
        return "source"
    if path.startswith("desktop/"):
        return "source"
    if path.startswith("security/"):
        return "security"
    if path.startswith("testing/"):
        return "docs"
    if path.startswith("installer/"):
        return "source"
    if path.startswith("infra/"):
        return "source"
    if any(
        part in ("node_modules", ".venv", "dist", "build", "__pycache__")
        for part in parts
    ):
        return "generated"
    return "unknown"


def path_matches(path: str, pattern: str) -> bool:
    """fnmatch with ** support (PurePosixPath.match handles **)."""
    return PurePosixPath(path).match(pattern)


def git_diff_files(base: str, head: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}..{head}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def git_rev_parse(rev: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", rev], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Command catalog (pinned, deterministic; live lanes are never defaults)
# ---------------------------------------------------------------------------

COMMAND_CATALOG: dict[str, str] = {
    "check_integrity": "python scripts/check_integrity.py",
    "check_ci_governance": "python scripts/check_ci_governance.py",
    "check_test_harness": "python scripts/check_test_harness.py",
    "check_feature_obligations": (
        "python scripts/check_feature_obligations.py --base {base} --head {head} "
        "--json-out artifacts/feature-obligations.json"
    ),
    "check_qa_capabilities": "python scripts/check_qa_capabilities.py",
    "check_workflow_contracts": "python scripts/check_workflow_contracts.py",
    "check_public_tree": (
        "python scripts/check_public_tree_clean.py --base {base} --head {head}"
    ),
    "security_benchmark": (
        "python scripts/security_benchmark.py --fail-on-threshold "
        "--output security/security_scorecard.json"
    ),
    "pytest_feature_obligations": "pytest tests/test_feature_obligations.py -q",
    "pytest_qa_stack": "pytest tests/test_qa_stack_contract.py -q",
    "pytest_qa_reset_seed": "pytest tests/test_qa_reset_seed.py -q",
    "pytest_qa_artifacts": "pytest tests/test_qa_artifacts.py -q",
    "pytest_provider_contracts": "pytest tests/test_provider_contracts.py -q",
    "pytest_model_provider_contract": "pytest tests/test_model_provider_contract.py -q",
    "pytest_embeddings_gateway": "pytest tests/pi_production/test_w8_embeddings_gateway.py -q",
    "pytest_migration_suites": (
        "pytest tests/pi_migration/ tests/test_settings.py "
        "tests/test_settings_agentic_pi_endpoints.py tests/test_audio_model_profile.py "
        "tests/test_projects.py tests/pi_production/test_w8_ux_parity.py -q"
    ),
    "pytest_core_routing": (
        "pytest tests/test_chat.py::test_resolve_chat_engine_precedence "
        "tests/test_chat.py::test_chat_blocked_when_provider_is_contract_stub "
        "tests/test_a11y_contrast.py tests/test_design_tokens.py -q"
    ),
    "pytest_research_validity": "pytest tests/test_research_validity_contract.py -q",
    "pytest_synthetic_provisional": "pytest tests/test_synthetic_provisional_boundary.py -q",
    "pytest_harness_contracts": (
        "pytest tests/test_harness_config.py tests/test_agentic_eval_contract.py "
        "tests/test_harness_project_scope_contracts.py tests/test_marathon_config_integrity.py -q"
    ),
    "pytest_property_contracts": "pytest tests/test_property_contracts.py -q",
    "pytest_project_scope": (
        "pytest tests/test_harness_project_scope_contracts.py "
        "tests/test_project_scope_contracts.py -q"
    ),
    "pytest_security_benchmark": "pytest tests/test_security_benchmark.py -q",
    "relay_unit": "npm test",
    "simulation_static": "npm run test:static",
    "real_user_static": "npm run check",
    "marathon_integrity": "pytest tests/test_marathon_config_integrity.py -q",
    "frontend_unit": "npm run test:unit",
    "frontend_typecheck": "npx tsc --noEmit",
    "frontend_lint": "npm run lint",
    "frontend_mutation": "npm run test:mutation",
    "compose_qa_render": "docker compose -f docker-compose.qa.yml --profile contract config --quiet",
    "feature_docs_check": "python scripts/feature_docs.py --seed-missing --generate-site --check",
    "check_testing_strategy": "python scripts/check_test_harness.py",
}

# Every selected obligation must have at least one test owner file present.
OBLIGATION_TEST_OWNERS: dict[str, list[str]] = {
    "governance": ["scripts/check_integrity.py"],
    "ci_governance": ["scripts/check_ci_governance.py"],
    "test_harness": ["scripts/check_test_harness.py"],
    "feature_obligations": ["tests/test_feature_obligations.py"],
    "qa_artifact_contract": [
        "tests/test_qa_stack_contract.py",
        "tests/test_qa_artifacts.py",
    ],
    "qa_stack_contract": ["tests/test_qa_stack_contract.py"],
    "public_tree": ["tests/test_public_repo_quality.py"],
    "workflow_contract": ["scripts/check_workflow_contracts.py"],
    "security_benchmark": ["tests/test_security_benchmark.py"],
    "backend_contracts": ["tests/test_model_provider_contract.py"],
    "provider_contracts": ["tests/test_provider_contracts.py"],
    "research_spine_contract": ["tests/test_research_validity_contract.py"],
    "synthetic_provisional": ["tests/test_synthetic_provisional_boundary.py"],
    "mutation_property": ["tests/test_property_contracts.py"],
    "frontend_contracts": ["frontend/src/lib/modelCatalog.test.ts"],
    "relay_contracts": ["relay/lib/llm-proxy.test.mjs"],
    "project_scope": ["tests/test_harness_project_scope_contracts.py"],
    "feature_docs": ["tests/test_feature_docs.py"],
}

# Cross-cutting obligations added from change class, independent of registry.
CROSS_CUTTING: dict[str, list[str]] = {
    "workflow": [
        "governance",
        "ci_governance",
        "test_harness",
        "feature_obligations",
        "workflow_contract",
        "security_benchmark",
    ],
    "qa": ["governance", "qa_stack_contract", "qa_artifact_contract", "public_tree"],
    "security": ["security_benchmark"],
    "script": ["governance"],
}

# Cross-cutting pinned commands added from change class (catalog keys).
CROSS_CUTTING_COMMANDS: dict[str, list[str]] = {
    "workflow": [
        "check_integrity",
        "check_ci_governance",
        "check_test_harness",
        "check_feature_obligations",
        "check_workflow_contracts",
        "security_benchmark",
    ],
    "qa": [
        "check_integrity",
        "compose_qa_render",
        "pytest_qa_stack",
        "check_public_tree",
    ],
    "security": ["security_benchmark", "pytest_security_benchmark"],
    "script": ["check_integrity"],
}

OPTIONAL_LANES = {
    "authorized_live",
    "staging_adapter",
    "simulation_live",
    "dimension_probe_live",
    "authorized_chat_smoke",
}


def build_report(base: str, head: str) -> dict:
    registry = load_registry()
    capabilities = load_capabilities()
    features = registry.get("features", [])
    allowlist = registry.get("allowlist", [])

    changed = git_diff_files(base, head)
    changed_set = set(changed)

    matched_features: list[dict] = []
    unknown_paths: list[str] = []
    allowlisted_paths: list[str] = []
    obligation_reasons: dict[str, list[str]] = {}

    for path in changed:
        zone = classify_path(path)
        matched = [
            f
            for f in features
            if any(path_matches(path, pat) for pat in f.get("paths", []))
        ]
        if matched:
            for feature in matched:
                entry = {
                    "id": feature.get("id"),
                    "owner": feature.get("owner"),
                    "matched_path": path,
                    "requires_human_review": bool(
                        feature.get("requires_human_review", False)
                    ),
                }
                if entry not in matched_features:
                    matched_features.append(entry)
                for group in ("deterministic", "live", "docs"):
                    for obl in feature.get("obligations", {}).get(group, []):
                        obligation_reasons.setdefault(obl, []).append(
                            f"{feature.get('id')} owns {path}"
                        )
            continue
        if any(path_matches(path, pat) for pat in allowlist):
            allowlisted_paths.append(path)
            continue
        if zone in ("docs", "test", "generated"):
            # Docs and tests are governed by cross-cutting obligations, not by
            # feature ownership; a test change without any source change still
            # runs harness governance.
            obligation_reasons.setdefault("governance", []).append(
                f"{path} is a {zone} path"
            )
            continue
        unknown_paths.append(path)

    # Cross-cutting obligations from change class.
    for path in changed:
        zone = classify_path(path)
        for obl in CROSS_CUTTING.get(zone, []):
            obligation_reasons.setdefault(obl, []).append(f"{zone} change: {path}")

    # Consulted capability surfaces: any changed path matching a surface triggers
    # the surface's deterministic obligations plus spine_touch handling.
    spine_touched = False
    for surface in capabilities.get("surfaces", []):
        if any(
            path_matches(path, pat)
            for pat in surface.get("paths", [])
            for path in changed
        ):
            for obl in surface.get("deterministic", []):
                obligation_reasons.setdefault(obl, []).append(
                    f"capability surface {surface.get('id')}"
                )
            if surface.get("spine_touch"):
                spine_touched = True
    if spine_touched:
        obligation_reasons.setdefault("synthetic_provisional", []).append(
            "spine-touching surface changed; synthetic-QA boundary required"
        )

    # Deduplicate obligations preserving order.
    ordered_obligations: list[str] = []
    for obl in obligation_reasons:
        if obl not in ordered_obligations:
            ordered_obligations.append(obl)
    deterministic = [o for o in ordered_obligations if o not in OPTIONAL_LANES]
    live = [o for o in ordered_obligations if o in OPTIONAL_LANES]
    skipped_optional = sorted(OPTIONAL_LANES - set(live))

    # Commands: collected from matched features' pinned `commands.deterministic`
    # lists (catalog keys), plus cross-cutting commands for change classes.
    commands: dict[str, list[str]] = {}
    command_names: list[str] = []
    for path in changed:
        zone = classify_path(path)
        for feature in features:
            if any(path_matches(path, pat) for pat in feature.get("paths", [])):
                for cmd in feature.get("commands", {}).get("deterministic", []):
                    if cmd not in command_names:
                        command_names.append(cmd)
        if zone in CROSS_CUTTING_COMMANDS:
            for cmd in CROSS_CUTTING_COMMANDS[zone]:
                if cmd not in command_names:
                    command_names.append(cmd)
    for cmd in command_names:
        if cmd in COMMAND_CATALOG:
            commands.setdefault(cmd, []).append(
                COMMAND_CATALOG[cmd].format(base=base, head=head)
            )

    # Test ownership validation: every deterministic obligation needs a test owner.
    missing_test_ownership: list[str] = []
    for obl in deterministic:
        owners = OBLIGATION_TEST_OWNERS.get(obl, [])
        if not owners:
            missing_test_ownership.append(f"{obl}: no declared test owner")
            continue
        if not any((ROOT / owner).exists() for owner in owners):
            missing_test_ownership.append(
                f"{obl}: test owner missing ({', '.join(owners)})"
            )

    required_artifacts = ["artifacts/feature-obligations.json"]
    if "security_benchmark" in deterministic:
        required_artifacts.append("security/security_scorecard.json")

    report = {
        "schema_version": registry.get("schema_version", 1),
        "base": git_rev_parse(base),
        "head": git_rev_parse(head),
        "changed_paths": sorted(changed_set),
        "unknown_paths": sorted(set(unknown_paths)),
        "allowlisted_paths": sorted(allowlisted_paths),
        "matched_features": matched_features,
        "obligations": {
            "deterministic": sorted(set(deterministic)),
            "live": sorted(set(live)),
            "skipped_optional_lanes": sorted(skipped_optional),
        },
        "commands": {k: sorted(set(v)) for k, v in commands.items()},
        "obligation_reasons": obligation_reasons,
        "missing_test_ownership": sorted(missing_test_ownership),
        "spine_touched": spine_touched,
        "required_artifacts": required_artifacts,
        "pass": not unknown_paths and not missing_test_ownership,
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="base git ref")
    parser.add_argument("--head", required=True, help="head git ref")
    parser.add_argument("--json-out", help="write JSON report to this path")
    args = parser.parse_args(argv)

    report = build_report(args.base, args.head)
    if args.json_out:
        out = (
            ROOT / args.json_out
            if not Path(args.json_out).is_absolute()
            else Path(args.json_out)
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Obligation report written to {out}")

    print(json.dumps(report, indent=2))

    if report["unknown_paths"]:
        print(
            "\nFAIL: unclassified changed paths require a registry entry or allowlist update:"
        )
        for path in report["unknown_paths"]:
            print(f"  - {path}")
    if report["missing_test_ownership"]:
        print("\nFAIL: obligations without test owners:")
        for item in report["missing_test_ownership"]:
            print(f"  - {item}")
    if not report["pass"]:
        return 1

    print("\nFeature-obligation classification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
