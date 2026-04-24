# Istara System Change Matrix

This document tells coding agents what else must be inspected, updated, or revalidated when a specific part of the system changes.

`Compass` is the name of the full system this matrix belongs to: entry docs, prompts, generated architecture maps, change matrix, checklists, changelog, Tech narrative, persona knowledge, and ongoing test/simulation maintenance.

Use it with:
- `SYSTEM_PROMPT.md` for repo-wide operating rules
- `AGENT.md` for the current generated inventory
- `COMPLETE_SYSTEM.md` for the broader generated architecture map
- `CHANGE_CHECKLIST.md` for step-by-step execution

The rule is simple: no change is local unless proven otherwise.

## Universal Rule

For any non-trivial change, check these six surfaces:

1. Source of truth
2. Consumers
3. Real-time or state propagation
4. UX and navigation impact
5. Tests and simulation coverage
6. Living documentation and prompts

## Core Cross-Cutting Contracts

| If You Change | Also Check | Why |
|---|---|---|
| Data shape | models, route responses, `frontend/src/lib/types.ts`, stores, renderers | Type/serialization drift breaks UI and agents |
| Endpoint behavior | `frontend/src/lib/api.ts`, calling stores/components, e2e/simulation flows | API consumers silently desync |
| View/menu structure | `Sidebar.tsx`, `HomeClient.tsx`, mobile nav, search/shortcuts, simulation coverage | UI routes and navigation contracts drift |
| Background jobs/events | websocket broadcasters, frontend listeners, notification handling, loops/autoresearch views | Async systems fail indirectly |
| Persona or skill behavior | persona files, skill definitions, routing/recommendation logic, tests, docs | Agent behavior changes without architectural memory |
| Release/update flow | version script, workflows, updater routes, desktop tray update logic, docs | Shipping/install/update path breaks |
| Compass doctrine | prompts, checklists, Tech narrative, personas, generated docs, scenarios | Future agents inherit the wrong operating model |

## Backend Matrix

### Routes and API Contracts

| If You Change | Must Also Inspect |
|---|---|
| `backend/app/api/routes/*.py` endpoint or payload | `backend/app/main.py`, `frontend/src/lib/api.ts`, `frontend/src/lib/types.ts`, relevant store(s), relevant view/component(s), e2e/simulation scenarios, generated docs |
| route auth/role rules | `backend/app/core/security_middleware.py`, `backend/app/core/auth.py`, `frontend/src/components/auth/LoginScreen.tsx`, auth-dependent UX, security tests |
| route side effects | websocket broadcasts, notifications, downstream services, audit logging, backup/restore expectations |
| upload/file endpoints | `backend/app/core/file_processor.py`, file watcher behavior, document ingestion flows, preview components, fixtures/tests |

### Models and Persistence

| If You Change | Must Also Inspect |
|---|---|
| model fields in `backend/app/models/*.py` | serialization methods, route responses, `frontend/src/lib/types.ts`, consuming stores/components, tests, migrations/alembic if needed |
| project-scoped models | cascade-delete behavior, project export/history, backup/restore, integrity checks |
| evidence-chain models (`Nugget`, `Fact`, `Insight`, `Recommendation`, `CodeApplication`) | findings routes, findings UI, laws/compliance links, interfaces/design seeding, reports |
| auth/team models (`User`, `ProjectMember`) | auth flows, RBAC checks, user management UI, project membership UI, security tests |
| integration models | setup wizards, credential handling, encryption, deployment/survey/channel flows, audit views |

### Services, Core, and Orchestration

| If You Change | Must Also Inspect |
|---|---|
| `backend/app/services/*.py` | calling routes, stores/components that depend on behavior, simulation flows, related tests |
| `backend/app/core/agent.py` or agent execution loop | tasks, chat, findings creation, skill execution, progress events, personas, agent tests |
| compute/LLM routing | settings, compute pool, relay, desktop health, autoresearch, validation flows |
| context/RAG/memory systems | chat, memory view, context DAG, prompt quality, simulation scenarios touching long-context behavior |
| scheduler/loops/autoresearch | loops UI, execution history, notifications, related regression scenarios |
| backup/version/update systems | updater routes, desktop update checks, release docs, runtime update UX |

### WebSocket and Notifications

| If You Change | Must Also Inspect |
|---|---|
| `backend/app/api/websocket.py` event names/payloads | `frontend/src/hooks/useWebSocket.ts`, stores/components that consume events, notification persistence, simulation scenarios |
| notification categories or metadata | notification store, notifications UI tabs, preferences UI, any emitting backend module |
| progress events for tasks/agents/deployments | StatusBar, toast notifications, dashboards, execution history tabs |

### Integrations, Channels, MCP, Deployments

| If You Change | Must Also Inspect |
|---|---|
| `backend/app/channels/*.py` | channel routes, integrations UI, message/conversation panels, deployment flows, webhook fixtures/tests |
| `backend/app/services/survey_platforms/*.py` | surveys tab, survey setup wizard, ingestion logic, fixtures/tests |
| MCP server/client behavior | MCP routes, access policy editor, audit log UI, featured server docs/tests, security rules |
| deployments/research channels | deployment wizard/dashboard, transcripts, analytics, channel response flows, scenarios |

## Frontend Matrix

### Navigation and Mounted Views

| If You Change | Must Also Inspect |
|---|---|
| `frontend/src/components/layout/Sidebar.tsx` | `HomeClient.tsx`, `MobileNav.tsx`, search modal results, keyboard shortcuts, simulation navigation scenarios, generated docs |
| `frontend/src/components/layout/HomeClient.tsx` view switch | sidebar IDs, mobile nav IDs, onboarding/tour transitions, project-required guards, generated docs |
| active view IDs | localStorage key usage, deep-link/navigation events, right panel logic, notifications and suggestions that navigate |

### Stores and Client State

| If You Change | Must Also Inspect |
|---|---|
| `frontend/src/stores/*.ts` state shape | types, calling components, websocket updates, optimistic UI paths, simulations using that feature |
| auth/session state | `LoginScreen.tsx`, API auth headers, route guards, onboarding boot flow, auth tests |
| project/task/chat stores | Kanban, chat sessions, findings flows, context and documents linking, simulation scenarios |
| integrations/compute/loops/autoresearch stores | corresponding dashboards, tabs, websocket updates, metrics/history UX |

### Components and UX

| If You Change | Must Also Inspect |
|---|---|
| shared components in `frontend/src/components/common` | all views using them, accessibility behavior, keyboard focus, simulation UX assumptions |
| onboarding components | auth boot logic, project fetch timing, localStorage onboarding flags, onboarding scenario |
| search and keyboard shortcuts | navigation IDs, searchable content sources, modal interactions, relevant tests |
| forms/wizards | API request contracts, validation errors, empty/loading states, mobile layout, simulation flows |
| view tabs within a feature | store state, query/loading behavior, empty/error states, docs describing those tabs |

### Feature-Area Specific Expectations

| Feature Area | Also Check When Modified |
|---|---|
| Chat | sessions, agents, RAG/context attachments, streaming behavior, evidence links, auth expiry flow |
| Findings | evidence chain integrity, deletion/linking rules, codebook/code application/report views, Laws/Interfaces consumers |
| Tasks/Kanban | agent assignment, locking, verification, document attachment, websocket progress, validation_method/consensus_score badges |
| Documents/Interviews/Context | upload pipeline, file previews, browser/audio support, memory/RAG indexing, voice transcription pipeline |
| Skills/Browser UX | browse_website system action, task URL pipeline (SkillInput.urls), Playwright MCP, heuristic/accessibility/benchmark skill definitions |
| Validation/Quality | consensus engine, adaptive validation selector, validation_executor, ensemble health view, quality evaluation skill, model intelligence dashboard |
| Simulation/Participants | participant_simulation module, game-theory strategies, istara-sim persona, simulation scenarios, payoff matrices |
| Observability/Telemetry | telemetry_spans table, agent_hooks system, ModelSkillStats production path, model-intelligence API, audit_log table, devops monitoring |
| Interfaces | Figma/Stitch config, findings seeding, generated screens, handoff contracts |
| Integrations | messaging, surveys, deployments, MCP policy/security, setup wizards |
| Loops/Autoresearch | scheduler, configs, experiment history, notifications |
| Notifications | event metadata, unread counts, preference filters |
| Settings/Compute/Ensemble | hardware/model/provider state, update checks, validation visibility |
| Laws of UX | law catalog, compliance profile/radar, finding linkage |

## Agent, Prompt, and Skill Matrix

| If You Change | Must Also Inspect |
|---|---|
| persona files in `backend/app/agents/personas/*` | any docs/prompts that describe agent behavior, tests/simulations that rely on that persona, generated docs if tracked inventory changes |
| skill definition JSON | skills API/routes, planning/execution flows, reports, recommendation logic, `scripts/validate_skills.py`, simulation/e2e coverage |
| removed legacy skill generator/export modules | do not reintroduce them as sources of truth; keep `definitions/*.json` canonical; run `python scripts/validate_skills.py` |
| system prompt / repo instructions | `SYSTEM_PROMPT.md`, wrappers (`CLAUDE.md`, `GEMINI.md`), checklist references, docs describing the workflow |
| agent orchestration/routing | task routing keywords, specialty assumptions, chat/session creation, audit behavior |

## Testing Matrix

| If You Change | Must Also Inspect |
|---|---|
| a user-visible flow | matching file(s) in `tests/simulation/scenarios/`, plus `tests/e2e_test.py` if it affects the Sarah journey |
| auth/security behavior | security tests, auth scenarios, middleware assumptions |
| evidence or research pipeline logic | findings chain scenarios, research integrity tests, full-pipeline/e2e flows |
| navigation or onboarding | navigation search scenario, onboarding scenario, mobile/responsive implications |
| channels/surveys/MCP/deployments | integration fixtures, scenarios, webhook/auth/security coverage |
| installer/update/release journey | install scripts, updater logic, release checks, plus dedicated simulation or regression coverage when existing scenarios do not model the journey clearly |

### Minimum Testing Rule

If a change would confuse a future agent reading the UI or API map, it probably deserves:
- one direct test or scenario update
- one new scenario when the behavior creates a new important journey or state transition
- one generated-doc refresh
- one prompt/checklist reference if it changes workflow expectations

## Documentation Matrix

| If You Change | Must Also Inspect |
|---|---|
| architecture shape | `AGENT.md`, `COMPLETE_SYSTEM.md`, `SYSTEM_INTEGRITY_GUIDE.md`, `Tech.md` if the narrative architecture changed |
| workflow/process expectations | `SYSTEM_PROMPT.md`, `CHANGE_CHECKLIST.md`, model wrappers, contributor docs |
| release/update behavior | `Tech.md`, release workflow docs, updater descriptions, versioning script references |
| user-facing capabilities | README/wiki/docs feature docs where applicable |
| Istara-agent understanding of a feature | relevant persona files in `backend/app/agents/personas/`, prompt/process docs, generated docs if inventory changed |

### Required Regeneration

After architecture-affecting changes, run:

```bash
python scripts/update_agent_md.py
python scripts/check_integrity.py
```

## Release, Versioning, and Update Matrix

| If You Change | Must Also Inspect |
|---|---|
| versioning format | `scripts/set-version.sh`, `scripts/prepare-release.sh`, `VERSION`, `CHANGELOG.md`, updater logic, desktop tag checks, release workflow |
| release workflow | `.github/workflows/build-installers.yml`, artifact naming, updater `latest.json`, release notes assumptions, `CHANGELOG.md` |
| release preparation | `scripts/prepare-release.sh`, `CHANGELOG.md`, integrity/doc regeneration flow, release commit/tag sequence |
| CI enforcement | `.github/workflows/ci.yml`, required checks, docs/checker steps, contributor workflow |
| runtime update behavior | `backend/app/api/routes/updates.py`, `desktop/src-tauri/src/health.rs`, settings update UI, backup/update docs |
| installer packaging | desktop build, bundled resources, source inclusion/exclusion, install docs |

## Governance Rules To Preserve

These are repo doctrines, not optional suggestions.

| Doctrine | What It Means In Practice |
|---|---|
| Compass must stay current | If a change alters how agents should understand, navigate, test, release, install, or preserve Istara, update the relevant Compass docs in the same change |
| Update `Tech.md` when the system meaningfully changes | If architecture, process, versioning, update flow, installer flow, or subsystem behavior changed, the narrative technical reference must change too |
| Update the testing suite for future changes | Do not only verify the current change manually; extend `tests/e2e_test.py`, `tests/simulation/scenarios/`, fixtures, or assertions so the feature remains protected later |
| Add scenarios when change scope demands it | If existing simulation coverage no longer describes the changed flow well, add a new scenario instead of forcing the change into unrelated old coverage |
| Istara-agent comprehension is a success metric | If Cleo/Sentinel/Pixel/Sage/Echo cannot understand, route, discuss, or operate around the new feature, the implementation is incomplete |
| Persona knowledge must move with capability changes | When the product gains a new capability or workflow meaning, update the relevant persona files so Istara's internal agents inherit that knowledge |
| Docs must move in the same change | Do not defer prompt, checklist, Tech, or architecture updates to a later commit |
| Release doctrine must stay coherent | Version scripts, Git tags, build workflows, updater endpoints, desktop checks, and docs must all describe the same release model |
| Releases must stay coherent with repo reality | If release-worthy pushes to `main` publish installers/releases, the workflows, updater logic, docs, and prompts must all say so; tag/manual flows may still exist, but they must not contradict the main publishing path |

### Governance Tuning Reminder

The CI governance checks should be reviewed after several real PRs/pushes. Tighten or relax trigger patterns based on real false positives/false negatives, but do not remove the review step from team memory.

## Worked Examples

### Example 1: Add a new route for project analytics

If you add `GET /api/projects/{id}/analytics`:
- update backend route module
- update `frontend/src/lib/api.ts`
- add/update `frontend/src/lib/types.ts`
- update the consuming store or component
- update the metrics/history/project settings UX if it surfaces there
- add or update simulation/e2e coverage
- regenerate docs

### Example 2: Add a new sidebar view

If you add a new `reports` view:
- add view ID/label to `Sidebar.tsx`
- mount it in `HomeClient.tsx`
- update `MobileNav.tsx` if needed
- update search/keyboard shortcuts if relevant
- add or update store/API wiring
- add a simulation scenario or extend an existing one
- regenerate docs

### Example 3: Change task status logic

If you change task transitions or verification:
- update task routes/services
- update task store
- update Kanban UI and any badges/progress UI
- update websocket progress handling if affected
- update task-oriented scenarios and e2e journey
- regenerate docs if any inventory or workflow expectations changed

## Maintenance Rule for Future Changes

When a new subsystem appears, do not leave it undocumented as tribal knowledge.

Do two things in the same change:
1. implement the subsystem
2. extend the living-doc system so future agents can discover and preserve it automatically
