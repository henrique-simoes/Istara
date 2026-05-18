---
stable_id: agents.proposals
title: Agent Proposals
ui_path: Agents > Proposals
audience: researcher
status: needs-verification
related_features: ["agents.registry", "skills.proposals", "tasks.review"]
related_glossary: ["a2a"]
code_references: ["frontend/src/components/agents/AgentsView.tsx", "backend/app/api/routes/agents.py", "backend/app/api/routes/permission_requests.py"]
api_references: ["backend/app/api/routes/agents.py", "backend/app/api/routes/permission_requests.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Agent Proposals

## What It Does

Agent proposal workflows surface suggested agent changes or actions for review.

## Why It Exists

Agent Proposals exists so the work represented by Agents > Proposals has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Agents > Proposals
- Navigation group: Agents
- Primary component: `AgentsView`

## How UX Researchers Use It

- Open Agents > Proposals from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with agent proposals in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Agents > Proposals when the current research task needs agent proposals.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: agents.registry, skills.proposals, tasks.review.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with agent proposals.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

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

- Source files: `frontend/src/components/agents/AgentsView.tsx`, `backend/app/api/routes/agents.py`, `backend/app/api/routes/permission_requests.py`
- API references: `backend/app/api/routes/agents.py`, `backend/app/api/routes/permission_requests.py`
- Tests: none recorded
