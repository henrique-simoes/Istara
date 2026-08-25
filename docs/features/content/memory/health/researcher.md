---
stable_id: memory.health
title: Memory Health
ui_path: Memory > Health
audience: researcher
status: needs-verification
related_features: ["memory.knowledge", "quality.dashboard"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/memory/MemoryView.tsx", "backend/app/core/vector_health.py", "backend/app/core/embeddings.py", "backend/app/core/rag.py", "backend/app/core/pi_runtime/embedding_profile.py", "backend/app/core/pi_runtime/embeddings_gateway.py", "backend/app/core/pi_runtime/model_manager_provisioning.py", "backend/app/core/agentic/dispatcher.py"]
api_references: ["backend/app/api/routes/memory.py"]
test_references: ["tests/test_memory.py", "tests/test_rag_resilience.py", "tests/pi_production/test_embedding_profile_authority.py", "tests/pi_production/test_w8_embeddings_gateway.py", "tests/pi_migration/test_count_to_zero.py"]
last_verified: 2026-08-25
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

- Retrieval and memory features use one versioned embedding profile owned by Pi Model Management. The
  profile fixes the model and exact endpoint for Istara and Pi loop choices alike. Changing a classical
  chat provider does not change the vector model. Missing or mismatched profile endpoints fail visibly.
- Startup loads the saved profile before checking vector health. Each project index is bound to that
  profile version; Istara refuses to search or add vectors when the binding differs, even if dimensions
  happen to match. Changing profile versions therefore requires a governed re-index, not a settings flip.
- Both engine routes are still probed independently for model/dimension equality. Empty, malformed,
  non-numeric, non-finite, or wrong-dimension vectors are rejected before cache or index writes.
- Embedding results are still cached first, so repeated lookups do not call the model again; only cache misses go through the new dispatch path, and each one is counted once in usage accounting regardless of engine. All fourteen retrieval, memory, and agent features that embed text keep working unchanged.
- Usage reports distinguish provider-reported embedding tokens/cost from estimates: remote responses with usage remain exact, while responses without usage are visibly governed as estimates rather than exact zero consumption.
- Switching back to Istara changes orchestration but keeps the same Pi-owned embedding profile, cache
  namespace, and project-index binding. It does not return embeddings to a separate Ollama authority.

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
