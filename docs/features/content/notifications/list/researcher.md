---
stable_id: notifications.list
title: Notifications List
ui_path: Notifications > All
audience: researcher
status: documented
related_features: ["shell.notifications-bell", "notifications.preferences"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/notifications/NotificationsView.tsx", "frontend/src/stores/notificationStore.ts", "frontend/src/lib/notificationApi.ts", "backend/app/api/routes/notifications.py"]
api_references: ["backend/app/api/routes/notifications.py"]
test_references: ["tests/test_notifications.py", "tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-60 / CF-759; CF-SPEC-71 / CF-913
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
- The list, unread count, pagination, and mark-all-read action stay on the selected project; there is no cross-project "All projects" view for project researchers.
- Project-facing notification list, count, and mark-all-read routes require a selected project for every role, including admins using this surface.
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

- Source files: `frontend/src/components/notifications/NotificationsView.tsx`, `frontend/src/stores/notificationStore.ts`, `frontend/src/lib/notificationApi.ts`, `backend/app/api/routes/notifications.py`
- API references: `backend/app/api/routes/notifications.py`
- Tests: `tests/test_notifications.py`, `tests/test_project_scope_contracts.py`
