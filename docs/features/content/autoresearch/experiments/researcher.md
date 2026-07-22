---
stable_id: autoresearch.experiments
title: Autoresearch Experiments
ui_path: Autoresearch > Experiments
audience: researcher
status: documented
related_features: ["autoresearch.dashboard", "autoresearch.config"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/autoresearch/AutoresearchView.tsx", "backend/app/core/autoresearch_engine.py", "backend/app/core/autoresearch_runners/model_temp.py", "backend/app/core/autoresearch_runners/question_bank.py", "backend/app/core/agentic/dispatcher.py"]
api_references: ["backend/app/api/routes/autoresearch.py"]
test_references: ["tests/test_autoresearch.py", "tests/test_project_scope_contracts.py", "tests/pi_production/test_w6_autoresearch_runners.py"]
last_verified: 2026-07-22
compass: CF-SPEC-60 / CF-754; CF-SPEC-96 / CF-1226; CF-SPEC-8
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

## Model Routing And Engine Selection

- Autoresearch experiments run through six loop runners — model-and-temperature sweeps, persona tuning, question-bank improvement, RAG-parameter tuning, skill-prompt tuning, and UI-simulation tuning. Each runner makes its own model calls to hypothesize a change, evaluate it, and score the result.
- Pi Replacement wave W6 sends those runner calls through Istara's shared agentic dispatcher when the `agentic_core` engine is enabled, so the same experiment can run on either the Pi replacement engine or the legacy engine without changing what the experiment does. When the flag is off, the runners use the legacy model plane exactly as before, so switching engines is a safe rollback.
- Which engine ran an experiment is recorded in the run's usage accounting, so Pi and legacy runs of the same experiment stay distinguishable and auditable; no prompts, hypotheses, or responses are added to that accounting.
- Model-and-temperature sweeps on the Pi engine explore the configured Pi model catalog (settings endpoints, registered LLM servers, and local Ollama or LM Studio models) across temperatures, skipping embedding-only models. Each catalog endpoint is swept as its own comparison point, so two endpoints that serve the same model still count as two distinct points rather than collapsing into one. If the catalog cannot span the requested number of distinct endpoints (two by default) the run is marked as a truncated sweep rather than quietly shrinking, so a narrow comparison stays visible instead of hidden.
- RAG-parameter tuning moves only its suggestion step onto the new engine; the retrieval-quality embedding it uses to score results stays on the legacy plane until a later wave (W8) adds the embeddings gateway.
- Every runner stays bound to the project that authorized the experiment: engine choice, telemetry, and execution all use that authorized project, and the governed proposal-only path for autoresearch is unchanged, so a run cannot act on or account against another project.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [autoresearch.dashboard](../../autoresearch/dashboard/researcher.md)
- [autoresearch.config](../../autoresearch/config/researcher.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Evidence

- Source files: `frontend/src/components/autoresearch/AutoresearchView.tsx`, `backend/app/core/autoresearch_engine.py`, `backend/app/core/autoresearch_runners/model_temp.py`, `backend/app/core/autoresearch_runners/question_bank.py`, `backend/app/core/agentic/dispatcher.py`
- API references: `backend/app/api/routes/autoresearch.py`
- Tests: `tests/test_autoresearch.py`, `tests/test_project_scope_contracts.py`, `tests/pi_production/test_w6_autoresearch_runners.py`
