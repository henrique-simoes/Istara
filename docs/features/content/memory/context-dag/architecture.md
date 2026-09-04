---
stable_id: memory.context-dag
title: Context DAG
ui_path: Memory > Context DAG
audience: architecture
status: documented
related_features: ["context.editor", "memory.knowledge", "chat.sessions"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/memory/MemoryView.tsx", "frontend/src/components/memory/ContextDAGView.tsx", "frontend/src/stores/sessionStore.ts", "frontend/src/lib/contextDagApi.ts", "backend/app/api/routes/context_dag.py", "backend/app/core/context_dag.py"]
api_references: ["backend/app/api/routes/context_dag.py"]
test_references: ["tests/test_context_dag.py", "tests/test_context_dag_ui_contracts.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-761
---

# Context DAG Architecture

## Implementation Summary

The Context DAG tab visualizes or inspects relationships across project context nodes. Its chat-session picker only renders sessions from the active project, and every Context DAG API call carries the active project id so stale session ids cannot read a previous project's graph.

## Frontend Surface

- `frontend/src/components/memory/MemoryView.tsx`
- `frontend/src/components/memory/ContextDAGView.tsx`
- `frontend/src/stores/sessionStore.ts`
- `frontend/src/lib/contextDagApi.ts`
- `backend/app/api/routes/context_dag.py`
- `backend/app/core/context_dag.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/sessionStore.ts`

### API And Backend

- `backend/app/api/routes/context_dag.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/memory/MemoryView.tsx` and the UI navigation path recorded in the inventory.
- `ContextDAGView` derives `scopedSessions` from the active project before rendering the session selector and derives `scopedActiveSessionId` before calling context DAG structure, health, expand, grep, or compact APIs.
- `backend/app/api/routes/context_dag.py` requires `project_id` on session-by-id routes and loads the session by both `session_id` and `project_id` before returning structure, health, expansion, search, node metadata, or compaction output.
- Chat-triggered compaction is owned by a per-session task registry. Duplicate schedules reuse the active task, unexpected failures are logged, and application shutdown drains current-loop work while cancelling stale cross-loop tasks before the database engine closes.
- When no active project session is selected, the DAG stays in the empty selection state instead of rendering or querying a session from another project.
- History Search renders its result count with an explicit separator before the query label, including the zero-result state.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- RAG-related behavior depends on project context, documents, memory, or retrieval material referenced by the cited stores and routes.

## Tests And Verification

- `tests/test_context_dag.py`
- `tests/test_context_dag_ui_contracts.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [context.editor](../../context/editor/architecture.md)
- [memory.knowledge](../../memory/knowledge/architecture.md)
- [chat.sessions](../../chat/sessions/architecture.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-761
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
