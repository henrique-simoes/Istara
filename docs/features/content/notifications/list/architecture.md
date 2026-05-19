---
stable_id: notifications.list
title: Notifications List
ui_path: Notifications > All
audience: architecture
status: documented
related_features: ["shell.notifications-bell", "notifications.preferences"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/notifications/NotificationsView.tsx", "frontend/src/components/notifications/NotificationListTab.tsx", "frontend/src/components/notifications/CategoryFilter.tsx", "frontend/src/stores/notificationStore.ts", "frontend/src/lib/notificationApi.ts", "frontend/src/lib/types.ts", "backend/app/api/routes/notifications.py", "backend/app/services/notification_service.py", "backend/app/api/websocket.py"]
api_references: ["backend/app/api/routes/notifications.py"]
test_references: ["tests/test_notifications.py", "tests/test_project_scope_contracts.py", "tests/test_websocket.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-759; CF-SPEC-71 / CF-913; CF-SPEC-79 / CF-1019; CF-SPEC-89 / CF-1125; CF-SPEC-94 / CF-1205
---

# Notifications List Architecture

## Implementation Summary

Notifications lists active-project notifications with read/unread state. List, unread-count, mark-all-read, mark-read, and delete routes require the active `project_id` for every caller, including global admins.

## Frontend Surface

- `frontend/src/components/notifications/NotificationsView.tsx`
- `frontend/src/components/notifications/CategoryFilter.tsx`
- `frontend/src/stores/notificationStore.ts`
- `frontend/src/lib/notificationApi.ts`
- `frontend/src/lib/types.ts`
- `backend/app/api/routes/notifications.py`
- `backend/app/services/notification_service.py`
- `backend/app/api/websocket.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/notificationStore.ts`

### API And Backend

- `backend/app/api/routes/notifications.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/notifications/NotificationsView.tsx` and the UI navigation path recorded in the inventory.
- The notification store refuses to list, count, or mark all notifications without an active project selected in the shell.
- The notification store passes the active project into by-id mark-read and delete actions, and the backend constrains those lookups by both notification id and project id.
- The list UI does not expose an "All projects" filter; project context comes from the active project store and backend RBAC verifies that membership.
- The backend list, unread-count, mark-all-read, mark-read, and delete APIs never fall back to a global inbox; cross-project notification aggregation belongs only on explicit admin reporting surfaces.
- Lower-level notification service helpers also require `project_id`, and project-bound event persistence skips records that cannot be tied to a project.
- System-wide notification-style websocket events such as updates, backups, and resource throttles fan out only to global admins.
- Agent promotion review notifications use the `agent_promotion` category in the API allow-list, frontend category filters, and badge styling so project-scoped review requests remain visible when users filter notification categories.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- `tests/test_notifications.py`
- `tests/test_project_scope_contracts.py`
- `tests/test_websocket.py`

## Related Features

- [shell.notifications-bell](../../shell/notifications-bell/architecture.md)
- [notifications.preferences](../../notifications/preferences/architecture.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-759; CF-SPEC-71 / CF-913; CF-SPEC-79 / CF-1019; CF-SPEC-89 / CF-1125; CF-SPEC-94 / CF-1205
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
