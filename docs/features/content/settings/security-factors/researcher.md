---
stable_id: settings.security-factors
title: Passkeys And Two-Factor Authentication
ui_path: Settings > Security Factors
audience: researcher
status: documented
related_features: ["auth.login", "settings.sessions"]
related_glossary: ["webauthn", "totp"]
code_references: ["frontend/src/components/settings/PasskeyManager.tsx", "frontend/src/components/settings/TOTPManager.tsx", "backend/app/api/routes/webauthn.py", "backend/app/core/recovery_codes.py"]
api_references: ["backend/app/api/routes/webauthn.py", "backend/app/api/routes/auth.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Passkeys And Two-Factor Authentication

## What It Does

Settings includes passkey and TOTP management for strengthening account authentication.

## Why It Exists

Passkeys And Two-Factor Authentication exists so the work represented by Settings > Security Factors has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Settings > Security Factors
- Navigation group: Settings
- Primary component: `PasskeyManager / TOTPManager`

## How UX Researchers Use It

- Open Settings > Security Factors from the Istara navigation or the parent tab.
- Use the visible controls in this surface to work with passkeys and two-factor authentication in the active project context.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Settings > Security Factors when the current research task needs passkeys and two-factor authentication.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: auth.login, settings.sessions.

## Inputs, Outputs, And Expected Outcomes

- Project-scoped state or artifact updates associated with passkeys and two-factor authentication.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.

## Related Features

- [auth.login](../../auth/login/researcher.md)
- [settings.sessions](../../settings/sessions/researcher.md)

## Related Concepts

- [webauthn](../../../glossary/webauthn.md)
- [totp](../../../glossary/totp.md)

## Evidence

- Source files: `frontend/src/components/settings/PasskeyManager.tsx`, `frontend/src/components/settings/TOTPManager.tsx`, `backend/app/api/routes/webauthn.py`, `backend/app/core/recovery_codes.py`
- API references: `backend/app/api/routes/webauthn.py`, `backend/app/api/routes/auth.py`
- Tests: none recorded
