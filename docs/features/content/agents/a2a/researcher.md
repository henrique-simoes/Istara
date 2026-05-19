---
stable_id: agents.a2a
title: Agent-To-Agent Log
ui_path: Agents > A2A
audience: researcher
status: documented
related_features: ["agents.registry", "loops.agent-loops"]
related_glossary: ["a2a"]
code_references: ["frontend/src/components/agents/AgentsView.tsx", "frontend/src/stores/agentStore.ts", "frontend/src/lib/api.ts", "backend/app/api/routes/agents.py", "backend/app/api/routes/a2a.py", "backend/app/api/websocket.py", "backend/app/services/a2a.py", "backend/app/models/agent.py", "backend/app/core/agent_lifecycle.py", "backend/app/core/sub_agent_worker.py"]
api_references: ["backend/app/api/routes/agents.py", "backend/app/api/routes/a2a.py", "backend/app/api/websocket.py"]
test_references: ["tests/test_agents.py", "tests/test_a2a_project_claims.py", "tests/test_a2a_service_scope.py", "tests/test_a2a_security.py", "tests/test_websocket.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-56 / CF-698; CF-SPEC-60 / CF-776; CF-SPEC-64 / CF-828; CF-SPEC-74 / CF-949; CF-SPEC-99 / CF-1244
---

# Agent-To-Agent Log

## What It Does

The A2A tab displays agent-to-agent communication or coordination events for operational visibility in the active project.

## Why It Exists

Agent-To-Agent Log exists so the work represented by Agents > A2A has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Agents > A2A
- Navigation group: Agents
- Primary component: `AgentsView`

## How UX Researchers Use It

- Open Agents > A2A from the Istara navigation or the parent tab.
- Review only the agent messages connected to the active project context.
- If no active project is selected, the A2A log stays empty instead of falling back to a global message feed.
- Switching projects clears the previous project's A2A rows before loading the new project, so stale messages should not remain visible during loading or failed refreshes.
- A2A discovery also uses the active project, so agents from another project are not disclosed as a global catalog.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Agents > A2A when the current research task needs agent-to-agent log.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: agents.registry, loops.agent-loops.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped A2A messages associated with the active project.
- New A2A messages are stored with the active project's id and are rejected before persistence if the project is missing or conflicting.
- A2A messages only appear when their metadata, task ownership, and project-scoped sender/recipient agents agree on the active project.
- External A2A JSON-RPC task submissions must carry `project_id`, so submitted work is attached to a project before it can appear in Istara.
- Autonomous agent inboxes and collaboration/debate threads use the same project boundary before building LLM prompt context, so messages from another project are not used as hidden coordination history.
- Realtime A2A and agent-thinking updates must resolve to the same active project from consistent metadata, task/deployment/channel, and agent ownership claims before they can appear in the shell.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [agents.registry](../../agents/registry/researcher.md)
- [loops.agent-loops](../../loops/agent-loops/researcher.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)

## Evidence

- Source files: `frontend/src/components/agents/AgentsView.tsx`, `frontend/src/stores/agentStore.ts`, `frontend/src/lib/api.ts`, `backend/app/api/routes/agents.py`, `backend/app/api/routes/a2a.py`, `backend/app/api/websocket.py`, `backend/app/services/a2a.py`, `backend/app/models/agent.py`
- API references: `backend/app/api/routes/agents.py`, `backend/app/api/routes/a2a.py`, `backend/app/api/websocket.py`
- Tests: `tests/test_agents.py`, `tests/test_a2a_project_claims.py`, `tests/test_a2a_service_scope.py`, `tests/test_a2a_security.py`, `tests/test_websocket.py`, `tests/test_project_scope_contracts.py`
