#!/usr/bin/env python3
"""Generate living agent/system docs from the current Istara codebase.

This script keeps the main LLM-facing docs grounded in the implementation:
- AGENT.md: concise operational map for coding agents
- COMPLETE_SYSTEM.md: broader architecture + coverage map

Usage:
    python scripts/update_agent_md.py
    python scripts/update_agent_md.py --check
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENT_MD = ROOT / "AGENT.md"
COMPLETE_SYSTEM_MD = ROOT / "COMPLETE_SYSTEM.md"
AGENT_ENTRYPOINT_MD = ROOT / "AGENT_ENTRYPOINT.md"
VERSION_FILE = ROOT / "VERSION"

BACKEND = ROOT / "backend" / "app"
FRONTEND = ROOT / "frontend" / "src"
TESTS_ROOT = ROOT / "tests"
SKILL_DEFINITIONS = BACKEND / "skills" / "definitions"
PERSONAS = BACKEND / "agents" / "personas"
ROUTES = BACKEND / "api" / "routes"
MODELS = BACKEND / "models"
STORES = FRONTEND / "stores"
WEBSOCKET_FILE = BACKEND / "api" / "websocket.py"
DESKTOP_SRC = ROOT / "desktop" / "src-tauri" / "src"
RELAY_ROOT = ROOT / "relay"
CHANNELS_DIR = BACKEND / "channels"
SURVEY_PLATFORMS_DIR = BACKEND / "services" / "survey_platforms"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def titleize(value: str) -> str:
    return value.replace("-", " ").replace("_", " ").title()


def read_version() -> str:
    if VERSION_FILE.exists():
        return read_text(VERSION_FILE).strip()
    return "unknown"


def scan_test_layers() -> dict[str, list[str]]:
    """Dynamically discover testing layers from the tests/ directory.
    
    Categorizes subdirectories (e.g. simulation, benchmarks, integration)
    and root-level files (e.g. e2e_test.py).
    """
    layers = defaultdict(list)
    if not TESTS_ROOT.exists():
        return layers

    # 1. Scan subdirectories for specific patterns
    for path in sorted(TESTS_ROOT.iterdir()):
        if path.is_dir() and not path.name.startswith(("_", ".")):
            # Label based on directory name
            label = f"Layer: {titleize(path.name)}"
            # Find all test files in this layer
            test_files = sorted([p.name for p in path.glob("test_*.py")])
            test_files += sorted([p.name for p in path.glob("*.mjs")])
            if test_files:
                layers[label] = test_files

    # 2. Scan root-level test files (Journeys)
    root_tests = sorted([p.name for p in TESTS_ROOT.glob("test_*.py")])
    root_tests += sorted([p.name for p in TESTS_ROOT.glob("*_test.py")])
    if root_tests:
        layers["Test Journeys"] = root_tests

    return dict(layers)


def scan_routes() -> list[dict[str, object]]:
    route_data: list[dict[str, object]] = []
    if not ROUTES.exists():
        return route_data

    for path in sorted(ROUTES.glob("*.py")):
        if path.name == "__init__.py":
            continue
        content = read_text(path)
        prefix_match = re.search(r"APIRouter\([^)]*prefix\s*=\s*[\"']([^\"']+)[\"']", content, re.DOTALL)
        prefix = prefix_match.group(1) if prefix_match else ""
        endpoints = []
        for match in re.finditer(
            r"@router\.(get|post|put|patch|delete)\(\s*[\"']([^\"']*)[\"']",
            content,
            re.MULTILINE,
        ):
            method = match.group(1).upper()
            suffix = match.group(2)
            full_path = f"/api{prefix}{suffix}" if not suffix.startswith("/api") else suffix
            endpoints.append({"method": method, "path": full_path or f"/api{prefix}"})
        route_data.append(
            {
                "module": path.stem,
                "prefix": prefix or "/",
                "endpoint_count": len(endpoints),
                "endpoints": endpoints,
            }
        )
    return route_data


def scan_models() -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    if not MODELS.exists():
        return results

    for path in sorted(MODELS.glob("*.py")):
        if path.name in {"__init__.py", "database.py"}:
            continue
        content = read_text(path)
        class_matches = list(re.finditer(r"class\s+(\w+)\(Base\):", content))
        for index, match in enumerate(class_matches):
            class_name = match.group(1)
            start = match.start()
            end = class_matches[index + 1].start() if index + 1 < len(class_matches) else len(content)
            chunk = content[start:end]
            table_match = re.search(r'__tablename__\s*=\s*"([^"]+)"', chunk)
            results.append(
                {
                    "class_name": class_name,
                    "table": table_match.group(1) if table_match else "n/a",
                    "file": path.relative_to(ROOT).as_posix(),
                    "has_to_dict": "def to_dict" in chunk,
                }
            )
    return results


def scan_personas() -> list[dict[str, str]]:
    personas: list[dict[str, str]] = []
    if not PERSONAS.exists():
        return personas

    for path in sorted(PERSONAS.iterdir()):
        if not path.is_dir() or path.name.startswith("."):
            continue
        if re.match(r"[0-9a-f]{8}-", path.name):
            continue
        core = path / "CORE.md"
        description = titleize(path.name)
        if core.exists():
            for line in read_text(core).splitlines():
                stripped = line.strip()
                if stripped:
                    description = stripped.lstrip("# ").strip()
                    break
        personas.append({"id": path.name, "description": description})
    return personas


def scan_skill_definitions() -> list[dict[str, str]]:
    skills: list[dict[str, str]] = []
    if not SKILL_DEFINITIONS.exists():
        return skills

    for path in sorted(SKILL_DEFINITIONS.glob("*.json")):
        if path.name.startswith("_"):
            continue
        data = json.loads(read_text(path))
        skills.append(
            {
                "name": data.get("name", path.stem),
                "display_name": data.get("display_name", titleize(path.stem)),
                "phase": data.get("phase", "unknown"),
                "skill_type": data.get("skill_type", "unknown"),
            }
        )
    return skills


def scan_navigation() -> dict[str, list[dict[str, str]]]:
    sidebar = FRONTEND / "components" / "layout" / "Sidebar.tsx"
    navigation = {"primary": [], "secondary": [], "utility": []}
    if not sidebar.exists():
        return navigation

    content = read_text(sidebar)

    def parse_block(name: str) -> list[dict[str, str]]:
        block_match = re.search(rf"{name}\s*=\s*\[(.*?)\]\s*;", content, re.DOTALL)
        if not block_match:
            return []
        block = block_match.group(1)
        items = []
        for item in re.finditer(r'{\s*id:\s*"([^"]+)",\s*icon:\s*[^,]+,\s*label:\s*"([^"]+)"\s*}', block):
            items.append({"id": item.group(1), "label": item.group(2)})
        return items

    navigation["primary"] = parse_block("primaryNav")
    navigation["secondary"] = parse_block("secondaryNav")
    navigation["utility"] = [{"id": "notifications", "label": "Notifications"}]
    return navigation


def scan_views() -> list[dict[str, str]]:
    home_client = FRONTEND / "components" / "layout" / "HomeClient.tsx"
    if not home_client.exists():
        return []

    content = read_text(home_client)
    views = []
    seen: set[str] = set()
    for match in re.finditer(r'case\s+"([^"]+)":\s+return\s+<([A-Za-z0-9_]+)', content):
        view_id = match.group(1)
        component = match.group(2)
        if view_id in seen:
            continue
        seen.add(view_id)
        views.append({"id": view_id, "component": component})
    return views


def scan_stores() -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    if not STORES.exists():
        return results

    for path in sorted(STORES.glob("*.ts")):
        content = read_text(path)
        export_match = re.search(r"export\s+const\s+(use[A-Za-z0-9_]+Store)\b", content)
        results.append(
            {
                "file": path.name,
                "hook": export_match.group(1) if export_match else path.stem,
            }
        )
    return results


def scan_websocket_events() -> list[str]:
    if not WEBSOCKET_FILE.exists():
        return []
    content = read_text(WEBSOCKET_FILE)
    return sorted(set(re.findall(r'broadcast\("([^"]+)"', content)))


def scan_simple_module_names(directory: Path, suffixes: tuple[str, ...]) -> list[str]:
    if not directory.exists():
        return []
    return sorted(path.stem for path in directory.iterdir() if path.is_file() and path.suffix in suffixes and not path.name.startswith("_"))


def build_inventory() -> dict[str, object]:
    skills = scan_skill_definitions()
    skills_by_phase: dict[str, list[str]] = defaultdict(list)
    for skill in skills:
        skills_by_phase[skill["phase"]].append(skill["display_name"])

    routes = scan_routes()
    total_endpoints = sum(route["endpoint_count"] for route in routes)

    return {
        "version": read_version(),
        "routes": routes,
        "total_endpoints": total_endpoints,
        "models": scan_models(),
        "personas": scan_personas(),
        "skills": skills,
        "skills_by_phase": dict(sorted(skills_by_phase.items())),
        "navigation": scan_navigation(),
        "views": scan_views(),
        "stores": scan_stores(),
        "websocket_events": scan_websocket_events(),
        "test_layers": scan_test_layers(),
        "desktop_modules": scan_simple_module_names(DESKTOP_SRC, (".rs",)),
        "relay_modules": scan_simple_module_names(RELAY_ROOT / "lib", (".mjs",)),
        "channel_adapters": [
            name
            for name in scan_simple_module_names(CHANNELS_DIR, (".py",))
            if name not in {"__init__", "base"}
        ],
        "survey_platforms": [
            name
            for name in scan_simple_module_names(SURVEY_PLATFORMS_DIR, (".py",))
            if name != "__init__"
        ],
    }


ENTRYPOINT_START = "<!-- ENTRYPOINT_GENERATED_START -->"
ENTRYPOINT_END = "<!-- ENTRYPOINT_GENERATED_END -->"


def render_entrypoint_generated_section(inventory: dict[str, object]) -> str:
    primary_labels = ", ".join(item["label"] for item in inventory["navigation"]["primary"])  # type: ignore[index]
    secondary_labels = ", ".join(item["label"] for item in inventory["navigation"]["secondary"])  # type: ignore[index]
    websocket_events = ", ".join(f"`{name}`" for name in inventory["websocket_events"])
    personas = ", ".join(f"`{persona['id']}`" for persona in inventory["personas"])  # type: ignore[index]
    channel_adapters = ", ".join(f"`{name}`" for name in inventory["channel_adapters"])
    survey_platforms = ", ".join(f"`{name}`" for name in inventory["survey_platforms"])
    desktop_modules = ", ".join(f"`{name}`" for name in inventory["desktop_modules"])
    relay_modules = ", ".join(f"`{name}`" for name in inventory["relay_modules"])
    total_test_files = sum(len(files) for files in inventory["test_layers"].values()) # type: ignore[attr-defined]

    lines = [
        ENTRYPOINT_START,
        "<!-- Hybrid-generated by scripts/update_agent_md.py -->",
        "",
        "## Live Snapshot",
        "",
        f"- Version: `{inventory['version']}`",
        f"- Backend route modules: {len(inventory['routes'])} with {inventory['total_endpoints']} detected endpoints",
        f"- Frontend mounted views: {len(inventory['views'])}",
        f"- Frontend stores: {len(inventory['stores'])}",
        f"- Data models: {len(inventory['models'])}",
        f"- Personas: {len(inventory['personas'])} ({personas})",
        f"- Active test files: {total_test_files} across {len(inventory['test_layers'])} layers", # type: ignore[attr-defined]
        "",
        "## Current Product Surface",
        "",
        f"- Primary navigation: {primary_labels}",
        f"- Secondary navigation: {secondary_labels}",
        f"- WebSocket events: {websocket_events}",
        f"- Channel adapters: {channel_adapters}",
        f"- Survey platforms: {survey_platforms}",
        f"- Desktop modules: {desktop_modules}",
        f"- Relay modules: {relay_modules}",
        "",
        "## Change-Type Playbooks",
        "",
        "Use these as the first-pass expansion rules before editing code.",
        "",
        "### 1. Backend Route or API Contract Change",
        "",
        "If you add, remove, rename, or change an endpoint or payload:",
        "",
        "- Update the route implementation in `backend/app/api/routes/`",
        "- Check route registration in `backend/app/main.py`",
        "- Update `frontend/src/lib/api.ts`",
        "- Update `frontend/src/lib/types.ts`",
        "- Update the relevant store in `frontend/src/stores/`",
        "- Update the consuming UI in `frontend/src/components/`",
        "- Update `tests/e2e_test.py` and/or `tests/simulation/scenarios/`",
        "- Update `Tech.md` if the system/API behavior story changed",
        "- Update persona files if Istara's own agents should understand or use the new capability",
        "- Regenerate docs and run integrity checks",
        "",
        "### 2. Model, Schema, or Persistence Change",
        "",
        "If you add/change/delete a model, field, relationship, or persistence rule:",
        "",
        "- Update files in `backend/app/models/`",
        "- Update `backend/app/models/database.py`",
        "- Update migrations in `backend/alembic/versions/` if needed",
        "- Update route responses and service logic",
        "- Update `frontend/src/lib/types.ts`",
        "- Update affected stores/components",
        "- Check project deletion/cascade behavior if project-scoped",
        "- Update tests covering integrity, CRUD, and downstream UI behavior",
        "- Update `Tech.md` if the data model or architecture meaning changed",
        "- Regenerate docs and run integrity checks",
        "",
        "### 3. Frontend View, Menu, Navigation, or UX Flow Change",
        "",
        "If you add/change a page, tab, submenu, view ID, navigation rule, onboarding step, or UX flow:",
        "",
        "- Update `frontend/src/components/layout/Sidebar.tsx`",
        "- Update `frontend/src/components/layout/HomeClient.tsx`",
        "- Update `frontend/src/components/layout/MobileNav.tsx` if relevant",
        "- Update search/shortcut/navigation helpers if relevant",
        "- Update related store state and API calls",
        "- Update simulation scenarios that represent the UX path",
        "- Update `tests/e2e_test.py` if it changes the Sarah journey or major product flow",
        "- Update `Tech.md` if the user-facing system story changed",
        "- Update persona files if Istara's own agents should discuss or navigate this feature",
        "- Regenerate docs and run integrity checks",
        "",
        "### 4. WebSocket, Notification, or Async Workflow Change",
        "",
        "If you change event names, payloads, broadcast timing, notification categories, or progress flows:",
        "",
        "- Update `backend/app/api/websocket.py`",
        "- Update emitters in routes/services/core logic",
        "- Update frontend WebSocket consumers and affected stores/components",
        "- Update notifications UI/prefs if categories or event semantics changed",
        "- Update tests/scenarios that depend on real-time behavior",
        "- Update `Tech.md` if the runtime behavior story changed",
        "- Regenerate docs and run integrity checks",
        "",
        "### 5. Skill, Persona, Agent, or Prompt Change",
        "",
        "If you add/change a skill, system persona, agent behavior, routing logic, or repo prompt rule:",
        "",
        "- Update `backend/app/skills/definitions/` and related `skills/` docs if needed",
        "- Update persona files in `backend/app/agents/personas/`",
        "- Update agent orchestration/routing code if behavior changes there",
        "- Update relevant APIs and UI surfaces",
        "- Update tests or scenarios covering execution/routing behavior",
        "- Update `Tech.md` if this changes how Istara works conceptually",
        "- Update `SYSTEM_PROMPT.md`, `SYSTEM_CHANGE_MATRIX.md`, or `CHANGE_CHECKLIST.md` if repo doctrine changed",
        "- Regenerate docs and run integrity checks",
        "",
        "### 6. Integrations, Channels, MCP, Deployments, or External Connectors",
        "",
        "If you change third-party connections or distributed workflows:",
        "",
        "- Update adapter/service logic in backend",
        "- Update routes and request/response contracts",
        "- Update integrations UI, setup wizards, dashboards, or policy editors",
        "- Update fixtures and tests for security, setup, ingestion, and end-to-end behavior",
        "- Update `Tech.md` if the integration model or security model changed",
        "- Update persona files if Istara's own agents should know how to reason about the new connector/workflow",
        "- Regenerate docs and run integrity checks",
        "",
        "### 7. Release, Versioning, Installer, or Auto-Update Change",
        "",
        "If you change how Istara is versioned, packaged, released, installed, or updated:",
        "",
        "- Update `scripts/set-version.sh`",
        "- Update `scripts/prepare-release.sh`",
        "- Update `.github/workflows/ci.yml` and/or `.github/workflows/build-installers.yml`",
        "- Update `backend/app/api/routes/updates.py`",
        "- Update `desktop/src-tauri/src/health.rs` and other desktop update/install logic if relevant",
        "- Update installer/build files",
        "- Update `Tech.md`",
        "- Update tests if release/update behavior has automated coverage",
        "- Regenerate docs and run integrity checks",
        "- Make sure the docs describe the same model: only release-worthy `main` pushes publish installers/releases, while tag/manual flow remains available for explicit release control",
        "",
        ENTRYPOINT_END,
    ]
    return "\n".join(lines)


def update_marked_section(path: Path, start_marker: str, end_marker: str, replacement: str) -> bool:
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8")
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)
    if start_idx == -1 or end_idx == -1:
        raise RuntimeError(f"Markers not found in {path.name}")
    new_content = content[:start_idx] + replacement + content[end_idx + len(end_marker):]
    if new_content == content:
        return False
    path.write_text(new_content, encoding="utf-8")
    return True


def render_skill_phase_lines(skills_by_phase: dict[str, list[str]]) -> list[str]:
    lines = []
    for phase, names in skills_by_phase.items():
        joined = ", ".join(names)
        lines.append(f"- **{phase.title()}** ({len(names)}): {joined}")
    return lines


def render_routes_summary(routes: list[dict[str, object]]) -> list[str]:
    lines = ["| Route Module | Prefix | Endpoints |", "|---|---|---|"]
    for route in routes:
        lines.append(f"| `{route['module']}.py` | `{route['prefix']}` | {route['endpoint_count']} |")
    return lines


def render_route_inventory(routes: list[dict[str, object]]) -> list[str]:
    lines: list[str] = []
    for route in routes:
        endpoint_text = ", ".join(
            f"`{endpoint['method']} {endpoint['path']}`" for endpoint in route["endpoints"]  # type: ignore[index]
        )
        lines.append(f"- **{route['module']}**: {endpoint_text or 'No decorators detected'}")
    return lines


def render_model_table(models: list[dict[str, object]]) -> list[str]:
    lines = ["| Model | Table | `to_dict()` | File |", "|---|---|---|---|"]
    for model in models:
        lines.append(
            f"| `{model['class_name']}` | `{model['table']}` | {'yes' if model['has_to_dict'] else 'no'} | `{model['file']}` |"
        )
    return lines


def render_navigation_table(inventory: dict[str, object]) -> list[str]:
    views_map = {view["id"]: view["component"] for view in inventory["views"]}  # type: ignore[index]
    lines = ["| Area | View ID | Label | Mounted Component |", "|---|---|---|---|"]
    for area in ("primary", "secondary", "utility"):
        for item in inventory["navigation"][area]:  # type: ignore[index]
            lines.append(
                f"| {area.title()} | `{item['id']}` | {item['label']} | `{views_map.get(item['id'], 'n/a')}` |"
            )
    return lines


def render_store_table(stores: list[dict[str, str]]) -> list[str]:
    lines = ["| Store File | Exported Hook |", "|---|---|"]
    for store in stores:
        lines.append(f"| `{store['file']}` | `{store['hook']}` |")
    return lines


def render_persona_table(personas: list[dict[str, str]]) -> list[str]:
    lines = ["| Persona ID | Description |", "|---|---|"]
    for persona in personas:
        lines.append(f"| `{persona['id']}` | {persona['description']} |")
    return lines


def render_scenarios(scenarios: list[dict[str, str]]) -> list[str]:
    return [f"- `{scenario['id']}` — {scenario['title']}" for scenario in scenarios]


def render_test_layers(test_layers: dict[str, list[str]]) -> list[str]:
    lines = []
    for label, files in test_layers.items():
        joined = ", ".join(f"`{f}`" for f in files)
        lines.append(f"- **{label}**: {joined}")
    return lines


def build_agent_document(inventory: dict[str, object]) -> str:
    total_skills = len(inventory["skills"])  # type: ignore[arg-type]
    total_models = len(inventory["models"])  # type: ignore[arg-type]
    total_views = len(inventory["views"])  # type: ignore[arg-type]
    total_stores = len(inventory["stores"])  # type: ignore[arg-type]
    total_routes = len(inventory["routes"])  # type: ignore[arg-type]
    total_personas = len(inventory["personas"])  # type: ignore[arg-type]
    total_test_files = sum(len(files) for files in inventory["test_layers"].values()) # type: ignore[attr-defined]

    lines = [
        "# Istara — Agent-Readable Operating Map",
        "",
        f"Generated from the repository on version `{inventory['version']}`. Treat this file as the fast inventory view after reading `AGENT_ENTRYPOINT.md`, then consult `COMPLETE_SYSTEM.md`, `SYSTEM_CHANGE_MATRIX.md`, `CHANGE_CHECKLIST.md`, and `SYSTEM_PROMPT.md` before structural work.",
        "",
        "## Non-Negotiable Workflow",
        "",
        "- Read `AGENT_ENTRYPOINT.md` first for the canonical document-reading order.",
        "- Read `SYSTEM_PROMPT.md` for operating rules and documentation duties.",
        "- Use `SYSTEM_CHANGE_MATRIX.md` to identify dependent backend, frontend, UX, test, release, and prompt surfaces.",
        "- Use `CHANGE_CHECKLIST.md` to identify every code, test, and doc surface touched by the change.",
        "- Regenerate this file and `COMPLETE_SYSTEM.md` with `python scripts/update_agent_md.py` in the same change that modifies architecture, flows, routes, stores, skills, personas, or tests.",
        "- Run `python scripts/check_integrity.py` before finalizing docs-related work.",
        "- Treat `tests/e2e_test.py` and `tests/simulation/scenarios/` as behavioral contracts for the UI and system flows.",
        "- Update `Tech.md` when architecture, workflow, installer, release, or update behavior changes.",
        "- Update future-facing tests and relevant Istara persona files when a feature changes what Istara's own agents must understand.",
        "- Use `./scripts/prepare-release.sh --bump` for intentional release preparation, but keep the docs aligned with the actual repo rule that release-worthy pushes to `main` publish installers/releases.",
        "",
        "## System Snapshot",
        "",
        f"- Frontend: Next.js app with {total_views} mounted views and {total_stores} Zustand stores.",
        f"- Backend: FastAPI app with {total_routes} route modules and {inventory['total_endpoints']} detected endpoints.",
        f"- Data layer: {total_models} SQLAlchemy models plus LanceDB-backed retrieval/context systems.",
        f"- Agents/personas: {total_personas} tracked persona directories under `backend/app/agents/personas`.",
        f"- Skills: {total_skills} JSON-defined skills across the Double Diamond phases.",
        f"- Regression map: {total_test_files} active test files across {len(inventory['test_layers'])} layers.", # type: ignore[attr-defined]
        "",
        "## Change Hotspots",
        "",
        "- New route or changed payload: update backend route, frontend API client, matching TypeScript types, consuming stores/components, tests, and regenerate docs.",
        "- New model or schema field: update model, serialization, frontend types, any route/store consumers, migration path, tests, and regenerate docs.",
        "- New view or menu item: update `Sidebar.tsx`, `HomeClient.tsx`, relevant store/components, simulation scenarios, and regenerate docs.",
        "- Persona, skill, or workflow changes: update persona files, skill definitions/prompts, related tests, and regenerate docs.",
        "",
        "## Navigation Map",
        "",
        *render_navigation_table(inventory),
        "",
        "## Persona Registry",
        "",
        *render_persona_table(inventory["personas"]),  # type: ignore[arg-type]
        "",
        "## Skills By Phase",
        "",
        *render_skill_phase_lines(inventory["skills_by_phase"]),  # type: ignore[arg-type]
        "",
        "## Backend Route Modules",
        "",
        *render_routes_summary(inventory["routes"]),  # type: ignore[arg-type]
        "",
        "## Data Model Registry",
        "",
        *render_model_table(inventory["models"]),  # type: ignore[arg-type]
        "",
        "## Frontend State Stores",
        "",
        *render_store_table(inventory["stores"]),  # type: ignore[arg-type]
        "",
        "## Real-Time Contract",
        "",
        f"- WebSocket event types detected: {', '.join(f'`{name}`' for name in inventory['websocket_events'])}.",
        "- When adding a new event, update both broadcaster + frontend handler + regression coverage + regenerated docs.",
        "",
        "## Test Coverage Map",
        "",
        *render_test_layers(inventory["test_layers"]), # type: ignore[arg-type]
        "",
        "## Documentation Contract",
        "",
        "- `SYSTEM_PROMPT.md`: model-agnostic operating contract.",
        "- `SYSTEM_CHANGE_MATRIX.md`: explicit X -> W/Y/Z dependency map for changes.",
        "- `CLAUDE.md` / `GEMINI.md`: model-specific wrappers around the same repo workflow.",
        "- `COMPLETE_SYSTEM.md`: broader architecture, integration, and test coverage map.",
        "- `SYSTEM_INTEGRITY_GUIDE.md`: legacy deep-reference manual; keep it coherent when underlying architecture shifts.",
        "- `Tech.md`: narrative technical source that must move with architecture/process/release changes.",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"


def build_complete_system_document(inventory: dict[str, object]) -> str:
    total_test_files = sum(len(files) for files in inventory["test_layers"].values()) # type: ignore[attr-defined]
    lines = [
        "# Istara Complete System Architecture & Living Map",
        "",
        f"Generated from the repository on version `{inventory['version']}`. This document is meant to be regenerated whenever the implementation changes so LLMs can reason from the current system instead of stale summaries.",
        "",
        "## Purpose",
        "",
        "- Use this as the broad architecture map for planning and code review.",
        "- Use `AGENT.md` for the compressed operating view.",
        "- Use `SYSTEM_CHANGE_MATRIX.md` for cross-surface dependency mapping.",
        "- Use `CHANGE_CHECKLIST.md` for implementation steps and `tests/simulation/scenarios/` as the practical UI contract.",
        "",
        "## Living-Doc Rules",
        "",
        "- Source of truth is the codebase plus generated inventories below, not remembered prose.",
        "- Any change to routes, models, personas, stores, views, skills, or regression scenarios should be followed by `python scripts/update_agent_md.py`.",
        "- `python scripts/check_integrity.py` should pass before shipping architecture-affecting changes.",
        "- If a change introduces a new subsystem that the scanner cannot see cleanly, extend the scanner in `scripts/update_agent_md.py` instead of silently documenting it by hand only once.",
        "",
        "## Repository Architecture Snapshot",
        "",
        f"- FastAPI backend with {len(inventory['routes'])} route modules and {inventory['total_endpoints']} detected endpoints.",
        f"- Next.js frontend with {len(inventory['views'])} mounted views and {len(inventory['stores'])} Zustand stores.",
        f"- {len(inventory['models'])} SQLAlchemy models in `backend/app/models`.",
        f"- {len(inventory['personas'])} tracked persona directories and {len(inventory['skills'])} JSON-defined skills.",
        f"- {total_test_files} active test files across {len(inventory['test_layers'])} regression layers.", # type: ignore[attr-defined]
        "",
        "## Backend Route Inventory",
        "",
        *render_routes_summary(inventory["routes"]),  # type: ignore[arg-type]
        "",
        "### Endpoint Coverage",
        "",
        *render_route_inventory(inventory["routes"]),  # type: ignore[arg-type]
        "",
        "## Data Model Inventory",
        "",
        *render_model_table(inventory["models"]),  # type: ignore[arg-type]
        "",
        "## Frontend View and Navigation Inventory",
        "",
        *render_navigation_table(inventory),
        "",
        "## Frontend Store Inventory",
        "",
        *render_store_table(inventory["stores"]),  # type: ignore[arg-type]
        "",
        "## Personas and Skills",
        "",
        *render_persona_table(inventory["personas"]),  # type: ignore[arg-type]
        "",
        "### Skills By Phase",
        "",
        *render_skill_phase_lines(inventory["skills_by_phase"]),  # type: ignore[arg-type]
        "",
        "## Real-Time and Integration Surface",
        "",
        f"- WebSocket events: {', '.join(f'`{name}`' for name in inventory['websocket_events'])}.",
        f"- Channel adapters: {', '.join(f'`{name}`' for name in inventory['channel_adapters'])}.",
        f"- Survey platform services: {', '.join(f'`{name}`' for name in inventory['survey_platforms'])}.",
        f"- Desktop modules: {', '.join(f'`{name}`' for name in inventory['desktop_modules'])}.",
        f"- Relay modules: {', '.join(f'`{name}`' for name in inventory['relay_modules'])}.",
        "",
        "## Behavioral Coverage from Tests",
        "",
        *render_test_layers(inventory["test_layers"]), # type: ignore[arg-type]
        "",
        "## What Agents Must Check Before Editing",
        "",
        "- Does the change alter the API contract, local state contract, or menu/view wiring?",
        "- Does the change add or remove a persistence entity, evidence-link path, or background process?",
        "- Does the change affect a simulation scenario or the Sarah journey in `tests/e2e_test.py`?",
        "- Does the change require a new prompt or persona rule so future agents make the same safe decision automatically?",
        "",
        "## Maintenance Workflow",
        "",
        "1. Make the implementation change.",
        "2. Update tests and any hand-authored guidance that explains the new behavior.",
        "3. Run `python scripts/update_agent_md.py`.",
        "4. Run `python scripts/check_integrity.py`.",
        "5. If the generated docs still miss something important, improve the generator instead of patching around it manually.",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"


def write_if_changed(path: Path, content: str) -> bool:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if current == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if docs are out of date.")
    args = parser.parse_args()

    inventory = build_inventory()
    generated_files = {
        AGENT_MD: build_agent_document(inventory),
        COMPLETE_SYSTEM_MD: build_complete_system_document(inventory),
    }
    entrypoint_generated = render_entrypoint_generated_section(inventory)

    if args.check:
        drift = [path.name for path, content in generated_files.items() if not path.exists() or read_text(path) != content]
        if (
            not AGENT_ENTRYPOINT_MD.exists()
            or ENTRYPOINT_START not in read_text(AGENT_ENTRYPOINT_MD)
            or ENTRYPOINT_END not in read_text(AGENT_ENTRYPOINT_MD)
        ):
            drift.append(AGENT_ENTRYPOINT_MD.name)
        else:
            entrypoint_content = read_text(AGENT_ENTRYPOINT_MD)
            start_idx = entrypoint_content.find(ENTRYPOINT_START)
            end_idx = entrypoint_content.find(ENTRYPOINT_END)
            current_generated = entrypoint_content[start_idx : end_idx + len(ENTRYPOINT_END)]
            if current_generated != entrypoint_generated:
                drift.append(AGENT_ENTRYPOINT_MD.name)
        if drift:
            print("Documentation drift detected:")
            for name in drift:
                print(f"  - {name}")
            print("Run: python scripts/update_agent_md.py")
            return 1
        print("AGENT.md and COMPLETE_SYSTEM.md are up to date.")
        return 0

    changed = []
    for path, content in generated_files.items():
        if write_if_changed(path, content):
            changed.append(path.name)
    if update_marked_section(AGENT_ENTRYPOINT_MD, ENTRYPOINT_START, ENTRYPOINT_END, entrypoint_generated):
        changed.append(AGENT_ENTRYPOINT_MD.name)

    if changed:
        print("Updated docs:")
        for name in changed:
            print(f"  - {name}")
    else:
        print("No documentation changes were needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
