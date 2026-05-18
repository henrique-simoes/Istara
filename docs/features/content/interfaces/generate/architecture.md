---
stable_id: interfaces.generate
title: Generate Interfaces
ui_path: Interfaces > Generate
audience: architecture
status: needs-verification
related_features: ["interfaces.screens", "interfaces.design-chat"]
related_glossary: ["minto-pyramid"]
code_references: ["frontend/src/components/interfaces/GenerateTab.tsx", "frontend/src/stores/interfacesStore.ts", "backend/app/api/routes/interfaces.py"]
api_references: ["backend/app/api/routes/interfaces.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Generate Interfaces Architecture

## Implementation Summary

The Generate tab creates interface assets or screen proposals from project context and design prompts.

## Frontend Surface

- `frontend/src/components/interfaces/GenerateTab.tsx`
- `frontend/src/stores/interfacesStore.ts`
- `backend/app/api/routes/interfaces.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/interfacesStore.ts`

### API And Backend

- `backend/app/api/routes/interfaces.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/interfaces/GenerateTab.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [interfaces.screens](../../interfaces/screens/architecture.md)
- [interfaces.design-chat](../../interfaces/design-chat/architecture.md)

## Related Concepts

- [minto-pyramid](../../../glossary/minto-pyramid.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
