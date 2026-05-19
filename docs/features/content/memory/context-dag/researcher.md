---
stable_id: memory.context-dag
title: Context DAG
ui_path: Memory > Context DAG
audience: researcher
status: documented
related_features: ["context.editor", "memory.knowledge", "chat.sessions"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/memory/MemoryView.tsx", "frontend/src/components/memory/ContextDAGView.tsx", "frontend/src/stores/sessionStore.ts", "frontend/src/lib/contextDagApi.ts", "backend/app/api/routes/context_dag.py", "backend/app/core/context_dag.py"]
api_references: ["backend/app/api/routes/context_dag.py"]
test_references: ["tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-761
---

# Context DAG

## What It Does

The Context DAG tab visualizes or inspects relationships across project context nodes. Its chat session selector only shows sessions that belong to the active project.

## Why It Exists

Context DAG exists so the work represented by Memory > Context DAG has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Memory > Context DAG
- Navigation group: Memory
- Primary component: `MemoryView / ContextDAGView`

## How UX Researchers Use It

- Open Memory > Context DAG from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with context dag in the active project context.
- If no active-project chat session exists, the DAG remains empty instead of showing a previous project's context graph.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Memory > Context DAG when the current research task needs context dag.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: context.editor, memory.knowledge, chat.sessions.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with context dag.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.
- Context DAG structure, search, expansion, and compaction for the selected session in the active project.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [context.editor](../../context/editor/researcher.md)
- [memory.knowledge](../../memory/knowledge/researcher.md)
- [chat.sessions](../../chat/sessions/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/memory/MemoryView.tsx`, `frontend/src/components/memory/ContextDAGView.tsx`, `frontend/src/stores/sessionStore.ts`, `frontend/src/lib/contextDagApi.ts`, `backend/app/api/routes/context_dag.py`, `backend/app/core/context_dag.py`
- API references: `backend/app/api/routes/context_dag.py`
- Tests: `tests/test_project_scope_contracts.py`
