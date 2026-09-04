---
stable_id: shell.projects
title: Project Switcher
ui_path: Shell > Projects
audience: architecture
status: documented
related_features: ["shell.navigation", "chat.overview", "tasks.kanban"]
related_glossary: ["compass-forge"]
code_references: ["frontend/src/components/layout/Sidebar.tsx", "frontend/src/stores/projectStore.ts", "backend/app/api/routes/projects.py"]
api_references: ["backend/app/api/routes/projects.py"]
test_references: ["tests/test_projects.py::test_delete_project_cleans_managed_runtime_artifacts_but_keeps_external_watch_folder", "tests/test_projects.py::test_delete_project_removes_project_memberships"]
last_verified: 2026-09-02
compass: CF-SPEC-53 / CF-657
---

# Project Switcher Architecture

## Implementation Summary

The sidebar project control lists available projects and lets users create, select, pause, resume, or delete the active project context used by most Istara views.

## Frontend Surface

- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/stores/projectStore.ts`
- `backend/app/api/routes/projects.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/projectStore.ts`

### API And Backend

- `backend/app/api/routes/projects.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/layout/Sidebar.tsx` and the UI navigation path recorded in the inventory.
- Deleting a project removes only its managed upload, vector, keyword-index, and versioning paths after the database transaction commits; linked external watch folders are retained while their watcher registrations are removed.
- Deleting a project explicitly removes its project memberships before commit so SQLite deployments cannot leave stale rows in Admin > Access when database-level cascades are unavailable.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [shell.navigation](../../shell/navigation/architecture.md)
- [chat.overview](../../chat/overview/architecture.md)
- [tasks.kanban](../../tasks/kanban/architecture.md)

## Related Concepts

- [compass-forge](../../../glossary/compass-forge.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
