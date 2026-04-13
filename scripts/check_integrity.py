#!/usr/bin/env python3
"""Integrity checker for Istara's living architecture docs."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from update_agent_md import (
    AGENT_MD,
    COMPLETE_SYSTEM_MD,
    ROOT,
    build_agent_document,
    build_complete_system_document,
    build_inventory,
)

GUIDE = ROOT / "SYSTEM_INTEGRITY_GUIDE.md"
TECH_MD = ROOT / "Tech.md"
PROMPT_DOCS = [
    ROOT / "AGENT_ENTRYPOINT.md",
    ROOT / "SYSTEM_PROMPT.md",
    ROOT / "SYSTEM_CHANGE_MATRIX.md",
    ROOT / "CLAUDE.md",
    ROOT / "GEMINI.md",
]


def check_exists(issues: list[str]) -> None:
    required = [AGENT_MD, COMPLETE_SYSTEM_MD, GUIDE, *PROMPT_DOCS]
    for path in required:
        if not path.exists():
            issues.append(f"MISSING: {path.name} does not exist")


def check_generated_docs(issues: list[str]) -> None:
    inventory = build_inventory()
    expected = {
        AGENT_MD: build_agent_document(inventory),
        COMPLETE_SYSTEM_MD: build_complete_system_document(inventory),
    }
    for path, content in expected.items():
        if not path.exists():
            continue
        if path.read_text(encoding="utf-8") != content:
            issues.append(f"DRIFT: {path.name} is out of date. Run `python scripts/update_agent_md.py`.")


def check_legacy_guide_mentions(issues: list[str]) -> None:
    if not GUIDE.exists():
        return
    guide_text = GUIDE.read_text(encoding="utf-8")

    database_file = ROOT / "backend" / "app" / "models" / "database.py"
    if database_file.exists():
        content = database_file.read_text(encoding="utf-8")
        imports = re.findall(r"from app\.models\.(\w+) import", content)
        imports += re.findall(r"from app\.core\.(\w+) import", content)
        for mod in imports:
            if mod not in guide_text and mod.replace("_", " ") not in guide_text.lower():
                issues.append(f"GUIDE: `{mod}` is registered in database.py but not mentioned in SYSTEM_INTEGRITY_GUIDE.md")

    main_file = ROOT / "backend" / "app" / "main.py"
    if main_file.exists():
        content = main_file.read_text(encoding="utf-8")
        routers = re.findall(r"include_router\((\w+)\.router", content)
        for router_name in routers:
            clean = router_name.replace("_routes", "").replace("_router", "")
            if clean not in guide_text and clean.replace("_", " ") not in guide_text.lower():
                issues.append(f"GUIDE: router `{router_name}` is registered in main.py but not mentioned in SYSTEM_INTEGRITY_GUIDE.md")


def check_tech_md_freshness(issues: list[str]) -> None:
    """Verify Tech.md mentions key concepts from recent major changes.

    This is a keyword-based heuristic to catch obvious omissions.
    When a new major feature is added to the codebase, add its signature
    keywords here so Tech.md freshness can be verified.
    """
    if not TECH_MD.exists():
        issues.append(f"MISSING: Tech.md does not exist")
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


def main() -> int:
    issues: list[str] = []

    print("Istara integrity check")
    print("=" * 50)

    check_exists(issues)
    if any(issue.startswith("MISSING") for issue in issues):
        for issue in issues:
            print(f"  - {issue}")
        return 1

    check_generated_docs(issues)
    check_legacy_guide_mentions(issues)
    check_tech_md_freshness(issues)

    if issues:
        print("Integrity issues detected:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    print("All tracked architecture docs are in sync.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
