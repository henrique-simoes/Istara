---
stable_id: settings.compute-donation
title: Compute Donation
ui_path: Settings > Compute Donation
audience: architecture
status: documented
related_features: ["compute.pool", "settings.general"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/common/DonateComputeToggle.tsx", "backend/app/core/compute_pool.py"]
api_references: ["backend/app/api/routes/compute.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Compute Donation Architecture

## Implementation Summary

Compute donation lets a browser session contribute local compute capacity under controlled limits.

## Frontend Surface

- `frontend/src/components/common/DonateComputeToggle.tsx`
- `backend/app/core/compute_pool.py`

## State, API, And Backend Contracts

### Stores

- None recorded.

### API And Backend

- `backend/app/api/routes/compute.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/common/DonateComputeToggle.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [compute.pool](../../compute/pool/architecture.md)
- [settings.general](../../settings/general/architecture.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
