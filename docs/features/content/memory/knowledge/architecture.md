---
stable_id: memory.knowledge
title: Knowledge Memory
ui_path: Memory > Knowledge
audience: architecture
status: documented
related_features: ["memory.agent", "memory.context-dag", "documents.library"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/memory/MemoryView.tsx", "frontend/src/lib/memoryApi.ts", "backend/app/api/routes/memory.py"]
api_references: ["backend/app/api/routes/memory.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Knowledge Memory Architecture

## Implementation Summary

The Memory knowledge tab manages project knowledge artifacts and retrieval material.

## Frontend Surface

- `frontend/src/components/memory/MemoryView.tsx`
- `frontend/src/lib/memoryApi.ts`
- `backend/app/api/routes/memory.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/memory.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/memory/MemoryView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [memory.agent](../../memory/agent/architecture.md)
- [memory.context-dag](../../memory/context-dag/architecture.md)
- [documents.library](../../documents/library/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
