---
stable_id: settings.connection-strings
title: Connection Strings
ui_path: Settings > Connection Strings
audience: architecture
status: documented
related_features: ["settings.llm-servers", "settings.users"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/settings/ConnectionStringPanel.tsx", "backend/app/api/routes/connections.py", "backend/app/core/connection_string.py"]
api_references: ["backend/app/api/routes/connections.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Connection Strings Architecture

## Implementation Summary

Connection string settings provide governed admin-only configuration for sensitive external or local service connection data.

## Frontend Surface

- `frontend/src/components/settings/ConnectionStringPanel.tsx`
- `backend/app/api/routes/connections.py`
- `backend/app/core/connection_string.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/authStore.ts`

### API And Backend

- `backend/app/api/routes/connections.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/settings/ConnectionStringPanel.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [settings.llm-servers](../../settings/llm-servers/architecture.md)
- [settings.users](../../settings/users/architecture.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
