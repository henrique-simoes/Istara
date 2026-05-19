---
stable_id: shell.notifications-bell
title: Notification Bell
ui_path: Shell > Notifications Bell
audience: researcher
status: documented
related_features: ["notifications.list", "notifications.preferences"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/layout/Sidebar.tsx", "frontend/src/hooks/useWebSocket.ts", "frontend/src/stores/notificationStore.ts", "backend/app/api/routes/notifications.py", "backend/app/api/websocket.py"]
api_references: ["backend/app/api/routes/notifications.py", "backend/app/api/websocket.py"]
test_references: ["tests/test_notifications.py", "tests/test_project_scope_contracts.py", "tests/test_websocket.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-754; CF-SPEC-60 / CF-759; CF-SPEC-60 / CF-776
---

# Notification Bell

## What It Does

The sidebar notification bell polls unread notification counts for the active project and links users into the notifications surface.

## Why It Exists

Notification Bell exists so the work represented by Shell > Notifications Bell has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Shell > Notifications Bell
- Navigation group: Shell
- Primary component: `Sidebar.NotificationBell`

## How UX Researchers Use It

- Open Shell > Notifications Bell from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with notification bell in the active project context.
- The unread badge reflects only the currently selected project and resets when no project is selected.
- Realtime project notifications follow the active project selection, so events from other projects are not delivered into the current project shell.
- If the realtime connection names a project the user cannot access, the socket is rejected instead of receiving that project's events.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Shell > Notifications Bell when the current research task needs notification bell.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: notifications.list, notifications.preferences.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with notification bell.
- Project scope is mandatory for non-admin notification lists, unread counts, and mark-all-read actions.
- Project-tagged websocket events must carry or resolve to a project before they can be delivered to project-connected clients.
- Project-bound realtime events that cannot be resolved to a project are not shown as global notifications.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [notifications.list](../../notifications/list/researcher.md)
- [notifications.preferences](../../notifications/preferences/researcher.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Evidence

- Source files: `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/hooks/useWebSocket.ts`, `frontend/src/stores/notificationStore.ts`, `backend/app/api/routes/notifications.py`, `backend/app/api/websocket.py`
- API references: `backend/app/api/routes/notifications.py`, `backend/app/api/websocket.py`
- Tests: `tests/test_notifications.py`, `tests/test_project_scope_contracts.py`, `tests/test_websocket.py`
