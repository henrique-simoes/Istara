#!/usr/bin/env python3
"""WCAG 2.2 AA contrast audit for the Agentic Core chooser (CF-SPEC-1 ITEM-005).

Measures every foreground/background pair AgenticCoreSection.tsx renders, in
both light and dark modes, against the surfaces declared in globals.css
(--background / .ui-panel) and the palette in frontend/tailwind.config.js.
Alpha-modified Tailwind colors (e.g. bg-istara-50/70) are composited over their
real parent chain before measuring.

Bar (DESIGN.md "Semantic tokens"): >= 4.5:1 body/helper text,
>= 3:1 UI boundaries, state borders, and focus indicators.

Exit codes: 0 all pairs pass, 1 any failure (missing tokens count as failures).

Usage:
    python scripts/check_a11y_contrast.py [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAILWIND_CONFIG = ROOT / "frontend" / "tailwind.config.js"

# Tailwind v3 default palette entries referenced by the chooser. The project
# istara palette is parsed live from tailwind.config.js so silent palette
# edits break this audit instead of drifting under it.
SLATE = {
    "50": "#f8fafc", "100": "#f1f5f9", "200": "#e2e8f0", "300": "#cbd5e1",
    "400": "#94a3b8", "500": "#64748b", "600": "#475569", "700": "#334155",
    "800": "#1e293b", "900": "#0f172a", "950": "#020617",
}
AMBER = {
    "50": "#fffbeb", "200": "#fde68a", "300": "#fcd34d",
    "800": "#92400e", "950": "#451a03",
}
RED = {"300": "#fca5a5", "700": "#b91c1c"}
BLUE = {"400": "#93c5fd", "600": "#2563eb"}
LITERALS = {"white": "#ffffff"}

LIGHT_PAGE = "#ffffff"
DARK_PAGE = SLATE["950"]
LIGHT_PANEL = "#ffffff"   # .ui-panel -> --ui-surface
DARK_PANEL = SLATE["900"]


def _parse_istara_palette() -> dict[str, str]:
    text = TAILWIND_CONFIG.read_text(encoding="utf-8")
    match = re.search(r"istara:\s*\{(.*?)\}", text, re.DOTALL)
    if not match:
        raise SystemExit("istara palette not found in tailwind.config.js")
    palette: dict[str, str] = {}
    for shade, hex_value in re.findall(r"(\d+):\s*\"(#[0-9a-fA-F]{6})\"", match.group(1)):
        palette[shade] = hex_value.lower()
    return palette


ISTARA = _parse_istara_palette()


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]


def _composite(fg_hex: str, alpha: float, bg_rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    fr, fg_, fb = _hex_to_rgb(fg_hex)
    return (
        fr * alpha + bg_rgb[0] * (1 - alpha),
        fg_ * alpha + bg_rgb[1] * (1 - alpha),
        fb * alpha + bg_rgb[2] * (1 - alpha),
    )


def _luminance(rgb: tuple[float, float, float]) -> float:
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(fg_rgb: tuple[float, float, float], bg_rgb: tuple[float, float, float]) -> float:
    l1, l2 = sorted((_luminance(fg_rgb), _luminance(bg_rgb)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def _resolve(token: str) -> str:
    if token in LITERALS:
        return LITERALS[token]
    family, _, shade = token.partition("-")
    source = {"istara": ISTARA, "slate": SLATE, "amber": AMBER, "red": RED, "blue": BLUE}[family]
    if shade not in source:
        raise KeyError(f"undefined color token: {token}")
    return source[shade]


def _effective(bg_chain: list[tuple[str, float]], base: str) -> tuple[float, float, float]:
    rgb = _hex_to_rgb(base)
    for token, alpha in reversed(bg_chain):
        rgb = _composite(_resolve(token), alpha, rgb)
    return rgb


# name, mode, fg token, background chain [(token, alpha)] outermost-last, kind, minimum
CARD_UNSEL_LIGHT: list[tuple[str, float]] = []
CARD_SEL_LIGHT: list[tuple[str, float]] = [("istara-50", 0.7)]
TILE_LIGHT: list[tuple[str, float]] = [("slate-50", 1.0)]
BENCH_LIGHT: list[tuple[str, float]] = [("white", 1.0)]
CARD_UNSEL_DARK: list[tuple[str, float]] = [("slate-900", 0.4)]
CARD_SEL_DARK: list[tuple[str, float]] = [("istara-950", 0.4)]
TILE_DARK: list[tuple[str, float]] = [("slate-900", 1.0)]
BENCH_DARK: list[tuple[str, float]] = [("slate-800", 1.0)]

PAIRS: list[dict[str, object]] = []


def _pair(name: str, mode: str, fg: str, chain: list[tuple[str, float]], kind: str, minimum: float, base: str) -> None:
    PAIRS.append(
        {
            "name": name,
            "mode": mode,
            "fg": fg,
            "chain": list(chain),
            "kind": kind,
            "minimum": minimum,
            "base": base,
        }
    )


# ── Light mode ────────────────────────────────────────────────────────────────
_pair("option-title/unselected", "light", "slate-950", CARD_UNSEL_LIGHT, "text", 4.5, LIGHT_PANEL)
_pair("option-title/selected", "light", "slate-950", CARD_SEL_LIGHT, "text", 4.5, LIGHT_PANEL)
_pair("option-description/unselected", "light", "slate-600", CARD_UNSEL_LIGHT, "text", 4.5, LIGHT_PANEL)
_pair("option-description/selected", "light", "slate-600", CARD_SEL_LIGHT, "text", 4.5, LIGHT_PANEL)
_pair("best-for-label/unselected", "light", "slate-500", CARD_UNSEL_LIGHT, "text", 4.5, LIGHT_PANEL)
_pair("best-for-label/selected", "light", "slate-500", CARD_SEL_LIGHT, "text", 4.5, LIGHT_PANEL)
_pair("selected-pill", "light", "white", [], "text", 4.5, _resolve("istara-600"))
_pair("provisional-badge-text", "light", "amber-800", [("amber-50", 1.0)], "text", 4.5, LIGHT_PANEL)
_pair("radio-circle/unselected-border", "light", "slate-500", CARD_UNSEL_LIGHT, "ui", 3.0, LIGHT_PANEL)
_pair("radio-circle/selected-border", "light", "istara-600", CARD_SEL_LIGHT, "ui", 3.0, LIGHT_PANEL)
_pair("card-border/selected-state", "light", "istara-600", CARD_UNSEL_LIGHT, "ui", 3.0, LIGHT_PANEL)
_pair("section-eyebrow", "light", "istara-700", [], "text", 4.5, LIGHT_PANEL)
_pair("section-heading", "light", "slate-950", [], "text", 4.5, LIGHT_PANEL)
_pair("section-lead", "light", "slate-600", [], "text", 4.5, LIGHT_PANEL)
_pair("principle-tile-strong", "light", "slate-900", TILE_LIGHT, "text", 4.5, LIGHT_PANEL)
_pair("principle-tile-text", "light", "slate-600", TILE_LIGHT, "text", 4.5, LIGHT_PANEL)
_pair("benchmark-label", "light", "slate-500", BENCH_LIGHT, "text", 4.5, LIGHT_PANEL)
_pair("benchmark-value", "light", "slate-900", BENCH_LIGHT, "text", 4.5, LIGHT_PANEL)
_pair("snapshot-note", "light", "slate-500", [], "text", 4.5, LIGHT_PANEL)
_pair("error-message", "light", "red-700", [], "text", 4.5, LIGHT_PANEL)
_pair("footer-strong", "light", "slate-700", [], "text", 4.5, LIGHT_PANEL)
_pair("footer-text", "light", "slate-500", [], "text", 4.5, LIGHT_PANEL)
_pair("focus-ring", "light", "blue-600", CARD_UNSEL_LIGHT, "ui", 3.0, LIGHT_PANEL)

# ── Dark mode ────────────────────────────────────────────────────────────────
_pair("option-title/unselected", "dark", "white", CARD_UNSEL_DARK, "text", 4.5, DARK_PANEL)
_pair("option-title/selected", "dark", "white", CARD_SEL_DARK, "text", 4.5, DARK_PANEL)
_pair("option-description/unselected", "dark", "slate-300", CARD_UNSEL_DARK, "text", 4.5, DARK_PANEL)
_pair("option-description/selected", "dark", "slate-300", CARD_SEL_DARK, "text", 4.5, DARK_PANEL)
_pair("best-for-label/unselected", "dark", "slate-400", CARD_UNSEL_DARK, "text", 4.5, DARK_PANEL)
_pair("best-for-label/selected", "dark", "slate-400", CARD_SEL_DARK, "text", 4.5, DARK_PANEL)
_pair("selected-pill", "dark", "white", [], "text", 4.5, _resolve("istara-600"))
_pair("provisional-badge-text", "dark", "amber-200", [("amber-950", 0.4), ("slate-900", 0.4)], "text", 4.5, DARK_PANEL)
_pair("radio-circle/unselected-border", "dark", "slate-400", CARD_UNSEL_DARK, "ui", 3.0, DARK_PANEL)
_pair("radio-circle/selected-border", "dark", "istara-400", CARD_SEL_DARK, "ui", 3.0, DARK_PANEL)
_pair("card-border/selected-state", "dark", "istara-400", CARD_UNSEL_DARK, "ui", 3.0, DARK_PANEL)
_pair("section-eyebrow", "dark", "istara-300", [], "text", 4.5, DARK_PANEL)
_pair("section-heading", "dark", "white", [], "text", 4.5, DARK_PANEL)
_pair("section-lead", "dark", "slate-300", [], "text", 4.5, DARK_PANEL)
_pair("principle-tile-strong", "dark", "white", TILE_DARK, "text", 4.5, DARK_PANEL)
_pair("principle-tile-text", "dark", "slate-300", TILE_DARK, "text", 4.5, DARK_PANEL)
_pair("benchmark-label", "dark", "slate-400", BENCH_DARK, "text", 4.5, DARK_PANEL)
_pair("benchmark-value", "dark", "white", BENCH_DARK, "text", 4.5, DARK_PANEL)
_pair("snapshot-note", "dark", "slate-400", [], "text", 4.5, DARK_PANEL)
_pair("error-message", "dark", "red-300", [], "text", 4.5, DARK_PANEL)
_pair("footer-strong", "dark", "slate-200", [], "text", 4.5, DARK_PANEL)
_pair("footer-text", "dark", "slate-400", [], "text", 4.5, DARK_PANEL)
_pair("focus-ring", "dark", "blue-400", CARD_UNSEL_DARK, "ui", 3.0, DARK_PANEL)


def run() -> tuple[list[dict[str, object]], bool]:
    findings: list[dict[str, object]] = []
    ok = True
    for spec in PAIRS:
        try:
            fg_rgb = _hex_to_rgb(_resolve(str(spec["fg"])))
            bg_rgb = _effective(list(spec["chain"]), str(spec["base"]))  # type: ignore[arg-type]
            ratio = round(_ratio(fg_rgb, bg_rgb), 2)
            missing = False
        except KeyError as exc:
            ratio = 0.0
            missing = True
            findings.append({**spec, "ratio": None, "error": str(exc)})
            ok = False
            continue
        passed = ratio >= float(spec["minimum"])
        ok = ok and passed
        row = {**spec, "ratio": ratio, "passed": passed}
        findings.append(row)
    return findings, ok


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = parser.parse_args()

    findings, ok = run()
    if args.json:
        print(json.dumps({"ok": ok, "pairs": findings}, indent=2))
    else:
        width = max(len(str(f["name"])) for f in findings)
        for f in findings:
            status = "PASS" if f.get("passed") else "FAIL"
            ratio = f.get("ratio")
            detail = f.get("error") or f"{ratio}:1 (min {f['minimum']})"
            print(f"{status}  [{f['mode']:^5}] {str(f['name']):<{width}}  {detail}")
        print()
        print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
