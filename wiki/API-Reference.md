# API Reference

> Status: Public/reference API page.
> Authority: Useful as a wiki-facing reference, but not the canonical internal development source of truth. For live API inventory and change obligations, start with `AGENT_ENTRYPOINT.md`.

Istara exposes a full REST API at `http://localhost:8000/api/` plus a WebSocket endpoint for real-time updates.

All API endpoints (except auth and health) require a valid JWT in the `Authorization: Bearer <token>` header.

---

## Authentication

### Get a Token

**Local mode** (no team setup):
```
POST /api/auth/login
Body: { "username": "admin", "password": "your-password" }
Response: { "access_token": "...", "token_type": "bearer" }
```

**Team mode**: Use the same endpoint with your team credentials. Admins can create user accounts via `POST /api/auth/register`.

### Token Usage
```
Authorization: Bearer <access_token>
```

Include this header in all subsequent requests.

---

## Core Endpoints

### Health Check
```
GET /api/health
```
Public endpoint. Returns system status, version, and LLM provider connectivity.

### Settings
```
GET  /api/settings          — Get all settings
PATCH /api/settings         — Update settings
GET  /api/settings/status   — Public health check
POST /api/settings/data-integrity  — Run data integrity check
POST /api/settings/export   — Export all data as JSON
```

---

## Projects

```
GET    /api/projects                    — List all projects
POST   /api/projects                    — Create project
GET    /api/projects/{id}               — Get project details
PATCH  /api/projects/{id}               — Update project
DELETE /api/projects/{id}               — Delete project (cascades to all data)
GET    /api/projects/{id}/stats         — Get project statistics
POST   /api/projects/{id}/pause         — Pause project
POST   /api/projects/{id}/resume        — Resume project
PATCH  /api/projects/{id}/watch-folder  — Link external folder
```

**Create project example**:
```json
POST /api/projects
{
  "name": "Mobile App Research 2026",
  "description": "Usability study for the new checkout flow"
}
```

---

## Tasks (Kanban)

```
GET    /api/tasks?project_id={id}            — List tasks for project
POST   /api/tasks                            — Create task
GET    /api/tasks/{id}                       — Get task details
PATCH  /api/tasks/{id}                       — Update task (status, priority, etc.)
DELETE /api/tasks/{id}                       — Delete task
POST   /api/tasks/{id}/attach                — Attach document (direction=input|output)
POST   /api/tasks/{id}/detach                — Detach document
GET    /api/tasks/{id}/checkpoints           — Get recovery checkpoints
```

**Create task example**:
```json
POST /api/tasks
{
  "project_id": "abc123",
  "title": "Analyze P03 interview transcript",
  "description": "Run thematic analysis on the checkout flow interview",
  "priority": "high",
  "skill_name": "thematic-analysis",
  "input_document_ids": ["doc456"],
  "urls": []
}
```

**Task status values**: `backlog`, `in_progress`, `review`, `done`
**Priority values**: `critical`, `high`, `medium`, `low`

---

## Findings (Atomic Research Chain)

### Nuggets
```
GET    /api/findings/nuggets?project_id={id}   — List nuggets
POST   /api/findings/nuggets                   — Create nugget
GET    /api/findings/nuggets/{id}              — Get nugget
PATCH  /api/findings/nuggets/{id}              — Update
DELETE /api/findings/nuggets/{id}              — Delete
```

### Facts
```
GET    /api/findings/facts?project_id={id}     — List facts
POST   /api/findings/facts                     — Create fact (links nugget_ids[])
GET    /api/findings/facts/{id}                — Get fact with linked nuggets
PATCH  /api/findings/facts/{id}                — Update
DELETE /api/findings/facts/{id}                — Delete
```

### Insights
```
GET    /api/findings/insights?project_id={id}  — List insights
POST   /api/findings/insights                  — Create insight (links fact_ids[])
GET    /api/findings/insights/{id}             — Get insight with full chain
PATCH  /api/findings/insights/{id}             — Update
DELETE /api/findings/insights/{id}             — Delete
```

### Recommendations
```
GET    /api/findings/recommendations?project_id={id}  — List recommendations
POST   /api/findings/recommendations                  — Create recommendation
GET    /api/findings/recommendations/{id}             — Get recommendation
PATCH  /api/findings/recommendations/{id}             — Update
DELETE /api/findings/recommendations/{id}             — Delete
```

**Create nugget example**:
```json
POST /api/findings/nuggets
{
  "project_id": "abc123",
  "content": "\"I always get confused at the payment step\" — P03, Interview 2",
  "source": "p03-interview-2.txt",
  "phase": "discover",
  "tags": ["checkout", "confusion", "payment"]
}
```

---

## Documents

```
GET    /api/documents?project_id={id}    — List documents
POST   /api/documents                    — Create document (with content)
GET    /api/documents/{id}               — Get document
PATCH  /api/documents/{id}               — Update document
DELETE /api/documents/{id}               — Delete document
```

### File Upload
```
POST /api/files/upload
Content-Type: multipart/form-data
Fields: file, project_id
```

The file watcher automatically ingests uploaded files into the vector store.

---

## Skills

```
GET  /api/skills                         — List all 53 skills
GET  /api/skills/{name}                  — Get skill definition and metadata
POST /api/skills/{name}/execute          — Execute skill on a task
POST /api/skills/register                — Register a new skill from definition
GET  /api/skills/leaderboard             — Model × skill performance matrix
GET  /api/skills/recommendations         — Recommend skills for a given context
```

**Execute skill example**:
```json
POST /api/skills/thematic-analysis/execute
{
  "task_id": "task789",
  "project_id": "abc123"
}
```

---

## Agents

```
GET    /api/agents                       — List all agents (system + custom)
POST   /api/agents                       — Create custom agent
GET    /api/agents/{id}                  — Get agent details
PATCH  /api/agents/{id}                  — Update agent config
DELETE /api/agents/{id}                  — Delete custom agent
POST   /api/agents/{id}/start            — Start agent worker
POST   /api/agents/{id}/stop             — Stop agent worker
GET    /api/agents/{id}/tasks            — List tasks assigned to this agent
GET    /api/agents/{id}/heartbeat        — Get current heartbeat status
POST   /api/agents/{id}/heartbeat        — Post heartbeat update
```

**Agent states**: `idle`, `working`, `paused`, `error`, `stopped`

---

## Chat

```
GET  /api/sessions?project_id={id}       — List chat sessions
POST /api/sessions                       — Create session
GET  /api/sessions/{id}/messages         — Get messages for session
POST /api/chat                           — Send message (returns SSE stream)
```

**Send message (SSE streaming)**:
```
POST /api/chat
{
  "project_id": "abc123",
  "session_id": "sess456",
  "content": "Run thematic analysis on the uploaded interviews"
}
```
Response is a streaming SSE response with `event: chunk` messages.

---

## Compute

```
GET    /api/compute/nodes                — List all compute nodes
POST   /api/compute/nodes                — Register new node
GET    /api/compute/nodes/{id}           — Get node details + available models
PATCH  /api/compute/nodes/{id}           — Update node config
DELETE /api/compute/nodes/{id}           — Deregister node
GET    /api/compute/nodes/{id}/health    — Get health status
POST   /api/compute/nodes/{id}/health    — Trigger health check
GET    /api/compute/models               — List all models across all nodes
GET    /api/compute/routing-stats        — Routing statistics and latencies
```

---

## Channels (Telegram / Slack)

```
GET    /api/channels/instances           — List channel integrations
POST   /api/channels/instances           — Create channel instance
GET    /api/channels/instances/{id}      — Get instance details
PATCH  /api/channels/instances/{id}      — Update instance config
DELETE /api/channels/instances/{id}      — Delete instance
GET    /api/channels/instances/{id}/messages  — Get channel messages
POST   /api/channels/instances/{id}/send — Send message to channel
```

---

## Surveys

```
GET    /api/surveys                      — List survey integrations
POST   /api/surveys                      — Create integration (Typeform, SurveyMonkey)
POST   /api/surveys/{id}/sync            — Fetch latest responses
GET    /api/surveys/{id}/responses       — Get all synced responses
```

---

## Deployments (Research Distribution)

```
GET    /api/deployments                  — List deployments
POST   /api/deployments                  — Create deployment (send to participants)
GET    /api/deployments/{id}             — Get deployment details
POST   /api/deployments/{id}/responses   — Record participant response
GET    /api/deployments/{id}/analytics   — Get response analytics
```

---

## Loops (Scheduled Tasks)

```
GET    /api/loops                        — List loop configurations
POST   /api/loops                        — Create loop (cron schedule + skill)
GET    /api/loops/{id}                   — Get loop details
PATCH  /api/loops/{id}                   — Update loop
DELETE /api/loops/{id}                   — Delete loop
POST   /api/loops/{id}/execute           — Run immediately
GET    /api/loops/{id}/history           — Get execution history
```

---

## Notifications

```
GET    /api/notifications                — List notifications
PATCH  /api/notifications/{id}           — Mark as read
DELETE /api/notifications/{id}           — Delete
PATCH  /api/notifications/preferences    — Update notification preferences
```

---

## Backup

```
GET    /api/backups                      — List backups
POST   /api/backups                      — Create manual backup
GET    /api/backups/{id}                 — Get backup metadata
POST   /api/backups/{id}/restore         — Restore from backup
DELETE /api/backups/{id}                 — Delete backup
```

---

## MCP Server Tools

When the MCP server is enabled (`http://localhost:8001/mcp`), external agents can call:

| Tool | Description |
|------|-------------|
| `list_skills()` | List all available research skills |
| `list_projects()` | List all projects |
| `get_findings(project_id)` | Get findings for a project |
| `search_memory(query)` | Search agent memory and learnings |
| `execute_skill(skill_name, task_id)` | Execute a research skill |
| `create_project(name, description)` | Create a new project |
| `deploy_research(project_id, config)` | Deploy research to participants |
| `get_deployment_status(deployment_id)` | Check deployment status |

Access to each tool is controlled by `MCPAccessPolicy` settings.

---

## WebSocket

Connect at: `ws://localhost:8000/ws?token=<jwt>`

Or with header: `Authorization: Bearer <jwt>`

### Event Types

| Event | Payload |
|-------|---------|
| `agent_status` | `{agent_id, status, current_task}` |
| `task_progress` | `{task_id, progress (0-1), stage}` |
| `file_processed` | `{filename, chunks, project_id}` |
| `finding_created` | `{type, count, project_id}` |
| `suggestion` | `{message, action_url}` |
| `resource_throttle` | `{reason, cpu_percent, ram_percent}` |
| `task_queue_update` | `{queue_depth, project_id}` |
| `document_created` | `{document_id, project_id}` |
| `document_updated` | `{document_id, project_id}` |

---

## A2A Protocol

Istara exposes standard A2A Protocol endpoints for agent-to-agent communication:

```
GET  /.well-known/agent.json   — Agent card discovery
POST /a2a                      — JSON-RPC 2.0 A2A endpoint
```

---

## Webhooks

```
POST /webhooks/survey    — Receive survey responses (Typeform, SurveyMonkey)
POST /webhooks/channel   — Receive channel messages (Telegram, Slack)
POST /webhooks/github    — Receive GitHub events
POST /webhooks/figma     — Receive Figma design updates
```

These endpoints do not require JWT authentication but validate webhook signatures.
