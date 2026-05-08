from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend" / "src" / "components"


def _home_client_view_ids() -> set[str]:
    text = (FRONTEND / "layout" / "HomeClient.tsx").read_text(encoding="utf-8")
    return set(re.findall(r'case "([^"]+)": return <', text))


def _onboarding_view_ids() -> set[str]:
    ids: set[str] = set()
    for path in FRONTEND.rglob("*.tsx"):
        text = path.read_text(encoding="utf-8")
        ids.update(re.findall(r'ViewOnboarding\s+viewId="([^"]+)"', text))
    return ids


def test_all_routed_menus_have_view_onboarding() -> None:
    missing = sorted(_home_client_view_ids() - _onboarding_view_ids())

    assert missing == []


def test_role_critical_menus_have_view_onboarding() -> None:
    covered = _onboarding_view_ids()

    for view_id in {
        "admin",
        "autoresearch",
        "compute",
        "loops",
        "settings",
        "skills",
        "project-settings",
    }:
        assert view_id in covered
