---
stable_id: settings.security-factors
title: Passkeys And Two-Factor Authentication
ui_path: Settings > Security Factors
audience: architecture
status: documented
related_features: ["auth.login", "settings.sessions"]
related_glossary: ["webauthn", "totp"]
code_references: ["frontend/src/components/settings/AccountSecurityManager.tsx", "frontend/src/lib/profileFormState.ts", "frontend/src/components/settings/PasskeyManager.tsx", "frontend/src/components/settings/TOTPManager.tsx", "frontend/src/stores/authStore.ts", "backend/app/api/routes/webauthn.py", "backend/app/api/routes/auth.py", "backend/app/core/recovery_codes.py"]
api_references: ["backend/app/api/routes/webauthn.py", "backend/app/api/routes/auth.py"]
test_references: ["frontend/src/stores/authStore.test.ts", "frontend/src/lib/profileFormState.test.ts", "frontend/src/lib/profileUpdatePayload.test.ts", "tests/test_auth_security.py"]
last_verified: 2026-09-01
compass: CF-SPEC-134 / CF-1671
---

# Passkeys And Two-Factor Authentication Architecture

## Implementation Summary

Settings includes account profile/password controls, recovery-code regeneration, passkey management, and TOTP management for strengthening account authentication.

## Frontend Surface

- `frontend/src/components/settings/AccountSecurityManager.tsx`
- `frontend/src/components/settings/PasskeyManager.tsx`
- `frontend/src/components/settings/TOTPManager.tsx`
- `backend/app/api/routes/auth.py`
- `backend/app/api/routes/webauthn.py`
- `backend/app/core/recovery_codes.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/authStore.ts`

### API And Backend

- `backend/app/api/routes/webauthn.py`
- `backend/app/api/routes/auth.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/settings/PasskeyManager.tsx` and the UI navigation path recorded in the inventory.
- Passkey listing and mutation read the in-memory `authStore` token. Login bootstrap must hydrate that token from the same browser JWT validated by `fetchMe()` so Settings never reports a false unauthenticated state after a successful sign-in.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Authentication-factor behavior is security-sensitive and must be verified with the repository security benchmark when implementation changes.
- Current factors are password plus optional TOTP, one-time recovery-code fallback, and WebAuthn/passkeys for passwordless sign-in. SMS and email OTP factors are not implemented.
- Recovery codes are shown once during first-admin onboarding, connection-string account creation, and admin-created user flows; regeneration invalidates previous codes.
- Profile and password changes require the current password. Password changes revoke other sessions where possible.
- Profile updates omit optional username/email fields when their form values are blank. This is fail-closed for encrypted PII that the API redacts after a decryption failure; an empty email is never submitted as an invalid replacement.
- The profile panel requests one authoritative `/api/auth/me` refresh when a non-local team identity mounts without a username or email, so a race during login bootstrap cannot leave editable identity fields blank. A redacted email remains blank after that single refresh and is never exposed as ciphertext.

## Tests And Verification

- `tests/test_auth_security.py`
- `frontend/src/stores/authStore.test.ts`
- `frontend/src/lib/profileFormState.test.ts`
- `frontend/src/lib/profileUpdatePayload.test.ts`

## Related Features

- [auth.login](../../auth/login/architecture.md)
- [settings.sessions](../../settings/sessions/architecture.md)

## Related Concepts

- [webauthn](../../../glossary/webauthn.md)
- [totp](../../../glossary/totp.md)

## Compass Evidence

- Spec/task: CF-SPEC-134 / CF-1671
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
