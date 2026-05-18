---
stable_id: agents.proposals
title: Agent Proposals
ui_path: Agents > Proposals
audience: architecture
status: needs-verification
related_features: ["agents.registry", "skills.proposals", "tasks.review"]
related_glossary: ["a2a"]
code_references: ["frontend/src/components/agents/AgentsView.tsx", "backend/app/api/routes/agents.py", "backend/app/api/routes/permission_requests.py"]
api_references: ["backend/app/api/routes/agents.py", "backend/app/api/routes/permission_requests.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Agent Proposals Architecture

## Implementation Summary

Agent proposal workflows surface suggested agent changes or actions for review.

## Frontend Surface

- `frontend/src/components/agents/AgentsView.tsx`
- `backend/app/api/routes/agents.py`
- `backend/app/api/routes/permission_requests.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/agentStore.ts`

### API And Backend

- `backend/app/api/routes/agents.py`
- `backend/app/api/routes/permission_requests.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/agents/AgentsView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Agent-to-agent behavior should be traced through agent stores, A2A routes, permissions, and review surfaces before changing assumptions.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [agents.registry](../../agents/registry/architecture.md)
- [skills.proposals](../../skills/proposals/architecture.md)
- [tasks.review](../../tasks/review/architecture.md)

## Related Concepts

- [a2a](../../../glossary/a2a.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
