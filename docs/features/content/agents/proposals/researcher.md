---
stable_id: agents.proposals
title: Agent Proposals
ui_path: Agents > Proposals
audience: researcher
status: needs-verification
related_features: ["agents.registry", "skills.proposals", "tasks.review"]
related_glossary: ["a2a"]
code_references: ["frontend/src/components/agents/AgentsView.tsx", "frontend/src/lib/api.ts", "backend/app/api/routes/agents.py", "backend/app/core/agent_factory.py", "backend/app/core/improvement_governance_evidence.py", "backend/app/core/meta_hyperagent.py", "backend/app/agents/orchestrator.py", "backend/app/api/routes/permission_requests.py"]
api_references: ["backend/app/api/routes/agents.py", "backend/app/api/routes/permission_requests.py"]
test_references: ["tests/test_agents.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-757
---

# Agent Proposals

## What It Does

Agent proposal workflows surface suggested agent changes or actions for the active project.

## Why It Exists

Agent Proposals exists so the work represented by Agents > Proposals has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Agents > Proposals
- Navigation group: Agents
- Primary component: `AgentsView`

## How UX Researchers Use It

- Open Agents > Proposals from the Istara navigation or the parent tab.
- Use the visible controls in this surface to review agent proposals in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Agents > Proposals when the current project has an autonomous suggestion for a new specialized agent.
- Approve or reject only proposals that belong to the active project.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active project.
- Move to related surfaces when needed: agents.registry, skills.proposals, tasks.review.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped proposal records generated from tasks in the active project.
- Approved custom agents scoped to the active project.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.
- Proposals from other projects are not listed and cannot be approved or rejected through this project view.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [agents.registry](../../agents/registry/researcher.md)
- [skills.proposals](../../skills/proposals/researcher.md)
- [tasks.review](../../tasks/review/researcher.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)

## Evidence

- Source files: `frontend/src/components/agents/AgentsView.tsx`, `frontend/src/lib/api.ts`, `backend/app/api/routes/agents.py`, `backend/app/core/agent_factory.py`, `backend/app/core/improvement_governance_evidence.py`, `backend/app/core/meta_hyperagent.py`, `backend/app/agents/orchestrator.py`, `backend/app/api/routes/permission_requests.py`
- API references: `backend/app/api/routes/agents.py`, `backend/app/api/routes/permission_requests.py`
- Tests: `tests/test_agents.py`, `tests/test_project_scope_contracts.py`
