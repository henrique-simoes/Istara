---
stable_id: agents.detail
title: Agent Detail Panels
ui_path: Agents > Agents > Detail
audience: researcher
status: documented
related_features: ["agents.registry", "memory.agent"]
related_glossary: ["a2a"]
code_references: ["frontend/src/components/agents/AgentsView.tsx", "backend/app/core/agent_identity.py", "backend/app/core/agent_memory.py", "backend/app/core/permissions.py"]
api_references: ["backend/app/api/routes/agents.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Agent Detail Panels

## What It Does

Selected agent details expose overview, identity, memory, and permission information for that agent.

## Why It Exists

Agent Detail Panels exists so the work represented by Agents > Agents > Detail has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Agents > Agents > Detail
- Navigation group: Agents
- Primary component: `AgentsView`

## How UX Researchers Use It

- Open Agents > Agents > Detail from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with agent detail panels in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Agents > Agents > Detail when the current research task needs agent detail panels.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: agents.registry, memory.agent.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with agent detail panels.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [agents.registry](../../agents/registry/researcher.md)
- [memory.agent](../../memory/agent/researcher.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)

## Evidence

- Source files: `frontend/src/components/agents/AgentsView.tsx`, `backend/app/core/agent_identity.py`, `backend/app/core/agent_memory.py`, `backend/app/core/permissions.py`
- API references: `backend/app/api/routes/agents.py`
- Tests: none recorded
