#!/usr/bin/env python3
"""Integrity checker — verifies SYSTEM_INTEGRITY_GUIDE.md is in sync with the codebase.

Run: python scripts/check_integrity.py
Returns exit code 0 if in sync, 1 if drift detected.

This script detects when the guide is out of date by checking:
1. Models registered in database.py vs documented in the guide
2. Routes registered in main.py vs documented in the guide
3. Skill definitions on disk vs documented in the guide
4. Frontend types vs documented in the guide
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDE = ROOT / "SYSTEM_INTEGRITY_GUIDE.md"
DRIFT = []


def check_models():
    """Check that all models in database.py init_db() are documented."""
    db_file = ROOT / "backend" / "app" / "models" / "database.py"
    if not db_file.exists():
        return
    content = db_file.read_text()
    # Extract all import lines in init_db
    imports = re.findall(r"from app\.models\.(\w+) import", content)
    imports += re.findall(r"from app\.core\.(\w+) import", content)

    guide_text = GUIDE.read_text() if GUIDE.exists() else ""
    for mod in imports:
        # Check if the module name appears anywhere in the guide
        if mod not in guide_text and mod.replace("_", " ") not in guide_text.lower():
            DRIFT.append(f"MODEL: '{mod}' registered in database.py but not found in SYSTEM_INTEGRITY_GUIDE.md")


def check_routes():
    """Check that all routers in main.py are documented."""
    main_file = ROOT / "backend" / "app" / "main.py"
    if not main_file.exists():
        return
    content = main_file.read_text()
    # Find all include_router calls
    routers = re.findall(r'include_router\((\w+)\.router', content)

    guide_text = GUIDE.read_text() if GUIDE.exists() else ""
    for router_name in routers:
        clean = router_name.replace("_routes", "").replace("_router", "")
        if clean not in guide_text and clean.replace("_", " ") not in guide_text.lower():
            DRIFT.append(f"ROUTE: '{router_name}' registered in main.py but not found in SYSTEM_INTEGRITY_GUIDE.md")


def check_skills():
    """Check that all skill definition JSONs are documented."""
    skills_dir = ROOT / "backend" / "app" / "skills" / "definitions"
    if not skills_dir.exists():
        return
    skill_files = [f.stem for f in skills_dir.glob("*.json") if not f.stem.startswith("_")]

    guide_text = GUIDE.read_text() if GUIDE.exists() else ""
    for skill in skill_files:
        if skill not in guide_text:
            DRIFT.append(f"SKILL: '{skill}' exists in definitions/ but not found in SYSTEM_INTEGRITY_GUIDE.md")


def check_frontend_types():
    """Check that all exported interfaces in types.ts are documented."""
    types_file = ROOT / "frontend" / "src" / "lib" / "types.ts"
    if not types_file.exists():
        return
    content = types_file.read_text()
    interfaces = re.findall(r"export interface (\w+)", content)

    guide_text = GUIDE.read_text() if GUIDE.exists() else ""
    for iface in interfaces:
        if iface not in guide_text:
            DRIFT.append(f"TYPE: '{iface}' exported in types.ts but not found in SYSTEM_INTEGRITY_GUIDE.md")


def check_guide_exists():
    """Check that the guide files exist."""
    for name in ["SYSTEM_INTEGRITY_GUIDE.md", "CHANGE_CHECKLIST.md", "INTEGRITY_INDEX.md"]:
        if not (ROOT / name).exists():
            DRIFT.append(f"MISSING: {name} does not exist")


def main():
    print("🔍 ReClaw Integrity Check")
    print("=" * 50)

    check_guide_exists()
    if any("MISSING" in d for d in DRIFT):
        for d in DRIFT:
            print(f"  ❌ {d}")
        sys.exit(1)

    check_models()
    check_routes()
    check_skills()
    check_frontend_types()

    if DRIFT:
        print(f"\n⚠️  {len(DRIFT)} drift(s) detected:\n")
        for d in DRIFT:
            print(f"  ❌ {d}")
        print(f"\n→ Update SYSTEM_INTEGRITY_GUIDE.md to fix these.")
        sys.exit(1)
    else:
        print("\n✅ System integrity guide is in sync with codebase.")
        sys.exit(0)


if __name__ == "__main__":
    main()
