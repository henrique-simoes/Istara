---
stable_id: autoresearch.dashboard
title: Autoresearch Dashboard
ui_path: Autoresearch > Dashboard
audience: architecture
status: documented
related_features: ["autoresearch.experiments", "autoresearch.leaderboard", "findings.review"]
related_glossary: ["triangulation", "fleiss-kappa", "rag"]
code_references: ["frontend/src/components/autoresearch/AutoresearchView.tsx", "frontend/src/stores/autoresearchStore.ts", "backend/app/api/routes/autoresearch.py", "backend/app/core/agent_research.py", "backend/app/core/research_validity.py"]
api_references: ["backend/app/api/routes/autoresearch.py", "backend/app/api/routes/research_validity.py"]
test_references: ["tests/test_autoresearch.py", "tests/test_project_scope_contracts.py", "tests/test_research_validity_contract.py"]
last_verified: 2026-05-21
compass: CF-SPEC-60 / CF-754; CF-SPEC-124 / CF-1590
---

# Autoresearch Dashboard Architecture

## Implementation Summary

The Autoresearch dashboard summarizes automated research experiment status and recent results. Autoresearch must follow the same research-validity pipeline as human-led research: evidence units, governed coding, reliability, reconciliation, review, and approved Done-task report gating.

## Frontend Surface

- `frontend/src/components/autoresearch/AutoresearchView.tsx`
- `frontend/src/stores/autoresearchStore.ts`
- `backend/app/api/routes/autoresearch.py`
- `backend/app/core/agent_research.py`
- `backend/app/core/research_validity.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/autoresearchStore.ts`
- Dashboard status requests use the active project id from `frontend/src/stores/projectStore.ts`; missing project context clears status instead of querying global metrics.

### API And Backend

- `backend/app/api/routes/autoresearch.py`
- `/api/autoresearch/status` requires `project_id`, enforces project access, and returns task, agent, document, finding, telemetry, schedule, and deployment metrics filtered to that project.
- Agent-generated code applications created from skill output should carry an evidence-unit handle and remain lower assurance until reliability/review gates are satisfied.

## Architecture Notes

- The feature is mounted through `frontend/src/components/autoresearch/AutoresearchView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Autoresearch status can inform automated experiment loops, so every operational signal in the dashboard must be scoped to the active project before it can influence agents, skills, LLM routing, or improvement proposals.
- Autoresearch may optimize retrieval, graph synthesis, coding prompts, and orchestration from telemetry, but it cannot silently alter protected methodology, codebooks, thresholds, authorization, human review, or report gates.

## Tests And Verification

- `tests/test_autoresearch.py` verifies project-scoped status metrics.
- `tests/test_project_scope_contracts.py` verifies frontend status calls carry the active project id and backend status uses project-filtered queries.
- `tests/test_research_validity_contract.py` verifies the shared research-validity contract that autoresearch must respect.

## Related Features

- [autoresearch.experiments](../../autoresearch/experiments/architecture.md)
- [autoresearch.leaderboard](../../autoresearch/leaderboard/architecture.md)
- [findings.review](../../findings/review/architecture.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)
- [fleiss-kappa](../../../glossary/fleiss-kappa.md)
- [rag](../../../glossary/rag.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-754
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
