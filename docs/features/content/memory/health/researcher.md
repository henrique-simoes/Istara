---
stable_id: memory.health
title: Memory Health
ui_path: Memory > Health
audience: researcher
status: needs-verification
related_features: ["memory.knowledge", "quality.dashboard"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/memory/MemoryView.tsx", "backend/app/core/vector_health.py"]
api_references: ["backend/app/api/routes/memory.py"]
test_references: ["tests/test_memory.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-757
---

# Memory Health

## What It Does

Memory health surfaces status and quality signals for memory or retrieval infrastructure in the active project.

## Why It Exists

Memory Health exists so the work represented by Memory > Health has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Memory > Health
- Navigation group: Memory
- Primary component: `MemoryView`

## How UX Researchers Use It

- Open Memory > Health from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with memory health in the active project context.
- Project switches clear loaded health statistics before the next project's memory stats are fetched.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Memory > Health when the current research task needs memory health.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: memory.knowledge, quality.dashboard.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with memory health.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [memory.knowledge](../../memory/knowledge/researcher.md)
- [quality.dashboard](../../quality/dashboard/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/memory/MemoryView.tsx`, `backend/app/core/vector_health.py`
- API references: `backend/app/api/routes/memory.py`
- Tests: `tests/test_memory.py`
