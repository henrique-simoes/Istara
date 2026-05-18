---
stable_id: findings.review
title: Findings Code Review
ui_path: Findings > Review
audience: architecture
status: needs-verification
related_features: ["findings.codebook", "tasks.review"]
related_glossary: ["triangulation"]
code_references: ["frontend/src/components/findings/FindingsView.tsx", "frontend/src/components/findings/CodeReviewQueue.tsx"]
api_references: ["backend/app/api/routes/codebooks.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Findings Code Review Architecture

## Implementation Summary

The Review tab presents code review queues for validating and adjudicating qualitative coding work.

## Frontend Surface

- `frontend/src/components/findings/FindingsView.tsx`
- `frontend/src/components/findings/CodeReviewQueue.tsx`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/codebooks.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/findings/FindingsView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [findings.codebook](../../findings/codebook/architecture.md)
- [tasks.review](../../tasks/review/architecture.md)

## Related Concepts

- [triangulation](../../../glossary/triangulation.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
