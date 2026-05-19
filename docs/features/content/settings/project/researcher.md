---
stable_id: settings.project
title: Project Settings
ui_path: Project Settings
audience: researcher
status: documented
related_features: ["shell.projects", "settings.general"]
related_glossary: ["compass-forge"]
code_references: ["frontend/src/components/settings/ProjectSettingsView.tsx", "backend/app/api/routes/projects.py", "backend/app/api/routes/permission_requests.py"]
api_references: ["backend/app/api/routes/projects.py", "backend/app/api/routes/permission_requests.py"]
test_references: ["tests/test_project_rbac.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-72 / CF-927
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

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [shell.projects](../../shell/projects/researcher.md)
- [settings.general](../../settings/general/researcher.md)

## Related Concepts

- [compass-forge](../../../glossary/compass-forge.md)

## Evidence

- Source files: `frontend/src/components/settings/ProjectSettingsView.tsx`, `backend/app/api/routes/projects.py`
- API references: `backend/app/api/routes/projects.py`
- Tests: `tests/test_project_rbac.py`, `tests/test_project_scope_contracts.py`
