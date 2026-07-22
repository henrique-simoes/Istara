"""Count-to-zero ratchet test for the Pi full-replacement (master plan §4.2).

Loads ``legacy_allowlist.yaml`` — the ONLY file allowed to authorize a direct
legacy-plane call — runs ``scripts/pi_migration_inventory.py`` in-process and
asserts:

1. ``set(inventory) ⊆ set(allowlist)`` — every direct legacy-plane call site
   found by the scanner is explicitly allowlisted.
2. ``len(product entries) == EXPECTED_PRODUCT_SITES`` — the ratchet literal,
   updated (downward) by each migration wave.

``check_count_to_zero()`` raises RuntimeError on any violation and is reused
by the ``tests/e2e_test.py`` phase list.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST_PATH = Path(__file__).resolve().parent / "legacy_allowlist.yaml"
SCANNER_PATH = REPO_ROOT / "scripts" / "pi_migration_inventory.py"

# The ratchet literal for the current wave. W0 baseline was 87 (69 chat + 17
# embed + 1 browser bypass); each wave lowers this by exactly its migrated
# sites. W2 (complete) migrated all 9 interactive surfaces to the
# AgenticDispatcher — the 4 one-shot completion surfaces (context_dag,
# context_summarizer, presentation slides, UI-audit heuristics), the 4
# streaming ReAct loops (chat.py native + text fallback, interfaces.py design
# native + text fallback), and the browser_service browse_website tool
# (PiModelManager-resolved endpoint identity). W3 migrated the 8 research-spine
# + steering sites (agent_research L1 ReAct/L2 planner/L3 step executor/L5
# reflection, self_check L6 claim verification, agent_execution L7 skill
# reflection, agent_lifecycle L10 steering reply). W8 migrated all 17 embed
# sites (the embeddings.py/validation.py wrappers now route through
# agentic.embed; the 14 wrapper consumers inherit the dispatch with zero
# edits) — so the ratchet is now 53.
EXPECTED_PRODUCT_SITES = 53


# ---------------------------------------------------------------------------
# Allowlist loading — pyyaml when available, else a tiny-subset YAML parser.
# The allowlist is written in that subset (block mappings/lists, flow lists,
# quoted scalars, ints, full-line comments) so no dependency is required.
# ---------------------------------------------------------------------------

def _parse_scalar(text: str):
    text = text.strip()
    if text.startswith("["):
        if not text.endswith("]"):
            raise ValueError(f"malformed flow list: {text!r}")
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(item) for item in inner.split(",")]
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {'"', "'"}:
        return text[1:-1]
    if text.isdigit():
        return int(text)
    return text


def _tiny_yaml_load(text: str) -> dict:
    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        lines.append((indent, stripped))

    pos = 0

    def parse_block(indent: int):
        nonlocal pos
        if lines[pos][1].startswith("- "):
            items: list = []
            while (
                pos < len(lines)
                and lines[pos][0] == indent
                and lines[pos][1].startswith("- ")
            ):
                item_text = lines[pos][1][2:].strip()
                if ":" in item_text and not item_text.startswith(('"', "'")):
                    item: dict = {}
                    key, _, value = item_text.partition(":")
                    item[key.strip()] = _parse_scalar(value)
                    pos += 1
                    while pos < len(lines) and lines[pos][0] > indent:
                        key, _, value = lines[pos][1].partition(":")
                        item[key.strip()] = _parse_scalar(value)
                        pos += 1
                    items.append(item)
                else:
                    items.append(_parse_scalar(item_text))
                    pos += 1
            return items
        mapping: dict = {}
        while (
            pos < len(lines)
            and lines[pos][0] == indent
            and not lines[pos][1].startswith("- ")
        ):
            key, _, value = lines[pos][1].partition(":")
            pos += 1
            if value.strip():
                mapping[key.strip()] = _parse_scalar(value)
            else:
                mapping[key.strip()] = parse_block(lines[pos][0])
        return mapping

    return parse_block(0)


def load_allowlist(path: Path = ALLOWLIST_PATH) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml
    except ImportError:
        return _tiny_yaml_load(text)
    return yaml.safe_load(text)


def run_scanner() -> list[dict]:
    """Run scripts/pi_migration_inventory.py in-process and return its rows."""
    spec = importlib.util.spec_from_file_location("pi_migration_inventory", SCANNER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.scan()


def _allowlist_keys(allowlist: dict) -> set[str]:
    keys: set[str] = set()
    for section in ("product", "permanent"):
        for entry in allowlist.get(section) or []:
            keys.update(entry.get("keys") or [])
    return keys


def check_count_to_zero() -> None:
    """Raise RuntimeError naming every offending site on any violation."""
    allowlist = load_allowlist()
    problems: list[str] = []

    inventory_keys = {f"{row['file']}:{row['line']}" for row in run_scanner()}
    allowed = _allowlist_keys(allowlist)
    unauthorized = sorted(inventory_keys - allowed)
    if unauthorized:
        problems.append(
            "direct legacy-plane call sites NOT in "
            "tests/pi_migration/legacy_allowlist.yaml:\n  "
            + "\n  ".join(unauthorized)
        )

    product_entries = allowlist.get("product") or []
    if len(product_entries) != EXPECTED_PRODUCT_SITES:
        problems.append(
            f"allowlist has {len(product_entries)} product entries but the "
            f"ratchet expects {EXPECTED_PRODUCT_SITES}; a wave must remove its "
            "migrated sites AND lower EXPECTED_PRODUCT_SITES together"
        )
    yaml_expected = (allowlist.get("ratchet") or {}).get("expected_product_sites")
    if yaml_expected != EXPECTED_PRODUCT_SITES:
        problems.append(
            f"legacy_allowlist.yaml ratchet.expected_product_sites={yaml_expected} "
            f"disagrees with test literal EXPECTED_PRODUCT_SITES={EXPECTED_PRODUCT_SITES}"
        )

    if problems:
        raise RuntimeError("count-to-zero ratchet violated:\n" + "\n".join(problems))


def test_inventory_is_subset_of_allowlist():
    allowlist = load_allowlist()
    inventory_keys = {f"{row['file']}:{row['line']}" for row in run_scanner()}
    unauthorized = sorted(inventory_keys - _allowlist_keys(allowlist))
    assert not unauthorized, (
        "direct legacy-plane call sites missing from "
        "tests/pi_migration/legacy_allowlist.yaml:\n  " + "\n  ".join(unauthorized)
    )


def test_product_site_count_matches_ratchet():
    allowlist = load_allowlist()
    product_entries = allowlist.get("product") or []
    assert len(product_entries) == EXPECTED_PRODUCT_SITES, (
        f"allowlist has {len(product_entries)} product entries, ratchet expects "
        f"{EXPECTED_PRODUCT_SITES} (69 chat + 17 embed + 1 browser bypass at W0)"
    )
    yaml_expected = (allowlist.get("ratchet") or {}).get("expected_product_sites")
    assert yaml_expected == EXPECTED_PRODUCT_SITES, (
        f"legacy_allowlist.yaml ratchet.expected_product_sites={yaml_expected} "
        f"disagrees with test literal {EXPECTED_PRODUCT_SITES}"
    )


def test_allowlist_keys_are_unique():
    allowlist = load_allowlist()
    seen: set[str] = set()
    duplicates: list[str] = []
    for section in ("product", "permanent"):
        for entry in allowlist.get(section) or []:
            for key in entry.get("keys") or []:
                if key in seen:
                    duplicates.append(key)
                seen.add(key)
    assert not duplicates, "duplicate allowlist keys: " + ", ".join(sorted(duplicates))
