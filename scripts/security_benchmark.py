#!/usr/bin/env python3
"""Evaluate Istara's auth/security benchmark control matrix."""

from __future__ import annotations

import argparse
import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MATRIX = ROOT / "security" / "control_matrix.json"

ALLOWED_STATUSES = {"pass", "partial", "fail", "na", "waived"}
ALLOWED_SEVERITIES = {"critical", "high", "medium", "low"}


@dataclass(frozen=True)
class BenchmarkResult:
    scorecard: dict[str, Any]
    passed: bool


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def load_matrix(path: Path = DEFAULT_MATRIX) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        matrix = json.load(handle)
    if not isinstance(matrix, dict):
        raise ValueError("control matrix must be a JSON object")
    return matrix


def read_changed_paths(paths: list[str], paths_file: Path | None) -> list[str]:
    changed = list(paths)
    if paths_file is not None:
        changed.extend(
            line.strip()
            for line in paths_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    return [normalize_path(path) for path in changed if path.strip()]


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def validate_matrix(matrix: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    for key in (
        "schema_version",
        "benchmark_version",
        "last_reviewed",
        "thresholds",
        "standards",
        "controls",
    ):
        if key not in matrix:
            issues.append(f"matrix missing required key: {key}")

    standards = matrix.get("standards", [])
    if not isinstance(standards, list) or not standards:
        issues.append("matrix must define at least one standard")
    else:
        for index, standard in enumerate(standards):
            if not isinstance(standard, dict):
                issues.append(f"standards[{index}] must be an object")
                continue
            for key in (
                "id",
                "name",
                "current_version",
                "official_url",
                "last_checked",
            ):
                if not str(standard.get(key, "")).strip():
                    issues.append(f"standard {standard.get('id', index)} missing {key}")

    controls = matrix.get("controls", [])
    if not isinstance(controls, list) or not controls:
        issues.append("matrix must define at least one control")
        return issues

    seen_ids: set[str] = set()
    for index, control in enumerate(controls):
        if not isinstance(control, dict):
            issues.append(f"controls[{index}] must be an object")
            continue

        control_id = str(control.get("id", "")).strip()
        if not control_id:
            issues.append(f"controls[{index}] missing id")
        elif control_id in seen_ids:
            issues.append(f"duplicate control id: {control_id}")
        seen_ids.add(control_id)

        status = str(control.get("status", "")).lower()
        severity = str(control.get("severity", "")).lower()
        if status not in ALLOWED_STATUSES:
            issues.append(f"{control_id}: invalid status {status!r}")
        if severity not in ALLOWED_SEVERITIES:
            issues.append(f"{control_id}: invalid severity {severity!r}")

        evidence = control.get("evidence")
        if status == "pass" and (not isinstance(evidence, list) or not evidence):
            issues.append(f"{control_id}: pass controls require evidence")
        if status in {"pass", "partial", "waived"}:
            if not isinstance(evidence, list) or not all(
                str(item).strip() for item in evidence
            ):
                issues.append(
                    f"{control_id}: evidence entries must be non-empty strings"
                )

        if not isinstance(control.get("standards", []), list) or not control.get(
            "standards"
        ):
            issues.append(f"{control_id}: missing standards mapping")

    return issues


def evaluate_matrix(
    matrix: dict[str, Any], changed_paths: list[str] | None = None
) -> BenchmarkResult:
    validation_issues = validate_matrix(matrix)
    thresholds = matrix.get("thresholds", {}).get("production_release", {})
    change_policy = matrix.get("thresholds", {}).get("auth_security_change", {})
    controls = matrix.get("controls", [])

    block_fail_statuses = set(thresholds.get("block_fail_statuses", ["fail"]))
    block_partial_severities = set(
        thresholds.get("block_partial_severities", ["critical", "high"])
    )
    minimum_score = float(thresholds.get("minimum_score_percent", 90))
    partial_credit = float(thresholds.get("partial_credit", 0.5))
    waived_credit = float(thresholds.get("waived_credit", 0.5))
    require_evidence_for_pass = bool(thresholds.get("require_evidence_for_pass", True))

    changed_paths = [normalize_path(path) for path in (changed_paths or [])]
    patterns = [
        normalize_path(pattern)
        for pattern in change_policy.get("changed_path_patterns", [])
    ]
    triggered_paths = sorted(
        path for path in changed_paths if matches_any(path, patterns)
    )

    counts = {status: 0 for status in sorted(ALLOWED_STATUSES)}
    severity_counts = {severity: 0 for severity in sorted(ALLOWED_SEVERITIES)}
    blocked_controls: list[dict[str, str]] = []
    warnings: list[str] = []
    applicable = 0
    earned = 0.0

    for control in controls:
        control_id = str(control.get("id", "unknown"))
        status = str(control.get("status", "")).lower()
        severity = str(control.get("severity", "")).lower()
        evidence = control.get("evidence", [])

        if status in counts:
            counts[status] += 1
        if severity in severity_counts:
            severity_counts[severity] += 1

        if status != "na":
            applicable += 1
        if status == "pass":
            earned += 1
        elif status == "partial":
            earned += partial_credit
        elif status == "waived":
            earned += waived_credit

        if status in block_fail_statuses:
            blocked_controls.append(
                {
                    "id": control_id,
                    "status": status,
                    "severity": severity,
                    "reason": "blocking status",
                }
            )
        if status == "partial" and severity in block_partial_severities:
            blocked_controls.append(
                {
                    "id": control_id,
                    "status": status,
                    "severity": severity,
                    "reason": "critical/high partial control",
                }
            )
        if require_evidence_for_pass and status == "pass" and not evidence:
            blocked_controls.append(
                {
                    "id": control_id,
                    "status": status,
                    "severity": severity,
                    "reason": "pass control missing evidence",
                }
            )

        if status == "partial" and severity in {"medium", "low"}:
            warnings.append(f"{control_id}: partial {severity} maturity item")

    score_percent = round((earned / applicable * 100), 2) if applicable else 0.0
    if score_percent < minimum_score:
        blocked_controls.append(
            {
                "id": "THRESHOLD",
                "status": "fail",
                "severity": "critical",
                "reason": f"score {score_percent}% is below {minimum_score}%",
            }
        )

    if validation_issues:
        blocked_controls.append(
            {
                "id": "SCHEMA",
                "status": "fail",
                "severity": "critical",
                "reason": "matrix validation failed",
            }
        )

    scorecard = {
        "benchmark_version": matrix.get("benchmark_version"),
        "last_reviewed": matrix.get("last_reviewed"),
        "status": "pass" if not blocked_controls else "fail",
        "score_percent": score_percent,
        "minimum_score_percent": minimum_score,
        "counts": counts,
        "severity_counts": severity_counts,
        "applicable_controls": applicable,
        "earned_points": round(earned, 2),
        "auth_security_change_detected": bool(triggered_paths),
        "triggered_paths": triggered_paths,
        "blocked_controls": blocked_controls,
        "warnings": warnings,
        "validation_issues": validation_issues,
    }
    return BenchmarkResult(scorecard=scorecard, passed=not blocked_controls)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--changed-path", action="append", default=[])
    parser.add_argument("--changed-paths-file", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-threshold", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        matrix = load_matrix(args.matrix)
        changed_paths = read_changed_paths(args.changed_path, args.changed_paths_file)
        result = evaluate_matrix(matrix, changed_paths=changed_paths)
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        scorecard = {
            "status": "fail",
            "error": str(exc),
            "blocked_controls": [
                {
                    "id": "RUNTIME",
                    "status": "fail",
                    "severity": "critical",
                    "reason": str(exc),
                }
            ],
        }
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(scorecard, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        print(json.dumps(scorecard, indent=2, sort_keys=True))
        return 1

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result.scorecard, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(result.scorecard, indent=2, sort_keys=True))
    if args.fail_on_threshold and not result.passed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
