---
stable_id: settings.sessions
title: Active Sessions
ui_path: Settings > Sessions
audience: architecture
status: documented
related_features: ["auth.login", "settings.security-factors"]
related_glossary: ["webauthn", "totp"]
code_references: ["frontend/src/components/settings/SessionManager.tsx", "backend/app/api/routes/sessions.py", "backend/app/core/auth_sessions.py"]
api_references: ["backend/app/api/routes/sessions.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Active Sessions Architecture

## Implementation Summary

Session management lists active authentication sessions and supports session-level control.

## Frontend Surface

- `frontend/src/components/settings/SessionManager.tsx`
- `backend/app/api/routes/sessions.py`
- `backend/app/core/auth_sessions.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/authStore.ts`

### API And Backend

- `backend/app/api/routes/sessions.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/settings/SessionManager.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Authentication-factor behavior is security-sensitive and must be verified with the repository security benchmark when implementation changes.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [auth.login](../../auth/login/architecture.md)
- [settings.security-factors](../../settings/security-factors/architecture.md)

## Related Concepts

- [webauthn](../../../glossary/webauthn.md)
- [totp](../../../glossary/totp.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
