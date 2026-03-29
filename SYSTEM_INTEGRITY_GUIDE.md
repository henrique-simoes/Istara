# ReClaw System Integrity Guide

**Last Updated**: 2026-03-28
**System Version**: Post-ComputeRegistry unification
**Coverage**: Complete end-to-end mapping of all subsystems, dependencies, and data flows

---

## TABLE OF CONTENTS

1. [Executive Summary](#executive-summary)
2. [Database & Model Layer](#database--model-layer)
3. [API Routes & Endpoints](#api-routes--endpoints)
4. [Agent System Architecture](#agent-system-architecture)
5. [Skill System](#skill-system)
6. [Compute & LLM Integration](#compute--llm-integration)
7. [Frontend Structure](#frontend-structure)
8. [WebSocket Events & Real-Time Communication](#websocket-events--real-time-communication)
9. [Configuration & Security](#configuration--security)
10. [Integration Points](#integration-points)
11. [Critical Data Flows](#critical-data-flows)
12. [Cross-Cutting Concerns & Change Impact Matrix](#cross-cutting-concerns--change-impact-matrix)

---

## EXECUTIVE SUMMARY

ReClaw is a local-first AI agent for UX research built on a **unified compute registry** that serves as the single source of truth for all LLM compute resources. The system is organized into clear layers:

- **Database Layer**: 51+ SQLAlchemy models with cascade-delete relationships anchored in Project entity
- **API Layer**: 35 route modules covering 200+ endpoints with global JWT authentication
- **Agent Layer**: 6 autonomous agents + orchestrators coordinating via A2A messages
- **Skill Layer**: 53 JSON-defined research skills executed through a factory pattern
- **Compute Layer**: ComputeRegistry unified across local, network, and relay nodes
- **Frontend Layer**: React/Zustand with 23 major component groups and 14 Zustand stores
- **Real-Time Layer**: WebSocket server with 16 broadcast event types and notification persistence

### Critical Design Principles

1. **Project-centric**: All data is scoped to a Project ID; delete a project cascades to all related data
2. **Atomic research**: Five-layer evidence chain (Nugget → Fact → Insight → Recommendation → CodeApplication)
3. **Double Diamond**: All data tagged with phase (discover/define/develop/deliver)
4. **Compute unification**: Single ComputeRegistry replaces old LLMRouter + ComputePool + RelayNodes
5. **Task-driven**: Every research activity originates as a Task → executes skill → produces findings/documents
6. **Convergence pyramid**: Reports progressively refine through L1 artifacts → L4 final deliverable

---

## DATABASE & MODEL LAYER

### Complete Model Registry

All models are registered in `backend/app/models/database.py::init_db()`:

#### CORE RESEARCH MODELS (Atomic Evidence Chain)
| Model | Table | FK Dependencies | Cascade | `to_dict()` |
|-------|-------|-----------------|---------|-----------|
| Project | `projects` | - | [Tasks, Messages, Nuggets, Facts, Insights, Recommendations, Sessions, Codebooks, Documents, DesignScreens, DesignBriefs, DesignDecisions] | ✓ | Fields: is_paused (bool), owner_id (str) |
| Nugget | `nuggets` | Project → projects.id | - | ✗ |
| Fact | `facts` | Project → projects.id | - | ✗ |
| Insight | `insights` | Project → projects.id | - | ✗ |
| Recommendation | `recommendations` | Project → projects.id | - | ✗ |

#### TASK & DOCUMENT MODELS
| Model | Table | FK Dependencies | Cascade | Notes |
|-------|-------|-----------------|---------|-------|
| Task | `tasks` | Project → projects.id | - | JSON fields: input_document_ids, output_document_ids, urls, validation_result, consensus_score |
| Document | `documents` | Project → projects.id | - | Full content stored in content_text, searchable preview in content_preview |
| TaskCheckpoint | `task_checkpoints` | Task → tasks.id | - | Recovery mechanism for crashed tasks |

#### COMMUNICATION MODELS
| Model | Table | FK Dependencies | Notes |
|-------|-------|-----------------|-------|
| Message | `messages` | Session → chat_sessions.id | Chat message history with sources metadata |
| ChatSession | `chat_sessions` | Project → projects.id | Groups messages, has model_override + inference_preset |
| A2AMessage | `a2a_messages` | - | Agent-to-agent communication (from_agent_id, to_agent_id can be null for broadcasts) |

#### AGENT MODELS
| Model | Table | Fields | Enum States |
|-------|-------|--------|------------|
| Agent | `agents` | capabilities (JSON), memory (JSON), specialties (JSON), system_prompt, scope (universal/project), project_id | AgentRole: TASK_EXECUTOR, DEVOPS_AUDIT, UI_AUDIT, UX_EVALUATION, USER_SIMULATION, CUSTOM; AgentState: IDLE, WORKING, PAUSED, ERROR, STOPPED; HeartbeatStatus: HEALTHY, DEGRADED, ERROR, STOPPED; AgentScope: UNIVERSAL, PROJECT |

#### RESEARCH ANALYSIS MODELS
| Model | Table | FK Dependencies | Scope |
|-------|-------|-----------------|-------|
| Codebook | `codebooks` | Project → projects.id | Code definitions for qualitative analysis |
| CodebookVersion | `codebook_versions` | Codebook → codebooks.id | Version history for codebooks |
| CodeApplication | `code_applications` | Project → projects.id (codebook_version_id optional) | Every code applied with full audit trail (WHO, WHAT, WHERE, WHY, REVIEW) |
| ProjectReport | `project_reports` | Project → projects.id (codebook_version_id optional) | Four-layer convergence pyramid (L1 artifacts → L4 final) |

#### VECTOR STORE & CONTEXT MODELS
| Model | Table | Notes |
|-------|-------|-------|
| ContextDocument | `context_documents` (injected by context_hierarchy.py) | Embedded in vector DB (LanceDB), indexed by project+session |
| ContextDAGNode | `context_dag_nodes` | DAG-based context summarization for long conversations |

#### OPERATIONAL MODELS
| Model | Table | Purpose |
|-------|-------|---------|
| User | `users` | Authentication; admin/user roles |
| ChatSession | `chat_sessions` | Conversation grouping with inference presets |
| Notification | `notifications` | User notifications persisted from WebSocket broadcasts |
| NotificationPreference | `notification_preferences` | Per-user notification filters |
| LLMServer | `llm_servers` | Persisted LLM server configs (for network discovery) |
| MethodMetric | `method_metrics` | Research method performance tracking |

#### ADVANCED FEATURES MODELS
| Model | Table | Purpose |
|-------|-------|---------|
| DesignScreen | `design_screens` | Figma/Stitch design imports |
| DesignBrief | `design_briefs` | Design briefs from screens |
| DesignDecision | `design_decisions` | Design decisions linked to findings |
| ChannelInstance | `channel_instances` | Messaging integrations (Slack, Teams, etc.) |
| ChannelMessage | `channel_messages` | Messages from channels |
| ChannelConversation | `channel_conversations` | Channel conversation threads |
| ResearchDeployment | `research_deployments` | Deployed research to participants |
| SurveyIntegration | `survey_integrations` | Survey platform connections |
| SurveyLink | `survey_links` | Survey response links |
| MCPServerConfig | `mcp_server_configs` | Model Context Protocol server configs (from mcp_server_config module) |
| MCPAccessPolicy | `mcp_access_policies` | MCP security policies (from mcp_access_policy module) |
| MCPAuditEntry | `mcp_audit_logs` | MCP audit trail (from mcp_audit_log module) |
| AutoresearchExperiment | `autoresearch_experiments` | Automated research loop execution |
| LoopExecution | `loop_executions` | Task loop execution history |
| AgentLoopConfig | `agent_loop_configs` | Configuration for agent task loops |
| BackupRecord | `backup_records` | Backup metadata |
| ModelSkillStats | `model_skill_stats` | LLM model × skill performance tracking |
| ScheduledTask | `scheduled_tasks` (injected by scheduler.py) | Cron-scheduled task execution |

### Model Dependency Graph

```
Project (root)
├─ Tasks
│  └─ TaskCheckpoint
├─ Messages
├─ ChatSession
│  └─ Messages
├─ Nugget → (agent_id optional)
├─ Fact → (nugget_ids[] JSON)
├─ Insight → (fact_ids[] JSON)
├─ Recommendation → (insight_ids[] JSON)
├─ Document
│  ├─ agent_ids[] (JSON)
│  ├─ skill_names[] (JSON)
│  └─ atomic_path (JSON lineage)
├─ Codebook
│  └─ CodebookVersion
├─ CodeApplication → (source_document_id optional, codebook_version_id optional)
├─ ProjectReport → (codebook_version_id optional)
├─ DesignScreen → DesignBrief, DesignDecision
├─ ChannelInstance → ChannelMessage, ChannelConversation
├─ ResearchDeployment
├─ SurveyIntegration → SurveyLink
└─ LoopExecution

Agent (independent)
├─ A2AMessage (from_agent_id, to_agent_id)

Global (independent of Project)
├─ User
├─ LLMServer
├─ MethodMetric
├─ MCPServerConfig → MCPAccessPolicy, MCPAuditEntry
├─ AutoresearchExperiment
├─ AgentLoopConfig
├─ BackupRecord
├─ ModelSkillStats
├─ Notification → NotificationPreference
├─ ScheduledTask
├─ ContextDocument (LanceDB, indexed by project+session)
├─ ContextDAGNode
```

### Database-Level Constraints

1. **Cascade Delete**: Deleting a Project cascades to Tasks, Messages, ChatSession, all findings, all documents, reports, etc.
2. **FK Nullable**: `agent_id` is nullable on Nugget, Fact, Insight, Recommendation (agent-generated findings don't need to record the agent)
3. **Soft Deletes**: None implemented — deletes are physical
4. **Foreign Key Indexes**: Project.id is indexed everywhere it's referenced for query performance

---

## API ROUTES & ENDPOINTS

### Complete Route Registry (35 modules, 200+ endpoints)

All routes are registered in `backend/app/main.py::app.include_router()` with `/api` prefix unless noted.

#### Authentication & Users (auth.py)
- `POST /api/auth/login` — Public, no JWT required. In local mode (team_mode=False), issues JWT without DB lookup
- `POST /api/auth/register` — Public, no JWT required
- `POST /api/auth/logout` — Clear token
- `GET /api/auth/verify` — Verify current JWT
- `POST /api/auth/refresh` — Refresh expired token
- `PATCH /api/auth/profile` — Update user profile

#### Projects (projects.py)
- `GET /api/projects` — List all projects
- `POST /api/projects` — Create project
- `GET /api/projects/{id}` — Get project details
- `PATCH /api/projects/{id}` — Update project
- `DELETE /api/projects/{id}` — Delete (cascades to all children)
- `GET /api/projects/{id}/versions` — Project history snapshots

#### Tasks (tasks.py)
- `GET /api/tasks` — List tasks (filterable by project_id, status)
- `POST /api/tasks` — Create task
- `GET /api/tasks/{id}` — Get task details
- `PATCH /api/tasks/{id}` — Update task
- `DELETE /api/tasks/{id}` — Delete task
- `POST /api/tasks/{id}/move?status={status}` — Move task in Kanban
- `POST /api/tasks/{id}/attach?document_id={}&direction=input|output` — Attach document
- `POST /api/tasks/{id}/detach?document_id={}&direction=input|output` — Detach document
- `POST /api/tasks/{id}/lock` — Lock task for editing
- `POST /api/tasks/{id}/unlock` — Unlock task
- `POST /api/tasks/{id}/validate` — Run validation/consensus

#### Findings (findings.py) — Atomic research chain
- `GET /api/findings/summary?project_id={id}` — Get counts (nuggets, facts, insights, recommendations)
- `GET /api/findings/nuggets?project_id={id}` — List nuggets
- `POST /api/findings/nuggets` — Create nugget
- `PATCH /api/findings/nuggets/{id}` — Update nugget
- `DELETE /api/findings/nuggets/{id}` — Delete nugget
- `GET /api/findings/facts?project_id={id}` — List facts
- `POST /api/findings/facts` — Create fact (with nugget_ids[])
- `PATCH /api/findings/facts/{id}` — Update fact
- `DELETE /api/findings/facts/{id}` — Delete fact
- `GET /api/findings/insights?project_id={id}` — List insights
- `POST /api/findings/insights` — Create insight (with fact_ids[])
- `PATCH /api/findings/insights/{id}` — Update insight
- `DELETE /api/findings/insights/{id}` — Delete insight
- `GET /api/findings/recommendations?project_id={id}` — List recommendations
- `POST /api/findings/recommendations` — Create recommendation (with insight_ids[])
- `PATCH /api/findings/recommendations/{id}` — Update recommendation
- `DELETE /api/findings/recommendations/{id}` — Delete recommendation

#### Chat (chat.py)
- `GET /api/chat/sessions` — List chat sessions
- `POST /api/chat/sessions` — Create session
- `GET /api/chat/sessions/{id}` — Get session
- `PATCH /api/chat/sessions/{id}` — Update session (model_override, inference_preset, etc.)
- `DELETE /api/chat/sessions/{id}` — Delete session
- `GET /api/chat/sessions/{id}/messages` — Get messages in session
- `POST /api/chat/sessions/{id}/messages` — Send message → triggers RAG → LLM → response
- `POST /api/chat/sessions/{id}/messages/{msg_id}/react` — React to message
- `DELETE /api/chat/sessions/{id}/messages/{msg_id}` — Delete message
- `GET /api/chat/sessions/{id}/context` — Get context for session
- `POST /api/chat/sessions/{id}/memory` — Save session memory

#### Codebooks (codebooks.py)
- `GET /api/codebooks?project_id={id}` — List codebooks
- `POST /api/codebooks` — Create codebook
- `GET /api/codebooks/{id}` — Get codebook
- `PATCH /api/codebooks/{id}` — Update codebook structure
- `DELETE /api/codebooks/{id}` — Delete codebook
- `POST /api/codebooks/{id}/codes` — Add code to codebook
- `PATCH /api/codebooks/{id}/codes/{code_id}` — Update code
- `DELETE /api/codebooks/{id}/codes/{code_id}` — Delete code

#### Codebook Versions (codebook_versions.py)
- `GET /api/codebook-versions?project_id={id}` — List versions
- `POST /api/codebook-versions` — Snapshot current codebook
- `GET /api/codebook-versions/{id}` — Get version details
- `POST /api/codebook-versions/{id}/apply` — Revert to version

#### Code Applications (code_applications.py)
- `GET /api/code-applications?project_id={id}` — List all code applications (audit trail)
- `POST /api/code-applications` — Create code application (from finding or document)
- `GET /api/code-applications/{id}` — Get application details
- `PATCH /api/code-applications/{id}` — Update review_status, reviewed_by, reviewed_at
- `DELETE /api/code-applications/{id}` — Delete application

#### Documents (documents.py)
- `GET /api/documents?project_id={id}` — List documents
- `POST /api/documents` — Create document record
- `GET /api/documents/{id}` — Get document details
- `GET /api/documents/{id}/content` — Get full document content
- `PATCH /api/documents/{id}` — Update document metadata
- `DELETE /api/documents/{id}` — Delete document
- `POST /api/documents/{id}/tag` — Add tags to document
- `POST /api/documents/{id}/version` — Create version (soft copy)

#### Files (files.py)
- `POST /api/files/upload?project_id={id}` — Upload file → process → index → create Document record
- `GET /api/files/list?project_id={id}` — List uploaded files
- `GET /api/files/{id}` — Get file metadata
- `POST /api/files/{id}/process` — Re-process file (re-chunk, re-embed)
- `DELETE /api/files/{id}` — Delete file and Document record

#### Sessions (sessions.py)
- `GET /api/sessions` — List chat sessions
- `POST /api/sessions` — Create session
- `GET /api/sessions/{id}` — Get session with message count
- `PATCH /api/sessions/{id}` — Update session
- `DELETE /api/sessions/{id}` — Delete session (cascades messages)

#### Skills (skills.py)
- `GET /api/skills` — List all 53 registered skills
- `GET /api/skills/{name}` — Get skill details
- `POST /api/skills/register` — Load skill from definition
- `POST /api/skills/{name}/execute` — Execute skill on task
- `GET /api/skills/leaderboard` — Model × skill performance matrix
- `GET /api/skills/recommendations?model={}&phase={}` — Recommend skills for context

#### Agents (agents.py)
- `GET /api/agents` — List all agents (6 system + custom workers)
- `POST /api/agents` — Create custom agent
- `GET /api/agents/{id}` — Get agent details
- `PATCH /api/agents/{id}` — Update agent config
- `DELETE /api/agents/{id}` — Delete agent
- `POST /api/agents/{id}/start` — Start agent
- `POST /api/agents/{id}/stop` — Stop agent
- `GET /api/agents/{id}/tasks` — List tasks assigned to agent
- `GET /api/agents/{id}/heartbeat` — Get heartbeat status
- `POST /api/agents/{id}/heartbeat` — Post heartbeat

#### Compute (compute.py) — ComputeRegistry API
- `GET /api/compute/nodes` — List all compute nodes (local, network, relay)
- `POST /api/compute/nodes` — Register new node
- `GET /api/compute/nodes/{id}` — Get node details + available models
- `PATCH /api/compute/nodes/{id}` — Update node config
- `DELETE /api/compute/nodes/{id}` — Deregister node
- `GET /api/compute/nodes/{id}/health` — Get node health status
- `POST /api/compute/nodes/{id}/health` — Trigger health check
- `GET /api/compute/models` — List all models across all nodes
- `GET /api/compute/routing-stats` — Routing statistics (requests/node, latencies, failures)

#### LLM Servers (llm_servers.py)
- `GET /api/llm-servers` — List persisted servers
- `POST /api/llm-servers` — Register server manually
- `GET /api/llm-servers/{id}` — Get server details
- `DELETE /api/llm-servers/{id}` — Delete server registration

#### Settings (settings.py)
- `GET /api/settings/status` — Public health check
- `GET /api/settings` — Get all settings
- `PATCH /api/settings` — Update settings (persists to .env)
- `GET /api/settings/data-integrity` — Run data integrity check
- `POST /api/settings/import-database` — Import data from another database
- `POST /api/settings/export` — Export all data as JSON

#### Audit (audit.py)
- `GET /api/audit/logs` — List audit events
- `GET /api/audit/agents` — Agent activity log
- `GET /api/audit/tasks` — Task execution log
- `GET /api/audit/findings` — Finding creation log
- `GET /api/audit/code-applications` — Coding audit trail

#### Reports (reports.py)
- `GET /api/reports?project_id={id}` — List all reports
- `POST /api/reports` — Create new report
- `GET /api/reports/{id}` — Get report (with L1-L4 layer data)
- `PATCH /api/reports/{id}` — Update report (refine synthesis)
- `DELETE /api/reports/{id}` — Delete report
- `POST /api/reports/{id}/finalize` — Create L4 snapshot
- `POST /api/reports/{id}/export` — Export as PDF/docx

#### Notifications (notifications.py)
- `GET /api/notifications` — List notifications
- `PATCH /api/notifications/{id}` — Mark as read
- `DELETE /api/notifications/{id}` — Delete notification
- `PATCH /api/notifications/preferences` — Update notification preferences

#### Backup (backup.py)
- `GET /api/backups` — List backups
- `POST /api/backups` — Create manual backup
- `GET /api/backups/{id}` — Get backup metadata
- `POST /api/backups/{id}/restore` — Restore from backup
- `DELETE /api/backups/{id}` — Delete backup

#### Context DAG (context_dag.py)
- `GET /api/context-dag?session_id={id}` — Get DAG nodes for session
- `POST /api/context-dag` — Create DAG node
- `POST /api/context-dag/{id}/summarize` — Summarize node (reduce context)
- `GET /api/context-dag/{id}/expand` — Expand summarized node
- `POST /api/context-dag/grep` — Search across DAG

#### Scheduling (scheduler.py)
- `GET /api/scheduler/tasks` — List scheduled tasks
- `POST /api/scheduler/tasks` — Create scheduled task
- `GET /api/scheduler/tasks/{id}` — Get task details
- `PATCH /api/scheduler/tasks/{id}` — Update schedule
- `DELETE /api/scheduler/tasks/{id}` — Delete scheduled task
- `POST /api/scheduler/tasks/{id}/run` — Execute immediately
- `POST /api/scheduler/tasks/{id}/pause` — Pause schedule
- `POST /api/scheduler/tasks/{id}/resume` — Resume schedule

#### Channels (channels.py)
- `GET /api/channels/instances` — List channel instances
- `POST /api/channels/instances` — Create channel instance (Slack, Teams, etc.)
- `GET /api/channels/instances/{id}` — Get instance details
- `PATCH /api/channels/instances/{id}` — Update instance config
- `DELETE /api/channels/instances/{id}` — Delete instance
- `GET /api/channels/instances/{id}/messages` — Get channel messages
- `POST /api/channels/instances/{id}/send` — Send message to channel

#### Memory (memory.py)
- `GET /api/memory?project_id={id}` — Get memory for project
- `POST /api/memory` — Store memory record
- `PATCH /api/memory/{id}` — Update memory
- `DELETE /api/memory/{id}` — Delete memory

#### Interfaces (interfaces.py)
- `GET /api/interfaces` — List interface definitions
- `POST /api/interfaces` — Register interface
- `GET /api/interfaces/status` — Get interface integration status

#### Meta-Hyperagent (meta_hyperagent.py)
- `GET /api/meta/proposals` — List pending proposals
- `POST /api/meta/proposals/{id}/confirm` — Confirm proposal
- `POST /api/meta/proposals/{id}/reject` — Reject proposal
- `GET /api/meta/overrides` — List confirmed overrides
- `GET /api/meta/status` — Get meta-hyperagent status

#### Autoresearch (autoresearch.py)
- `GET /api/autoresearch/status` — Current experiment status
- `POST /api/autoresearch/start` — Start experiment loop
- `POST /api/autoresearch/stop` — Stop experiment
- `GET /api/autoresearch/experiments` — List completed experiments
- `GET /api/autoresearch/leaderboard` — Model leaderboard from experiments

#### Loops (loops.py)
- `GET /api/loops` — List loop configurations
- `POST /api/loops` — Create loop config
- `GET /api/loops/{id}` — Get loop details
- `PATCH /api/loops/{id}` — Update loop
- `DELETE /api/loops/{id}` — Delete loop
- `POST /api/loops/{id}/execute` — Run loop immediately
- `GET /api/loops/{id}/history` — Get execution history

#### Deployments (deployments.py)
- `GET /api/deployments` — List deployments
- `POST /api/deployments` — Create deployment
- `GET /api/deployments/{id}` — Get deployment details
- `POST /api/deployments/{id}/responses` — Record participant response
- `GET /api/deployments/{id}/analytics` — Get response analytics

#### Surveys (surveys.py)
- `GET /api/surveys` — List survey integrations
- `POST /api/surveys` — Create survey integration
- `GET /api/surveys/{id}` — Get survey details
- `POST /api/surveys/{id}/sync` — Fetch responses from survey platform
- `GET /api/surveys/{id}/responses` — Get all responses

#### MCP (mcp.py)
- `GET /api/mcp/servers` — List registered MCP servers
- `POST /api/mcp/servers` — Register server
- `GET /api/mcp/servers/{id}` — Get server details
- `PATCH /api/mcp/servers/{id}` — Update server config
- `POST /api/mcp/servers/{id}/policies` — Add access policy
- `GET /api/mcp/audit-log` — Get MCP audit trail

#### Laws of UX (laws.py)
- `GET /api/laws` — List UX laws
- `GET /api/laws/{id}` — Get law details
- `POST /api/laws/{id}/match` — Find law matches in findings
- `GET /api/laws/compliance-profile` — Get project compliance radar

#### Webhooks (webhooks.py) — no `/api` prefix
- `POST /webhooks/survey` — Receive survey responses
- `POST /webhooks/channel` — Receive channel messages
- `POST /webhooks/github` — Receive GitHub events
- `POST /webhooks/figma` — Receive Figma updates
- `POST /webhooks/stripe` — Receive Stripe events (payment)

#### Health & Discovery
- `GET /api/health` — Public health check (no auth required)
- `GET /.well-known/agent.json` — A2A Protocol agent card discovery
- `POST /a2a` — A2A JSON-RPC 2.0 endpoint

#### WebSocket
- `GET /ws?token={jwt}` or `Authorization: Bearer {jwt}` — WebSocket for real-time updates (separate handler)

### Security Enforcement

**Global JWT Middleware**: Every request to `/api/*` requires valid JWT in `Authorization: Bearer <token>` header, except:
- `POST /api/auth/login` — Public (local mode issues JWT without DB)
- `POST /api/auth/register` — Public
- `GET /api/auth/team-status` — Public
- `GET /api/health` — Public
- `GET /api/settings/status` — Public
- `GET /.well-known/agent.json` — Public (A2A agent card)
- `POST /a2a` — Public (A2A Protocol JSON-RPC)
- Trailing slashes are normalized before exemption check
- `GET /.well-known/agent.json` — Public
- `/webhooks/*` — External verification (webhook signature or token)
- `/_next/*`, `/favicon`, `/static/*` — Static assets

**WebSocket**: JWT via `?token=` query parameter (browsers can't send custom headers).

**Network Security (Optional)**: If `NETWORK_ACCESS_TOKEN` is set, non-localhost requests must provide it via `X-Access-Token` header or `?token=` parameter.

### Rate Limiting

Global rate limiter (configurable per endpoint): Default 200 requests/minute.
- Can be tuned per route or globally via settings
- Respects `X-RateLimit-*` headers

---

## AGENT SYSTEM ARCHITECTURE

### System Agents (6 autonomous workers)

All agents are initialized in `backend/app/main.py::lifespan()` and run as background tasks.

#### 1. **DevOps Agent** (`backend/app/agents/devops_agent.py`)
- **Role**: `AgentRole.DEVOPS_AUDIT`
- **Capabilities**: System monitoring, performance diagnostics, resource governance
- **Executes**: DevOps-focused skills (check_system_health, monitor_resources, etc.)
- **Triggered By**: Scheduler, task assignment, heartbeat loop
- **Outputs**: Findings in DevOps scope, resource alerts

#### 2. **UI Audit Agent** (`backend/app/agents/ui_audit_agent.py`)
- **Role**: `AgentRole.UI_AUDIT`
- **Capabilities**: Visual inspection, accessibility checks, design consistency
- **Executes**: UI audit skills (accessibility_check, visual_regression, design_spec_validation)
- **Triggered By**: Design screen uploads, task assignment
- **Outputs**: UI findings, design compliance recommendations

#### 3. **UX Evaluation Agent** (`backend/app/agents/ux_eval_agent.py`)
- **Role**: `AgentRole.UX_EVALUATION`
- **Capabilities**: Usability analysis, heuristic evaluation, UX law matching
- **Executes**: UX evaluation skills (heuristic_eval, laws_of_ux_match, personas_from_data)
- **Triggered By**: User research data uploaded, task assignment
- **Outputs**: UX insights, persona definitions, UX law matches

#### 4. **User Simulation Agent** (`backend/app/agents/user_sim_agent.py`)
- **Role**: `AgentRole.USER_SIMULATION`
- **Capabilities**: User journey testing, persona-based simulation, feedback generation
- **Executes**: Simulation skills (user_journey_map, personas, scenario_testing)
- **Triggered By**: Interface definitions uploaded, task assignment
- **Outputs**: User journey findings, feedback

#### 5. **Main Orchestrator Agent** (`backend/app/core/agent.py`)
- **Role**: `AgentRole.TASK_EXECUTOR` (system, is_system=True)
- **Responsibilities**:
  - Long-running task execution loop (polls Task queue)
  - Task → Skill mapping
  - Skill execution with retries and checkpointing
  - Finding creation from skill outputs
  - Document generation from outputs
  - Task completion and reporting
- **Key State**: `_current_task_id` (for graceful shutdown)
- **Outputs**: Documents, findings, task progress updates

#### 6. **Meta Orchestrator** (`backend/app/agents/orchestrator.py`)
- **Role**: Coordination and delegation
- **Responsibilities**:
  - Agent task assignment balancing
  - Skill selection recommendation
  - Agent heartbeat monitoring
  - Error recovery and escalation
- **Outputs**: Task assignments, A2A messages

### Custom Agents (user-defined)

Loaded from database at startup (`backend/app/agents/custom_worker.py`):
- Created via `POST /api/agents`
- Each runs in a dedicated worker thread
- Inherits capabilities from Agent model definition
- Can execute any registered skill
- Stopped gracefully on shutdown

### Agent Communication

**A2A (Agent-to-Agent) Messages**:
- Model: `A2AMessage` (table: `a2a_messages`)
- Types: `consult`, `finding`, `status`, `request`, `response`
- Flow: `from_agent_id` → `to_agent_id` (null = broadcast)
- Persisted in database for audit trail
- Accessed via `POST /a2a` JSON-RPC endpoint

**Heartbeat System**:
- Each agent reports `HeartbeatStatus` (HEALTHY, DEGRADED, ERROR, STOPPED)
- Interval: `Agent.heartbeat_interval_seconds` (default 60s)
- Endpoint: `POST /api/agents/{id}/heartbeat`
- Monitored by meta orchestrator
- Published to WebSocket as `agent_status` events

---

## SKILL SYSTEM

### Skill Registry & Discovery

**Location**: `backend/app/skills/registry.py`

```python
class SkillRegistry:
    def register(skill_class: Type[BaseSkill]) -> None
    def get(name: str) -> BaseSkill | None
    def list_all() -> list[BaseSkill]
    def list_by_phase(phase: SkillPhase) -> list[BaseSkill]
    def to_dict() -> dict  # Exposed at GET /api/skills
```

### Skill Definition & Structure

**Base Skill Class**: `backend/app/skills/base.py`

```python
class BaseSkill:
    name: str
    display_name: str
    description: str
    phase: SkillPhase  # discover|define|develop|deliver
    skill_type: SkillType  # analysis|generation|retrieval|validation|transformation
    plan_prompt: str  # LLM prompt to plan execution
    execute_prompt: str  # LLM prompt to execute
    output_schema: dict  # JSON schema for outputs

    async def plan(input: SkillInput) -> str
    async def execute(input: SkillInput) -> SkillOutput
    def to_dict() -> dict
```

**Input/Output Structure**:
```python
class SkillInput:
    task_id: str
    project_id: str
    context: str  # RAG context
    documents: list[str]  # Document IDs to process
    parameters: dict  # Skill-specific params

class SkillOutput:
    status: "success" | "error" | "partial"
    findings: list[dict]  # Nuggets, facts, insights
    documents: list[dict]  # Generated documents
    error: str | None
    metadata: dict
```

### All 50+ Registered Skills

**Skill Definitions** stored in `backend/app/skills/definitions/` as JSON files (hyphenated filenames).

Loaded at startup via `backend/app/skills/registry.py::load_default_skills()`.

Can be loaded at runtime via `POST /api/skills/register?name={skill_name}`.

#### Complete Skill Registry

| Skill Name (Filename) | Phase | Type | Description |
|-------|-------|------|-------------|
| `ab-test-analysis` | deliver | analysis | Analyze A/B test results |
| `accessibility-audit` | develop | validation | Audit WCAG accessibility compliance |
| `affinity-mapping` | define | analysis | Group user research insights into themes |
| `analytics-review` | discover | analysis | Review analytics data and metrics |
| `card-sorting` | define | analysis | Analyze card sorting results |
| `cognitive-walkthrough` | develop | validation | Conduct cognitive walkthrough evaluation |
| `competitive-analysis` | discover | analysis | Analyze competitor products and strategies |
| `concept-testing` | develop | validation | Test design concepts with users |
| `contextual-inquiry` | discover | retrieval | Conduct contextual inquiry field research |
| `design-critique` | develop | analysis | Conduct design critique sessions |
| `design-decision-documentation` | deliver | generation | Document design decisions and rationale |
| `design-handoff-documentation` | deliver | generation | Create design handoff specs |
| `design-iteration-feedback` | develop | analysis | Analyze iteration feedback |
| `empathy-mapping` | define | analysis | Create empathy maps for users |
| `design-pattern-application` | develop | transformation | Apply design patterns to solutions |
| `design-specification-creation` | deliver | generation | Write detailed design specifications |
| `design-system-audit` | develop | validation | Audit design system consistency |
| `desk-research` | discover | retrieval | Conduct desk research |
| `diary-studies` | discover | retrieval | Conduct diary study research |
| `field-studies` | discover | retrieval | Conduct field study observations |
| `heuristic-evaluation` | develop | validation | Apply Nielsen's usability heuristics |
| `hmw-statements` | define | generation | Generate How-Might-We statements |
| `impact-measurement-plan` | deliver | generation | Plan impact measurement strategy |
| `information-architecture-validation` | develop | validation | Validate information architecture |
| `interaction-design-validation` | develop | validation | Validate interaction design |
| `interview-question-generator` | discover | generation | Generate interview questions |
| `journey-mapping` | define | analysis | Map user journeys |
| `jtbd-analysis` | define | analysis | Jobs-to-be-Done framework analysis |
| `kappa-thematic-analysis` | discover | analysis | Thematic analysis with inter-rater reliability |
| `longitudinal-tracking` | discover | retrieval | Conduct longitudinal tracking studies |
| `nps-analysis` | discover | analysis | Analyze NPS survey data |
| `persona-creation` | discover | generation | Create user personas |
| `prioritization-matrix` | define | analysis | Prioritize insights/recommendations |
| `prototype-feedback` | develop | analysis | Analyze prototype feedback |
| `prototype-testing` | develop | validation | Test prototypes with users |
| `regression-impact` | develop | analysis | Analyze regression impact |
| `repository-curation` | discover | retrieval | Curate research repositories |
| `research-retro` | deliver | analysis | Retrospective research analysis |
| `research-synthesis` | deliver | analysis | Synthesize research findings |
| `stakeholder-interviews` | discover | retrieval | Conduct stakeholder interviews |
| `stakeholder-presentation` | deliver | generation | Create stakeholder presentations |
| `stitch-design` | develop | transformation | Integrate Stitch design artifacts |
| `stitch-design-system` | develop | transformation | Enhance design system via Stitch |
| `stitch-enhance-prompt` | develop | transformation | Enhance prompts with Stitch context |
| `stitch-react-components` | develop | generation | Generate React components via Stitch |
| `survey-ai-detection` | discover | analysis | Detect AI-generated survey responses |
| `survey-design` | discover | generation | Design survey questionnaires |
| `survey-generator` | discover | generation | Generate survey questions |
| `sus-umux-scoring` | discover | analysis | Calculate SUS/UMUX scores |
| `task-analysis-quant` | discover | analysis | Quantitative task analysis |
| `taxonomy-generator` | define | generation | Generate research taxonomies |
| `thematic-analysis` | discover | analysis | Conduct thematic analysis |
| `tree-testing` | develop | validation | Conduct tree testing studies |
| `usability-testing` | develop | validation | Conduct usability tests |
| `user-flow-mapping` | define | analysis | Map user flows |
| `user-interviews` | discover | retrieval | Conduct user interviews |
| `ux-law-compliance` | deliver | validation | Audit UX law compliance |
| `workshop-facilitation` | define | analysis | Facilitate research workshops |

#### Legacy/Deprecated Skill Names (for reference)

These represent older naming conventions that should be migrated to hyphenated format:
- `interviews_thematic_analysis` → `thematic-analysis`
- `surveys_data_analysis` → `survey-design`
- `usability_tests_analysis` → `usability-testing`
- `field_study_synthesis` → `field-studies`
- `user_interviews_personas` → `persona-creation`
- `survey_sentiment_analysis` → `survey-ai-detection`
- `focus_group_analysis` → `interview-question-generator`
- `analytics_user_behavior` → `analytics-review`
- `personas_refinement` → `persona-creation`
- `jobs_to_be_done_analysis` → `jtbd-analysis`
- `empathy_mapping` → `affinity-mapping`
- `user_journey_mapping` → `journey-mapping`
- `design_concept_generation` → `concept-testing`
- `accessibility_evaluation` → `accessibility-audit`
- `design_systems_documentation` → `design-system-audit`
- `research_report_synthesis` → `research-synthesis`
- `stakeholder_presentation_creation` → `stakeholder-presentation`
- `design_handoff_documentation` → `design-handoff-documentation`
- `design_decision_documentation` → `design-decision-documentation`

### Skill Execution Flow

1. **Task Selection**: Main orchestrator picks task from backlog
2. **Skill Lookup**: Get skill by `Task.skill_name`
3. **Input Preparation**:
   - Fetch Task metadata (context, instructions)
   - Fetch input documents by IDs
   - Run RAG to get relevant context
   - Build `SkillInput` object
4. **Planning Phase**:
   - Call `skill.plan(input)`
   - LLM generates execution plan using `plan_prompt`
5. **Execution Phase**:
   - Call `skill.execute(input)`
   - LLM executes using `execute_prompt`
   - Validate output against `output_schema`
6. **Result Processing**:
   - Parse findings from `SkillOutput.findings`
   - Create Nugget/Fact/Insight/Recommendation records
   - Create Document records for outputs
   - Broadcast `finding_created` WebSocket event
7. **Task Completion**:
   - Move task to IN_REVIEW or DONE
   - Update `Task.progress`
   - Broadcast `task_progress` WebSocket event

### Skill Factory

**Location**: `backend/app/skills/skill_factory.py`

Dynamically creates skill classes from JSON definitions:
```python
def create_skill(
    skill_name: str,
    display: str,
    desc: str,
    phase: SkillPhase,
    skill_type: SkillType,
    plan_prompt: str,
    execute_prompt: str,
    output_schema: dict,
) -> Type[BaseSkill]
```

Enables runtime skill registration without code changes.

### Skill Performance Tracking

**Model**: `ModelSkillStats` (table: `model_skill_stats`)

Tracks:
- `model_name` × `skill_name` → success_rate, avg_execution_time, confidence_score
- Updated by autoresearch loop
- Exposed at `GET /api/skills/leaderboard`
- Used for skill recommendation

---

## COMPUTE & LLM INTEGRATION

### ComputeRegistry: Single Source of Truth

**Location**: `backend/app/core/compute_registry.py`

**Architecture**: Unified registry for ALL LLM compute resources (replaces old LLMRouter + ComputePool).

```python
class ComputeRegistry:
    _nodes: dict[str, ComputeNode]  # node_id → ComputeNode

    def register_node(node: ComputeNode) -> None
    def remove_node(node_id: str) -> None
    def remove_duplicate_network_nodes(relay_node: ComputeNode) -> None  # dedup on relay register
    def update_heartbeat(node_id: str, stats: dict) -> None
    async def check_all_health() -> dict[str, bool]  # also detects relay capabilities
    def _sorted_servers(require_tools, require_vision, min_context) -> list[ComputeNode]
    async def chat_stream(messages, model, ...) -> AsyncGenerator[str | dict, None]
    async def embed(text, model) -> list[float]
    def get_stats() -> dict  # nodes, tier, RAM, models
```

### ComputeNode Structure

```python
@dataclass
class ComputeNode:
    # Identity
    node_id: str
    name: str
    host: str  # http://localhost:1234 or http://192.168.1.100:8000
              # NOTE: for relay nodes, localhost is auto-resolved to relay's IP
    source: str  # "local" | "network" | "relay" | "browser"
    provider_type: str  # "lmstudio" | "ollama" | "openai_compat"

    # Health
    is_healthy: bool
    health_state: str
    last_health_check: float
    consecutive_failures: int
    cooldown_until: float  # Circuit breaker

    # Hardware
    ram_total_gb: float
    ram_available_gb: float
    cpu_cores: int
    cpu_load_pct: float
    gpu_name: str
    gpu_vram_mb: int

    # Models
    loaded_models: list[str]  # ["model1", "model2", ...]
    model_capabilities: dict  # {"model1": ["vision", "function_calling"]}

    # Routing
    priority: int  # 1 (highest) - 10 (lowest)
    latency_ms: float
    active_requests: int  # Current request count
    is_local: bool
    is_relay: bool

    # Connection (relay nodes)
    websocket: WebSocket | None
    last_heartbeat: float
    user_id: str
    ip_address: str
    provider_host: str
    state: str  # "idle" | "busy"
    priority_level: int
    connected_at: float
```

### Node Registration at Startup

**Sequence** (from `backend/app/main.py::lifespan()`):

1. **Local Node Registration** (line 218-237):
   ```python
   local_node = ComputeNode(
       node_id=f"local-{local_type}",  # "local-lmstudio" or "local-ollama"
       name=f"Local {local_type.title()}",
       host=settings.lmstudio_host or settings.ollama_host,
       source="local",
       provider_type=settings.llm_provider,
       priority=1,  # Highest priority
       is_local=True,
   )
   compute_registry.register_node(local_node)
   ```

2. **Network Discovery** (line 242-250):
   ```python
   from app.core.network_discovery import discover_and_register
   discovered = await discover_and_register()
   # Finds other ReClaw instances, Ollama servers, LM Studio on network
   # Auto-registers as "network" type nodes
   ```

3. **Persisted Server Loading** (line 252-257):
   ```python
   from app.core.ollama import load_persisted_servers_async
   await load_persisted_servers_async()
   # Restores manually-registered servers from LLMServer records
   ```

4. **Health Checks** (line 259-266):
   ```python
   await compute_registry.check_all_health()
   # Probes all nodes for availability
   # Populates available_models for each
   # Sets is_healthy flag
   ```

5. **Provider Detection** (line 268-324):
   ```python
   from app.core.ollama import auto_detect_provider
   await auto_detect_provider()
   # Tries configured provider first
   # Falls back to other provider if first unreachable
   # Auto-detects loaded model
   # Persists to .env
   ```

### Request Routing

**Routing Flow** (in skill execution):

```python
async def route_request(model: str, prompt: str, **kwargs):
    # 1. Filter nodes by capability (has model, is healthy)
    capable_nodes = [
        n for n in self._nodes.values()
        if n.is_healthy and model in n.loaded_models
    ]

    # 2. Score and sort (priority, latency, load)
    nodes_scored = sorted(
        capable_nodes,
        key=lambda n: (n.priority, n.latency_ms, n.active_requests)
    )

    # 3. Try each node with 3 retries
    for node in nodes_scored:
        try:
            node.active_requests += 1
            # Call node with timeout
            async for chunk in node.client.stream_generate(model, prompt, **kwargs):
                yield chunk
            node.latency_ms = ...  # Update latency
            return
        except Exception as e:
            node.consecutive_failures += 1
            if node.consecutive_failures >= 3:
                node.is_healthy = False
                node.cooldown_until = time.time() + 300  # 5 min
        finally:
            node.active_requests -= 1

    # 4. If all fail, raise error
    raise RuntimeError(f"No healthy nodes available for model={model}")
```

### LLM Client Abstraction

Three provider types share a common streaming interface:

#### 1. **LM Studio** (`backend/app/core/lmstudio.py`)
- Provider: OpenAI-compatible API
- Default host: `http://localhost:1234`
- Detected model: Probed via minimal chat request (reveals loaded model)

#### 2. **Ollama** (`backend/app/core/ollama.py`)
- Provider: Native Ollama API
- Default host: `http://localhost:11434`
- Detected model: Queried from `/api/tags`

#### 3. **OpenAI-Compatible** (e.g., vLLM, Together.ai)
- Provider: Any OpenAI-compatible API
- Detected model: From response headers

All providers implement:
```python
async def stream_generate(
    model: str,
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    **kwargs
) -> AsyncGenerator[str, None]

async def list_models() -> list[dict]
async def health() -> bool
```

### Model Capabilities Detection

**Location**: `backend/app/core/model_capabilities.py`

Analyzes model name and response patterns to detect:
- Vision support (image analysis)
- Function calling (tool use)
- Structured output (JSON mode)
- Token counting accuracy
- Context window size

Stored in `ComputeNode.model_capabilities[model_name]`.

Used for skill routing (prefer models with required capabilities).

### Configuration

**Environment Variables** (from `backend/app/config.py`):

```python
# Provider selection
llm_provider: str = "lmstudio"  # "ollama" or "lmstudio"

# Ollama
ollama_host: str = "http://localhost:11434"
ollama_model: str = "qwen3:latest"
ollama_embed_model: str = "nomic-embed-text"

# LM Studio
lmstudio_host: str = "http://localhost:1234"
lmstudio_model: str = "default"
lmstudio_embed_model: str = "default"

# Hardware constraints
resource_reserve_ram_gb: float = 4.0
resource_reserve_cpu_percent: int = 30
```

---

## FRONTEND STRUCTURE

### TypeScript Types (`frontend/src/lib/types.ts`)

All frontend types are defined in a single file for consistency:

| Type | Usage |
|------|-------|
| `Project` | Project metadata (id, name, phase) |
| `Task` | Task in Kanban (title, status, skill_name, progress) |
| `ChatMessage` | Message in chat (role, content, sources) |
| `ChatSession` | Chat conversation group (project_id, model_override, inference_preset) |
| `Document` | Project output (title, file_path, status, tags, atomic_path) |
| `Nugget` | Raw evidence (text, source, confidence) |
| `Fact` | Verified claim (text, nugget_ids[], confidence) |
| `Insight` | Pattern (text, fact_ids[], impact) |
| `Recommendation` | Action (text, insight_ids[], priority, effort, status) |
| `FindingsSummary` | Counts (nuggets, facts, insights, recommendations) |
| `CodebookVersion` | Codebook snapshot (id, version, structure_json) |
| `CodeEntry` | Individual code in codebook (id, name, description, definition) |
| `CodeApplicationType` | Code audit record (source_text, code_id, coder_type, review_status) |
| `CodebookVersionType` | Type definition for codebook versions (id, version_number, created_at) |
| `ProjectReport` | Convergence pyramid (layer 1-4, content_json, status) |
| `Agent` | Agent metadata (role, capabilities, heartbeat_status) |
| `ReclawDocument` | Document with full content (content_text, content_preview) |
| `DocumentStats` | Document analytics (word_count, chunk_count) |
| `DocumentContent` | Document full content with metadata |
| `DocumentTag` | Tag applied to documents (name, color, usage_count) |
| `ChannelInstance` | Messaging integration (platform, status) |
| `ChannelMessage` | Message from channel (content, author) |
| `ChannelConversation` | Channel thread (messages[]) |
| `ResearchDeployment` | Participant research (status, participant_count) |
| `DeploymentAnalytics` | Response metrics (response_rate, completion_rate) |
| `SurveyIntegration` | Survey platform config (platform, api_key) |
| `SurveyLink` | Survey response link (url, responses_count) |
| `MCPServerConfig` | MCP server registration (name, host, capabilities) |
| `MCPAccessPolicy` | MCP security policy (role, allowed_resources) |
| `MCPAuditEntry` | MCP action audit (action, timestamp, result) |
| `AutoresearchStatus` | Experiment progress (current_iteration, total_iterations) |
| `AutoresearchExperiment` | Completed experiment (model, skill, success_rate) |
| `AutoresearchConfig` | Loop settings (iterations, models[], skills[]) |
| `ModelSkillLeaderboard` | Performance matrix (model × skill → stats) |
| `UXLaw` | UX principle definition (name, description) |
| `LawMatch` | Finding matched to law (law_id, match_score, evidence) |
| `ComplianceProfile` | Project compliance radar (laws, matches, gaps) |
| `BackupRecord` | Backup metadata (id, timestamp, size, status) |
| `BackupConfig` | Backup settings (interval_hours, retention_count) |
| `MetaProposal` | Meta-hyperagent proposal (action, reasoning, confidence) |
| `MetaVariant` | Proposal alternative (variant_id, parameters) |
| `MetaHyperagentStatus` | Meta status (proposals_pending, confirmed_count) |
| `DAGNode` | Context DAG node (type, content, children[]) |
| `DAGHealth` | DAG analytics (total_nodes, summary_ratio) |
| `DAGExpandResult` | Expanded node details (original_summary, expanded_content) |
| `DAGGrepResult` | Search result (node_id, matches[]) |
| `InterfacesStatus` | Integration health (platform, status, last_sync) |
| `InferencePresetConfig` | LLM preset (temperature, max_tokens, context_window) |
| `ReclawUser` | User record (username, role) |
| `AppNotification` | Application notification (type, message, timestamp, read_status) |
| `WSEvent` | WebSocket event structure (type, data, timestamp) |
| `HardwareInfo` | Hardware capabilities (ram_gb, cpu_cores, gpu_name, gpu_vram_mb) |
| `ModelRecommendation` | Model recommendation (model_name, match_score, reason, capabilities) |
| `AgentCapacityCheck` | Agent capacity metrics (current_load, max_capacity, available_slots) |
| `FeaturedMCPServer` | Featured MCP server listing (id, name, description, stars) |
| `RadarChartData` | Radar chart visualization data (axes[], values[]) |
| `LoopHealthItem` | Loop execution health metric (status, last_run, success_rate) |

### API Client (`frontend/src/lib/api.ts`)

Object-oriented API client with namespaces:

```typescript
// Authentication
api.auth.login(username, password)
api.auth.register(username, password, email)
api.auth.logout()
api.auth.verify()
api.auth.refresh()
api.auth.profile()

// Projects
api.projects.list()
api.projects.get(id)
api.projects.create({name, description})
api.projects.update(id, data)
api.projects.delete(id)
api.projects.versions(id)

// Tasks
api.tasks.list(projectId?, status?)
api.tasks.create({project_id, title, skill_name, instructions, ...})
api.tasks.update(id, data)
api.tasks.move(id, status)
api.tasks.delete(id)
api.tasks.attach(taskId, documentId, "input" | "output")
api.tasks.detach(taskId, documentId, "input" | "output")

// Chat
api.chat.sessions.list()
api.chat.sessions.create({project_id, title})
api.chat.sessions.get(id)
api.chat.sessions.update(id, {model_override, inference_preset})
api.chat.sessions.delete(id)
api.chat.messages(sessionId)
api.chat.send(sessionId, message)

// Findings
api.findings.summary(projectId)
api.findings.nuggets(projectId)
api.findings.createNugget({project_id, text, source})
api.findings.facts(projectId)
api.findings.createFact({project_id, text, nugget_ids[]})
api.findings.insights(projectId)
api.findings.createInsight({project_id, text, fact_ids[]})
api.findings.recommendations(projectId)
api.findings.createRecommendation({project_id, text, insight_ids[]})

// Documents
api.documents.list(projectId)
api.documents.get(id)
api.documents.create({project_id, title, file_name})
api.documents.update(id, data)
api.documents.delete(id)
api.documents.content(id)

// Skills
api.skills.list()
api.skills.get(name)
api.skills.execute(taskId, skillName)
api.skills.leaderboard()

// Agents
api.agents.list()
api.agents.get(id)
api.agents.create({name, role, system_prompt})
api.agents.start(id)
api.agents.stop(id)

// Compute
api.compute.nodes.list()
api.compute.nodes.get(id)
api.compute.models.list()
api.compute.routingStats()

// ... and 30+ more namespaces
```

### Component Architecture

**Location**: `frontend/src/components/`

23 major component directories:

```
components/
├─ layout/
│  ├─ HomeClient.tsx          (main app router)
│  ├─ Sidebar.tsx             (navigation)
│  ├─ RightPanel.tsx          (context sidebar)
│  ├─ StatusBar.tsx           (footer)
│  └─ MobileNav.tsx           (mobile menu)
├─ chat/
│  ├─ ChatView.tsx            (chat interface)
│  ├─ ChatInput.tsx           (message input)
│  └─ MessageList.tsx         (message rendering)
├─ kanban/
│  ├─ KanbanBoard.tsx         (task board)
│  ├─ KanbanColumn.tsx        (status column)
│  └─ TaskCard.tsx            (task card)
├─ findings/
│  ├─ FindingsView.tsx        (atomic chain viewer)
│  ├─ NuggetList.tsx          (nuggets)
│  ├─ FactList.tsx            (facts)
│  ├─ InsightList.tsx         (insights)
│  └─ RecommendationList.tsx  (recommendations)
├─ codebooks/
│  ├─ CodebookManager.tsx     (codebook CRUD)
│  └─ CodeEditor.tsx          (code editor)
├─ documents/
│  ├─ DocumentsView.tsx       (document browser)
│  ├─ DocumentUpload.tsx      (file upload)
│  └─ DocumentViewer.tsx      (document preview)
├─ interviews/
│  ├─ InterviewView.tsx       (interview management)
│  └─ TranscriptAnalyzer.tsx  (transcript analysis)
├─ skills/
│  ├─ SkillsView.tsx          (skill browser)
│  └─ SkillExecutor.tsx       (skill runner)
├─ agents/
│  ├─ AgentsView.tsx          (agent dashboard)
│  ├─ AgentCard.tsx           (agent status)
│  └─ AgentCreator.tsx        (create agent)
├─ metrics/
│  ├─ MetricsView.tsx         (KPI dashboard)
│  └─ MetricsChart.tsx        (chart components)
├─ projects/
│  ├─ ProjectsList.tsx        (project list)
│  ├─ ProjectCreator.tsx      (create project)
│  ├─ ContextEditor.tsx       (project context/guardrails)
│  └─ PhaseSwitch.tsx         (Double Diamond phase selector)
├─ loops/
│  ├─ LoopsView.tsx           (loop configuration)
│  └─ LoopExecutor.tsx        (run loop)
├─ laws/
│  ├─ LawsView.tsx            (UX laws viewer)
│  └─ LawMatcher.tsx          (compliance radar)
├─ memory/
│  ├─ MemoryView.tsx          (context memory manager)
│  └─ MemoryCard.tsx          (memory item)
├─ notifications/
│  ├─ NotificationsView.tsx   (notification center)
│  └─ NotificationPrefs.tsx   (preferences)
├─ integrations/
│  ├─ IntegrationsView.tsx    (channel/survey setup)
│  └─ ChannelConfig.tsx       (channel configuration)
├─ interfaces/
│  ├─ InterfacesView.tsx      (design integration status)
│  └─ ScreenUploader.tsx      (upload screens)
├─ autoresearch/
│  ├─ AutoresearchView.tsx    (experiment loop)
│  └─ ExperimentChart.tsx     (results visualization)
├─ backup/
│  ├─ BackupView.tsx          (backup manager)
│  └─ BackupList.tsx          (backup history)
├─ meta/
│  ├─ MetaHyperagentView.tsx  (meta proposals)
│  └─ ProposalCard.tsx        (proposal reviewer)
├─ auth/
│  ├─ LoginScreen.tsx         (login form)
│  └─ RegisterScreen.tsx      (registration)
├─ onboarding/
│  ├─ OnboardingWizard.tsx    (first-run flow)
│  └─ ProjectSetup.tsx        (project setup)
├─ common/
│  ├─ SearchModal.tsx         (global search)
│  ├─ VersionHistory.tsx      (project history)
│  ├─ SettingsView.tsx        (app settings)
│  ├─ ComputePoolView.tsx     (compute node status)
│  ├─ EnsembleHealthView.tsx  (agent health dashboard)
│  ├─ ToastNotification.tsx   (toast alerts)
│  ├─ ErrorBoundary.tsx       (error handling)
│  ├─ KeyboardShortcuts.tsx   (help modal)
│  └─ Modal.tsx               (reusable modal)
```

### Zustand Stores (`frontend/src/stores/`)

14 stores manage global state:

| Store | State | Methods |
|-------|-------|---------|
| `projectStore` | projects[], currentProjectId, phase | fetchProjects, createProject, setPhase |
| `taskStore` | tasks[], filters | fetchTasks, createTask, updateTask, moveTask |
| `chatStore` | sessions[], messages[], currentSessionId | fetchSessions, sendMessage, updateSession |
| `sessionStore` | sessions[], activeSession | fetchSessions, setActive |
| `documentStore` | documents[], uploads[], processing | fetchDocuments, uploadFile, deleteDoc |
| `agentStore` | agents[], heartbeats[], statuses | fetchAgents, startAgent, stopAgent |
| `authStore` | user, token, isAuthenticated | login, register, logout, verify |
| `computeStore` | nodes[], models[], routingStats | fetchNodes, getHealth, listModels |
| `integrationsStore` | channels[], surveys[], status | fetchChannels, createChannel |
| `interfacesStore` | designs[], status, lastSync | fetchDesigns, uploadScreen |
| `lawsStore` | laws[], matches[], compliance | fetchLaws, matchLaws, getRadar |
| `loopsStore` | loops[], executions[], results | fetchLoops, createLoop, executeLoop |
| `notificationStore` | notifications[], preferences | fetchNotifications, markRead, updatePrefs |
| `autoresearchStore` | experiments[], leaderboard, status | fetchExperiments, startExperiment, getLeaderboard |

### Navigation & Routing

**Main Router** (`frontend/src/components/layout/HomeClient.tsx`):

```typescript
const activeView = useState("chat");

switch(activeView) {
  case "chat": return <ChatView />;
  case "kanban": return <KanbanBoard />;
  case "findings": return <FindingsView />;
  case "interviews": return <InterviewView />;
  case "metrics": return <MetricsView />;
  case "context": return <ContextEditor />;
  case "skills": return <SkillsView />;
  case "agents": return <AgentsView />;
  case "memory": return <MemoryView />;
  case "documents": return <DocumentsView />;
  case "loops": return <LoopsView />;
  case "integrations": return <IntegrationsView />;
  case "notifications": return <NotificationsView />;
  case "backup": return <BackupView />;
  case "meta-hyperagent": return <MetaHyperagentView />;
  case "autoresearch": return <AutoresearchView />;
  case "laws": return <LawsView />;
  case "version-history": return <VersionHistory />;
  case "settings": return <SettingsView />;
  case "compute-pool": return <ComputePoolView />;
  case "ensemble-health": return <EnsembleHealthView />;
  default: return <ChatView />;
}
```

**Sidebar Navigation** (`frontend/src/components/layout/Sidebar.tsx`):

Primary nav items:
- Projects → selectProject
- Chat → chat view
- Kanban → kanban view
- Findings → findings view
- Documents → documents view
- Skills → skills view

Secondary nav items:
- Interviews, Metrics, Context, Memory, Loops, Laws
- Integrations, Notifications, Backup, Compute Pool
- Meta-Hyperagent, Autoresearch, Version History, Settings

### Real-Time Updates

**WebSocket Connection** (initialized in chat/memory stores):

```typescript
const ws = new WebSocket(
  `ws://${API_BASE}/ws?token=${localStorage.getItem("reclaw_token")}`
);

ws.onmessage = (e) => {
  const { type, data } = JSON.parse(e.data);

  switch(type) {
    case "agent_status":
      agentStore.updateHeartbeat(data);
      break;
    case "task_progress":
      taskStore.updateProgress(data);
      break;
    case "finding_created":
      fetchFindings();
      break;
    case "document_created":
      documentStore.add(data);
      break;
    // ... handle other events
  }
};
```

---

## WEBSOCKET EVENTS & REAL-TIME COMMUNICATION

### ConnectionManager

**Location**: `backend/app/api/websocket.py`

Global singleton: `manager = ConnectionManager()`

Maintains list of connected WebSocket clients, broadcasts events to all.

```python
class ConnectionManager:
    _connections: list[WebSocket]

    async def broadcast(event_type: str, data: dict) -> None
    async def send_to(websocket: WebSocket, event_type: str, data: dict) -> None
    async def _persist_notification(event_type: str, data: dict) -> None
```

### All 16 Broadcast Event Types

| Event Type | Data Structure | Triggered By | Consumer |
|------------|---------------|-------------|----------|
| `agent_status` | `{status: str, details: str}` | Agent heartbeat | AgentStore |
| `task_progress` | `{task_id: str, progress: float, notes: str}` | Main orchestrator | TaskStore |
| `file_processed` | `{filename: str, chunks: int, project_id: str}` | File watcher | DocumentStore |
| `finding_created` | `{type: "nugget"\|"fact"\|"insight"\|"recommendation", id: str, data: dict}` | Skill executor | FindingsView |
| `resource_throttle` | `{reason: str, resources: {ram_gb: float, cpu_pct: int}}` | Resource governor | ToastNotification |
| `task_queue_update` | `{pending: int, in_progress: int, completed: int}` | Main orchestrator | StatusBar |
| `document_created` | `{id: str, title: str, project_id: str, source: str}` | Document service | DocumentStore |
| `document_updated` | `{id: str, title: str, version: int}` | Document service | DocumentStore |
| `deployment_response` | `{deployment_id: str, participant_id: str, response: dict}` | Webhook | DeploymentView |
| `deployment_finding` | `{deployment_id: str, finding_id: str, type: str}` | Deployment analyzer | FindingsView |
| `deployment_progress` | `{deployment_id: str, response_rate: float, completion_rate: float}` | Analytics | DeploymentView |
| `backup_event` | `{event: "started"\|"completed"\|"failed", backup_id: str}` | Backup manager | BackupView |
| `meta_proposal` | `{proposal_id: str, action: str, reasoning: str, confidence: float}` | Meta-hyperagent | MetaProposalView |
| `channel_status` | `{instance_id: str, status: "connected"\|"disconnected"\|"error"}` | Channel router | IntegrationsView |
| `channel_message` | `{instance_id: str, author: str, content: str, timestamp: str}` | Channel adapter | ChatView |
| `autoresearch_progress` | `{iteration: int, total: int, model: str, skill: str, status: str}` | Autoresearch loop | AutoresearchView |
| `autoresearch_complete` | `{loop_type: str, summary: {success_count, error_count, avg_time}}` | Autoresearch loop | AutoresearchView |

### Broadcast Functions

All broadcast functions follow the pattern:

```python
async def broadcast_X(param1: type, param2: type, ...) -> None:
    await manager.broadcast("event_type", {
        "field1": param1,
        "field2": param2,
        ...
    })
```

Example:
```python
async def broadcast_task_progress(task_id: str, progress: float, notes: str = "") -> None:
    await manager.broadcast("task_progress", {
        "task_id": task_id,
        "progress": progress,
        "notes": notes,
    })
```

### Notification Persistence

Every broadcast event is asynchronously persisted to `Notification` table:

```python
async def _persist_notification(event_type: str, data: dict) -> None:
    try:
        from app.services.notification_service import persist_notification
        await persist_notification(event_type, data)
    except Exception:
        pass  # Never block broadcasts
```

Allows users to retrieve missed notifications on reconnect.

---

## CONFIGURATION & SECURITY

### Environment Variables (`backend/app/config.py`)

All configuration loaded from `.env` file and environment:

**LLM Provider**:
- `LLM_PROVIDER` = "lmstudio" | "ollama"
- `OLLAMA_HOST`, `OLLAMA_MODEL`, `OLLAMA_EMBED_MODEL`
- `LMSTUDIO_HOST`, `LMSTUDIO_MODEL`, `LMSTUDIO_EMBED_MODEL`

**Database**:
- `DATABASE_URL` = "sqlite+aiosqlite:///./data/reclaw.db" or PostgreSQL URL
- `LANCE_DB_PATH` = "./data/lance_db" (vector store)

**Files**:
- `UPLOAD_DIR` = "./data/uploads"
- `PROJECTS_DIR` = "./data/projects"
- `DATA_DIR` = "./data"
- `BACKUP_DIR` = "./data/backups"

**Authentication**:
- `JWT_SECRET` = auto-generated on first run if empty
- `JWT_EXPIRE_MINUTES` = 1440 (24 hours)
- `ADMIN_USERNAME`, `ADMIN_PASSWORD` = auto-generated on first run
- `DATA_ENCRYPTION_KEY` = auto-generated on first run (for sensitive DB fields)

**Network Security**:
- `BIND_HOST` = "0.0.0.0" (network accessible) or "127.0.0.1" (localhost only)
- `NETWORK_ACCESS_TOKEN` = token required for non-localhost requests (optional)
- `CORS_ORIGINS` = comma-separated list of allowed origins

**Rate Limiting**:
- `RATE_LIMIT_ENABLED` = true
- `RATE_LIMIT_DEFAULT` = "200/minute"

**Resource Limits**:
- `RESOURCE_RESERVE_RAM_GB` = 4.0 (reserve for system)
- `RESOURCE_RESERVE_CPU_PERCENT` = 30

**Integrations**:
- `STITCH_API_KEY` (Generative AI for design)
- `FIGMA_API_TOKEN` (Design imports)

**Features**:
- `BACKUP_ENABLED` = true
- `BACKUP_INTERVAL_HOURS` = 24
- `BACKUP_RETENTION_COUNT` = 7
- `DAG_ENABLED` = true (context summarization)
- `TEAM_MODE` = false (multi-user)
- `META_HYPERAGENT_ENABLED` = false (self-modifying agent)

### Security Middleware

**Global JWT Enforcement** (`backend/app/core/security_middleware.py`):

1. **Exempt Paths** (no auth required):
   - `/api/health`
   - `/api/auth/login`
   - `/api/auth/register`
   - `/api/auth/team-status`
   - `/api/settings/status`
   - `/api/connections/validate` (connection string check)
   - `/api/connections/redeem` (connection string redemption)
   - `/.well-known/agent.json` (A2A agent card)
   - `/_next/*` (static assets)
   - `/favicon`
   - `/webhooks/*` (external verification)
   - `/a2a` prefix (A2A Protocol JSON-RPC)
   - `/` and non-`/api` paths (frontend)
   - Trailing-slash variants are normalized (e.g. `/api/auth/login/` → `/api/auth/login`)

2. **JWT Verification**:
   - Extract token from `Authorization: Bearer <token>` header
   - Verify signature with `JWT_SECRET`
   - Decode payload and attach to `request.state.user`
   - On failure: return 401 Unauthorized JSON

3. **WebSocket Authentication**:
   - Token passed as `?token=` query parameter (browsers can't send custom headers)
   - Verified before accepting connection
   - Unauth clients receive 4001 close code

### Network Security (`backend/app/core/network_security.py`)

**Optional**: If `NETWORK_ACCESS_TOKEN` is set:

1. Check if request is from localhost (127.0.0.1, ::1, localhost)
2. If non-localhost, require `X-Access-Token` header or `?token=` param
3. Token must match `NETWORK_ACCESS_TOKEN` exactly
4. Mismatch: return 403 Forbidden

### Field Encryption (`backend/app/core/field_encryption.py`)

Sensitive database fields are AES-256 encrypted at rest:

```python
# Encrypted fields (examples):
User.password_hash  # Actually just hash, no encryption
SurveyIntegration.api_key
MCPServerConfig.api_credentials
```

Key management:
- Generated on first run in `DATA_ENCRYPTION_KEY` file
- Backed up with database exports
- No master key external storage (for local-first philosophy)

### Webhook Security (`backend/app/api/routes/webhooks.py`)

External webhooks (from Stripe, Figma, survey platforms) have their own verification:

1. **Signature Verification**: Each platform provides a signature header
2. **Rate Limiting**: Per-webhook rate limits
3. **Payload Validation**: Schema validation before processing

---

## INTEGRATION POINTS

### Messaging Channels (`backend/app/channels/`)

Adapters for external messaging platforms:

| Channel | Adapter | Status |
|---------|---------|--------|
| Slack | `slack_adapter.py` | Listens for messages, posts findings |
| Microsoft Teams | `teams_adapter.py` | Same as Slack |
| Discord | `discord_adapter.py` | Same as Slack |
| Telegram | `telegram_adapter.py` | Same as Slack |
| Generic Webhook | `webhook_handler.py` | Receives POST requests |

**Flow**:
1. User creates `ChannelInstance` with platform + credentials
2. Adapter loads at startup from DB
3. Adapter connects (Slack bot token, Teams webhook, etc.)
4. Messages received → `ChannelMessage` records created
5. Findings can be posted back to channel

**Model**: `ChannelInstance`, `ChannelMessage`, `ChannelConversation`

### Design Integrations

#### Figma (`backend/app/integrations/figma.py`)
- Upload design screens from Figma (via file or API)
- Creates `DesignScreen` records with images
- Extracts text/layout information
- Linked to project findings

#### Stitch (Google Generative AI) (`backend/app/integrations/stitch.py`)
- Analyzes design screens for compliance
- UX law matching
- Accessibility violations detection
- Feeds into findings

**Models**: `DesignScreen`, `DesignBrief`, `DesignDecision`

### Survey Platforms

Adapters for survey data collection:

| Platform | Adapter | Method |
|----------|---------|--------|
| Typeform | `typeform_adapter.py` | Webhook + API polling |
| Qualtrics | `qualtrics_adapter.py` | API polling |
| SurveySparrow | `surveysparrow_adapter.py` | Webhook |
| Google Forms | `googleforms_adapter.py` | Manual upload (API limited) |

**Flow**:
1. User creates `SurveyIntegration` with platform + API key
2. Adapter syncs responses at interval (or webhook)
3. Creates `SurveyLink` records
4. Responses analyzed by survey analysis skills
5. Findings stored in atomic chain

**Model**: `SurveyIntegration`, `SurveyLink`

### Automated Research Deployment

**Model**: `ResearchDeployment`

Allows researchers to deploy questions/tasks to participants:

1. Create deployment with participant list
2. Send to participants (via email, link, channel)
3. Participants respond
4. Responses collected in deployment
5. Auto-analyzed by agents
6. Findings created

**Analytics**: Response rate, completion rate, time to completion

### Model Context Protocol (MCP) (`backend/app/api/routes/mcp.py`)

Integration with external tool servers following MCP spec:

**Models**:
- `MCPServerConfig` — Server registration (name, host, capabilities)
- `MCPAccessPolicy` — Role-based access (who can use what)
- `MCPAuditEntry` — Audit trail of MCP calls

**Flow**:
1. Register MCP server via API
2. Server exposes tools (read_file, execute_script, etc.)
3. Agents can invoke tools in skills
4. All tool calls audited

---

## CRITICAL DATA FLOWS

### Flow 1: Chat Message → LLM Response

```
User sends message in ChatView
    ↓
POST /api/chat/sessions/{id}/messages
    ↓
chat_service.create_message()
    ↓
RAG: Retrieve context from documents
    ↓
build SkillInput with context
    ↓
compute_registry.route_request()
    ↓
LLM provider (local Ollama or LM Studio)
    ↓
Stream response chunks
    ↓
Create Message record (role=assistant)
    ↓
broadcast_task_progress() WebSocket event
    ↓
Frontend receives update, renders response in ChatView
```

### Flow 2: Task Execution → Skill → Findings

```
User creates Task in KanbanBoard
    ↓
POST /api/tasks
    ↓
Task record created (status=backlog)
    ↓
Main orchestrator picks task
    ↓
Get Skill by Task.skill_name
    ↓
Fetch input documents (from Task.input_document_ids[])
    ↓
RAG: Retrieve context
    ↓
Build SkillInput
    ↓
skill.plan() → LLM generates plan
    ↓
skill.execute() → LLM executes
    ↓
Validate output against output_schema
    ↓
Parse findings from SkillOutput
    ↓
For each finding:
  ├─ Create Nugget/Fact/Insight/Recommendation record
  ├─ Link to Project
  └─ broadcast_finding_created() WebSocket event
    ↓
Create Document record for outputs
    ↓
Move Task to in_review or done
    ↓
broadcast_task_progress() WebSocket event
    ↓
Frontend updates Kanban board, displays findings
```

### Flow 3: File Upload → Processing → Indexing

```
User uploads file in DocumentUpload
    ↓
POST /api/files/upload?project_id={id}
    ↓
file_processor.process()
    ↓
Detect file type (PDF, DOCX, TXT, etc.)
    ↓
Extract text content
    ↓
Split into chunks (rag_chunk_size=1200, overlap=180)
    ↓
Embed chunks (using ollama_embed_model)
    ↓
Store in LanceDB vector store
    ↓
Create Document record (status=ready)
    ↓
Store content_text for full-text search
    ↓
broadcast_file_processed() WebSocket event
    ↓
broadcast_document_created() WebSocket event
    ↓
Frontend adds document to DocumentStore, displays in UI
```

### Flow 4: Finding → CodeApplication → ProjectReport

```
Finding created (Nugget/Fact/Insight/Recommendation)
    ↓
Agent extracts relevant codes from Codebook
    ↓
For each applicable code:
  ├─ Create CodeApplication record
  ├─ source_text = finding text
  ├─ code_id = code from codebook
  ├─ coder_id = agent ID
  ├─ confidence = 0.0-1.0
  └─ review_status = pending
    ↓
User reviews CodeApplications
    ↓
PATCH /api/code-applications/{id} (review_status=approved)
    ↓
aggregate_report_manager.build()
    ↓
For each study method/scope:
  ├─ Gather all approved code applications
  ├─ Group by code category
  ├─ Create ProjectReport (layer=L2 analysis)
    ↓
Findings triangulated across methods
    ↓
Create ProjectReport (layer=L3 synthesis)
    ↓
Final report synthesized (layer=L4)
    ↓
Export to PDF/DOCX
```

### Flow 5: Agent Heartbeat → Status Broadcast

```
Agent running (e.g., DevOps Agent)
    ↓
Every heartbeat_interval_seconds (default 60)
    ↓
POST /api/agents/{id}/heartbeat
    ↓
Update Agent.last_heartbeat_at
    ↓
Update Agent.heartbeat_status (healthy/degraded/error/stopped)
    ↓
broadcast_agent_status() WebSocket event
    ↓
broadcast_task_queue_update() WebSocket event
    ↓
Frontend receives, updates AgentStore
    ↓
AgentCard displays status (green/yellow/red)
```

### Flow 6: AutoResearch Loop (Continuous Experimentation)

```
User starts autoresearch experiment
    ↓
POST /api/autoresearch/start
    ↓
For iteration=1 to N:
  ├─ For each model in config.models[]:
  │  ├─ For each skill in config.skills[]:
  │  │  ├─ Create Task with (model, skill)
  │  │  ├─ Execute task (skill on sample data)
  │  │  ├─ Measure: success_rate, execution_time, confidence
  │  │  ├─ Store result in ModelSkillStats
  │  │  └─ broadcast_autoresearch_progress()
  │  └─ End skill loop
  └─ End model loop
    ↓
Aggregate results
    ↓
Create AutoresearchExperiment record
    ↓
broadcast_autoresearch_complete()
    ↓
Frontend displays leaderboard (model × skill matrix)
```

---

## CROSS-CUTTING CONCERNS & CHANGE IMPACT MATRIX

### Scenario 1: Adding a New Model

**When you add a new LLM model** (e.g., deploy LLaMA 2):

1. **Start/Register Node**:
   - Node appears in `ComputeRegistry._nodes`
   - Health check runs (`check_all_health()`)
   - Model list populated in `ComputeNode.loaded_models`

2. **Frontend Impact**:
   - `computeStore.fetchNodes()` updates node list
   - ComputePoolView displays new node
   - Model dropdown in ChatView populates new option

3. **Routing Impact**:
   - `compute_registry.route_request(model="llama2")` routes to new node
   - Skills can now request LLaMA 2 by name
   - Performance tracked in `ModelSkillStats`

4. **Skill Impact**:
   - No code changes needed
   - Skills automatically available with new model
   - `GET /api/skills/leaderboard` shows performance data once skills execute

5. **Database Impact**:
   - New rows in `model_skill_stats` (one per skill execution)
   - Optionally: manually register in `LLMServer` if network node

**Changes Required**: None (zero code changes)

---

### Scenario 2: Adding a New Skill

**When you add a new research skill**:

1. **Create Skill Definition**:
   - Add `backend/app/skills/definitions/{skill_name}.json`
   - Define name, phase, skill_type, plan_prompt, execute_prompt, output_schema

2. **Register Skill**:
   - POST `/api/skills/register?name={skill_name}`
   - OR load at startup via `load_default_skills()`
   - Skill appears in registry

3. **Frontend Impact**:
   - `GET /api/skills` lists new skill
   - Skill appears in skill browser
   - Can be selected when creating tasks

4. **Data Model Impact**:
   - If skill creates new finding types, models already support (Nugget, Fact, Insight, Recommendation)
   - If skill needs custom fields, may need Document.tags or atomic_path extension

5. **Agent Impact**:
   - No changes needed
   - All agents can now execute new skill via `POST /api/skills/{name}/execute`

6. **Report Impact**:
   - Reports auto-include findings from new skill
   - No config needed

**Changes Required**:
- Create `{skill_name}.json` definition file
- Optionally: add skill to SCOPE_MAP in `report_manager.py` if creating specialized report sections

---

### Scenario 3: Adding a New API Route

**When you add a new endpoint** (e.g., `POST /api/research-methods`):

1. **Create Route Module**:
   - Create `backend/app/api/routes/research_methods.py`
   - Define FastAPI router with endpoints
   - Define request/response models

2. **Register Route**:
   - Import in `backend/app/main.py`
   - Add `app.include_router(research_methods.router, prefix="/api", tags=["Research Methods"])`

3. **Security Impact**:
   - Route automatically protected by `SecurityAuthMiddleware`
   - JWT required for all endpoints (except exempt paths)
   - No additional code needed

4. **Frontend Impact**:
   - Add namespace to `frontend/src/lib/api.ts`
   - Create corresponding store in `frontend/src/stores/`
   - Import store in components
   - Call API via `api.researchMethods.list()` etc.

5. **Database Impact**:
   - If using new models, register in `backend/app/models/database.py::init_db()`
   - Add ORM model file in `backend/app/models/`

6. **WebSocket Impact**:
   - If route should broadcast updates, add broadcast function in `websocket.py`
   - Frontend listens via `ws.onmessage` handler

7. **Types Impact**:
   - Add TypeScript interfaces to `frontend/src/lib/types.ts`
   - Match backend response schema exactly

**Changes Required**:
- Create route file (standard FastAPI pattern)
- Register router in main.py
- Add API client namespace
- Add TypeScript types
- Optionally: add Zustand store, WebSocket events, models

---

### Scenario 4: Adding a New WebSocket Event Type

**When you want to broadcast a new event**:

1. **Add Broadcast Function**:
   - Add to `backend/app/api/websocket.py`:
   ```python
   async def broadcast_my_event(param1: str, param2: dict) -> None:
       await manager.broadcast("my_event", {
           "field1": param1,
           "field2": param2,
       })
   ```

2. **Call from Service/Agent**:
   - Import and call in your service/agent code:
   ```python
   from app.api.websocket import broadcast_my_event
   await broadcast_my_event("value1", {...})
   ```

3. **Frontend Listener**:
   - Add handler in store's WebSocket setup:
   ```typescript
   case "my_event":
     handleMyEvent(data);
     break;
   ```

4. **Notification Persistence**:
   - Automatically persisted to `Notification` table via `_persist_notification()`
   - No additional code needed

5. **Update WebSocket Docstring**:
   - Add event type to `@router.websocket("/ws")` docstring

**Changes Required**:
- Add broadcast function in websocket.py
- Call from triggering service/agent
- Add case handler in frontend WebSocket listener

---

### Scenario 5: Adding a New Database Model

**When you need to persist a new entity type**:

1. **Create Model Class**:
   - Create file `backend/app/models/{entity}.py`
   - Define SQLAlchemy model with proper fields
   - Add `to_dict()` method for API serialization

2. **Register Model**:
   - Import in `backend/app/models/database.py::init_db()`
   - Add to imports list in `init_db()` function

3. **Create Database Table**:
   - Run `init_db()` at startup
   - Table auto-created via `Base.metadata.create_all()`
   - For production: generate Alembic migration

4. **Create Service**:
   - Create `backend/app/services/{entity}_service.py`
   - Implement CRUD methods
   - Use async/await with AsyncSession

5. **Create Routes**:
   - Create `backend/app/api/routes/{entity}.py`
   - Implement GET, POST, PATCH, DELETE endpoints
   - Returns entity via `entity.to_dict()`

6. **Frontend Types**:
   - Add interface to `frontend/src/lib/types.ts`
   - Match backend `to_dict()` exactly

7. **Frontend API Client**:
   - Add namespace to `frontend/src/lib/api.ts`
   - Implement CRUD methods

8. **Zustand Store** (optional):
   - Create `frontend/src/stores/{entity}Store.ts`
   - Manage entity state locally

**Changes Required**:
- Create model file
- Register in init_db()
- Create service file
- Create routes file
- Register router in main.py
- Add TypeScript interfaces
- Add API client namespace
- Optional: create Zustand store

---

### Scenario 6: Adding a New Finding Type

**If you need a new atomic research finding (beyond Nugget→Fact→Insight→Recommendation)**:

This is NOT recommended as the 4-layer model is designed to be comprehensive.

But if needed:

1. **Create New Model**:
   - Add to `backend/app/models/finding.py`
   - Follow same pattern as existing finding classes
   - Add FK to Project

2. **Add to Project Relationships**:
   - Update `Project.relationships` to cascade

3. **Update API Routes**:
   - Add CRUD endpoints in `backend/app/api/routes/findings.py`

4. **Update Finding Summary**:
   - Add count to `GET /api/findings/summary` response

5. **Update Frontend Types**:
   - Add interface to `frontend/src/lib/types.ts`
   - Add to FindingsSummary type

6. **Update Components**:
   - Add viewer component in `FindingsView.tsx`

---

### Change Impact Matrix

| Change Type | Database | Models | Routes | Frontend Types | API Client | Stores | WebSocket | Security | Config |
|------------|----------|--------|--------|--------------|-----------|--------|-----------|----------|--------|
| Add Model | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| Add Skill Definition | ✗ | ✗ | ✗ | ✗ | ✓ (listing) | ✗ | ✗ | ✗ | ✗ |
| Add Route | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | △ | △ | ✗ |
| Add WebSocket Event | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✗ | ✗ |
| Add Finding Type | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ |
| Add Agent | ✗ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | △ | ✓ |
| Change Model Schema | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | △ | ✗ | ✗ |
| Add Compute Node | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | △ | ✓ |
| Add Messaging Channel | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | △ | ✓ |
| Add Integration | ✗ | ✓ | ✓ | ✓ | ✓ | △ | ✓ | ✓ | ✓ |
| Change Security Policy | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |

Legend:
- ✓ = Must update
- ✗ = No impact
- △ = Optional/conditional

---

## CRITICAL MAINTENANCE CHECKLISTS

### Before Deploying Any Change

1. **Database Check**:
   - [ ] New models registered in `init_db()`
   - [ ] No breaking schema changes (use migrations for production)
   - [ ] Foreign keys properly indexed
   - [ ] Cascade deletes verified

2. **API Check**:
   - [ ] New routes registered in `main.py`
   - [ ] Request/response schemas match frontend types
   - [ ] Authentication/authorization tested
   - [ ] Error handling implemented

3. **Frontend Check**:
   - [ ] TypeScript interfaces match backend `to_dict()`
   - [ ] API client methods implemented
   - [ ] Components render without errors
   - [ ] WebSocket listeners configured

4. **Agent Check**:
   - [ ] Skills can execute without errors
   - [ ] Findings created with proper structure
   - [ ] Task completion workflow verified

5. **Test Coverage**:
   - [ ] Unit tests for new services
   - [ ] Integration tests for API routes
   - [ ] E2E tests for user workflows
   - [ ] Simulation scenarios updated

---

### Quarterly Data Health Review

1. **Orphaned Records**:
   ```sql
   SELECT * FROM tasks WHERE project_id NOT IN (SELECT id FROM projects)
   SELECT * FROM messages WHERE session_id NOT IN (SELECT id FROM chat_sessions)
   ```

2. **Index Health**:
   - [ ] All FK columns properly indexed
   - [ ] Full-text search indexes up-to-date
   - [ ] Vector store chunk counts match documents

3. **Backup Integrity**:
   - [ ] Restore from latest backup, verify completeness
   - [ ] Compare record counts across methods
   - [ ] Check encryption key rotation schedule

4. **Model Performance**:
   - [ ] `ModelSkillStats` entries > 100
   - [ ] No skills with 0% success rate (investigate)
   - [ ] Latency trends (detect model degradation)

---

## VERSION HISTORY & BACKWARD COMPATIBILITY

### Current Version Compatibility

| Component | Version | Breaking Changes |
|-----------|---------|-----------------|
| Database Schema | 0.1.0 | None (new in this version) |
| ComputeRegistry | 0.2.0 | Replaces LLMRouter (internal only) |
| Skill Factory | 0.1.0 | None |
| API Routes | 0.1.0 | None |
| WebSocket Events | 0.1.0 | None |

### Migration Path from Old Systems

If migrating from older ReClaw version:

1. **Export Data**:
   ```bash
   POST /api/settings/export → JSON dump
   ```

2. **Create New Instance**:
   - Fresh database initialization

3. **Import Data**:
   ```bash
   POST /api/settings/import-database (with JSON)
   ```

4. **Verify**:
   - Run `POST /api/settings/data-integrity`
   - Check audit logs for errors
   - Spot-check key entities

---

## APPENDIX: QUICK REFERENCE

### All 51+ Database Models (Alphabetical)

A2AMessage, Agent, AgentLoopConfig, AutoresearchExperiment, BackupRecord, ChannelConversation, ChannelInstance, ChannelMessage, ChatSession, Codebook, CodebookVersion, CodeApplication, ContextDAGNode, ContextDocument, DesignBrief, DesignDecision, DesignScreen, Document, Fact, Insight, LoopExecution, MCPAccessPolicy, MCPAuditEntry, MCPServerConfig, Message, MethodMetric, ModelSkillStats, Notification, NotificationPreference, Nugget, Project, ProjectReport, Recommendation, ResearchDeployment, ScheduledTask, SurveyIntegration, SurveyLink, Task, TaskCheckpoint, User

### All 35 API Route Modules

agents, audit, auth, autoresearch, backup, channels, chat, code_applications, codebook_versions, codebooks, compute, context_dag, deployments, documents, files, findings, interfaces, laws, llm_servers, loops, mcp, memory, meta_hyperagent, metrics, notifications, projects, reports, scheduler, sessions, settings, skills, surveys, tasks, webhooks

### All 16 WebSocket Event Types

agent_status, task_progress, file_processed, finding_created, resource_throttle, task_queue_update, document_created, document_updated, deployment_response, deployment_finding, deployment_progress, backup_event, meta_proposal, channel_status, channel_message, autoresearch_progress, autoresearch_complete

### All 53 Skills (by Phase)

**Discover** (10): interviews_thematic_analysis, surveys_data_analysis, usability_tests_analysis, field_study_synthesis, competitive_analysis, user_interviews_personas, survey_sentiment_analysis, focus_group_analysis, analytics_user_behavior, social_listening_trends

**Define** (12): personas_refinement, jobs_to_be_done_analysis, empathy_mapping, user_journey_mapping, service_blueprint_creation, problem_statement_generation, opportunity_mapping, mental_models_extraction, design_principles_synthesis, research_gap_analysis, insights_prioritization, recommendation_validation

**Develop** (15): design_concept_generation, design_iteration_feedback, prototype_testing, accessibility_evaluation, information_architecture_validation, content_strategy_optimization, design_pattern_application, interaction_design_validation, performance_optimization_analysis, responsive_design_validation, design_systems_documentation, component_testing, color_contrast_validation, typography_analysis, usability_heuristics_evaluation

**Deliver** (12): research_report_synthesis, stakeholder_presentation_creation, implementation_roadmap_generation, design_handoff_documentation, training_material_creation, design_specification_creation, metrics_framework_definition, launch_readiness_checklist, impact_measurement_plan, design_decision_documentation, lessons_learned_compilation, knowledge_transfer_planning

**Generic** (4): web_research, document_summarization, data_transformation, quality_validation

---

**END OF SYSTEM INTEGRITY GUIDE**

This guide represents the complete, current state of the ReClaw system as of 2026-03-28. Use it as the authoritative reference for:
- What exists and how it's structured
- What changes when you modify each component
- How to add new features safely
- How to validate data integrity
- How to onboard new developers

Keep this guide updated as the system evolves.
