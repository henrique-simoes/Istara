# Project Isolation Completion Audit

Date: 2026-05-19
Compass Forge spec: CF-SPEC-105
Branch: `compass-forge/complete-health-pass`

## Completion Standard

Istara project isolation is complete only if every project-content surface meets
these invariants:

1. Project-facing reads require an explicit active `project_id` and viewer access
   unless the route is a deliberate global-admin surface.
2. Project-facing writes require an explicit active `project_id`, researcher or
   project-admin access as appropriate, and reject paused projects before
   background or LLM work starts.
3. By-id reads and mutations bind the record id back to the active project and
   conceal stale cross-project ids as not found where feasible.
4. Frontend project views pass the active project id and defensively filter
   returned collections before render or mutation.
5. Websocket, notification, A2A, MCP, and compute-pool paths do not fall back to
   global delivery or global content routing when project scope is missing,
   conflicting, or unauthorized.
6. Global aggregation is allowed only on explicit admin-only routes.

## Current Result

No open project-isolation authorization gap was found in this final audit pass.
The remaining risk is release-level assurance risk: this matrix is backed by
source review, static contract tests, unit tests, Compass Forge gates, and the
security benchmark, but it is not a substitute for an external penetration test
or a live multi-user exploratory test. Live backend/frontend servers, live
chat-completion probes, and model loading were intentionally not run because the
repository instructions forbid them without explicit user permission.

## Surface Matrix

| Surface | Invariant | Evidence | Status |
| --- | --- | --- | --- |
| Central authorization | Project role logic is centralized, hides unrelated projects by default, and blocks insufficient project roles. | `backend/app/core/permissions.py` defines `require_project_access`, `get_visible_project_or_404`, and `get_active_project_or_404`; `AUTHZ-001` in `security/control_matrix.json` is passing with broad project-scope evidence. | Proved by source and benchmark evidence. |
| Backend route guards | Project-content routes use centralized helpers or route-local wrappers that require active project scope. | Static route sweep found helpers across agents, chat, sessions, tasks, documents, files, findings, deployments, channels, surveys, loops, MCP, notifications, reports, reasoning bank, autoresearch, skills, settings, and compute routes. `tests/test_project_scope_contracts.py` and feature-specific tests contain 174 project-scope tests across the audited set. | Proved by source and regression coverage. |
| Frontend active project flow | Project views pass `activeProjectId` and filter scoped collections before rendering or mutating. | `frontend/src/lib/api.ts` carries active `project_id` through skills, agents, compute, documents, loops, deployments, MCP, notifications, reasoning bank, and meta-hyperagent APIs. Static frontend sweep found 1771 project-scope markers. `tests/test_project_scope_contracts.py` asserts active-project wiring for integrations, tasks, compute, autoresearch, agents, skills, chat, loops, websocket consumers, notifications, and simulation harnesses. | Proved by static contract tests. |
| Chat, sessions, voice, and Context DAG | Chat and session ids are bound to the active project before message writes, history reads, voice transcription, and DAG inspection. | `backend/app/api/routes/chat.py` requires project access before session creation or use, scopes message history by `Message.project_id`, passes `project_id` into RAG/tools/LLM routing, and checks session-agent assignability. `backend/app/api/routes/sessions.py` requires active project scope for session-by-id routes. `backend/app/api/routes/chat_voice.py` requires researcher access before dummy transcription. Tests cover missing project, cross-project session, chat history concealment, and voice authorization before audio work. | Proved by source and tests. |
| Documents, files, tasks, reports, findings, codebooks | Project content is listed, searched, created, updated, and deleted only inside the active project. | `backend/app/api/routes/documents.py` binds document id routes to `Document.project_id`, scopes search/tag/sync by project, and rejects cross-project task references. `backend/app/api/routes/files.py` authorizes upload/serve paths and resolves files inside project roots. `backend/app/api/routes/tasks.py` filters task lists and by-id mutations by project and checks document references. Dedicated tests cover active project requirements and cross-project rejection. | Proved by source and tests. |
| Websocket fanout | Project-bound realtime events resolve a single project, reject missing or conflicting project claims, and deliver only to subscribed members of that project. | `backend/app/api/websocket.py` stores `active_project_id` per connection, rechecks membership before fanout, resolves project ids from tasks/deployments/channels/agents, drops unresolved project-bound events, and treats global admin events separately. `tests/test_websocket.py` covers membership, deployment project resolution, conflicting claims, missing scope, and membership rechecks. | Proved by source and tests. |
| Notifications | Project-facing notification APIs never fall back to a global inbox, and project-bound notification persistence refuses orphan project events. | `backend/app/api/routes/notifications.py` requires active project scope for list, unread count, mark read, mark all read, and delete. `backend/app/services/notification_service.py` skips project-bound events without `project_id`. `tests/test_notifications.py` covers admin scoping, member scoping, item actions, orphan drops, and helper requirements. | Proved by source and tests. |
| Deployments, channels, surveys, and integrations | Research deployment and integration state is scoped to the active project, and child objects are bound back to the deployment or integration project before access. | `backend/app/api/routes/deployments.py` uses `_get_active_project_deployment_or_404`, requires active projects for create/activate/respond, passes `project_id` into service calls, and binds conversations/transcripts to deployment project. Integration frontend and backend static tests cover recent activity, subtabs, wizard creation, MCP, messaging, and surveys. | Proved by source and tests. |
| A2A JSON-RPC and autonomous inbox | A2A writes require explicit active project id, persist it on rows/metadata, reject conflicting claims, and read/mutate messages only inside the active project. | `backend/app/api/routes/a2a.py` requires `project_id` for tasks/send, tasks/get, tasks/list, and discovery, authorizes with `require_project_access`, and passes project id into service calls. `backend/app/services/a2a.py` requires project id for writes, filters logs/threads/mark-read by project, and resolves row/metadata/task/agent claims. Tests cover service-scope regressions and agent/A2A project contract wiring. | Proved by source and tests. |
| MCP client/server and audit logs | MCP client descriptors, tool calls, and audit views are project-scoped unless the route is an admin-only server exposure control. | `backend/app/api/routes/mcp.py` requires `project_id` for project-facing client APIs, binds client ids to `MCPServerConfig.project_id`, passes project id into tool calls, and records project evidence. `MCP-001` is passing. `tests/test_mcp.py` covers project id requirements, scoped clients, detail actions, tool aggregates, service helpers, registration, allowlists, and audit filtering. | Proved by source, tests, and benchmark evidence. |
| Compute pool and donated compute | Project users see only compute nodes authorized for the active project, and donated relay/browser nodes receive content only for allowed project ids. | `backend/app/api/routes/compute.py` requires active `project_id` for nodes/stats/model-warnings, derives relay scope from user membership and compute donation strings, and blocks team-mode wildcard donation scope. `backend/app/core/compute_registry_routing.py` filters candidate nodes by project. `backend/app/core/compute_node_invocation.py` fails closed for donated dispatch without authorized project id. `CONN-001` is passing. | Proved by source, tests, and benchmark evidence. |
| Loops, schedulers, background jobs | Background process dashboards and mutations require active project scope; execution history persists and queries project ownership. | `backend/app/api/routes/loops.py` and `backend/app/api/routes/scheduler.py` require active project scope for overview, agents, schedules, health, history, and mutations. Recent commit `2f9710d` persisted loop execution project scope, and project-scope contracts assert loops API and views pass active project ids. | Proved by source and tests. |
| Autoresearch and governed evolution | Autoresearch and self-evolution require authorized active project ids before runner work, proposal mutations, or project evidence retrieval. | `backend/app/api/routes/autoresearch.py` uses `_require_active_project_scope` before start, scopes status/experiments/leaderboard, and filters current experiment by project. Runner base class fails closed if not project-bound. Recent commits `5cbca3e`, `65fe129`, and `9eb2398` hardened question-bank, reasoning, and settings/evolution surfaces. Tests cover paused project rejection and cross-project deployment targets. | Proved by source and tests. |
| Reasoning memory and agent learning | ReasoningBank retrieval defaults to project-only memory and requires explicit trusted opt-in for global memory. | `backend/app/core/reasoning_bank.py` stores project id on task/autoresearch traces, retrieves only matching project memories by default, and uses `include_global` only when explicitly set. `AI-003` is passing. `tests/test_reasoning_bank.py` covers redaction, project-scoped retrieval, and global opt-in. | Proved by source, tests, and benchmark evidence. |
| Skills, simulations, and proposals | Skill health/proposal views and simulation harnesses carry active project ids and do not call project proposal endpoints when no project is available. | Recent commit `9167e04` scoped skill simulation proposal checks. `frontend/src/lib/api.ts` requires project id for skill proposal APIs. `tests/test_simulation_project_scope_contracts.py` and `tests/test_project_scope_contracts.py` cover active simulation project scope and skill proposal actions. | Proved by source and tests. |
| Admin-only global aggregation | System-wide metrics and global project/user/access/connection-string lists are allowed only for global admins. | `backend/app/api/routes/admin.py` requires `require_global_admin` on overview, compute stats, projects, users, access, and connection-string routes. Admin compute stats intentionally call `compute_registry.get_stats(project_id=None)` and label `scope: global_admin`. | Proved as deliberate admin exception. |
| Public discovery and health exceptions | Public or semi-public endpoints must not expose private project content. | `GET /.well-known/agent.json` returns static A2A agent-card metadata and can require auth in team mode depending on settings. Generic health/registry endpoints are outside project-content scope and should remain free of private project records. | Bounded exception; no private project-content exposure identified. |

## Recent Hardening Commits Included In This Audit

- `9167e04` - Scope skill simulation proposal checks.
- `8f96d3d` - Bind chat voice transcription to project scope.
- `9eb2398` - Harden settings infrastructure scope.
- `03d47ae` - Cover deployment websocket project fanout.
- `4631829` - Add A2A service scope regression tests.
- `65fe129` - Harden A2A and reasoning memory project scope.
- `5cbca3e` - Bind autoresearch question bank to projects.
- `2f9710d` - Persist loop execution project scope.
- `4959517` - Scope MCP audit logs by project.
- `729d9a6` - Bind notifications and reports to active project.
- `7c7aa79` - Harden project pause background isolation.
- `32e8738` - Harden project scoped integration creation.
- `68122a8` - Scope validation compute routing to projects.

## Final Verification Results

Final local verification completed on 2026-05-19:

- `rtk python -m pytest tests/test_project_scope_contracts.py tests/test_simulation_project_scope_contracts.py tests/test_project_rbac.py tests/test_chat.py tests/test_compute.py tests/test_websocket.py tests/test_mcp.py tests/test_notifications.py tests/test_reports.py tests/test_tasks.py tests/test_documents.py tests/test_sessions.py tests/test_autoresearch.py tests/test_reasoning_bank.py tests/test_security_benchmark.py -q` - `260 passed in 73.71s`.
- `rtk python scripts/security_benchmark.py --fail-on-threshold` - pass, `28` controls, `100.0%`.
- `rtk python scripts/feature_docs.py --seed-missing --generate-site --check` - pass, `86` feature docs checked, `0` seeded.
- `rtk git diff --check` - pass.
- `rtk compass-forge gate after` - required final gate; output attached to Compass Forge evidence.

## Completion Decision

Based on source review, the existing regression surface, and the final
verification commands above, the system-wide project-isolation objective is
complete with no open code gap identified. The final mark-complete action is
allowed after the Compass Forge tasks for CF-SPEC-105 contain evidence for
implementation, verification, review, and gate-after status.
