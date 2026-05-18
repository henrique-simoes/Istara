---
stable_id: admin.dashboard
title: Admin Dashboard
ui_path: Admin
audience: researcher
status: needs-verification
related_features: ["settings.users", "settings.connection-strings"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/admin/AdminDashboard.tsx", "backend/app/api/routes/admin.py"]
api_references: ["backend/app/api/routes/admin.py"]
test_references: ["tests/test_project_rbac.py"]
last_verified: 2026-05-18
compass: CF-SPEC-60 / CF-754
---

# Admin Dashboard

## What It Does

The Admin dashboard provides administrator-only operational controls and visibility. It may aggregate metrics across projects for admins, but any compute donation string created here is still bound to a selected project.

## Why It Exists

Admin Dashboard exists so the work represented by Admin has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Admin
- Navigation group: Secondary
- Primary component: `AdminDashboard`

## How UX Researchers Use It

- Open Admin from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with admin dashboard in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.
- Select a project when creating a compute donation string so the donated machine can only process content for that project.

## Supported Workflows

- Start from Admin when the current research task needs admin dashboard.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: settings.users, settings.connection-strings.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with admin dashboard.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.
- Global admin metrics do not imply global donated compute access.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [settings.users](../../settings/users/researcher.md)
- [settings.connection-strings](../../settings/connection-strings/researcher.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Evidence

- Source files: `frontend/src/components/admin/AdminDashboard.tsx`, `backend/app/api/routes/admin.py`
- API references: `backend/app/api/routes/admin.py`
- Tests: `tests/test_project_rbac.py`
