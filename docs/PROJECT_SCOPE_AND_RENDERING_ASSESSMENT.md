# Project Scope And Rendering Assessment

Date: 2026-05-18
Compass: CF-SPEC-59 / CF-740

## Summary

The browser is currently showing a stale production frontend bundle. The running process on port 3000 is `next-server` from `frontend/`, but `frontend/.next/BUILD_ID` was last modified on May 8, 2026 while the relevant source files were edited on May 18, 2026. The live compiled chunk still contains the old Interfaces tab config with `label:"Figma"`, even though `frontend/src/components/interfaces/InterfacesView.tsx` now uses `label: "Configuration"`.

That same stale bundle explains why Integrations > Overview still renders SIM deployment activity in the current project. The source now fetches and filters channels, deployments, and survey integrations by the active `project_id`, but the live browser is still running the older compiled overview.

## Evidence Captured

- Live app process: `next-server (v16.2.4)` listening on port 3000 with cwd `/Users/studio/Documents/Istara-main/frontend`.
- Build freshness: `frontend/.next/BUILD_ID` timestamp is May 8, 2026; `InterfacesView.tsx` and `IntegrationsOverview.tsx` were modified on May 18, 2026.
- Compiled runtime evidence: `frontend/.next/static/chunks/0t9_yelnx2fyr.js` contains the minified tab entry `{id:"figma", icon: ..., label:"Figma"}`.
- Live browser evidence: Integrations > Overview showed `Recent Activity` rows for `SIM: Analytics Test`, `SIM: Week-long Diary`, and `SIM: Quick Survey` despite project-facing stats being zero.
- Source evidence: `IntegrationsOverview.tsx` now passes `activeProjectId` into channel, deployment, and survey fetches and builds recent activity from `scopedChannels` and `scopedDeployments`.

## Scope Model

Istara has two different kinds of data surfaces:

- Project-owned workspace data: chat, findings, documents, tasks, interviews, interfaces screens, agents/A2A project views, channels, research deployments, survey integrations, schedules, reports, memory, metrics, and compliance views. These must use the active project id in project-facing UI.
- Global/admin/runtime data: compute pool, LLM server registry, MCP server inventory, admin users/projects, backups, platform settings, connection invites, security/audit views, and some diagnostics. These may be global by design, but project-facing pages must not blend them into project activity without a visible global/admin context.

The confusing behavior comes from these two categories being displayed near each other without enough runtime freshness and scope verification. Admin users can call some list endpoints without `project_id`; that is acceptable for admin diagnostics, but project views must still always pass `project_id`.

## Current Source-State Findings

- Interfaces tab copy is fixed in source: `Interfaces > Configuration`.
- Integrations overview is fixed in source for project-owned rows and counts.
- Agents A2A project view is fixed in source: the frontend passes `activeProjectId`, the API accepts `project_id`, and the backend delegates the filter to the A2A service.
- Backend project-owned integration list endpoints now require `project_id` for non-admin users and allow unscoped results only for global admins.
- Compute Pool remains intentionally global infrastructure; the RAM/IP and no-model-loaded issues are separate compute registry contracts, already covered by the compute tests and feature docs.
- MCP inventory is global infrastructure by design, but duplicate display names and incorrect flags are UI/data-quality issues in the global integration surface, not project-scope behavior.

## Testing Gap

Previous checks proved the TypeScript source and backend route tests, but they did not prove that the running production bundle matched the source. That left a hole where the browser could keep showing old behavior after source fixes passed.

Added `tests/test_project_scope_contracts.py` to pin the source-level project-scope contracts for:

- Interfaces tab label copy.
- Integrations overview active-project fetch and recent-activity filtering.
- Integrations store/API project filter plumbing.
- Backend non-admin project filter requirements for channels, deployments, and survey integrations.
- Agents A2A active-project filter plumbing.

## Remaining Operational Risk

The running app needs a rebuild/restart to pick up the source fixes. I did not restart or rebuild the live frontend because repository safety rules require explicit permission before starting or restarting live frontend/backend servers.

The next hardening step should be a runtime freshness check: expose build id/source timestamp in the status bar or add a developer-only diagnostic route so operators can see when the running bundle predates the source tree.
