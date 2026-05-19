---
stable_id: interfaces.screens
title: Screens Gallery
ui_path: Interfaces > Screens
audience: architecture
status: documented
related_features: ["interfaces.generate", "interfaces.handoff"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/interfaces/ScreensGalleryTab.tsx", "frontend/src/components/interfaces/ScreenPreview.tsx", "backend/app/api/routes/interfaces_screens.py"]
api_references: ["backend/app/api/routes/interfaces_screens.py"]
test_references: ["tests/test_interfaces.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-763
---

# Screens Gallery Architecture

## Implementation Summary

Screens displays generated interface screens and previews for review in the active project.

## Frontend Surface

- `frontend/src/components/interfaces/ScreensGalleryTab.tsx`
- `frontend/src/components/interfaces/ScreenPreview.tsx`
- `backend/app/api/routes/interfaces_screens.py`
- `frontend/src/stores/interfacesStore.ts`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/interfacesStore.ts`

### API And Backend

- `backend/app/api/routes/interfaces_screens.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/interfaces/ScreensGalleryTab.tsx` and the UI navigation path recorded in the inventory.
- `GET /api/interfaces/screens` requires an explicit `project_id`, checks project viewer access, and filters `DesignScreen.project_id` at the database query.
- The frontend store clears stale screens when fetching a new project, and `ScreensGalleryTab` defensively renders only screens whose `project_id` equals the active project id.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- `tests/test_interfaces.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [interfaces.generate](../../interfaces/generate/architecture.md)
- [interfaces.handoff](../../interfaces/handoff/architecture.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-763
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
