---
stable_id: loops.custom
title: Custom Loops
ui_path: Loops > Custom
audience: researcher
status: needs-verification
related_features: ["loops.schedules", "skills.catalog"]
related_glossary: ["mcp"]
code_references: ["frontend/src/components/loops/CustomLoopsTab.tsx", "backend/app/api/routes/loops.py"]
api_references: ["backend/app/api/routes/loops.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Custom Loops

## What It Does

Custom loops provide a surface for user-defined recurring or automated research actions.

## Why It Exists

Custom Loops exists so the work represented by Loops > Custom has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Loops > Custom
- Navigation group: Loops
- Primary component: `CustomLoopsTab`

## How UX Researchers Use It

- Open Loops > Custom from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with custom loops in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Loops > Custom when the current research task needs custom loops.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: loops.schedules, skills.catalog.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with custom loops.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [loops.schedules](../../loops/schedules/researcher.md)
- [skills.catalog](../../skills/catalog/researcher.md)

## Related Concepts

- [mcp](../../../glossary/mcp.md)

## Evidence

- Source files: `frontend/src/components/loops/CustomLoopsTab.tsx`, `backend/app/api/routes/loops.py`
- API references: `backend/app/api/routes/loops.py`
- Tests: none recorded
