---
stable_id: shell.notifications-bell
title: Notification Bell
ui_path: Shell > Notifications Bell
audience: researcher
status: documented
related_features: ["notifications.list", "notifications.preferences"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/layout/Sidebar.tsx", "frontend/src/stores/notificationStore.ts", "backend/app/api/routes/notifications.py"]
api_references: ["backend/app/api/routes/notifications.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Notification Bell

## What It Does

The sidebar notification bell polls unread notification counts and links users into the notifications surface.

## Why It Exists

Notification Bell exists so the work represented by Shell > Notifications Bell has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Shell > Notifications Bell
- Navigation group: Shell
- Primary component: `Sidebar.NotificationBell`

## How UX Researchers Use It

- Open Shell > Notifications Bell from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with notification bell in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Shell > Notifications Bell when the current research task needs notification bell.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: notifications.list, notifications.preferences.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with notification bell.
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

- Source files: `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/stores/notificationStore.ts`, `backend/app/api/routes/notifications.py`
- API references: `backend/app/api/routes/notifications.py`
- Tests: none recorded
