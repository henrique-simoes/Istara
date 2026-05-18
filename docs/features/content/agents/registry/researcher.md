---
stable_id: agents.registry
title: Agent Registry
ui_path: Agents > Agents
audience: researcher
status: documented
related_features: ["agents.detail", "agents.a2a", "agents.create"]
related_glossary: ["a2a", "mcp"]
code_references: ["frontend/src/components/agents/AgentsView.tsx", "frontend/src/stores/agentStore.ts", "backend/app/api/routes/agents.py"]
api_references: ["backend/app/api/routes/agents.py"]
test_references: ["tests/test_agents.py"]
last_verified: 2026-05-18
compass: CF-SPEC-56 / CF-698
---

# Agent Registry

## What It Does

The Agents view lists and manages available agents, including their status and project-facing roles.

## Why It Exists

Agent Registry exists so the work represented by Agents > Agents has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Agents > Agents
- Navigation group: Agents
- Primary component: `AgentsView`

## How UX Researchers Use It

- Open Agents > Agents from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with universal agents and agents scoped to the active project.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Agents > Agents when the current research task needs agent registry.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: agents.detail, agents.a2a, agents.create.

## Inputs, Outputs, And Expected Outcomes

- Universal system agents and project-scoped custom agents associated with the active project.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [agents.detail](../../agents/detail/researcher.md)
- [agents.a2a](../../agents/a2a/researcher.md)
- [agents.create](../../agents/create/researcher.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)
- [mcp](../../../glossary/mcp.md)

## Evidence

- Source files: `frontend/src/components/agents/AgentsView.tsx`, `frontend/src/stores/agentStore.ts`, `backend/app/api/routes/agents.py`
- API references: `backend/app/api/routes/agents.py`
- Tests: `tests/test_agents.py`
