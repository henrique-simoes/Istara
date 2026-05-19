---
stable_id: autoresearch.config
title: Autoresearch Configuration
ui_path: Autoresearch > Config
audience: researcher
status: documented
related_features: ["autoresearch.experiments", "chat.model-controls"]
related_glossary: ["rag"]
code_references: ["frontend/src/components/autoresearch/AutoresearchView.tsx", "backend/app/core/autoresearch_runners/rag_params.py"]
api_references: ["backend/app/api/routes/autoresearch.py"]
test_references: ["tests/test_autoresearch.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-18
compass: CF-SPEC-60 / CF-754
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

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [autoresearch.experiments](../../autoresearch/experiments/researcher.md)
- [chat.model-controls](../../chat/model-controls/researcher.md)

## Related Concepts

- [rag](../../../glossary/rag.md)

## Evidence

- Source files: `frontend/src/components/autoresearch/AutoresearchView.tsx`, `backend/app/core/autoresearch_runners/rag_params.py`
- API references: `backend/app/api/routes/autoresearch.py`
- Tests: `tests/test_autoresearch.py`, `tests/test_project_scope_contracts.py`
