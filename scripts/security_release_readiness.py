#!/usr/bin/env python3
"""Validate Istara's release security readiness evidence."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@dataclass(frozen=True)
class ReadinessCheck:
    path: str
    label: str
    snippet: str


REQUIRED_SNIPPETS: tuple[ReadinessCheck, ...] = (
    ReadinessCheck(
        "SECURITY.md", "vulnerability disclosure", "Reporting a Vulnerability"
    ),
    ReadinessCheck("SECURITY.md", "incident response", "Incident Response"),
    ReadinessCheck(
        "SECURITY.md", "log sensitivity", "Logs are treated as sensitive data"
    ),
    ReadinessCheck(
        "security/RELEASE_SECURITY_READINESS.md",
        "Better Auth comparison",
        "Better Auth",
    ),
    ReadinessCheck(
        "security/RELEASE_SECURITY_READINESS.md",
        "OWASP ASVS mapping",
        "OWASP ASVS",
    ),
    ReadinessCheck(
        "security/RELEASE_SECURITY_READINESS.md",
        "NIST identity mapping",
        "NIST SP 800-63",
    ),
    ReadinessCheck(
        "security/RELEASE_SECURITY_READINESS.md",
        "WebAuthn mapping",
        "W3C WebAuthn",
    ),
    ReadinessCheck(
        "security/RELEASE_SECURITY_READINESS.md",
        "Scorecard mapping",
        "OpenSSF Scorecard",
    ),
    ReadinessCheck(
        "security/RELEASE_SECURITY_READINESS.md",
        "artifact attestations mapping",
        "GitHub Artifact Attestations",
    ),
    ReadinessCheck(
        "security/RELEASE_SECURITY_READINESS.md",
        "log redaction requirement",
        "tokens, credentials, connection strings",
    ),
    ReadinessCheck(
        "security/RELEASE_SECURITY_READINESS.md",
        "single-model serving guard",
        "must not autoload multiple heavy models",
    ),
    ReadinessCheck(
        "security/RELEASE_SECURITY_READINESS.md",
        "runtime artifact exclusion",
        "LLMs/",
    ),
    ReadinessCheck(
        ".github/workflows/scorecard.yml",
        "OpenSSF Scorecard action",
        "ossf/scorecard-action",
    ),
    ReadinessCheck(
        ".github/workflows/scorecard.yml",
        "Scorecard SARIF upload",
        "github/codeql-action/upload-sarif",
    ),
    ReadinessCheck(
        ".github/workflows/scorecard.yml",
        "Scorecard security-events permission",
        "security-events: write",
    ),
    ReadinessCheck(
        ".github/workflows/build-installers.yml",
        "artifact attestation action",
        "actions/attest-build-provenance",
    ),
    ReadinessCheck(
        ".github/workflows/build-installers.yml",
        "attestation permission",
        "attestations: write",
    ),
    ReadinessCheck(
        ".github/workflows/build-installers.yml",
        "OIDC permission",
        "id-token: write",
    ),
    ReadinessCheck(
        "scripts/prepare-release.sh",
        "release readiness script",
        "python scripts/security_release_readiness.py",
    ),
    ReadinessCheck(
        ".github/workflows/ci.yml",
        "CI readiness script",
        "python scripts/security_release_readiness.py",
    ),
)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _load_matrix() -> dict[str, Any]:
    with (ROOT / "security" / "control_matrix.json").open(encoding="utf-8") as handle:
        matrix = json.load(handle)
    if not isinstance(matrix, dict):
        raise ValueError("security/control_matrix.json must be a JSON object")
    return matrix


def evaluate_readiness() -> dict[str, Any]:
    issues: list[str] = []

    for check in REQUIRED_SNIPPETS:
        path = ROOT / check.path
        if not path.exists():
            issues.append(f"{check.path}: missing {check.label}")
            continue
        text = path.read_text(encoding="utf-8").lower()
        if check.snippet.lower() not in text:
            issues.append(f"{check.path}: missing {check.label} (`{check.snippet}`)")

    try:
        matrix = _load_matrix()
    except Exception as exc:  # pragma: no cover - defensive CLI path
        return {"status": "fail", "issues": [f"control matrix unreadable: {exc}"]}

    threshold = (
        matrix.get("thresholds", {})
        .get("production_release", {})
        .get("minimum_score_percent", 0)
    )
    if float(threshold) < 98:
        issues.append(
            "security/control_matrix.json: production threshold must be >= 98"
        )

    partial_controls = [
        str(control.get("id", "unknown"))
        for control in matrix.get("controls", [])
        if str(control.get("status", "")).lower() == "partial"
    ]
    if partial_controls:
        issues.append(
            "security/control_matrix.json: partial controls remain: "
            + ", ".join(partial_controls)
        )

    standards = {
        str(standard.get("id", ""))
        for standard in matrix.get("standards", [])
        if isinstance(standard, dict)
    }
    for required in ("better-auth", "owasp-logging", "github-attestations"):
        if required not in standards:
            issues.append(f"security/control_matrix.json: missing {required} standard")

    try:
        from app.core.security_headers import (
            SECURITY_HEADERS,
            validate_security_headers,
        )

        issues.extend(
            f"security headers: {issue}"
            for issue in validate_security_headers(SECURITY_HEADERS)
        )
    except Exception as exc:  # pragma: no cover - defensive CLI path
        issues.append(f"security headers contract unreadable: {exc}")

    try:
        from app.core.auth_origins import production_security_configuration_issues

        secure_production_config = SimpleNamespace(
            istara_runtime_profile="public",
            team_mode=True,
            jwt_secret="x" * 48,
            cors_origins="https://istara.example.com",
            webauthn_origins="https://istara.example.com",
            webauthn_rp_id="istara.example.com",
            cors_origin_regex="",
        )
        issues.extend(
            f"production auth config: {issue}"
            for issue in production_security_configuration_issues(
                secure_production_config
            )
        )
    except Exception as exc:  # pragma: no cover - defensive CLI path
        issues.append(f"production auth config audit unreadable: {exc}")

    return {
        "status": "pass" if not issues else "fail",
        "minimum_score_percent": threshold,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="print JSON output")
    args = parser.parse_args()

    result = evaluate_readiness()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    elif result["status"] == "pass":
        print("Release security readiness check passed.")
    else:
        print("Release security readiness check failed:")
        for issue in result["issues"]:
            print(f"  - {issue}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
