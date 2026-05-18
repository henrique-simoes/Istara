---
stable_id: memory.context-dag
title: Context DAG
ui_path: Memory > Context DAG
audience: architecture
status: documented
related_features: ["context.editor", "memory.knowledge"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/memory/MemoryView.tsx", "frontend/src/lib/contextDagApi.ts", "backend/app/api/routes/context_dag.py", "backend/app/core/context_dag.py"]
api_references: ["backend/app/api/routes/context_dag.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Context DAG Architecture

## Implementation Summary

The Context DAG tab visualizes or inspects relationships across project context nodes.

## Frontend Surface

- `frontend/src/components/memory/MemoryView.tsx`
- `frontend/src/lib/contextDagApi.ts`
- `backend/app/api/routes/context_dag.py`
- `backend/app/core/context_dag.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/context_dag.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/memory/MemoryView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [context.editor](../../context/editor/architecture.md)
- [memory.knowledge](../../memory/knowledge/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
