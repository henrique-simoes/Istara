---
stable_id: loops.agent-loops
title: Agent Loops
ui_path: Loops > Agent Loops
audience: researcher
status: documented
related_features: ["agents.registry", "loops.schedules"]
related_glossary: ["a2a"]
code_references: ["frontend/src/components/loops/AgentLoopsTab.tsx", "backend/app/api/routes/loops.py", "backend/app/core/scheduler.py"]
api_references: ["backend/app/api/routes/loops.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Agent Loops

## What It Does

Agent Loops connects recurring work with configured agents and their automated research responsibilities.

## Why It Exists

Agent Loops exists so the work represented by Loops > Agent Loops has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Loops > Agent Loops
- Navigation group: Loops
- Primary component: `AgentLoopsTab`

## How UX Researchers Use It

- Open Loops > Agent Loops from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with agent loops in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Loops > Agent Loops when the current research task needs agent loops.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: agents.registry, loops.schedules.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with agent loops.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [agents.registry](../../agents/registry/researcher.md)
- [loops.schedules](../../loops/schedules/researcher.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)

## Evidence

- Source files: `frontend/src/components/loops/AgentLoopsTab.tsx`, `backend/app/api/routes/loops.py`, `backend/app/core/scheduler.py`
- API references: `backend/app/api/routes/loops.py`
- Tests: none recorded
