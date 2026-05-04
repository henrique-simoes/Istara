#!/usr/bin/env python3
"""Integrity checker for Istara's active release governance docs."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TECH_MD = ROOT / "Tech.md"
ACTIVE_GOVERNANCE_DOCS = [
    TECH_MD,
    ROOT / "CHANGE_CHECKLIST.md",
    ROOT / "SYSTEM_CHANGE_MATRIX.md",
    ROOT / "SYSTEM_PROMPT.md",
]
LEGACY_COMPASS_DOCS = [
    ROOT / "AGENT.md",
    ROOT / "AGENT_ENTRYPOINT.md",
    ROOT / "COMPLETE_SYSTEM.md",
    ROOT / "SYSTEM_INTEGRITY_GUIDE.md",
]
BACKEND_DEPENDENCY_MARKERS = {
    "webauthn": "WebAuthn/FIDO2 passkey support",
    "openai-whisper": "local interview transcription",
    "pydub": "audio format conversion fallback",
}


def check_exists(issues: list[str]) -> None:
    for path in ACTIVE_GOVERNANCE_DOCS:
        if not path.exists():
            issues.append(f"MISSING: active governance doc {path.name} does not exist")


def check_legacy_compass_not_active(issues: list[str]) -> None:
    """Guard against accidentally re-promoting legacy Compass markdown to CI truth."""
    ci_text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8").lower()
    build_text = (
        (ROOT / ".github" / "workflows" / "build-installers.yml")
        .read_text(encoding="utf-8")
        .lower()
    )
    release_text = (ROOT / "scripts" / "prepare-release.sh").read_text(encoding="utf-8").lower()

    legacy_names = {path.name.lower() for path in LEGACY_COMPASS_DOCS}
    for name in sorted(legacy_names):
        if name in ci_text or name in build_text or name in release_text:
            issues.append(
                f"LEGACY: {name} is referenced by active CI/release governance. "
                "Keep legacy Compass markdown optional; Compass Forge is the control plane."
            )

    if (
        "update_agent_md.py" in ci_text
        or "update_agent_md.py" in build_text
        or "update_agent_md.py" in release_text
    ):
        issues.append(
            "LEGACY: scripts/update_agent_md.py is referenced by active CI/release governance. "
            "Generated legacy Compass docs are optional and must not block release checks."
        )


def check_tech_md_freshness(issues: list[str]) -> None:
    """Verify Tech.md mentions key concepts from recent major changes.

    This is a keyword-based heuristic to catch obvious omissions.
    When a new major feature is added to the codebase, add its signature
    keywords here so Tech.md freshness can be verified.
    """
    if not TECH_MD.exists():
        issues.append("MISSING: Tech.md does not exist")
        return

    tech_text = TECH_MD.read_text(encoding="utf-8").lower()

    # Signature keywords for major features that should be documented in Tech.md
    required_topics = {
        "argon2": "Argon2id password hashing",
        "totp": "TOTP two-factor authentication",
        "webauthn": "WebAuthn/FIDO2 passkeys",
        "steering": "Mid-execution steering",
        "cap_drop": "Docker container hardening",
        "no-new-privileges": "Container security (no-new-privileges)",
        "frontend-net": "Network segmentation (Docker networks)",
        "caddy": "Caddy/TLS configuration",
        "pre-push": "Compass authorship enforcement",
        "stitch": "Google Stitch AI screen generation",
        "interfaces": "Interfaces & Design System",
        "design-chat": "Design-specific chat with RAG",
        "transcription": "Voice transcription pipeline",
        "playwright": "Playwright-based browser skills",
        "evaluate-research": "LLM-as-Judge evaluation framework",
        "game theory": "Game Theory participant simulation",
        "audit log middleware": "Audit Log Middleware",
        "opentelemetry": "Local-First OpenTelemetry & Tracing",
        "agent hooks": "Agent Hooks lifecycle interception",
        "compute registry": "Unified ComputeRegistry architecture",
        "compute capacity": "Compute capacity envelope for pooled hardware",
        "rfc 3986": "RFC 3986 URI normalization",
        "layer 5": "Layer 5 Real-World Orchestration benchmarks",
        "minto": "Minto Pyramid and SCR framework for presentations",
        "connection string": "Connection string lifecycle and relay management",
        "governed evolution": "System-wide governed evolution contract",
        "sandbox evaluation": "Pre-apply sandbox evaluation for self-improvement proposals",
        "production rehearsal": "Production rehearsal gate for release-critical processes",
        "reasoningbank": "ReasoningBank shared orchestration memory",
        "dgm-h": "DGM-H archive evolution and rollback lineage",
        "route/type contract": "Route/type contract governance",
    }

    missing = []
    for keyword, description in required_topics.items():
        if keyword not in tech_text:
            missing.append(description)

    if missing:
        issues.append(
            f"TECH.md: Missing documentation for: {', '.join(missing)}. "
            f"Update Tech.md to reflect current security architecture."
        )


def check_backend_dependency_alignment(issues: list[str]) -> None:
    """Verify source-install and editable-install dependency manifests stay aligned."""
    requirements_text = (ROOT / "backend" / "requirements.txt").read_text(encoding="utf-8").lower()
    pyproject_text = (ROOT / "backend" / "pyproject.toml").read_text(encoding="utf-8").lower()

    missing = []
    for marker, description in BACKEND_DEPENDENCY_MARKERS.items():
        if marker in requirements_text and marker not in pyproject_text:
            missing.append(description)

    if missing:
        issues.append(
            "DEPENDENCIES: backend/pyproject.toml is missing dependencies present in "
            f"backend/requirements.txt for: {', '.join(missing)}."
        )


def main() -> int:
    issues: list[str] = []

    print("Istara integrity check")
    print("=" * 50)

    check_exists(issues)
    if any(issue.startswith("MISSING") for issue in issues):
        for issue in issues:
            print(f"  - {issue}")
        return 1

    check_legacy_compass_not_active(issues)
    check_tech_md_freshness(issues)
    check_backend_dependency_alignment(issues)

    if issues:
        print("Integrity issues detected:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    print("Active release governance docs are coherent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
