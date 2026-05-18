---
stable_id: settings.sessions
title: Active Sessions
ui_path: Settings > Sessions
audience: researcher
status: documented
related_features: ["auth.login", "settings.security-factors"]
related_glossary: ["webauthn", "totp"]
code_references: ["frontend/src/components/settings/SessionManager.tsx", "backend/app/api/routes/sessions.py", "backend/app/core/auth_sessions.py"]
api_references: ["backend/app/api/routes/sessions.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Active Sessions

## What It Does

Session management lists active authentication sessions and supports session-level control.

## Why It Exists

Active Sessions exists so the work represented by Settings > Sessions has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Settings > Sessions
- Navigation group: Settings
- Primary component: `SessionManager`

## How UX Researchers Use It

- Open Settings > Sessions from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with active sessions in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Settings > Sessions when the current research task needs active sessions.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: auth.login, settings.security-factors.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with active sessions.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [auth.login](../../auth/login/researcher.md)
- [settings.security-factors](../../settings/security-factors/researcher.md)

## Related Concepts

- [webauthn](../../../glossary/webauthn.md)
- [totp](../../../glossary/totp.md)

## Evidence

- Source files: `frontend/src/components/settings/SessionManager.tsx`, `backend/app/api/routes/sessions.py`, `backend/app/core/auth_sessions.py`
- API references: `backend/app/api/routes/sessions.py`
- Tests: none recorded
