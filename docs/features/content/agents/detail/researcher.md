---
stable_id: agents.detail
title: Agent Detail Panels
ui_path: Agents > Agents > Detail
audience: researcher
status: documented
related_features: ["agents.registry", "memory.agent"]
related_glossary: ["a2a"]
code_references: ["frontend/src/components/agents/AgentsView.tsx", "frontend/src/lib/api.ts", "frontend/src/stores/agentStore.ts", "backend/app/api/routes/agents.py", "backend/app/core/agent_identity.py", "backend/app/core/agent_memory.py", "backend/app/core/permissions.py"]
api_references: ["backend/app/api/routes/agents.py"]
test_references: ["tests/test_agents.py", "tests/test_agent_mutation_scope.py", "tests/test_agent_scope_contracts.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-83 / CF-1075; CF-SPEC-89 / CF-1125
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
- Mutating controls are limited to agents owned by the active project; universal/system agent details remain inspectable without becoming a global mutation path.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Agents > Agents > Detail when the current research task needs agent detail panels.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: agents.registry, memory.agent.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with agent detail panels.
- Identity, memory, permission, lifecycle, and export updates require the active project to match the selected agent.
- Promotion review requests remain attached to the selected agent's project so they do not appear as global review activity in unrelated projects.
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

- Source files: `frontend/src/components/agents/AgentsView.tsx`, `frontend/src/lib/api.ts`, `frontend/src/stores/agentStore.ts`, `backend/app/api/routes/agents.py`, `backend/app/core/agent_identity.py`, `backend/app/core/agent_memory.py`, `backend/app/core/permissions.py`
- API references: `backend/app/api/routes/agents.py`
- Tests: `tests/test_agents.py`, `tests/test_agent_mutation_scope.py`, `tests/test_agent_scope_contracts.py`, `tests/test_project_scope_contracts.py`
