---
stable_id: loops.custom
title: Custom Loops
ui_path: Loops > Custom
audience: architecture
status: needs-verification
related_features: ["loops.schedules", "skills.catalog"]
related_glossary: ["mcp"]
code_references: ["frontend/src/components/loops/CustomLoopsTab.tsx", "backend/app/api/routes/loops.py"]
api_references: ["backend/app/api/routes/loops.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Custom Loops Architecture

## Implementation Summary

Custom loops provide a surface for user-defined recurring or automated research actions.

## Frontend Surface

- `frontend/src/components/loops/CustomLoopsTab.tsx`
- `backend/app/api/routes/loops.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/loopsStore.ts`

### API And Backend

- `backend/app/api/routes/loops.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/loops/CustomLoopsTab.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- MCP-related behavior must keep access policy, audit evidence, and tool/resource exposure synchronized with the cited route or integration component.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [loops.schedules](../../loops/schedules/architecture.md)
- [skills.catalog](../../skills/catalog/architecture.md)

## Related Concepts

- [mcp](../../../glossary/mcp.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
