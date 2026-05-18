---
stable_id: settings.updates
title: Software Updates
ui_path: Settings > Software Updates
audience: researcher
status: documented
related_features: ["settings.general"]
related_glossary: ["compass-forge"]
code_references: ["frontend/src/components/settings/UpdateChecker.tsx", "frontend/src/lib/updatesApi.ts", "backend/app/api/routes/updates.py"]
api_references: ["backend/app/api/routes/updates.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Software Updates

## What It Does

The update checker surfaces available Istara software updates from the settings view.

## Why It Exists

Software Updates exists so the work represented by Settings > Software Updates has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Settings > Software Updates
- Navigation group: Settings
- Primary component: `UpdateChecker`

## How UX Researchers Use It

- Open Settings > Software Updates from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with software updates in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Settings > Software Updates when the current research task needs software updates.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: settings.general.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with software updates.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [settings.general](../../settings/general/researcher.md)

## Related Concepts

- [compass-forge](../../../glossary/compass-forge.md)

## Evidence

- Source files: `frontend/src/components/settings/UpdateChecker.tsx`, `frontend/src/lib/updatesApi.ts`, `backend/app/api/routes/updates.py`
- API references: `backend/app/api/routes/updates.py`
- Tests: none recorded
