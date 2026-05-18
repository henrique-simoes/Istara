---
stable_id: laws.catalog
title: UX Laws Catalog
ui_path: UX Laws > Catalog
audience: architecture
status: documented
related_features: ["laws.compliance", "findings.evidence"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/laws/LawsView.tsx", "frontend/src/stores/lawsStore.ts", "backend/app/api/routes/laws.py"]
api_references: ["backend/app/api/routes/laws.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# UX Laws Catalog Architecture

## Implementation Summary

The UX Laws catalog gives researchers a structured reference for applying UX laws to research and design interpretation.

## Frontend Surface

- `frontend/src/components/laws/LawsView.tsx`
- `frontend/src/stores/lawsStore.ts`
- `backend/app/api/routes/laws.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/lawsStore.ts`

### API And Backend

- `backend/app/api/routes/laws.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/laws/LawsView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [laws.compliance](../../laws/compliance/architecture.md)
- [findings.evidence](../../findings/evidence/architecture.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
