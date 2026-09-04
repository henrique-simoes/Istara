---
stable_id: auth.login
title: Login And Session Bootstrap
ui_path: Shell > Authentication
audience: architecture
status: documented
related_features: ["settings.security-factors", "settings.sessions"]
related_glossary: ["webauthn", "totp"]
code_references: ["frontend/src/components/layout/HomeClient.tsx", "frontend/src/stores/authStore.ts", "frontend/src/lib/runtimeConfig.ts", "backend/app/api/routes/auth.py", "backend/app/core/auth_sessions.py", "docker-compose.qa.yml"]
api_references: ["backend/app/api/routes/auth.py", "backend/app/api/routes/sessions.py"]
test_references: ["frontend/src/stores/authStore.test.ts", "tests/test_auth_encrypted_pii.py", "tests/test_auth_security.py", "tests/test_qa_stack_contract.py", "tests/test_marathon_config_integrity.py", "scripts/marathon/run-cycle.mjs"]
last_verified: 2026-08-31
compass: CF-SPEC-53 / CF-657; CF-SPEC-116
---

# Login And Session Bootstrap Architecture

## Implementation Summary

The application shell checks authentication state, shows the login surface when needed, and loads session state before mounting protected views.

## Frontend Surface

- `frontend/src/components/layout/HomeClient.tsx`
- `frontend/src/stores/authStore.ts`
- `frontend/src/lib/runtimeConfig.ts`
- `backend/app/api/routes/auth.py`
- `backend/app/core/auth_sessions.py`
- `docker-compose.qa.yml`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/authStore.ts`

### API And Backend

- `backend/app/api/routes/auth.py`
- `backend/app/api/routes/sessions.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/layout/HomeClient.tsx` and the UI navigation path recorded in the inventory.
- `LoginScreen` credential, passkey, registration, and connection-string flows persist the returned JWT before `HomeClient` calls `fetchMe()`; a successful `fetchMe()` must hydrate both the user and the same token into `authStore` before protected child views mount.
- The QA UI is published canonically on a loopback host, with its API proxy on a separate loopback port. Frontend runtime configuration aligns explicit loopback API and WebSocket overrides (`localhost`, `127.0.0.1`, or `::1`) with the browser's loopback hostname and scheme. If a local tunnel must retain the other loopback spelling, the backend accepts that request only when the exact UI origin is configured as trusted, both hosts are loopback, and the schemes match; arbitrary cross-site origins remain denied. Explicit non-loopback deployments stay authoritative.
- The disposable QA compose contract may inject a per-run `QA_NETWORK_ACCESS_TOKEN` into the backend and loopback proxy so container-network requests remain authenticated without using a production credential. The UI lane may also set `QA_TEAM_MODE=true` to exercise first-admin registration and normal session bootstrap; contract-only runs remain in local mode by default.
- A freshly recreated team-mode QA backend can receive `QA_ADMIN_USERNAME` and `QA_ADMIN_PASSWORD` for a deterministic first-admin fixture. Those values are runtime-only and must never be committed, logged, or reused outside the disposable stack.
- The QA backend also sets a stable QA-only `DATA_ENCRYPTION_KEY`, overridable with `QA_DATA_ENCRYPTION_KEY`, so disposable QA backend recreation does not strand encrypted auth/user fields behind an unreadable random key. This key is not a production secret and must remain isolated to the QA compose contract.
- Local marathon and simulation harnesses must use an explicit test JWT or the opt-in local signed-token path; third-party LLM provider tokens are not Istara admin session credentials.
- Frontend role checks use `frontend/src/lib/roleCapabilities.ts` and `frontend/src/hooks/useRoleCapabilities.ts` so global role and active-project role are evaluated together. Researcher sessions may mount personal settings, project workspaces, and researcher workflows, but must not mount global-admin panels that call user-management, connection-string, telemetry-toggle, governed-evolution, or steering endpoints.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Authentication-factor behavior is security-sensitive and must be verified with the repository security benchmark when implementation changes.

## Tests And Verification

- `tests/test_marathon_config_integrity.py`
- `tests/test_auth_encrypted_pii.py`
- `tests/test_auth_security.py`
- `tests/test_qa_stack_contract.py`
- `frontend/src/stores/authStore.test.ts`
- `scripts/marathon/run-cycle.mjs`

## Related Features

- [settings.security-factors](../../settings/security-factors/architecture.md)
- [settings.sessions](../../settings/sessions/architecture.md)

## Related Concepts

- [webauthn](../../../glossary/webauthn.md)
- [totp](../../../glossary/totp.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657; CF-SPEC-116
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
