---
stable_id: autoresearch.config
title: Autoresearch Configuration
ui_path: Autoresearch > Config
audience: researcher
status: documented
related_features: ["autoresearch.experiments", "chat.model-controls"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/autoresearch/AutoresearchView.tsx", "backend/app/core/autoresearch_runners/rag_params.py", "backend/app/core/agentic/dispatcher.py"]
api_references: ["backend/app/api/routes/autoresearch.py"]
test_references: ["tests/test_autoresearch.py", "tests/test_project_scope_contracts.py", "tests/pi_production/test_w6_autoresearch_runners.py"]
last_verified: 2026-07-22
compass: CF-SPEC-60 / CF-754; CF-SPEC-8
---

# Autoresearch Configuration

## What It Does

Autoresearch configuration sets parameters for automated research strategies and runs.

## Why It Exists

Autoresearch Configuration exists so the work represented by Autoresearch > Config has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Autoresearch > Config
- Navigation group: Autoresearch
- Primary component: `AutoresearchView`

## How UX Researchers Use It

- Open Autoresearch > Config from the Istara navigation or the parent tab.
- Use the visible controls in this surface to review autoresearch configuration; global enable/disable and limit changes require global admin access.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Autoresearch > Config when the current research task needs autoresearch configuration.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: autoresearch.experiments, chat.model-controls.

## Inputs, Outputs, And Expected Outcomes

- Global runtime configuration values that contain no project content.
- Project-scoped status refreshes shown from this tab, filtered to the active project before any operational metrics are rendered.

## Model Routing And Engine Selection

- The RAG-parameter runner tunes retrieval settings by asking a model to suggest the next parameters to try, then scoring how well retrieval performs with them.
- Pi Replacement wave W6 sends that suggestion call through Istara's shared agentic dispatcher, so RAG tuning can run on either the Pi replacement engine or the legacy engine without changing what the tuning does. The experiment start boundary binds an explicit `pi` or `legacy` choice once, or defaults from `settings.agentic_core` when no engine is supplied. W9 removed the old per-site legacy fallback: the dispatcher is the only path, and selecting the legacy engine is still a safe rollback because the dispatcher serves it through its own legacy executor.
- Only the suggestion step is a direct `agentic.completion` call. The embedding the runner uses to score retrieval quality inherits the W8 `agentic.embed` dispatch, so legacy keeps the unchanged embedding plane and Pi uses the embeddings gateway without changing retrieval scoring semantics.
- The runner stays bound to the project that authorized the experiment for engine choice, telemetry, and execution, and global configuration changes remain admin-only and carry no project content.
- The full engine-selection behavior for all six autoresearch runners is described on the [Autoresearch Experiments](../../autoresearch/experiments/researcher.md) page.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [autoresearch.experiments](../../autoresearch/experiments/researcher.md)
- [chat.model-controls](../../chat/model-controls/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/autoresearch/AutoresearchView.tsx`, `backend/app/core/autoresearch_runners/rag_params.py`, `backend/app/core/agentic/dispatcher.py`
- API references: `backend/app/api/routes/autoresearch.py`
- Tests: `tests/test_autoresearch.py`, `tests/test_project_scope_contracts.py`, `tests/pi_production/test_w6_autoresearch_runners.py`
