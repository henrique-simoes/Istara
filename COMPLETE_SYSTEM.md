# Istara Complete System Architecture & Living Map

Generated from the repository on version `2026.04.17.1`. This document is meant to be regenerated whenever the implementation changes so LLMs can reason from the current system instead of stale summaries.

## Purpose

- Use this as the broad architecture map for planning and code review.
- Use `AGENT.md` for the compressed operating view.
- Use `SYSTEM_CHANGE_MATRIX.md` for cross-surface dependency mapping.
- Use `CHANGE_CHECKLIST.md` for implementation steps and `tests/simulation/scenarios/` as the practical UI contract.

## Living-Doc Rules

- Source of truth is the codebase plus generated inventories below, not remembered prose.
- Any change to routes, models, personas, stores, views, skills, or regression scenarios should be followed by `python scripts/update_agent_md.py`.
- `python scripts/check_integrity.py` should pass before shipping architecture-affecting changes.
- If a change introduces a new subsystem that the scanner cannot see cleanly, extend the scanner in `scripts/update_agent_md.py` instead of silently documenting it by hand only once.

## Repository Architecture Snapshot

- FastAPI backend with 38 route modules and 367 detected endpoints.
- Next.js frontend with 22 mounted views and 15 Zustand stores.
- 42 SQLAlchemy models in `backend/app/models`.
- 6 tracked persona directories and 56 JSON-defined skills.
- 73 Playwright simulation scenarios plus 27 Python e2e phases.

## Backend Route Inventory

| Route Module | Prefix | Endpoints |
|---|---|---|
| `agents.py` | `/` | 48 |
| `audit.py` | `/` | 7 |
| `auth.py` | `/` | 15 |
| `autoresearch.py` | `/autoresearch` | 9 |
| `backup.py` | `/` | 9 |
| `channels.py` | `/` | 11 |
| `chat.py` | `/` | 3 |
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
| `metrics.py` | `/` | 3 |
| `notifications.py` | `/` | 7 |
| `projects.py` | `/` | 15 |
| `reports.py` | `/reports` | 1 |
| `scheduler.py` | `/` | 5 |
| `sessions.py` | `/` | 8 |
| `settings.py` | `/` | 14 |
| `skills.py` | `/` | 18 |
| `steering.py` | `/` | 8 |
| `surveys.py` | `/` | 9 |
| `tasks.py` | `/` | 11 |
| `updates.py` | `/` | 4 |
| `webauthn.py` | `/` | 6 |
| `webhooks.py` | `/webhooks` | 3 |

### Endpoint Coverage

- **agents**: `GET /api/agents`, `GET /api/agents/capacity`, `GET /api/agents/heartbeat/status`, `GET /api/agents/a2a/log`, `GET /api/agents/status`, `GET /api/agents/log/recent`, `POST /api/agents`, `GET /api/agents/{agent_id}`, `PATCH /api/agents/{agent_id}`, `DELETE /api/agents/{agent_id}`, `POST /api/agents/{agent_id}/pause`, `POST /api/agents/{agent_id}/resume`, `POST /api/agents/{agent_id}/restart`, `POST /api/agents/{agent_id}/set-scope`, `POST /api/agents/{agent_id}/request-promotion`, `POST /api/agents/{agent_id}/avatar`, `GET /api/agents/{agent_id}/avatar`, `GET /api/agents/{agent_id}/identity`, `PUT /api/agents/{agent_id}/identity`, `GET /api/agents/personas/list`, `GET /api/agents/{agent_id}/learnings`, `GET /api/agents/{agent_id}/evolution/candidates`, `POST /api/agents/{agent_id}/evolution/promote/{learning_id}`, `POST /api/agents/{agent_id}/evolution/auto`, `GET /api/agents/evolution/scan`, `GET /api/agents/creation-proposals/pending`, `GET /api/agents/creation-proposals/all`, `POST /api/agents/creation-proposals/{proposal_id}/approve`, `POST /api/agents/creation-proposals/{proposal_id}/reject`, `GET /api/agents/{agent_id}/prompt/stats`, `POST /api/agents/{agent_id}/prompt/compose`, `GET /api/agents/{agent_id}/memory`, `PATCH /api/agents/{agent_id}/memory`, `GET /api/agents/{agent_id}/messages`, `POST /api/agents/{agent_id}/messages`, `GET /api/audit/ux/latest`, `POST /api/audit/ux/run`, `GET /api/audit/sim/latest`, `POST /api/audit/sim/run`, `GET /api/agents/{agent_id}/export`, `POST /api/agents/import`, `GET /api/resources`, `GET /api/contexts`, `POST /api/contexts`, `GET /api/contexts/{doc_id}`, `PATCH /api/contexts/{doc_id}`, `DELETE /api/contexts/{doc_id}`, `GET /api/contexts/composed/{project_id}`
- **audit**: `GET /api/audit/devops/latest`, `GET /api/audit/devops/history`, `POST /api/audit/devops/run`, `GET /api/audit/ui/latest`, `GET /api/audit/ui/history`, `POST /api/audit/ui/run`, `GET /api/audit/logs`
- **auth**: `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `POST /api/auth/totp/setup`, `POST /api/auth/totp/verify`, `POST /api/auth/totp/disable`, `POST /api/auth/recovery-codes/generate`, `GET /api/auth/recovery-codes/status`, `GET /api/auth/me`, `PUT /api/auth/preferences`, `GET /api/auth/team-status`, `GET /api/auth/users`, `POST /api/auth/users`, `DELETE /api/auth/users/{user_id}`, `PATCH /api/auth/users/{user_id}/role`
- **autoresearch**: `GET /api/autoresearch/status`, `GET /api/autoresearch/experiments`, `GET /api/autoresearch/experiments/{experiment_id}`, `POST /api/autoresearch/start`, `POST /api/autoresearch/stop`, `GET /api/autoresearch/config`, `PATCH /api/autoresearch/config`, `GET /api/autoresearch/leaderboard`, `POST /api/autoresearch/toggle`
- **backup**: `GET /api/backups`, `POST /api/backups/create`, `POST /api/backups/{backup_id}/restore`, `POST /api/backups/{backup_id}/verify`, `DELETE /api/backups/{backup_id}`, `GET /api/backups/config`, `POST /api/backups/config`, `GET /api/backups/estimate`, `GET /api/backups/{backup_id}/download`
- **channels**: `GET /api/channels`, `POST /api/channels`, `GET /api/channels/{instance_id}`, `PATCH /api/channels/{instance_id}`, `DELETE /api/channels/{instance_id}`, `POST /api/channels/{instance_id}/start`, `POST /api/channels/{instance_id}/stop`, `GET /api/channels/{instance_id}/health`, `GET /api/channels/{instance_id}/messages`, `GET /api/channels/{instance_id}/conversations`, `POST /api/channels/{instance_id}/send`
- **chat**: `POST /api/chat`, `GET /api/chat/history/{project_id}`, `POST /api/chat/voice`
- **code_applications**: `GET /api/code-applications/{project_id}`, `GET /api/code-applications/{project_id}/pending`, `PATCH /api/code-applications/{application_id}/review`, `POST /api/code-applications/{project_id}/bulk-approve`
- **codebook_versions**: `GET /api/codebook-versions/{project_id}`, `GET /api/codebook-versions/{project_id}/latest`, `POST /api/codebook-versions`, `GET /api/codebook-versions/detail/{version_id}`
- **codebooks**: `GET /api/codebooks`, `POST /api/codebooks`, `GET /api/codebooks/{codebook_id}`, `PATCH /api/codebooks/{codebook_id}`, `DELETE /api/codebooks/{codebook_id}`, `POST /api/codes`, `PATCH /api/codes/{code_id}`, `DELETE /api/codes/{code_id}`
- **compute**: `GET /api/compute/nodes`, `GET /api/compute/stats`, `GET /api/compute/model-warnings`
- **connections**: `POST /api/connections/generate`, `POST /api/connections/validate`, `POST /api/connections/redeem`, `POST /api/connections/rotate-network-token`
- **context_dag**: `GET /api/context-dag/{session_id}`, `GET /api/context-dag/{session_id}/health`, `POST /api/context-dag/{session_id}/expand`, `POST /api/context-dag/{session_id}/grep`, `GET /api/context-dag/{session_id}/node/{node_id}`, `POST /api/context-dag/{session_id}/compact`
- **deployments**: `POST /api/deployments`, `GET /api/deployments`, `GET /api/deployments/overview`, `GET /api/deployments/{deployment_id}`, `GET /api/deployments/{deployment_id}/analytics`, `POST /api/deployments/{deployment_id}/activate`, `POST /api/deployments/{deployment_id}/pause`, `POST /api/deployments/{deployment_id}/complete`, `POST /api/deployments/{deployment_id}/respond`, `GET /api/deployments/{deployment_id}/conversations`, `GET /api/deployments/{deployment_id}/conversations/{conversation_id}`, `GET /api/deployments/{deployment_id}/conversations/{conversation_id}/transcript`
- **documents**: `GET /api/documents`, `GET /api/documents/{document_id}`, `POST /api/documents`, `PATCH /api/documents/{document_id}`, `DELETE /api/documents/{document_id}`, `GET /api/documents/{document_id}/content`, `GET /api/documents/search/full`, `GET /api/documents/tags/{project_id}`, `POST /api/documents/sync/{project_id}`, `GET /api/documents/stats/{project_id}`
- **files**: `POST /api/files/upload/{project_id}`, `GET /api/files/{project_id}`, `POST /api/files/{project_id}/reprocess`, `GET /api/files/{project_id}/stats`, `GET /api/files/{project_id}/content/{filename}`, `POST /api/files/{project_id}/scan`, `GET /api/files/{project_id}/serve/{filename}`
- **findings**: `GET /api/findings/nuggets`, `POST /api/findings/nuggets`, `DELETE /api/findings/nuggets/{nugget_id}`, `GET /api/findings/facts`, `POST /api/findings/facts`, `DELETE /api/findings/facts/{fact_id}`, `GET /api/findings/insights`, `POST /api/findings/insights`, `DELETE /api/findings/insights/{insight_id}`, `GET /api/findings/recommendations`, `POST /api/findings/recommendations`, `DELETE /api/findings/recommendations/{rec_id}`, `GET /api/findings/search/global`, `GET /api/findings/search/{project_id}`, `GET /api/findings/{finding_type}/{finding_id}/evidence-chain`, `PATCH /api/findings/{finding_type}/{finding_id}/link`, `GET /api/findings/summary/{project_id}`, `GET /api/findings/design-decisions`, `POST /api/findings/design-decisions`, `DELETE /api/findings/design-decisions/{dd_id}`, `GET /api/findings/{finding_type}/{finding_id}/evidence-chain-extended`
- **interfaces**: `GET /api/interfaces/design-chat/{project_id}/history`, `POST /api/interfaces/design-chat`, `GET /api/interfaces/screens`, `GET /api/interfaces/screens/{screen_id}`, `POST /api/interfaces/screens/generate`, `POST /api/interfaces/screens/edit`, `POST /api/interfaces/screens/variant`, `DELETE /api/interfaces/screens/{screen_id}`, `POST /api/interfaces/figma/import`, `POST /api/interfaces/figma/export`, `GET /api/interfaces/figma/design-system/{file_key}`, `GET /api/interfaces/handoff/briefs`, `POST /api/interfaces/handoff/brief`, `POST /api/interfaces/handoff/dev-spec`, `GET /api/interfaces/status`, `POST /api/interfaces/configure/stitch`, `POST /api/interfaces/configure/figma`, `POST /api/interfaces/mock/generate`, `POST /api/interfaces/mock/edit`, `POST /api/interfaces/mock/variants`, `POST /api/interfaces/mock/figma-import`
- **laws**: `GET /api/laws`, `GET /api/laws/by-heuristic/{heuristic_id}`, `GET /api/laws/match`, `GET /api/laws/compliance/{project_id}`, `GET /api/laws/compliance/{project_id}/radar`, `GET /api/laws/{law_id}`
- **llm_servers**: `GET /api/llm-servers`, `POST /api/llm-servers`, `POST /api/llm-servers/{server_id}/health-check`, `PATCH /api/llm-servers/{server_id}`, `DELETE /api/llm-servers/{server_id}`, `POST /api/llm-servers/discover`
- **loops**: `GET /api/loops/overview`, `GET /api/loops/agents`, `GET /api/loops/agents/{agent_id}/config`, `PATCH /api/loops/agents/{agent_id}/config`, `POST /api/loops/agents/{agent_id}/pause`, `POST /api/loops/agents/{agent_id}/resume`, `GET /api/loops/executions`, `GET /api/loops/executions/stats`, `GET /api/loops/health`, `POST /api/loops/custom`
- **mcp**: `GET /api/mcp/server/status`, `POST /api/mcp/server/toggle`, `GET /api/mcp/server/policy`, `PATCH /api/mcp/server/policy`, `GET /api/mcp/server/audit`, `GET /api/mcp/server/exposure`, `GET /api/mcp/clients`, `POST /api/mcp/clients`, `GET /api/mcp/clients/tools`, `DELETE /api/mcp/clients/{server_id}`, `POST /api/mcp/clients/{server_id}/discover`, `GET /api/mcp/clients/{server_id}/tools`, `POST /api/mcp/clients/{server_id}/call`, `GET /api/mcp/clients/{server_id}/health`, `GET /api/mcp/featured`, `GET /api/mcp/featured/{server_id}`, `POST /api/mcp/featured/{server_id}/connect`
- **memory**: `GET /api/memory/{project_id}`, `GET /api/memory/{project_id}/search`, `GET /api/memory/{project_id}/stats`, `GET /api/memory/{project_id}/agent/{agent_id}/notes`, `DELETE /api/memory/{project_id}/source/{source_name:path}`
- **meta_hyperagent**: `GET /api/meta-hyperagent/status`, `GET /api/meta-hyperagent/proposals`, `POST /api/meta-hyperagent/proposals/{proposal_id}/approve`, `POST /api/meta-hyperagent/proposals/{proposal_id}/reject`, `GET /api/meta-hyperagent/variants`, `POST /api/meta-hyperagent/variants/{variant_id}/revert`, `POST /api/meta-hyperagent/variants/{variant_id}/confirm`, `GET /api/meta-hyperagent/observations`, `POST /api/meta-hyperagent/toggle`
- **metrics**: `GET /api/metrics/{project_id}`, `GET /api/metrics/{project_id}/validation`, `GET /api/metrics/{project_id}/model-intelligence`
- **notifications**: `GET /api/notifications`, `GET /api/notifications/unread-count`, `POST /api/notifications/{notification_id}/read`, `POST /api/notifications/read-all`, `DELETE /api/notifications/{notification_id}`, `GET /api/notifications/preferences`, `PUT /api/notifications/preferences`
- **projects**: `GET /api/projects`, `POST /api/projects`, `GET /api/projects/{project_id}`, `PATCH /api/projects/{project_id}`, `POST /api/projects/{project_id}/pause`, `POST /api/projects/{project_id}/resume`, `POST /api/projects/{project_id}/link-folder`, `POST /api/projects/{project_id}/unlink-folder`, `DELETE /api/projects/{project_id}`, `GET /api/projects/{project_id}/versions`, `POST /api/projects/{project_id}/export`, `GET /api/projects/{project_id}/members`, `POST /api/projects/{project_id}/members`, `DELETE /api/projects/{project_id}/members/{user_id}`, `PATCH /api/projects/{project_id}/members/{user_id}`
- **reports**: `GET /api/reports/{project_id}`
- **scheduler**: `POST /api/schedules`, `GET /api/schedules`, `GET /api/schedules/{schedule_id}`, `PATCH /api/schedules/{schedule_id}`, `DELETE /api/schedules/{schedule_id}`
- **sessions**: `GET /api/sessions/{project_id}`, `POST /api/sessions`, `GET /api/sessions/detail/{session_id}`, `PATCH /api/sessions/{session_id}`, `DELETE /api/sessions/{session_id}`, `POST /api/sessions/{session_id}/star`, `GET /api/inference-presets`, `GET /api/sessions/{project_id}/ensure-default`
- **settings**: `GET /api/settings/hardware`, `GET /api/settings/models`, `POST /api/settings/model`, `POST /api/settings/provider`, `POST /api/settings/maintenance/pause`, `POST /api/settings/maintenance/resume`, `GET /api/settings/maintenance`, `GET /api/settings/integrations-status`, `GET /api/settings/vector-health`, `GET /api/settings/data-integrity`, `POST /api/settings/export-database`, `POST /api/settings/import-database`, `GET /api/settings/status`, `POST /api/settings/team-mode`
- **skills**: `GET /api/skills`, `GET /api/skills/health/all`, `GET /api/skills/proposals/pending`, `GET /api/skills/proposals/all`, `GET /api/skills/creation-proposals/pending`, `GET /api/skills/creation-proposals/all`, `POST /api/skills/creation-proposals/{proposal_id}/approve`, `POST /api/skills/creation-proposals/{proposal_id}/reject`, `GET /api/skills/{name}`, `POST /api/skills`, `PATCH /api/skills/{name}`, `DELETE /api/skills/{name}`, `POST /api/skills/{name}/toggle`, `GET /api/skills/{name}/health`, `POST /api/skills/proposals/{proposal_id}/approve`, `POST /api/skills/proposals/{proposal_id}/reject`, `POST /api/skills/{name}/execute`, `POST /api/skills/{name}/plan`
- **steering**: `POST /api/steering/{agent_id}`, `POST /api/steering/{agent_id}/follow-up`, `POST /api/steering/{agent_id}/abort`, `GET /api/steering/{agent_id}/status`, `GET /api/steering/{agent_id}/queues`, `DELETE /api/steering/{agent_id}/queues`, `GET /api/steering/{agent_id}/idle`, `GET /api/steering`
- **surveys**: `GET /api/surveys/integrations`, `POST /api/surveys/integrations`, `DELETE /api/surveys/integrations/{integration_id}`, `GET /api/surveys/integrations/{integration_id}/surveys`, `POST /api/surveys/integrations/{integration_id}/create`, `POST /api/surveys/links`, `GET /api/surveys/links`, `POST /api/surveys/links/{link_id}/sync`, `GET /api/surveys/links/{link_id}/responses`
- **tasks**: `GET /api/tasks`, `POST /api/tasks`, `GET /api/tasks/{task_id}`, `PATCH /api/tasks/{task_id}`, `POST /api/tasks/{task_id}/move`, `POST /api/tasks/{task_id}/verify`, `POST /api/tasks/{task_id}/attach`, `POST /api/tasks/{task_id}/detach`, `POST /api/tasks/{task_id}/lock`, `POST /api/tasks/{task_id}/unlock`, `DELETE /api/tasks/{task_id}`
- **updates**: `GET /api/updates/version`, `GET /api/updates/check`, `POST /api/updates/prepare`, `POST /api/updates/apply`
- **webauthn**: `POST /api/webauthn/register/start`, `POST /api/webauthn/register/finish`, `POST /api/webauthn/authenticate/start`, `POST /api/webauthn/authenticate/finish`, `GET /api/webauthn/credentials`, `DELETE /api/webauthn/credentials/{credential_id}`
- **webhooks**: `GET /api/webhooks/whatsapp/{instance_id}`, `POST /api/webhooks/whatsapp/{instance_id}`, `POST /api/webhooks/google-chat/{instance_id}`

## Data Model Inventory

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
| `TelemetrySpan` | `telemetry_spans` | no | `backend/app/models/telemetry_span.py` |
| `User` | `users` | no | `backend/app/models/user.py` |
| `WebAuthnCredential` | `webauthn_credentials` | no | `backend/app/models/webauthn_credential.py` |

## Frontend View and Navigation Inventory

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

## Frontend Store Inventory

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

## Personas and Skills

| Persona ID | Description |
|---|---|
| `design-lead` | Design Lead -- Istara Interface Agent |
| `istara-devops` | Sentinel -- DevOps Audit Agent |
| `istara-main` | Istara Research Coordinator |
| `istara-sim` | Echo -- User Simulation Agent |
| `istara-ui-audit` | Pixel -- UI Audit Agent |
| `istara-ux-eval` | Sage -- UX Evaluation Agent |

### Skills By Phase

- **Define** (13): Affinity Mapping, Empathy Mapping, Problem Statements / HMW, Journey Mapping, Jobs-to-be-Done Analysis, Kappa Intercoder Thematic Analysis, Participant Simulation (Game Theory), Persona Creation, Prioritization Matrix, Research Synthesis Report, Taxonomy Generator, Thematic Analysis, User Flow Mapping
- **Deliver** (12): Handoff Documentation, Longitudinal Study Tracking, NPS Analysis, Regression / Impact Analysis, Research Repository Curation, Evaluate Research Quality, Research Ops Retrospective, Stakeholder Presentation, Design System Synthesis, HTML to React Components, SUS / UMUX Scoring, Task Analysis (Quantitative)
- **Develop** (16): A/B Test Analysis, Live Site Accessibility Audit, Live Site UX Audit, Card Sorting Analysis, Cognitive Walkthrough, Concept Testing, Design Critique / Expert Review, Design System Audit, Heuristic Evaluation, Prototype Feedback Analysis, Stitch Design Generation, Design Prompt Enhancement, Tree Testing Analysis, Usability Testing, UX Law Compliance Audit, Workshop Facilitation
- **Discover** (15): Accessibility Audit, Analytics Review, Competitor UX Benchmarking, Competitive Analysis, Contextual Inquiry, Literature / Desk Research, Diary Studies, Field Studies / Ethnography, Interview Question Generator, Stakeholder Interviews, Survey AI Response Detection, Survey Design & Analysis, Survey Generator, Audio Transcription & Analysis, User Interviews

## Real-Time and Integration Surface

- WebSocket events: `agent_idle`, `agent_status`, `agent_thinking`, `autoresearch_complete`, `autoresearch_progress`, `channel_message`, `channel_status`, `deployment_finding`, `deployment_progress`, `deployment_response`, `file_processed`, `finding_created`, `meta_proposal`, `plan_progress`, `resource_throttle`, `steering_message`, `suggestion`, `task_progress`, `task_queue_update`.
- Channel adapters: `google_chat`, `slack`, `telegram`, `whatsapp`.
- Survey platform services: `google_forms`, `surveymonkey`, `typeform`.
- Desktop modules: `backend_setup`, `commands`, `config`, `first_run`, `health`, `installer`, `main`, `path_resolver`, `process`, `stats`, `tray`.
- Relay modules: `connection`, `connection-string`, `heartbeat`, `llm-proxy`, `state-machine`.

## Behavioral Coverage from Tests

### Python E2E Journey

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
- Mid-Execution Steering
- Chat Flow
- Findings CRUD
- Project Management
- Task Management
- Skills Deep Dive
- Documents Deep Dive
- Sessions Deep Dive
- Settings Deep Dive
- Backup Deep Dive
- Meta-Agent Deep Dive
- Interfaces Deep Dive
- Loops Deep Dive
- Voice Transcription
- Voice Transcription

### Simulation Scenario Matrix

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
- `70` — Mid Execution Steering
- `70` — Research Integrity
- `71` — Plan And Execute
- `72` — Circuit Breaker Health
- `73` — A2A Debate And Reports
- `74` — Voice Transcription
- `75` — Participant Simulation

## What Agents Must Check Before Editing

- Does the change alter the API contract, local state contract, or menu/view wiring?
- Does the change add or remove a persistence entity, evidence-link path, or background process?
- Does the change affect a simulation scenario or the Sarah journey in `tests/e2e_test.py`?
- Does the change require a new prompt or persona rule so future agents make the same safe decision automatically?

## Maintenance Workflow

1. Make the implementation change.
2. Update tests and any hand-authored guidance that explains the new behavior.
3. Run `python scripts/update_agent_md.py`.
4. Run `python scripts/check_integrity.py`.
5. If the generated docs still miss something important, improve the generator instead of patching around it manually.

