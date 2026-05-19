---
stable_id: autoresearch.experiments
title: Autoresearch Experiments
ui_path: Autoresearch > Experiments
audience: researcher
status: documented
related_features: ["autoresearch.dashboard", "autoresearch.config"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/autoresearch/AutoresearchView.tsx", "backend/app/core/autoresearch_engine.py", "backend/app/core/autoresearch_runners/question_bank.py"]
api_references: ["backend/app/api/routes/autoresearch.py"]
test_references: ["tests/test_autoresearch.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-754; CF-SPEC-96 / CF-1226
---

# Autoresearch Experiments

## What It Does

Experiments configure and inspect automated research runs across strategies or parameters.

## Why It Exists

Autoresearch Experiments exists so the work represented by Autoresearch > Experiments has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Autoresearch > Experiments
- Navigation group: Autoresearch
- Primary component: `AutoresearchView`

## How UX Researchers Use It

- Open Autoresearch > Experiments from the Istara navigation or the parent tab.
- Use the visible controls in this surface to start, stop, and inspect only autoresearch experiments in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Autoresearch > Experiments when the current research task needs autoresearch experiments.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: autoresearch.dashboard, autoresearch.config.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped experiment history and runtime actions associated with the active project.
- Generated experiment records, reasoning memories, and improvement proposals keep the project id that authorized the run.
- Question-bank experiments can only evaluate or rewrite deployments that belong to the active project; stale deployment ids from another project are treated as not found before LLM evaluation or mutation.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [autoresearch.dashboard](../../autoresearch/dashboard/researcher.md)
- [autoresearch.config](../../autoresearch/config/researcher.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Evidence

- Source files: `frontend/src/components/autoresearch/AutoresearchView.tsx`, `backend/app/core/autoresearch_engine.py`, `backend/app/core/autoresearch_runners/question_bank.py`
- API references: `backend/app/api/routes/autoresearch.py`
- Tests: `tests/test_autoresearch.py`, `tests/test_project_scope_contracts.py`
