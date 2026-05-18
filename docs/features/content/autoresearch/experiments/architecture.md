---
stable_id: autoresearch.experiments
title: Autoresearch Experiments
ui_path: Autoresearch > Experiments
audience: architecture
status: documented
related_features: ["autoresearch.dashboard", "autoresearch.config"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/autoresearch/AutoresearchView.tsx", "backend/app/core/autoresearch_engine.py"]
api_references: ["backend/app/api/routes/autoresearch.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Autoresearch Experiments Architecture

## Implementation Summary

Experiments configure and inspect automated research runs across strategies or parameters.

## Frontend Surface

- `frontend/src/components/autoresearch/AutoresearchView.tsx`
- `backend/app/core/autoresearch_engine.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/autoresearchStore.ts`

### API And Backend

- `backend/app/api/routes/autoresearch.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/autoresearch/AutoresearchView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [autoresearch.dashboard](../../autoresearch/dashboard/architecture.md)
- [autoresearch.config](../../autoresearch/config/architecture.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
