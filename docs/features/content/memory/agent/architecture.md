---
stable_id: memory.agent
title: Agent Memory
ui_path: Memory > Agent
audience: architecture
status: documented
related_features: ["agents.detail", "memory.knowledge"]
related_glossary: ["rag", "a2a"]
code_references: ["frontend/src/components/memory/MemoryView.tsx", "backend/app/core/agent_memory.py"]
api_references: ["backend/app/api/routes/memory.py"]
test_references: ["tests/test_memory.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-757
---

# Agent Memory Architecture

## Implementation Summary

The Agent memory tab exposes memory tied to agent behavior and project collaboration in the active project.

## Frontend Surface

- `frontend/src/components/memory/MemoryView.tsx`
- `backend/app/core/agent_memory.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/memory.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/memory/MemoryView.tsx` and the UI navigation path recorded in the inventory.
- Agent notes are read through `backend/app/api/routes/memory.py`, which validates project visibility before loading project agent-memory data.
- `MemoryView` remounts the Agent memory tab on active-project changes so notes cached for one project are not reused in another project view.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.
- Agent-to-agent behavior should be traced through agent stores, A2A routes, permissions, and review surfaces before changing assumptions.

## Tests And Verification

- `tests/test_memory.py`

## Related Features

- [agents.detail](../../agents/detail/architecture.md)
- [memory.knowledge](../../memory/knowledge/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)
- [a2a](../../../glossary/a2a.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-757
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
