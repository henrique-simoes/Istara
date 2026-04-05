# Istara — Agent-Readable Operating Map

Generated from the repository on version `2026.04.05.2`. Treat this file as the fast inventory view after reading `AGENT_ENTRYPOINT.md`, then consult `COMPLETE_SYSTEM.md`, `SYSTEM_CHANGE_MATRIX.md`, `CHANGE_CHECKLIST.md`, and `SYSTEM_PROMPT.md` before structural work.

## Non-Negotiable Workflow

- Read `AGENT_ENTRYPOINT.md` first for the canonical document-reading order.
- Read `SYSTEM_PROMPT.md` for operating rules and documentation duties.
- Use `SYSTEM_CHANGE_MATRIX.md` to identify dependent backend, frontend, UX, test, release, and prompt surfaces.
- Use `CHANGE_CHECKLIST.md` to identify every code, test, and doc surface touched by the change.
- Regenerate this file and `COMPLETE_SYSTEM.md` with `python scripts/update_agent_md.py` in the same change that modifies architecture, flows, routes, stores, skills, personas, or tests.
- Run `python scripts/check_integrity.py` before finalizing docs-related work.
- Treat `tests/e2e_test.py` and `tests/simulation/scenarios/` as behavioral contracts for the UI and system flows.
- Update `Tech.md` when architecture, workflow, installer, release, or update behavior changes.
- Update future-facing tests and relevant Istara persona files when a feature changes what Istara's own agents must understand.
- Use `./scripts/prepare-release.sh --bump` for intentional release preparation, but keep the docs aligned with the actual repo rule that release-worthy pushes to `main` publish installers/releases.

## System Snapshot

- Frontend: Next.js app with 22 mounted views and 15 Zustand stores.
- Backend: FastAPI app with 36 route modules and 343 detected endpoints.
- Data layer: 40 SQLAlchemy models plus LanceDB-backed retrieval/context systems.
- Agents/personas: 6 tracked persona directories under `backend/app/agents/personas`.
- Skills: 50 JSON-defined skills across the Double Diamond phases.
- Regression map: 70 simulation scenarios plus 12 e2e phases.

## Change Hotspots

- New route or changed payload: update backend route, frontend API client, matching TypeScript types, consuming stores/components, tests, and regenerate docs.
- New model or schema field: update model, serialization, frontend types, any route/store consumers, migration path, tests, and regenerate docs.
- New view or menu item: update `Sidebar.tsx`, `HomeClient.tsx`, relevant store/components, simulation scenarios, and regenerate docs.
- Persona, skill, or workflow changes: update persona files, skill definitions/prompts, related tests, and regenerate docs.

## Navigation Map

| Area | View ID | Label | Mounted Component |
|---|---|---|---|
| Primary | `chat` | Chat | `ChatView` |
| Primary | `findings` | Findings | `FindingsView` |
| Primary | `laws` | UX Laws | `LawsView` |
| Primary | `tasks` | Tasks | `KanbanBoard` |
| Primary | `interviews` | Interviews | `InterviewView` |
| Primary | `documents` | Documents | `DocumentsView` |
| Primary | `context` | Context | `ContextEditor` |
| Primary | `skills` | Skills | `SkillsView` |
| Primary | `agents` | Agents | `AgentsView` |
| Primary | `memory` | Memory | `MemoryView` |
| Primary | `interfaces` | Interfaces | `InterfacesView` |
| Primary | `integrations` | Integrations | `IntegrationsView` |
| Primary | `loops` | Loops | `LoopsView` |
| Primary | `settings` | Settings | `SettingsView` |
| Secondary | `autoresearch` | Autoresearch | `AutoresearchView` |
| Secondary | `backup` | Backup | `BackupView` |
| Secondary | `meta-hyperagent` | Meta-Agent | `MetaHyperagentView` |
| Secondary | `compute` | Compute Pool | `ComputePoolView` |
| Secondary | `ensemble` | Ensemble Health | `EnsembleHealthView` |
| Secondary | `project-settings` | Project Settings | `ProjectSettingsView` |
| Secondary | `history` | History | `VersionHistory` |
| Utility | `notifications` | Notifications | `NotificationsView` |

## Persona Registry

| Persona ID | Description |
|---|---|
| `design-lead` | Design Lead -- Istara Interface Agent |
| `istara-devops` | Sentinel -- DevOps Audit Agent |
| `istara-main` | Istara Research Coordinator |
| `istara-sim` | Echo -- User Simulation Agent |
| `istara-ui-audit` | Pixel -- UI Audit Agent |
| `istara-ux-eval` | Sage -- UX Evaluation Agent |

## Skills By Phase

- **Define** (12): Affinity Mapping, Empathy Mapping, Problem Statements / HMW, Journey Mapping, Jobs-to-be-Done Analysis, Kappa Intercoder Thematic Analysis, Persona Creation, Prioritization Matrix, Research Synthesis Report, Taxonomy Generator, Thematic Analysis, User Flow Mapping
- **Deliver** (11): Handoff Documentation, Longitudinal Study Tracking, NPS Analysis, Regression / Impact Analysis, Research Repository Curation, Research Ops Retrospective, Stakeholder Presentation, Design System Synthesis, HTML to React Components, SUS / UMUX Scoring, Task Analysis (Quantitative)
- **Develop** (14): A/B Test Analysis, Card Sorting Analysis, Cognitive Walkthrough, Concept Testing, Design Critique / Expert Review, Design System Audit, Heuristic Evaluation, Prototype Feedback Analysis, Stitch Design Generation, Design Prompt Enhancement, Tree Testing Analysis, Usability Testing, UX Law Compliance Audit, Workshop Facilitation
- **Discover** (13): Accessibility Audit, Analytics Review, Competitive Analysis, Contextual Inquiry, Literature / Desk Research, Diary Studies, Field Studies / Ethnography, Interview Question Generator, Stakeholder Interviews, Survey AI Response Detection, Survey Design & Analysis, Survey Generator, User Interviews

## Backend Route Modules

| Route Module | Prefix | Endpoints |
|---|---|---|
| `agents.py` | `/` | 48 |
| `audit.py` | `/` | 6 |
| `auth.py` | `/` | 9 |
| `autoresearch.py` | `/autoresearch` | 9 |
| `backup.py` | `/` | 9 |
| `channels.py` | `/` | 11 |
| `chat.py` | `/` | 2 |
| `code_applications.py` | `/code-applications` | 4 |
| `codebook_versions.py` | `/codebook-versions` | 4 |
| `codebooks.py` | `/` | 8 |
| `compute.py` | `/` | 3 |
| `connections.py` | `/` | 4 |
| `context_dag.py` | `/` | 6 |
| `deployments.py` | `/` | 12 |
| `documents.py` | `/` | 10 |
| `files.py` | `/` | 7 |
| `findings.py` | `/` | 21 |
| `interfaces.py` | `/` | 21 |
| `laws.py` | `/laws` | 6 |
| `llm_servers.py` | `/` | 6 |
| `loops.py` | `/` | 10 |
| `mcp.py` | `/` | 17 |
| `memory.py` | `/` | 5 |
| `meta_hyperagent.py` | `/` | 9 |
| `metrics.py` | `/` | 1 |
| `notifications.py` | `/` | 7 |
| `projects.py` | `/` | 15 |
| `reports.py` | `/reports` | 1 |
| `scheduler.py` | `/` | 5 |
| `sessions.py` | `/` | 8 |
| `settings.py` | `/` | 14 |
| `skills.py` | `/` | 18 |
| `surveys.py` | `/` | 9 |
| `tasks.py` | `/` | 11 |
| `updates.py` | `/` | 4 |
| `webhooks.py` | `/webhooks` | 3 |

## Data Model Registry

| Model | Table | `to_dict()` | File |
|---|---|---|---|
| `Agent` | `agents` | yes | `backend/app/models/agent.py` |
| `A2AMessage` | `a2a_messages` | yes | `backend/app/models/agent.py` |
| `AgentLoopConfig` | `agent_loop_configs` | yes | `backend/app/models/agent_loop_config.py` |
| `AutoresearchExperiment` | `autoresearch_experiments` | yes | `backend/app/models/autoresearch_experiment.py` |
| `BackupRecord` | `backup_records` | yes | `backend/app/models/backup.py` |
| `ChannelConversation` | `channel_conversations` | yes | `backend/app/models/channel_conversation.py` |
| `ChannelInstance` | `channel_instances` | yes | `backend/app/models/channel_instance.py` |
| `ChannelMessage` | `channel_messages` | yes | `backend/app/models/channel_message.py` |
| `CodeApplication` | `code_applications` | yes | `backend/app/models/code_application.py` |
| `Codebook` | `codebooks` | yes | `backend/app/models/codebook.py` |
| `Code` | `codes` | yes | `backend/app/models/codebook.py` |
| `CodebookVersion` | `codebook_versions` | yes | `backend/app/models/codebook_version.py` |
| `ContextDAGNode` | `context_dag_nodes` | no | `backend/app/models/context_dag.py` |
| `DesignScreen` | `design_screens` | yes | `backend/app/models/design_screen.py` |
| `DesignBrief` | `design_briefs` | yes | `backend/app/models/design_screen.py` |
| `DesignDecision` | `design_decisions` | yes | `backend/app/models/design_screen.py` |
| `Document` | `documents` | yes | `backend/app/models/document.py` |
| `Nugget` | `nuggets` | no | `backend/app/models/finding.py` |
| `Fact` | `facts` | no | `backend/app/models/finding.py` |
| `Insight` | `insights` | no | `backend/app/models/finding.py` |
| `Recommendation` | `recommendations` | no | `backend/app/models/finding.py` |
| `LLMServer` | `llm_servers` | no | `backend/app/models/llm_server.py` |
| `LoopExecution` | `loop_executions` | yes | `backend/app/models/loop_execution.py` |
| `MCPAccessPolicy` | `mcp_access_policies` | yes | `backend/app/models/mcp_access_policy.py` |
| `MCPAuditEntry` | `mcp_audit_log` | yes | `backend/app/models/mcp_audit_log.py` |
| `MCPServerConfig` | `mcp_server_configs` | yes | `backend/app/models/mcp_server_config.py` |
| `Message` | `messages` | no | `backend/app/models/message.py` |
| `MethodMetric` | `method_metrics` | no | `backend/app/models/method_metric.py` |
| `ModelSkillStats` | `model_skill_stats` | yes | `backend/app/models/model_skill_stats.py` |
| `Notification` | `notifications` | yes | `backend/app/models/notification.py` |
| `NotificationPreference` | `notification_preferences` | yes | `backend/app/models/notification.py` |
| `Project` | `projects` | no | `backend/app/models/project.py` |
| `ProjectMember` | `project_members` | yes | `backend/app/models/project_member.py` |
| `ProjectReport` | `project_reports` | yes | `backend/app/models/project_report.py` |
| `ResearchDeployment` | `research_deployments` | yes | `backend/app/models/research_deployment.py` |
| `ChatSession` | `chat_sessions` | yes | `backend/app/models/session.py` |
| `SurveyIntegration` | `survey_integrations` | yes | `backend/app/models/survey_integration.py` |
| `SurveyLink` | `survey_links` | yes | `backend/app/models/survey_integration.py` |
| `Task` | `tasks` | no | `backend/app/models/task.py` |
| `User` | `users` | no | `backend/app/models/user.py` |

## Frontend State Stores

| Store File | Exported Hook |
|---|---|
| `agentStore.ts` | `useAgentStore` |
| `authStore.ts` | `useAuthStore` |
| `autoresearchStore.ts` | `useAutoresearchStore` |
| `chatStore.ts` | `useChatStore` |
| `computeStore.ts` | `useComputeStore` |
| `documentStore.ts` | `useDocumentStore` |
| `integrationsStore.ts` | `useIntegrationsStore` |
| `interfacesStore.ts` | `useInterfacesStore` |
| `lawsStore.ts` | `useLawsStore` |
| `loopsStore.ts` | `useLoopsStore` |
| `notificationStore.ts` | `useNotificationStore` |
| `projectStore.ts` | `useProjectStore` |
| `sessionStore.ts` | `useSessionStore` |
| `taskStore.ts` | `useTaskStore` |
| `tourStore.ts` | `useTourStore` |

## Real-Time Contract

- WebSocket event types detected: `agent_status`, `agent_thinking`, `autoresearch_complete`, `autoresearch_progress`, `channel_message`, `channel_status`, `deployment_finding`, `deployment_progress`, `deployment_response`, `file_processed`, `finding_created`, `meta_proposal`, `plan_progress`, `resource_throttle`, `suggestion`, `task_progress`, `task_queue_update`.
- When adding a new event, update both broadcaster + frontend handler + regression coverage + regenerated docs.

## Test Coverage Map

- E2E phases:
  - Authentication
  - System Health
  - Project Setup (Sarah creates her project)
  - Context Hierarchy
  - File Upload & Processing
  - Chat & Skill Execution
  - Findings Verification
  - Tasks & Kanban
  - Metrics & History
  - Skills Registry
  - Agents & Audit
  - Frontend Check
- Simulation scenarios:
  - `01` — Health Check
  - `02` — Onboarding
  - `03` — Project Setup
  - `04` — File Upload
  - `05` — Chat Interaction
  - `06` — Skill Execution
  - `07` — Findings Chain
  - `08` — Kanban Workflow
  - `09` — Navigation Search
  - `10` — Agent Architecture
  - `10` — Settings Models
  - `11` — Agents System
  - `12` — Chat Sessions
  - `13` — Task Agent Assignment
  - `14` — Agent Communication
  - `15` — Vector Db
  - `16` — Findings Population
  - `17` — Full Pipeline
  - `18` — Task Verification
  - `19` — File Preview
  - `20` — All Skills Comprehensive
  - `21` — Agent Work Simulation
  - `22` — Architecture Evaluation
  - `23` — Memory View
  - `24` — Context Dag
  - `25` — Systemic Robustness
  - `26` — Model Session Persistence
  - `27` — Agent Identity System
  - `28` — Self Evolution Prompt Compression
  - `29` — Documents System
  - `30` — Event Wiring Audit
  - `31` — Task Documents Tools
  - `32` — Auth Flow
  - `33` — Task Locking
  - `34` — Compute Pool
  - `35` — Ensemble Validation
  - `36` — Llm Servers
  - `37` — Ensemble Health View
  - `38` — Task Routing
  - `39` — Data Migration
  - `40` — Agent Identity Editing
  - `41` — Skill Creation
  - `42` — Content Guard
  - `43` — Process Hardening
  - `44` — Agent Factory
  - `45` — Interfaces Menu
  - `46` — Stitch Figma Integration
  - `47` — Atomic Research Design
  - `48` — Real User Simulation
  - `49` — Loops Schedule
  - `50` — Notifications
  - `51` — Backup System
  - `52` — Meta Hyperagent
  - `53` — Channel Lifecycle
  - `55` — Survey Integration
  - `56` — Mcp Server Security
  - `57` — Mcp Client Registry
  - `58` — Research Deployment
  - `59` — Agent Integration Knowledge
  - `61` — Autoresearch Isolation
  - `64` — Docker Security
  - `65` — Laws Of Ux
  - `66` — Featured Mcp Servers
  - `67` — Auth Enforcement
  - `68` — Data Security
  - `69` — User Management Ui
  - `70` — Research Integrity
  - `71` — Plan And Execute
  - `72` — Circuit Breaker Health
  - `73` — A2A Debate And Reports

## Documentation Contract

- `SYSTEM_PROMPT.md`: model-agnostic operating contract.
- `SYSTEM_CHANGE_MATRIX.md`: explicit X -> W/Y/Z dependency map for changes.
- `CLAUDE.md` / `GEMINI.md`: model-specific wrappers around the same repo workflow.
- `COMPLETE_SYSTEM.md`: broader architecture, integration, and test coverage map.
- `SYSTEM_INTEGRITY_GUIDE.md`: legacy deep-reference manual; keep it coherent when underlying architecture shifts.
- `Tech.md`: narrative technical source that must move with architecture/process/release changes.

