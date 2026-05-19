---
stable_id: memory.agent
title: Agent Memory
ui_path: Memory > Agent
audience: researcher
status: documented
related_features: ["agents.detail", "memory.knowledge"]
related_glossary: ["rag", "a2a"]
code_references: ["frontend/src/components/memory/MemoryView.tsx", "backend/app/core/agent_memory.py"]
api_references: ["backend/app/api/routes/memory.py"]
test_references: ["tests/test_memory.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-757
---

# Agent Memory

## What It Does

The Agent memory tab exposes memory tied to agent behavior and project collaboration in the active project.

## Why It Exists

Agent Memory exists so the work represented by Memory > Agent has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Memory > Agent
- Navigation group: Memory
- Primary component: `MemoryView`

## How UX Researchers Use It

- Open Memory > Agent from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with agent memory in the active project context.
- Project switches clear loaded agent notes before the next project's agents are fetched.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Memory > Agent when the current research task needs agent memory.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: agents.detail, memory.knowledge.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with agent memory.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [agents.detail](../../agents/detail/researcher.md)
- [memory.knowledge](../../memory/knowledge/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)
- [a2a](../../../glossary/a2a.md)

## Evidence

- Source files: `frontend/src/components/memory/MemoryView.tsx`, `backend/app/core/agent_memory.py`
- API references: `backend/app/api/routes/memory.py`
- Tests: `tests/test_memory.py`
