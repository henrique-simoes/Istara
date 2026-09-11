---
stable_id: settings.security-factors
title: Passkeys And Two-Factor Authentication
ui_path: Settings > Security Factors
audience: researcher
status: documented
related_features: ["auth.login", "settings.sessions"]
related_glossary: ["webauthn", "totp"]
code_references: ["frontend/src/components/settings/AccountSecurityManager.tsx", "frontend/src/lib/profileFormState.ts", "frontend/src/components/settings/PasskeyManager.tsx", "frontend/src/components/settings/TOTPManager.tsx", "backend/app/api/routes/webauthn.py", "backend/app/api/routes/auth.py", "backend/app/core/recovery_codes.py"]
api_references: ["backend/app/api/routes/webauthn.py", "backend/app/api/routes/auth.py"]
test_references: ["frontend/src/lib/profileFormState.test.ts", "frontend/src/lib/profileUpdatePayload.test.ts", "tests/test_auth_security.py"]
last_verified: 2026-09-01
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
- If the server cannot decrypt stored email PII, Settings intentionally shows a blank email rather than ciphertext. Saving another profile field omits that blank optional email, so the action does not accidentally submit an invalid replacement.
- If login bootstrap briefly supplies an incomplete team identity, the profile panel performs one safe authoritative refresh. It does not retry indefinitely, and a still-unavailable email remains blank rather than exposing encrypted data.

## Related Features

- [auth.login](../../auth/login/researcher.md)
- [settings.sessions](../../settings/sessions/researcher.md)

## Related Concepts

- [webauthn](../../../glossary/webauthn.md)
- [totp](../../../glossary/totp.md)

## Evidence

- Source files: `frontend/src/components/settings/AccountSecurityManager.tsx`, `frontend/src/lib/profileFormState.ts`, `frontend/src/components/settings/PasskeyManager.tsx`, `frontend/src/components/settings/TOTPManager.tsx`, `backend/app/api/routes/webauthn.py`, `backend/app/api/routes/auth.py`, `backend/app/core/recovery_codes.py`
- API references: `backend/app/api/routes/webauthn.py`, `backend/app/api/routes/auth.py`
- Tests: `frontend/src/lib/profileFormState.test.ts`, `frontend/src/lib/profileUpdatePayload.test.ts`, `tests/test_auth_security.py`
