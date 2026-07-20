"""Canonical tool catalog export for the Pi runtime.

The authoritative tool contract lives in Python (``OPENAI_TOOLS`` in
``app.skills.system_actions``). The Pi worker never hand-maintains a schema: the
run catalog is serialized here and sent at ``session.open``. Each OpenAI
function's ``parameters`` block is already JSON Schema — the exact shape the
pi-agent-core tools validate against — so the pass-through is mechanical.
"""

from __future__ import annotations

from typing import Any, Iterable

from app.skills.system_actions import OPENAI_TOOLS


def build_tool_catalog(allowed_tools: Iterable[str] | None = None) -> list[dict[str, Any]]:
    """Return ``[{name, description, parameters}]`` for the worker.

    When ``allowed_tools`` is provided the catalog is restricted to that
    allowlist (route- or delegation-scoped subsets); otherwise the full
    canonical chat surface is exported.
    """
    allow = set(allowed_tools) if allowed_tools is not None else None
    catalog: list[dict[str, Any]] = []
    for entry in OPENAI_TOOLS:
        fn = entry.get("function", {})
        name = fn.get("name")
        if not name:
            continue
        if allow is not None and name not in allow:
            continue
        catalog.append(
            {
                "name": name,
                "description": fn.get("description", name),
                "parameters": fn.get("parameters", {"type": "object", "properties": {}}),
            }
        )
    return catalog


def catalog_tool_names(allowed_tools: Iterable[str] | None = None) -> set[str]:
    return {entry["name"] for entry in build_tool_catalog(allowed_tools)}
