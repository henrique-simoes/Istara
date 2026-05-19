---
stable_id: quality.dashboard
title: Quality Dashboard
ui_path: Quality Dashboard
audience: architecture
status: documented
related_features: ["ensemble.health", "settings.governed-evolution"]
related_glossary: ["triangulation", "fleiss-kappa"]
code_references: ["frontend/src/components/common/QualityView.tsx", "backend/app/core/validation.py", "backend/app/core/adaptive_validation.py", "backend/app/core/agent_execution.py"]
api_references: ["backend/app/api/routes/metrics.py"]
test_references: ["tests/test_validation_project_scope.py", "tests/test_evaluation_skill.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-92 / CF-1170
---

# Quality Dashboard Architecture

## Implementation Summary

Quality Dashboard summarizes system quality, validation, and operational signals for the running Istara installation.

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
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- LLM validation calls must carry project scope whenever they validate project task output or skill artifacts.

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
