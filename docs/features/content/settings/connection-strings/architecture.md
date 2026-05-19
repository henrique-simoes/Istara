---
stable_id: settings.connection-strings
title: Connection Strings
ui_path: Settings > Connection Strings
audience: architecture
status: documented
related_features: ["settings.llm-servers", "settings.users", "settings.compute-donation"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/settings/ConnectionStringPanel.tsx", "backend/app/api/routes/connections.py", "backend/app/core/connection_string.py"]
api_references: ["backend/app/api/routes/connections.py"]
test_references: ["tests/test_project_rbac.py", "tests/test_compute.py"]
last_verified: 2026-05-18
compass: CF-SPEC-60 / CF-754
---

# Connection Strings Architecture

## Implementation Summary

Connection string settings provide governed admin-only configuration for sensitive external or local service connection data. User invites create account access, while compute donation strings authorize relay compute and carry an explicit `allowed_project_ids` scope.

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
- In team mode, compute donation strings require at least one selected project and persist that scope in both the signed payload and the server-side connection-string record.
- Relay connections must present the issued compute-donation string for scoped donated routing; the shared network token alone is not enough to receive project content.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Compute donation strings control which project-scoped LLM requests may be routed to a donated node.

## Tests And Verification

- `tests/test_project_rbac.py`
- `tests/test_compute.py`

## Related Features

- [settings.llm-servers](../../settings/llm-servers/architecture.md)
- [settings.users](../../settings/users/architecture.md)
- [settings.compute-donation](../../settings/compute-donation/architecture.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-754
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
