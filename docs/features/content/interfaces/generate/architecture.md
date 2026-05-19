---
stable_id: interfaces.generate
title: Generate Interfaces
ui_path: Interfaces > Generate
audience: architecture
status: needs-verification
related_features: ["interfaces.screens", "interfaces.design-chat"]
related_glossary: ["minto-pyramid"]
code_references: ["frontend/src/components/interfaces/GenerateTab.tsx", "frontend/src/stores/interfacesStore.ts", "backend/app/api/routes/interfaces_screens.py", "backend/app/models/interface_config.py", "backend/app/services/stitch_service.py"]
api_references: ["backend/app/api/routes/interfaces_screens.py"]
test_references: ["tests/test_interfaces.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-763
---

# Generate Interfaces Architecture

## Implementation Summary

The Generate tab creates interface assets or screen proposals from the active project's context and design prompts.

## Frontend Surface

- `frontend/src/components/interfaces/GenerateTab.tsx`
- `frontend/src/stores/interfacesStore.ts`
- `backend/app/api/routes/interfaces_screens.py`
- `backend/app/models/interface_config.py`
- `backend/app/services/stitch_service.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/interfacesStore.ts`

### API And Backend

- `backend/app/api/routes/interfaces_screens.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/interfaces/GenerateTab.tsx` and the UI navigation path recorded in the inventory.
- Screen generation checks project researcher access and stores new `DesignScreen`/`DesignDecision` records with the request project's id.
- When Stitch is configured, generation uses the active project's encrypted `ProjectInterfaceConfig.stitch_api_key`; otherwise it falls back to the local design tool path for that same project id.
- Seed findings are resolved within the request project before any generation call is made, preventing cross-project finding references from shaping generated screens.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- `tests/test_interfaces.py`
- `tests/test_project_scope_contracts.py`

## Related Features

- [interfaces.screens](../../interfaces/screens/architecture.md)
- [interfaces.design-chat](../../interfaces/design-chat/architecture.md)

## Related Concepts

- [minto-pyramid](../../../glossary/minto-pyramid.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-763
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
