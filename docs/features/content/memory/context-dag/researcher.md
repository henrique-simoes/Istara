---
stable_id: memory.context-dag
title: Context DAG
ui_path: Memory > Context DAG
audience: researcher
status: documented
related_features: ["context.editor", "memory.knowledge"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/memory/MemoryView.tsx", "frontend/src/lib/contextDagApi.ts", "backend/app/api/routes/context_dag.py", "backend/app/core/context_dag.py"]
api_references: ["backend/app/api/routes/context_dag.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Context DAG

## What It Does

The Context DAG tab visualizes or inspects relationships across project context nodes.

## Why It Exists

Context DAG exists so the work represented by Memory > Context DAG has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Memory > Context DAG
- Navigation group: Memory
- Primary component: `MemoryView / ContextDAGView`

## How UX Researchers Use It

- Open Memory > Context DAG from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with context dag in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Memory > Context DAG when the current research task needs context dag.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: context.editor, memory.knowledge.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with context dag.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [context.editor](../../context/editor/researcher.md)
- [memory.knowledge](../../memory/knowledge/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/memory/MemoryView.tsx`, `frontend/src/lib/contextDagApi.ts`, `backend/app/api/routes/context_dag.py`, `backend/app/core/context_dag.py`
- API references: `backend/app/api/routes/context_dag.py`
- Tests: none recorded
