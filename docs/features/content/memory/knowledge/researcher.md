---
stable_id: memory.knowledge
title: Knowledge Memory
ui_path: Memory > Knowledge
audience: researcher
status: documented
related_features: ["memory.agent", "memory.context-dag", "documents.library"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/memory/MemoryView.tsx", "frontend/src/lib/memoryApi.ts", "backend/app/api/routes/memory.py"]
api_references: ["backend/app/api/routes/memory.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Knowledge Memory

## What It Does

The Memory knowledge tab manages project knowledge artifacts and retrieval material.

## Why It Exists

Knowledge Memory exists so the work represented by Memory > Knowledge has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Memory > Knowledge
- Navigation group: Memory
- Primary component: `MemoryView`

## How UX Researchers Use It

- Open Memory > Knowledge from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with knowledge memory in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Memory > Knowledge when the current research task needs knowledge memory.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: memory.agent, memory.context-dag, documents.library.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with knowledge memory.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [memory.agent](../../memory/agent/researcher.md)
- [memory.context-dag](../../memory/context-dag/researcher.md)
- [documents.library](../../documents/library/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/memory/MemoryView.tsx`, `frontend/src/lib/memoryApi.ts`, `backend/app/api/routes/memory.py`
- API references: `backend/app/api/routes/memory.py`
- Tests: none recorded
