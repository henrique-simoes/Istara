---
stable_id: agents.create
title: Create Agent
ui_path: Agents > Create
audience: researcher
status: documented
related_features: ["agents.registry", "skills.catalog"]
related_glossary: ["a2a", "mcp"]
code_references: ["frontend/src/components/agents/AgentsView.tsx", "frontend/src/components/agents/CreateAgentWizard.tsx", "frontend/src/stores/agentStore.ts", "frontend/src/lib/api.ts", "backend/app/api/routes/agents.py", "backend/app/services/agent_service.py", "backend/app/core/agent_factory.py"]
api_references: ["backend/app/api/routes/agents.py"]
test_references: ["tests/test_agents.py", "tests/test_agent_mutation_scope.py", "tests/test_agent_scope_contracts.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-757; CF-SPEC-83 / CF-1075
---

# Create Agent

## What It Does

Create Agent supports configuring new project-scoped agents and their role-facing metadata.

## Why It Exists

Create Agent exists so the work represented by Agents > Create has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Agents > Create
- Navigation group: Agents
- Primary component: `AgentsView`

## How UX Researchers Use It

- Open Agents > Create from the Istara navigation or the parent tab.
- Use the visible controls in this surface to create agents in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Agents > Create when the current project needs a specialized custom agent.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active project.
- Move to related surfaces when needed: agents.registry, skills.catalog.

## Inputs, Outputs, And Expected Outcomes

- A custom agent with `scope=project` and the active project id.
- Imported agent configs are recreated as project-scoped agents for the active project.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.
- Missing active project context prevents creation or import rather than creating a global agent.

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

- Source files: `frontend/src/components/agents/AgentsView.tsx`, `frontend/src/components/agents/CreateAgentWizard.tsx`, `frontend/src/stores/agentStore.ts`, `frontend/src/lib/api.ts`, `backend/app/api/routes/agents.py`, `backend/app/services/agent_service.py`, `backend/app/core/agent_factory.py`
- API references: `backend/app/api/routes/agents.py`
- Tests: `tests/test_agents.py`, `tests/test_agent_mutation_scope.py`, `tests/test_agent_scope_contracts.py`, `tests/test_project_scope_contracts.py`
