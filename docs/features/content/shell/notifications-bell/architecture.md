---
stable_id: shell.notifications-bell
title: Notification Bell
ui_path: Shell > Notifications Bell
audience: architecture
status: documented
related_features: ["notifications.list", "notifications.preferences"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/layout/Sidebar.tsx", "frontend/src/hooks/useWebSocket.ts", "frontend/src/stores/notificationStore.ts", "backend/app/api/routes/notifications.py", "backend/app/api/websocket.py", "backend/app/services/notification_service.py"]
api_references: ["backend/app/api/routes/notifications.py", "backend/app/api/websocket.py"]
test_references: ["tests/test_notifications.py", "tests/test_project_scope_contracts.py", "tests/test_websocket.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-754; CF-SPEC-60 / CF-759; CF-SPEC-60 / CF-776; CF-SPEC-69 / CF-885; CF-SPEC-71 / CF-913; CF-SPEC-94 / CF-1205
---

# Notification Bell Architecture

## Implementation Summary

The sidebar notification bell polls unread notification counts for the active project and links users into the notifications surface.

## Frontend Surface

- `frontend/src/components/layout/Sidebar.tsx`
- `frontend/src/hooks/useWebSocket.ts`
- `frontend/src/stores/notificationStore.ts`
- `backend/app/api/routes/notifications.py`
- `backend/app/api/websocket.py`
- `backend/app/services/notification_service.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/notificationStore.ts`

### API And Backend

- `backend/app/api/routes/notifications.py`
- `backend/app/api/websocket.py`
- `backend/app/services/notification_service.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/layout/Sidebar.tsx` and the UI navigation path recorded in the inventory.
- Realtime websocket connections include the active `project_id`; the backend validates that subscription against project membership before accepting the connection.
- Project event fan-out rechecks the connection's current project membership before each delivery, so revoked access stops receiving realtime project content without waiting for the browser to reconnect.
- The browser websocket hook also drops project-bound events that lack the active project id or carry another project's id, which prevents stale producer output from updating status bars, toasts, notification surfaces, or project views.
- The bell passes the active project into unread-count polling and clears to zero when no project is selected instead of polling a global inbox.
- The unread-count API requires that active project for every role, including global admins; missing project scope returns an error instead of counting all projects.
- The websocket manager infers project scope from event data, A2A metadata, task ids, deployment ids, channel instance ids, or agent ids before sending and before notification persistence.
- Project-bound realtime event types, including agent status, A2A, task, document, finding, deployment, channel, steering, and autoresearch events, without a resolvable project are dropped rather than delivered as global events.
- Global/system notification events such as backup, update, and resource-throttle broadcasts are delivered only to global-admin websocket clients in team mode.
- Notification persistence refuses project-bound records without `project_id`, so malformed realtime producers cannot create a later global inbox leak.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- No direct agent, skill, LLM, or MCP behavior is asserted beyond the cited source files.

## Tests And Verification

- `tests/test_project_scope_contracts.py`
- `tests/test_notifications.py`
- `tests/test_websocket.py`

## Related Features

- [notifications.list](../../notifications/list/architecture.md)
- [notifications.preferences](../../notifications/preferences/architecture.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-754; CF-SPEC-60 / CF-759; CF-SPEC-60 / CF-776; CF-SPEC-69 / CF-885; CF-SPEC-71 / CF-913; CF-SPEC-94 / CF-1205
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
