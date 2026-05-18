---
stable_id: context.editor
title: Project Context Editor
ui_path: Context > Editor
audience: architecture
status: documented
related_features: ["chat.steering", "memory.context-dag"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/projects/ContextEditor.tsx", "backend/app/api/routes/projects.py"]
api_references: ["backend/app/api/routes/projects.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Project Context Editor Architecture

## Implementation Summary

The Context view edits project background, goals, assumptions, and other structured context used by Istara workflows.

## Frontend Surface

- `frontend/src/components/projects/ContextEditor.tsx`
- `backend/app/api/routes/projects.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/projectStore.ts`

### API And Backend

- `backend/app/api/routes/projects.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/projects/ContextEditor.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [chat.steering](../../chat/steering/architecture.md)
- [memory.context-dag](../../memory/context-dag/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
