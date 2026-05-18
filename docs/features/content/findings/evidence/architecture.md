---
stable_id: findings.evidence
title: Findings Evidence
ui_path: Findings > Evidence
audience: architecture
status: documented
related_features: ["findings.phase-tabs", "findings.codebook", "findings.reports"]
related_glossary: ["atomic-research", "triangulation"]
code_references: ["frontend/src/components/findings/FindingsView.tsx", "backend/app/api/routes/findings.py"]
api_references: ["backend/app/api/routes/findings.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Findings Evidence Architecture

## Implementation Summary

The Findings evidence tab lists research insights and recommendations for the active project and supports phase-oriented review.

## Frontend Surface

- `frontend/src/components/findings/FindingsView.tsx`
- `backend/app/api/routes/findings.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/projectStore.ts`

### API And Backend

- `backend/app/api/routes/findings.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/findings/FindingsView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [findings.phase-tabs](../../findings/phase-tabs/architecture.md)
- [findings.codebook](../../findings/codebook/architecture.md)
- [findings.reports](../../findings/reports/architecture.md)

## Related Concepts

- [atomic-research](../../../glossary/atomic-research.md)
- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
