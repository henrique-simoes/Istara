---
stable_id: interfaces.generate
title: Generate Interfaces
ui_path: Interfaces > Generate
audience: researcher
status: needs-verification
related_features: ["interfaces.screens", "interfaces.design-chat"]
related_glossary: ["minto-pyramid"]
code_references: ["frontend/src/components/interfaces/GenerateTab.tsx", "frontend/src/stores/interfacesStore.ts", "backend/app/api/routes/interfaces.py"]
api_references: ["backend/app/api/routes/interfaces.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Generate Interfaces

## What It Does

The Generate tab creates interface assets or screen proposals from project context and design prompts.

## Why It Exists

Generate Interfaces exists so the work represented by Interfaces > Generate has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Interfaces > Generate
- Navigation group: Interfaces
- Primary component: `GenerateTab`

## How UX Researchers Use It

- Open Interfaces > Generate from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with generate interfaces in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Interfaces > Generate when the current research task needs generate interfaces.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: interfaces.screens, interfaces.design-chat.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with generate interfaces.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [interfaces.screens](../../interfaces/screens/researcher.md)
- [interfaces.design-chat](../../interfaces/design-chat/researcher.md)

## Related Concepts

- [minto-pyramid](../../../glossary/minto-pyramid.md)

## Evidence

- Source files: `frontend/src/components/interfaces/GenerateTab.tsx`, `frontend/src/stores/interfacesStore.ts`, `backend/app/api/routes/interfaces.py`
- API references: `backend/app/api/routes/interfaces.py`
- Tests: none recorded
