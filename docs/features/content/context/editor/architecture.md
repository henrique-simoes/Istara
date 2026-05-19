---
stable_id: context.editor
title: Project Context Editor
ui_path: Context > Editor
audience: architecture
status: documented
related_features: ["chat.steering", "memory.context-dag"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/projects/ContextEditor.tsx", "frontend/src/components/common/ContextPreview.tsx", "backend/app/api/routes/projects.py", "backend/app/api/routes/context_hierarchy.py", "backend/app/core/context_hierarchy.py"]
api_references: ["backend/app/api/routes/projects.py", "backend/app/api/routes/context_hierarchy.py"]
test_references: ["tests/test_context_hierarchy.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-776
---

# Project Context Editor Architecture

## Implementation Summary

The Context view edits project background, goals, assumptions, and other structured context used by Istara workflows. The context hierarchy prompt composition is project-local: database-backed company, product, project, task, and agent context rows are loaded only when their `project_id` matches the active project. Shared platform guidance comes from the built-in platform prompt, not mutable global context rows.

## Frontend Surface

- `frontend/src/components/projects/ContextEditor.tsx`
- `frontend/src/components/common/ContextPreview.tsx`
- `backend/app/api/routes/projects.py`
- `backend/app/api/routes/context_hierarchy.py`
- `backend/app/core/context_hierarchy.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/projectStore.ts`

### API And Backend

- `backend/app/api/routes/projects.py`
- `backend/app/api/routes/context_hierarchy.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/projects/ContextEditor.tsx` and the UI navigation path recorded in the inventory.
- Context preview calls `/api/contexts/composed/{project_id}` for the active project. The route verifies project viewer access and the backend composer filters context rows by exact project id.
- Admin-only unscoped context maintenance may list unassigned rows, but those rows are not inherited by project prompt composition.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.
- Database-backed context hierarchy rows are project content. They must not be treated as org-global inheritance for project-facing prompts, previews, or agent execution.

## Tests And Verification

- `tests/test_context_hierarchy.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [chat.steering](../../chat/steering/architecture.md)
- [memory.context-dag](../../memory/context-dag/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-776
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
