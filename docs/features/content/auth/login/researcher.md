---
stable_id: auth.login
title: Login And Session Bootstrap
ui_path: Shell > Authentication
audience: researcher
status: documented
related_features: ["settings.security-factors", "settings.sessions"]
related_glossary: ["webauthn", "totp"]
code_references: ["frontend/src/components/layout/HomeClient.tsx", "frontend/src/stores/authStore.ts", "backend/app/api/routes/auth.py", "backend/app/core/auth_sessions.py"]
api_references: ["backend/app/api/routes/auth.py", "backend/app/api/routes/sessions.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Login And Session Bootstrap

## What It Does

The application shell checks authentication state, shows the login surface when needed, and loads session state before mounting protected views.

## Why It Exists

Login And Session Bootstrap exists so the work represented by Shell > Authentication has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Shell > Authentication
- Navigation group: Shell
- Primary component: `HomeClient`

## How UX Researchers Use It

- Open Shell > Authentication from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with login and session bootstrap in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Shell > Authentication when the current research task needs login and session bootstrap.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: settings.security-factors, settings.sessions.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with login and session bootstrap.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [settings.security-factors](../../settings/security-factors/researcher.md)
- [settings.sessions](../../settings/sessions/researcher.md)

## Related Concepts

- [webauthn](../../../glossary/webauthn.md)
- [totp](../../../glossary/totp.md)

## Evidence

- Source files: `frontend/src/components/layout/HomeClient.tsx`, `frontend/src/stores/authStore.ts`, `backend/app/api/routes/auth.py`, `backend/app/core/auth_sessions.py`
- API references: `backend/app/api/routes/auth.py`, `backend/app/api/routes/sessions.py`
- Tests: none recorded
