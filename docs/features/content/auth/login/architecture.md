---
stable_id: auth.login
title: Login And Session Bootstrap
ui_path: Shell > Authentication
audience: architecture
status: documented
related_features: ["settings.security-factors", "settings.sessions"]
related_glossary: ["webauthn", "totp"]
code_references: ["frontend/src/components/layout/HomeClient.tsx", "frontend/src/stores/authStore.ts", "backend/app/api/routes/auth.py", "backend/app/core/auth_sessions.py"]
api_references: ["backend/app/api/routes/auth.py", "backend/app/api/routes/sessions.py"]
test_references: []
last_verified: 2026-05-15
compass: CF-SPEC-53 / CF-657
---

# Login And Session Bootstrap Architecture

## Implementation Summary

The application shell checks authentication state, shows the login surface when needed, and loads session state before mounting protected views.

## Frontend Surface

- `frontend/src/components/layout/HomeClient.tsx`
- `frontend/src/stores/authStore.ts`
- `backend/app/api/routes/auth.py`
- `backend/app/core/auth_sessions.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/authStore.ts`

### API And Backend

- `backend/app/api/routes/auth.py`
- `backend/app/api/routes/sessions.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/layout/HomeClient.tsx` and the UI navigation path recorded in the inventory.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Authentication-factor behavior is security-sensitive and must be verified with the repository security benchmark when implementation changes.

## Tests And Verification

- No focused test reference recorded yet.

## Related Features

- [settings.security-factors](../../settings/security-factors/architecture.md)
- [settings.sessions](../../settings/sessions/architecture.md)

## Related Concepts

- [webauthn](../../../glossary/webauthn.md)
- [totp](../../../glossary/totp.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
