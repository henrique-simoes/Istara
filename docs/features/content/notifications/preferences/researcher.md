---
stable_id: notifications.preferences
title: Notification Preferences
ui_path: Notifications > Preferences
audience: researcher
status: documented
related_features: ["notifications.list", "shell.notifications-bell"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/notifications/NotificationsView.tsx", "frontend/src/components/notifications/NotificationPrefsTab.tsx", "frontend/src/stores/notificationStore.ts", "frontend/src/lib/types.ts", "backend/app/api/routes/notifications.py"]
api_references: ["backend/app/api/routes/notifications.py"]
test_references: ["tests/test_project_scope_contracts.py"]
last_verified: 2026-05-19
compass: CF-SPEC-53 / CF-657; CF-SPEC-89 / CF-1125
---

# Notification Preferences

## What It Does

Notification preferences let users configure which notifications they receive and how notification categories are handled.

## Why It Exists

Notification Preferences exists so the work represented by Notifications > Preferences has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Notifications > Preferences
- Navigation group: Notifications
- Primary component: `NotificationsView`

## How UX Researchers Use It

- Open Notifications > Preferences from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with notification preferences in the active project context.
- Configure the Agent Promotion category when project-scoped agent review requests should appear or notify differently.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Notifications > Preferences when the current research task needs notification preferences.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: notifications.list, shell.notifications-bell.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with notification preferences.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [notifications.list](../../notifications/list/researcher.md)
- [shell.notifications-bell](../../shell/notifications-bell/researcher.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Evidence

- Source files: `frontend/src/components/notifications/NotificationsView.tsx`, `frontend/src/components/notifications/NotificationPrefsTab.tsx`, `frontend/src/stores/notificationStore.ts`, `frontend/src/lib/types.ts`, `backend/app/api/routes/notifications.py`
- API references: `backend/app/api/routes/notifications.py`
- Tests: `tests/test_project_scope_contracts.py`
