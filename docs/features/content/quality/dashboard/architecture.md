---
stable_id: quality.dashboard
title: Quality Dashboard
ui_path: Quality Dashboard
audience: architecture
status: documented
related_features: ["ensemble.health", "settings.governed-evolution"]
related_glossary: ["triangulation", "fleiss-kappa"]
code_references: ["frontend/src/components/common/QualityView.tsx", "backend/app/core/validation.py", "backend/app/core/adaptive_validation.py"]
api_references: ["backend/app/api/routes/metrics.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
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
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [ensemble.health](../../ensemble/health/architecture.md)
- [settings.governed-evolution](../../settings/governed-evolution/architecture.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)
- [fleiss-kappa](../../../glossary/fleiss-kappa.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
