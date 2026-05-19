---
stable_id: ensemble.health
title: Ensemble Health
ui_path: Ensemble Health
audience: architecture
status: documented
related_features: ["quality.dashboard", "compute.pool"]
related_glossary: ["fleiss-kappa"]
code_references: ["frontend/src/components/common/EnsembleHealthView.tsx", "backend/app/core/consensus.py", "backend/app/core/validation.py", "backend/app/core/agent_execution.py"]
api_references: ["backend/app/api/routes/metrics.py"]
test_references: ["tests/test_validation_project_scope.py", "tests/test_evaluation_skill.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-92 / CF-1170
---

# Ensemble Health Architecture

## Implementation Summary

Ensemble Health surfaces health and consensus signals for Istara's multi-model or multi-agent ensemble behavior.

## Frontend Surface

- `frontend/src/components/common/EnsembleHealthView.tsx`
- `backend/app/core/consensus.py`
- `backend/app/core/validation.py`
- `backend/app/core/agent_execution.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/metrics.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/common/EnsembleHealthView.tsx` and the UI navigation path recorded in the inventory.
- Project-bound ensemble validation must carry the active `project_id` into adversarial review, self-MoA, full ensemble, debate rounds, model-server selection, and validation embeddings, so donated relay/browser compute is only selected when authorized for that project.
- Validation calls without project context remain server-owned/local only; cross-project compute aggregation is reserved for explicit admin-only surfaces.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Ensemble LLM calls must preserve project scope when validating task output or skill artifacts.

## Tests And Verification

- `tests/test_validation_project_scope.py`
- `tests/test_evaluation_skill.py`

## Related Features

- [quality.dashboard](../../quality/dashboard/architecture.md)
- [compute.pool](../../compute/pool/architecture.md)

## Related Concepts

- [fleiss-kappa](../../../glossary/fleiss-kappa.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-92 / CF-1170
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
