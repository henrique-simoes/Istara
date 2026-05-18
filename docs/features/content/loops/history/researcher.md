---
stable_id: loops.history
title: Loop Execution History
ui_path: Loops > History
audience: researcher
status: documented
related_features: ["loops.overview", "history.version"]
related_glossary: ["a2a"]
code_references: ["frontend/src/components/loops/ExecutionHistoryTab.tsx", "backend/app/api/routes/loops.py"]
api_references: ["backend/app/api/routes/loops.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Loop Execution History

## What It Does

Execution History records loop runs, outcomes, and recent automation activity.

## Why It Exists

Loop Execution History exists so the work represented by Loops > History has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Loops > History
- Navigation group: Loops
- Primary component: `ExecutionHistoryTab`

## How UX Researchers Use It

- Open Loops > History from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with loop execution history in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Loops > History when the current research task needs loop execution history.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: loops.overview, history.version.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with loop execution history.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [loops.overview](../../loops/overview/researcher.md)
- [history.version](../../history/version/researcher.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)

## Evidence

- Source files: `frontend/src/components/loops/ExecutionHistoryTab.tsx`, `backend/app/api/routes/loops.py`
- API references: `backend/app/api/routes/loops.py`
- Tests: none recorded
