---
stable_id: settings.project
title: Project Settings
ui_path: Project Settings
audience: researcher
status: documented
related_features: ["shell.projects", "settings.general"]
related_glossary: ["compass-forge"]
code_references: ["frontend/src/components/settings/ProjectSettingsView.tsx", "frontend/src/components/layout/Sidebar.tsx", "frontend/src/lib/types.ts", "frontend/src/lib/utils.ts", "backend/app/api/routes/projects.py", "backend/app/api/routes/permission_requests.py", "backend/app/core/agentic/dispatcher.py"]
api_references: ["backend/app/api/routes/projects.py", "backend/app/api/routes/permission_requests.py"]
test_references: ["tests/test_project_rbac.py", "tests/test_project_scope_contracts.py", "tests/pi_production/test_w8_embeddings_gateway.py", "tests/simulation/scenarios/79-engine-selector.mjs"]
last_verified: 2026-07-22
compass: CF-SPEC-53 / CF-657; CF-SPEC-72 / CF-927; CF-SPEC-8
---

# Project Settings

## What It Does

Project Settings configure project-specific metadata and operational preferences separate from global system settings. Permission requests shown here belong to the active project only.

## Why It Exists

Project Settings exists so the work represented by Project Settings has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Project Settings
- Navigation group: Secondary
- Primary component: `ProjectSettingsView`

## How UX Researchers Use It

- Open Project Settings from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with project settings in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Project Settings when the current research task needs project settings.
- Project admins can review only the permission requests for the active project shown in this settings view.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: shell.projects, settings.general.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with project settings.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Choosing The Agent Engine Per Project

- Istara can run its agentic work on a legacy engine or the newer Pi replacement engine. Pi Replacement wave W8 lets each project choose its own engine instead of only following the global default.
- Project admins see an "Agent Engine" section in Project Settings with three options: Inherit global default, Legacy, or Pi. The inherit label and read-only badge use the server's current normalized global default, so they stay accurate when the default is Pi. Choosing an unrecognized engine value is rejected by the server, so a project can never end up with a broken setting.
- The current engine is always visible while you work: the sidebar shows a small "Pi" or "Legacy" badge next to each project's phase label, so it is clear which engine serves that project's chat, agents, and validation before you run anything.
- The project choice sits between per-call overrides and the global default: an explicit request or header still wins, the project setting applies next, and projects left on "Inherit" follow whatever the global default says. Switching a project back to Legacy is a safe rollback.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [shell.projects](../../shell/projects/researcher.md)
- [settings.general](../../settings/general/researcher.md)

## Related Concepts

- [compass-forge](../../../glossary/compass-forge.md)

## Evidence

- Source files: `frontend/src/components/settings/ProjectSettingsView.tsx`, `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/lib/types.ts`, `frontend/src/lib/utils.ts`, `backend/app/api/routes/projects.py`
- API references: `backend/app/api/routes/projects.py`
- Tests: `tests/test_project_rbac.py`, `tests/test_project_scope_contracts.py`, `tests/pi_production/test_w8_embeddings_gateway.py`, `tests/simulation/scenarios/79-engine-selector.mjs`
