---
stable_id: admin.dashboard
title: Admin Dashboard
ui_path: Admin
audience: architecture
status: documented
related_features: ["settings.users", "settings.connection-strings", "compute.pool"]
related_glossary: ["wcag"]
code_references: ["frontend/src/components/admin/AdminDashboard.tsx", "backend/app/api/routes/admin.py", "backend/app/api/routes/permission_requests.py", "backend/app/core/compute_registry_invocation.py", "tests/real_user_benchmark/run.mjs", "tests/real_user_benchmark/lib/donor-sandboxes.mjs"]
api_references: ["backend/app/api/routes/admin.py", "backend/app/api/routes/permission_requests.py"]
test_references: ["tests/test_project_rbac.py", "tests/test_compute.py", "tests/test_project_scope_contracts.py", "tests/test_harness_project_scope_contracts.py", "tests/simulation/lib/project-selection.test.mjs", "tests/real_user_benchmark/run.mjs", "tests/real_user_benchmark/lib/donor-sandboxes.test.mjs"]
last_verified: 2026-05-20
compass: CF-SPEC-60 / CF-754; CF-SPEC-63 / CF-815; CF-SPEC-72 / CF-927; CF-SPEC-115; CF-SPEC-116; CF-SPEC-118; CF-SPEC-121
---

# Admin Dashboard Architecture

## Implementation Summary

The Admin dashboard provides administrator-only operational controls and visibility. Core sections load independently so a secondary endpoint failure, such as permission requests, does not blank Users, Projects, Access, or Connection Strings. Admin is the explicit global aggregation exception, but global compute capacity comes from `/api/admin/compute/stats` after `require_global_admin`; project-facing Compute Pool routes still require an active `project_id`. Compute donation strings generated here still require a selected project scope. The dashboard's pending permission request queue is also an explicit global-admin exception; project-facing request queues and reviews remain active-project-bound.

## Frontend Surface

- `frontend/src/components/admin/AdminDashboard.tsx`
- `backend/app/api/routes/admin.py`

## State, API, And Backend Contracts

### Stores

- `frontend/src/stores/authStore.ts`

### API And Backend

- `backend/app/api/routes/admin.py`

## Architecture Notes

- The feature is mounted through `frontend/src/components/admin/AdminDashboard.tsx` and the UI navigation path recorded in the inventory.
- The dashboard should prefer partial data with an explicit section error over all-or-nothing loading.
- The dashboard loads compute capacity through the admin-only aggregate endpoint instead of reusing project-facing `/api/compute/*` routes.
- The dashboard's donation-string action sends `allowed_project_ids` for the chosen project so donated compute does not become a global content processor.
- When the server has no network access token yet, compute donation string generation creates one before signing the donation string; invite strings for human users remain separate and do not include relay credentials.
- The dashboard may list and review pending permission requests without `project_id` only because the route checks global admin status; Project Settings must pass the active project id for the same permission-request APIs.
- Simulation and harness smoke tests model the admin-many-projects case by selecting the canonical unpaused simulation project by name and failing if the harness would fall back to the first visible admin project or a paused project.
- The real-user benchmark uses role-specific UI journeys: global admins visit global settings and admin-only panels, project admins visit project-scoped administration surfaces, and researchers avoid Settings/global-admin panels during normal journeys. Any unexpected 403 during a normal UI journey is recorded as a role-contract failure instead of being treated as a harmless console error.
- The real-user benchmark now models the admin as setup/governance lead, then authenticates multiple researcher actors who perform normal project work. Admin-only setup remains admin-owned; researcher chat, task creation, review, and document/interview work must happen through researcher-authorized routes.
- The frontmatter and manifest entries are the durable contract for agents updating this page after code changes.
- When the referenced component, store, route, agent, skill, or test behavior changes, regenerate and validate the feature documentation.

## Agents, Skills, LLM, MCP, And Permissions

- Admin aggregates global metrics, while delegated compute remains project-scoped for LLM routing and donor authorization.
- The real-user benchmark can validate multi-donor compute by requiring distinct donor endpoints and, when explicitly configured, starting per-donor Colima/Docker model server sandboxes with Q4/4-bit evidence before relay donation. Architecture scoring observes Istara's natural scheduler counters after collaborative research work rather than forcing a specific donor for the agentic workflow.

## Tests And Verification

- `tests/test_project_rbac.py`
- `tests/test_compute.py`
- `tests/test_project_scope_contracts.py`
- `tests/test_harness_project_scope_contracts.py`
- `tests/simulation/lib/project-selection.test.mjs`
- `tests/real_user_benchmark/run.mjs`
- `tests/real_user_benchmark/lib/donor-sandboxes.test.mjs`

## Related Features

- [settings.users](../../settings/users/architecture.md)
- [settings.connection-strings](../../settings/connection-strings/architecture.md)
- [compute.pool](../../compute/pool/architecture.md)

## Related Concepts

- [wcag](../../../glossary/wcag.md)

## Compass Evidence

- Spec/task: CF-SPEC-60 / CF-754; CF-SPEC-63 / CF-815; CF-SPEC-72 / CF-927; CF-SPEC-115; CF-SPEC-116; CF-SPEC-118; CF-SPEC-121
- Inventory source: `docs/features/inventory.json`

## When To Update

- Update this page whenever the listed UI components, stores, routes, model behavior, permissions, or tests change.
- Regenerate the site and machine manifests with `python scripts/feature_docs.py --seed-missing --generate-site --check`.
