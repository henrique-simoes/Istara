---
stable_id: agents.create
title: Create Agent
ui_path: Agents > Create
audience: researcher
status: needs-verification
related_features: ["agents.registry", "skills.catalog"]
related_glossary: ["a2a", "mcp"]
code_references: ["frontend/src/components/agents/AgentsView.tsx", "backend/app/api/routes/agents.py", "backend/app/core/agent_factory.py"]
api_references: ["backend/app/api/routes/agents.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Create Agent

## What It Does

Create Agent supports configuring new agents and their role-facing metadata.

## Why It Exists

Create Agent exists so the work represented by Agents > Create has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Agents > Create
- Navigation group: Agents
- Primary component: `AgentsView`

## How UX Researchers Use It

- Open Agents > Create from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with create agent in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Agents > Create when the current research task needs create agent.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: agents.registry, skills.catalog.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with create agent.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [agents.registry](../../agents/registry/researcher.md)
- [skills.catalog](../../skills/catalog/researcher.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)
- [mcp](../../../glossary/mcp.md)

## Evidence

- Source files: `frontend/src/components/agents/AgentsView.tsx`, `backend/app/api/routes/agents.py`, `backend/app/core/agent_factory.py`
- API references: `backend/app/api/routes/agents.py`
- Tests: none recorded
