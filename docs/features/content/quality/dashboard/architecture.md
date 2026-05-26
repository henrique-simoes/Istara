---
stable_id: quality.dashboard
title: Quality Dashboard
ui_path: Quality Dashboard
audience: architecture
status: documented
related_features: ["ensemble.health", "settings.governed-evolution"]
related_glossary: ["triangulation", "fleiss-kappa"]
code_references: ["frontend/src/components/common/QualityView.tsx", "backend/app/core/validation.py", "backend/app/core/adaptive_validation.py", "backend/app/core/agent_execution.py", "backend/app/core/research_validity.py", "backend/app/models/telemetry_span.py"]
api_references: ["backend/app/api/routes/metrics.py", "backend/app/api/routes/research_validity.py"]
test_references: ["tests/test_validation_project_scope.py", "tests/test_evaluation_skill.py", "tests/test_research_validity_contract.py", "tests/test_telemetry.py"]
last_verified: 2026-05-21
compass: CF-SPEC-53 / CF-657; CF-SPEC-92 / CF-1170; CF-SPEC-124 / CF-1590
---

# Quality Dashboard Architecture

## Implementation Summary

Quality Dashboard summarizes system quality, validation, research-validity, and operational signals for the running Istara installation.

## Frontend Surface

- `frontend/src/components/common/QualityView.tsx`
- `backend/app/core/validation.py`
- `backend/app/core/adaptive_validation.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/metrics.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/common/QualityView.tsx` and the UI navigation path recorded in the inventory.
- Project-bound ensemble validation receives the active `project_id` from task execution and forwards it through adversarial review, self-MoA, full ensemble, debate rounds, and validation embeddings so donated relay/browser compute is only eligible when authorized for that project.
- Validation helpers without a project context keep relay/browser donors excluded by the compute registry, preserving the explicit admin/global compute exception on admin surfaces instead of making validation global by omission.
- Research-validity telemetry records content-free handles for coding runs, evidence units, codebook versions, route IDs, donor IDs, retrieval mode, and reliability score. Telemetry must support audits without storing prompts, responses, source quotes, or private document content.
- The project-scoped research-validity telemetry audit route summarizes the canonical lifecycle categories: evidence extraction, codebook governance, coding reliability, review/reconciliation, donor lifecycle, retrieval traceability, context safety, promotion gates, and governed learning. These signals are process evidence for dashboards and self-improvement systems, not report evidence.
- Quality signals that come from response-level validation must stay distinct from formal qualitative coding reliability over evidence-unit matrices. Debate/adversarial validation only emits review/reconciliation telemetry when the caller supplies coded-evidence handles such as coding run, evidence unit, and codebook version.
- Governed-learning producers emit content-free audit events: `autoresearch.validity_update`, `self_evolution.proposal`, `reasoning_bank.lesson`, `memento_skill.health`, and `meta_hyperagent.proposal`. These events carry project/agent/skill handles and quality status only; they do not store memory bodies, proposal reasons, hypotheses, prompts, source quotes, or report text.
- The real-user benchmark records `research-spine-evidence.json` and `self-improvement-evidence.json` as test evidence for this contract: telemetry, ReasoningBank, Memento skill health, Meta-Hyperagent, Autoresearch, RAG/GraphRAG traceability, and governance proposal checks are process-learning inputs, never report evidence by themselves.
- The dashboard must interpret tool success, execution success, verification result, research quality, and reportability as separate signals. Verification-failed or provisional skill output can be visible for review but cannot improve Memento health, model ranking, or report eligibility as accepted research.
- Model/skill quality statistics are project-scoped. Telemetry leaderboards and skill routing boosts must not use another project's model performance as positive evidence.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- LLM validation calls must carry project scope whenever they validate project task output or skill artifacts.
- Self-evolution, autoresearch, Memento skills, and ReasoningBank may use research-validity telemetry to propose improvements, but they must not silently weaken methodology, thresholds, authorization, review, or report gates. ReasoningBank memories remain process lessons and cannot be used as report evidence.

## Tests And Verification

- `tests/test_validation_project_scope.py`
- `tests/test_evaluation_skill.py`

## Related Features

- [ensemble.health](../../ensemble/health/architecture.md)
- [settings.governed-evolution](../../settings/governed-evolution/architecture.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)
- [fleiss-kappa](../../../glossary/fleiss-kappa.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-92 / CF-1170
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
