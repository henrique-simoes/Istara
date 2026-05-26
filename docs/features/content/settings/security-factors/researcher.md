---
stable_id: settings.security-factors
title: Passkeys And Two-Factor Authentication
ui_path: Settings > Security Factors
audience: researcher
status: documented
related_features: ["auth.login", "settings.sessions"]
related_glossary: ["webauthn", "totp"]
code_references: ["frontend/src/components/settings/AccountSecurityManager.tsx", "frontend/src/components/settings/PasskeyManager.tsx", "frontend/src/components/settings/TOTPManager.tsx", "backend/app/api/routes/webauthn.py", "backend/app/api/routes/auth.py", "backend/app/core/recovery_codes.py"]
api_references: ["backend/app/api/routes/webauthn.py", "backend/app/api/routes/auth.py"]
test_references: ["tests/test_auth_security.py"]
last_verified: 2026-05-22
compass: CF-SPEC-134 / CF-1671
---

# Passkeys And Two-Factor Authentication

## What It Does

Settings includes account profile/password controls, recovery-code regeneration, passkey management, and TOTP management for strengthening account authentication.

## Why It Exists

Passkeys And Two-Factor Authentication exists so the work represented by Settings > Security Factors has a stable, discoverable place in Istara's project workflow. It keeps user actions, generated artifacts, and related follow-up surfaces connected to the active project rather than scattering them across unrelated tools.

## Where It Lives

- UI path: Settings > Security Factors
- Navigation group: Settings
- Primary component: `PasskeyManager / TOTPManager`

## How UX Researchers Use It

- Open Settings > Security Factors from the Istara navigation or the parent tab.
- Use the visible controls to update username/profile/password, regenerate recovery codes, register passkeys, and enable or disable TOTP.
- Review the output in the same view and follow the related feature links when the workflow moves into another Istara surface.

## Supported Workflows

- Start from Settings > Security Factors when the current research task needs passkeys and two-factor authentication.
- Use the visible controls to create, inspect, refine, or route project work without leaving the active Istara context.
- Move to related surfaces when needed: auth.login, settings.sessions.

## Inputs, Outputs, And Expected Outcomes

- Account security state associated with username/profile, password, recovery codes, passkeys, TOTP, and active sessions.
- Visible status, lists, forms, generated artifacts, or review results shown by the referenced component and routes.

## Caveats

- Needs interactive verification for exact empty, loading, error, and permission-denied states.
- Do not expand this documentation beyond the cited source files without adding new code or walkthrough evidence.
- Recovery codes are shown once. Save them offline before leaving the screen.
- Current 2FA options are TOTP plus recovery codes. Passkeys are passwordless sign-in credentials, not SMS or email OTP.

## Related Features

- [auth.login](../../auth/login/researcher.md)
- [settings.sessions](../../settings/sessions/researcher.md)

## Related Concepts

- [webauthn](../../../glossary/webauthn.md)
- [totp](../../../glossary/totp.md)

## Evidence

- Source files: `frontend/src/components/settings/AccountSecurityManager.tsx`, `frontend/src/components/settings/PasskeyManager.tsx`, `frontend/src/components/settings/TOTPManager.tsx`, `backend/app/api/routes/webauthn.py`, `backend/app/api/routes/auth.py`, `backend/app/core/recovery_codes.py`
- API references: `backend/app/api/routes/webauthn.py`, `backend/app/api/routes/auth.py`
- Tests: `tests/test_auth_security.py`
