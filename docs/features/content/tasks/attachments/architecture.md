---
stable_id: tasks.attachments
title: Task Attachments
ui_path: Tasks > Attachments
audience: architecture
status: needs-verification
related_features: ["documents.upload", "tasks.editor"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/kanban/TaskEditor.tsx", "backend/app/api/routes/tasks.py", "backend/app/api/routes/files.py"]
api_references: ["backend/app/api/routes/tasks.py", "backend/app/api/routes/files.py"]
test_references: ["tests/test_tasks.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-73 / CF-941
---

# Task Attachments Architecture

## Implementation Summary

Tasks can reference project files or documents so research work stays connected to the evidence it depends on.

## Frontend Surface

- `frontend/src/components/kanban/TaskEditor.tsx`
- `backend/app/api/routes/tasks.py`
- `backend/app/api/routes/files.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/taskStore.ts`

### API And Backend

- `backend/app/api/routes/tasks.py`
- `backend/app/api/routes/files.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/kanban/TaskEditor.tsx` and the UI navigation path recorded in the inventory.
- Attachment and detachment routes require the active `project_id`, load the task by both id and project, and then verify the document belongs to the same project before updating task input or output document ids.
- The Task Editor opens the document picker only for the active project and sends task updates with the same active project scope.
- Attached documents and task outputs feed retrieval, but the research-validity chain is task-linked evidence units, code applications, and coding runs. Document-heavy task work must not use generic retrieval chunks as coding identity; accepted/reconciled task-linked evidence is the substrate that later report routing checks.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- `tests/test_tasks.py`

## Related Features

- [documents.upload](../../documents/upload/architecture.md)
- [tasks.editor](../../tasks/editor/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-73 / CF-941
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
