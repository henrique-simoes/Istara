---
stable_id: autoresearch.experiments
title: Autoresearch Experiments
ui_path: Autoresearch > Experiments
audience: architecture
status: documented
related_features: ["autoresearch.dashboard", "autoresearch.config"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/autoresearch/AutoresearchView.tsx", "backend/app/core/autoresearch_engine.py", "backend/app/core/autoresearch_runners/__init__.py", "backend/app/core/autoresearch_runners/question_bank.py"]
api_references: ["backend/app/api/routes/autoresearch.py"]
test_references: ["tests/test_autoresearch.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-60 / CF-754; CF-SPEC-68 / CF-870; CF-SPEC-96 / CF-1226
---

# Autoresearch Experiments Architecture

## Implementation Summary

Experiments configure and inspect automated research runs across strategies or parameters.

## Frontend Surface

- `frontend/src/components/autoresearch/AutoresearchView.tsx`
- `backend/app/core/autoresearch_engine.py`
- `backend/app/core/autoresearch_runners/__init__.py`
- `backend/app/core/autoresearch_runners/question_bank.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/autoresearchStore.ts`
- Experiment history and start/stop actions are bound to the active project id; the store returns an empty experiment list instead of issuing an unscoped request when no project is active.

### API And Backend

- `backend/app/api/routes/autoresearch.py`
- Experiment list, start, and stop routes require `project_id` and enforce project access. Autoresearch engine records and broadcasts the experiment project id, and experiment history filters by `AutoresearchExperiment.project_id`.
- Starting an experiment requires the requested project to be active and unpaused before the runner is constructed or scheduled. The engine records the active project owner for the whole run, including baseline measurement, and repeats the active-project check before baseline and iteration work so a paused or missing project cannot keep processing in the background.
- The engine binds the authorized project id into each loop runner before baseline measurement. Question-bank runners then load and update `ResearchDeployment` rows by both deployment id and that bound project id, so a stale deployment id from another project cannot be measured, mutated, reverted, or sent into LLM evaluation.

## Architecture Notes

- The feature is mounted through `frontend/src/components/autoresearch/AutoresearchView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Autoresearch experiments can mutate strategies that later affect agents, skills, LLM choice, RAG behavior, question banks, or UI simulations. Each experiment must remain attached to the project that authorized it.
- Paused projects are execution-stop boundaries for autoresearch: no baseline measurement, mutation, model-choice exploration, reasoning memory, or improvement proposal should be produced after the project is paused.
- Baseline and candidate measurements run inside the autoresearch isolation context, so experiment probes do not write normal learning, skill-stat, or self-improvement evidence until they are explicitly promoted through project-bound governance.

## Tests And Verification

- `tests/test_autoresearch.py` verifies start/stop routing, runner project binding, and project-scoped question-bank deployment behavior.
- `tests/test_project_scope_contracts.py` verifies the frontend and backend keep experiment requests project-bound.

## Related Features

- [autoresearch.dashboard](../../autoresearch/dashboard/architecture.md)
- [autoresearch.config](../../autoresearch/config/architecture.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-754; CF-SPEC-68 / CF-870; CF-SPEC-96 / CF-1226
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
