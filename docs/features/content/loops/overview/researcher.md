---
stable_id: loops.overview
title: Loops Overview
ui_path: Loops > Overview
audience: researcher
status: documented
related_features: ["loops.schedules", "loops.agent-loops"]
related_glossary: ["a2a"]
code_references: ["frontend/src/components/loops/LoopsView.tsx", "frontend/src/components/loops/LoopOverviewTab.tsx", "frontend/src/stores/loopsStore.ts", "backend/app/api/routes/loops.py"]
api_references: ["backend/app/api/routes/loops.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Loops Overview

## What It Does

Loops overview summarizes automated and scheduled research loop health.

## Why It Exists

Loops Overview exists so the work represented by Loops > Overview has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Loops > Overview
- Navigation group: Loops
- Primary component: `LoopOverviewTab`

## How UX Researchers Use It

- Open Loops > Overview from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with loops overview in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Loops > Overview when the current research task needs loops overview.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: loops.schedules, loops.agent-loops.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with loops overview.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [loops.schedules](../../loops/schedules/researcher.md)
- [loops.agent-loops](../../loops/agent-loops/researcher.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)

## Evidence

- Source files: `frontend/src/components/loops/LoopsView.tsx`, `frontend/src/components/loops/LoopOverviewTab.tsx`, `frontend/src/stores/loopsStore.ts`, `backend/app/api/routes/loops.py`
- API references: `backend/app/api/routes/loops.py`
- Tests: none recorded
