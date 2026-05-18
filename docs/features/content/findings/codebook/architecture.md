---
stable_id: findings.codebook
title: Findings Codebook
ui_path: Findings > Codebook
audience: architecture
status: documented
related_features: ["findings.evidence", "findings.review"]
related_glossary: ["atomic-research"]
code_references: ["frontend/src/components/findings/FindingsView.tsx", "frontend/src/components/findings/CodebookViewer.tsx", "backend/app/api/routes/codebooks.py", "backend/app/api/routes/codebook_versions.py"]
api_references: ["backend/app/api/routes/codebooks.py", "backend/app/api/routes/codebook_versions.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Findings Codebook Architecture

## Implementation Summary

The Codebook tab surfaces qualitative coding structures and codebook versions associated with project findings.

## Frontend Surface

- `frontend/src/components/findings/FindingsView.tsx`
- `frontend/src/components/findings/CodebookViewer.tsx`
- `backend/app/api/routes/codebooks.py`
- `backend/app/api/routes/codebook_versions.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/codebooks.py`
- `backend/app/api/routes/codebook_versions.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/findings/FindingsView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [findings.evidence](../../findings/evidence/architecture.md)
- [findings.review](../../findings/review/architecture.md)

## Related Concepts

- [atomic-research](../../../glossary/atomic-research.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
