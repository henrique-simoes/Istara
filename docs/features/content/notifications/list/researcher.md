---
stable_id: notifications.list
title: Notifications List
ui_path: Notifications > All
audience: researcher
status: documented
related_features: ["shell.notifications-bell", "notifications.preferences"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/notifications/NotificationsView.tsx", "frontend/src/components/notifications/NotificationListTab.tsx", "frontend/src/components/notifications/CategoryFilter.tsx", "frontend/src/stores/notificationStore.ts", "frontend/src/lib/notificationApi.ts", "frontend/src/lib/types.ts", "backend/app/api/routes/notifications.py", "backend/app/services/notification_service.py", "backend/app/api/websocket.py"]
api_references: ["backend/app/api/routes/notifications.py"]
test_references: ["tests/test_notifications.py", "tests/test_project_scope_contracts.py", "tests/test_websocket.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-759; CF-SPEC-71 / CF-913; CF-SPEC-79 / CF-1019; CF-SPEC-89 / CF-1125; CF-SPEC-94 / CF-1205
---

# Notifications List

## What It Does

Notifications lists notifications for the currently selected project with read/unread state.

## Why It Exists

Notifications List exists so the work represented by Notifications > All has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Notifications > All
- Navigation group: Notifications
- Primary component: `NotificationsView`

## How UX Researchers Use It

- Open Notifications > All from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with notifications list in the active project context.
- The list, unread count, pagination, mark-all-read, mark-read, and delete actions stay on the selected project; there is no cross-project "All projects" view for project researchers.
- Project-facing notification list, count, mark-all-read, mark-read, and delete routes require a selected project for every role, including admins using this surface.
- Project-bound notification records are only persisted when the event includes or resolves to a project, so orphaned project activity is not shown later as a global notification.
- System-wide notification-style events are restricted to global admins rather than appearing in project user sockets.
- Agent promotion review requests appear under the Agent Promotion category for the selected project instead of as unscoped/global review activity.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Notifications > All when the current research task needs notifications list.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: shell.notifications-bell, notifications.preferences.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with notifications list.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [shell.notifications-bell](../../shell/notifications-bell/researcher.md)
- [notifications.preferences](../../notifications/preferences/researcher.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Evidence

- Source files: `frontend/src/components/notifications/NotificationsView.tsx`, `frontend/src/components/notifications/NotificationListTab.tsx`, `frontend/src/components/notifications/CategoryFilter.tsx`, `frontend/src/stores/notificationStore.ts`, `frontend/src/lib/notificationApi.ts`, `frontend/src/lib/types.ts`, `backend/app/api/routes/notifications.py`, `backend/app/services/notification_service.py`, `backend/app/api/websocket.py`
- API references: `backend/app/api/routes/notifications.py`
- Tests: `tests/test_notifications.py`, `tests/test_project_scope_contracts.py`, `tests/test_websocket.py`
