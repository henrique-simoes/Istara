---
stable_id: settings.users
title: User Management
ui_path: Settings > Users
audience: researcher
status: needs-verification
related_features: ["auth.login", "settings.security-factors"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/common/UserManagement.tsx", "backend/app/api/routes/admin.py"]
api_references: ["backend/app/api/routes/admin.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# User Management

## What It Does

User management supports team member visibility and administrative user operations.

## Why It Exists

User Management exists so the work represented by Settings > Users has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Settings > Users
- Navigation group: Settings
- Primary component: `UserManagement`

## How UX Researchers Use It

- Open Settings > Users from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with user management in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Settings > Users when the current research task needs user management.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: auth.login, settings.security-factors.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with user management.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [auth.login](../../auth/login/researcher.md)
- [settings.security-factors](../../settings/security-factors/researcher.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Evidence

- Source files: `frontend/src/components/common/UserManagement.tsx`, `backend/app/api/routes/admin.py`
- API references: `backend/app/api/routes/admin.py`
- Tests: none recorded
