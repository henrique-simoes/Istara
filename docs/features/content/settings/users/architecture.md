---
stable_id: settings.users
title: User Management
ui_path: Settings > Users
audience: architecture
status: documented
related_features: ["auth.login", "settings.security-factors"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/common/UserManagement.tsx", "backend/app/api/routes/auth.py", "backend/app/core/field_encryption.py", "docker-compose.qa.yml"]
api_references: ["backend/app/api/routes/auth.py"]
test_references: ["tests/test_auth_encrypted_pii.py", "tests/test_auth_security.py", "tests/test_field_encryption.py", "tests/test_qa_stack_contract.py"]
last_verified: 2026-08-31
compass: CF-SPEC-134 / CF-1671; CF-SPEC-7 / CF-64
---

# User Management Architecture

## Implementation Summary

User management supports team member visibility and administrative user operations through `/auth/users`. User email is encrypted at rest and the API must fail closed if an encrypted email cannot be decrypted: Settings may show an unavailable/blank value, but it must never receive or render raw `ENC:` ciphertext.

## Frontend Surface

- `frontend/src/components/common/UserManagement.tsx`
- `backend/app/api/routes/auth.py`
- `backend/app/core/field_encryption.py`
- `docker-compose.qa.yml`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/authStore.ts`

### API And Backend

- `backend/app/api/routes/auth.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/common/UserManagement.tsx` and the UI navigation path recorded in the inventory.
- `/api/auth/users` serializes `User.email` only after SQLAlchemy field decryption. Unreadable encrypted field values return an unavailable empty string and increment value-free encryption health counters; ciphertext, keys, and encrypted blobs are never returned to the browser.
- The QA stack sets a stable test-only `DATA_ENCRYPTION_KEY` for `qa-backend`, overridable with `QA_DATA_ENCRYPTION_KEY`, so backend recreation does not break encrypted user PII in disposable QA databases. The fallback is QA-only and must not be copied into the base compose.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- User creation is global-admin scoped and returns one-time recovery codes for the new account. Researchers do not call this admin-only surface in normal journeys.

## Tests And Verification

- `tests/test_auth_security.py`
- `tests/test_auth_encrypted_pii.py`
- `tests/test_field_encryption.py`
- `tests/test_qa_stack_contract.py`

## Related Features

- [auth.login](../../auth/login/architecture.md)
- [settings.security-factors](../../settings/security-factors/architecture.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Compass Evidence

- Spec/task: CF-SPEC-53 / CF-657
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
