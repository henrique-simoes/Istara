---
stable_id: notifications.list
title: Notifications List
ui_path: Notifications > All
audience: architecture
status: documented
related_features: ["shell.notifications-bell", "notifications.preferences"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/notifications/NotificationsView.tsx", "frontend/src/stores/notificationStore.ts", "frontend/src/lib/notificationApi.ts", "backend/app/api/routes/notifications.py"]
api_references: ["backend/app/api/routes/notifications.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Notifications List Architecture

## Implementation Summary

Notifications lists system and project notifications with read/unread state.

## Frontend Surface

- `frontend/src/components/notifications/NotificationsView.tsx`
- `frontend/src/stores/notificationStore.ts`
- `frontend/src/lib/notificationApi.ts`
- `backend/app/api/routes/notifications.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/notificationStore.ts`

### API And Backend

- `backend/app/api/routes/notifications.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/notifications/NotificationsView.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [shell.notifications-bell](../../shell/notifications-bell/architecture.md)
- [notifications.preferences](../../notifications/preferences/architecture.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
