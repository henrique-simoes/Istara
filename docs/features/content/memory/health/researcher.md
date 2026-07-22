---
stable_id: memory.health
title: Memory Health
ui_path: Memory > Health
audience: researcher
status: needs-verification
related_features: ["memory.knowledge", "quality.dashboard"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/memory/MemoryView.tsx", "backend/app/core/vector_health.py", "backend/app/core/embeddings.py", "backend/app/core/pi_runtime/embeddings_gateway.py", "backend/app/core/pi_runtime/model_manager_provisioning.py", "backend/app/core/agentic/dispatcher.py"]
api_references: ["backend/app/api/routes/memory.py"]
test_references: ["tests/test_memory.py", "tests/pi_production/test_w8_embeddings_gateway.py", "tests/pi_migration/test_count_to_zero.py"]
last_verified: 2026-07-22
compass: CF-SPEC-60 / CF-757; CF-SPEC-8
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

## Embeddings And Engine Selection

- Retrieval and memory features embed text into vectors. Pi Replacement wave W8 gives the Pi replacement engine its own embeddings path: because the Pi runtime cannot execute embeddings itself, a small gateway calls the configured embedding endpoint directly over HTTP, choosing a local Ollama or LM Studio model when one is available and otherwise a compatible remote endpoint. If no compatible endpoint exists it fails visibly instead of quietly using the legacy engine.
- Both engines embed with the same model, so switching engines never changes the meaning of a project's stored vectors. Istara checks this invariant at startup — together with the existing embedding-dimension health probe — and refuses to start with a mismatched configuration rather than silently mixing vector spaces.
- Embedding results are still cached first, so repeated lookups do not call the model again; only cache misses go through the new dispatch path, and each one is counted once in usage accounting regardless of engine. All fourteen retrieval, memory, and agent features that embed text keep working unchanged.
- Rolling back to the legacy engine is safe: embeddings return to the previous Ollama-based path and, because the model is the same on both engines, existing project vectors remain valid.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [memory.knowledge](../../memory/knowledge/researcher.md)
- [quality.dashboard](../../quality/dashboard/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/memory/MemoryView.tsx`, `backend/app/core/vector_health.py`, `backend/app/core/embeddings.py`, `backend/app/core/pi_runtime/embeddings_gateway.py`, `backend/app/core/agentic/dispatcher.py`
- API references: `backend/app/api/routes/memory.py`
- Tests: `tests/test_memory.py`, `tests/pi_production/test_w8_embeddings_gateway.py`, `tests/pi_migration/test_count_to_zero.py`
