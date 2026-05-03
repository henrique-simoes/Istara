# Team RBAC Permission Matrix

Status: implementation contract for team-mode authorization.

This matrix follows the 2026-05-01 Planner verdict: Istara uses global RBAC for system privileges, project relationship checks for project visibility, and resource/action attributes for operation-level decisions.

## Principles

- Deny by default.
- Check authorization on the backend for every protected request.
- Use frontend role states only for UX guidance, never as the enforcement layer.
- Local mode maps to a built-in local admin identity.
- Uninvited project access returns `404` to avoid confirming project existence.
- Forbidden actions inside a visible project return `403`.
- Legacy project role `member` maps to `researcher` until stored data can be safely migrated.
- Legacy project role `admin` maps to `project_admin`.

## Roles

| Scope | Role | Meaning |
|---|---|---|
| Global | `admin` | Full system administrator. Sees and manages all projects and system settings. |
| Global | `researcher` | Authenticated team user. Can work only inside invited projects. |
| Global | `viewer` | Authenticated team user. Can only observe invited projects. |
| Project | `project_admin` | Can manage project settings and project membership for one project. Cannot gain global privileges. |
| Project | `researcher` | Can perform research work inside one invited project. |
| Project | `viewer` | Can observe one invited project only. |

## Project Operations

| Operation | Global Admin | Project Admin | Researcher | Viewer | Uninvited |
|---|---:|---:|---:|---:|---:|
| List visible projects | all | invited only | invited only | invited only | not listed |
| Read project detail | yes | yes | yes | yes | `404` |
| Create project | yes | no | no | no | no |
| Update project metadata | yes | yes | no | no | `404` |
| Pause/resume project | yes | yes | no | no | `404` |
| Link/unlink watch folder | yes | yes | no | no | `404` |
| Export project | yes | yes | no | no | `404` |
| Delete project | yes | no | no | no | `404`/`403` |
| List project members | yes | yes | yes | yes | `404` |
| Add/remove/change project members | yes | yes | no | no | `404`/`403` |

## Project Resource Operations

These rules apply to project-scoped routes after the project itself is visible.

| Resource/action family | Global Admin | Project Admin | Researcher | Viewer |
|---|---:|---:|---:|---:|
| Read tasks/findings/documents/interviews/reports/metrics | yes | yes | yes | yes |
| Chat/send messages | yes | yes | yes | no |
| Upload/import files | yes | yes | yes | no |
| Create/edit/delete documents | yes | yes | yes | no |
| Create/edit/delete tasks | yes | yes | yes | no |
| Drag/move Kanban cards | yes | yes | yes | no |
| Approve/request-revision task review | yes | yes | yes | no |
| Create/edit/delete findings/codebooks/code applications | yes | yes | yes | no |
| Execute skills or trigger agents | yes | yes | yes | no |
| Generate interface/design artifacts | yes | yes | yes | no |

Locked-down route families currently covered by backend tests include projects, Chat, sessions, Interfaces Design Chat, Tasks, Documents, Findings, Codebooks, Skills, Files, Metrics, MCP admin policy/client reads, connection strings, and `/api/admin/*`.

Additional route families now wired into the central policy layer include Memory, Context DAG, UX Laws compliance, Reports, Code Applications, Codebook Versions, Deployments, Agents, Context hierarchy, Channels, Surveys, Loops, Autoresearch, Notifications, Backup reads/writes, Scheduler reads/writes, and Audit routes. New project-scoped route families must use the same `require_project_access` policy before they ship.

Final inventory coverage also includes Compute Pool readouts, legacy voice-transcribe, presentation slide-instruction generation, steering queues, Meta-Hyperagent controls, Interfaces screen/Figma/handoff/mock endpoints, and settings telemetry/self-healing exports.

## Global Admin Operations

Only global admins may:

- Manage users and global roles.
- Delete projects.
- Manage remote LLM servers and network discovery.
- Manage MCP server exposure and access policy.
- Manage MCP client registries, external MCP tool discovery, and external MCP tool calls.
- Create, restore, download, delete, or configure backups.
- Read backup inventory, estimates, and verification results.
- Toggle team mode.
- Change telemetry config.
- Pause/resume all work via maintenance mode.
- Manage global schedules and global autoresearch toggles.
- Promote agents to universal scope.
- Run self-evolution promotions, agent creation proposals, system audit agents, channels, loops, and global survey integrations.
- Inspect compute pool topology/readouts and use steering queues.
- View or change Meta-Hyperagent proposals, variants, observations, and toggles.
- Access `/api/admin/*`.
- Generate user invite strings and compute donation strings.

## Connection String Types

| Token kind | Purpose | Contains JWT | Contains relay/network token | Redeemable as user |
|---|---|---:|---:|---:|
| `user_invite` | Invite a human user to Istara | yes | no | yes |
| `compute_donation` | Let a compute node connect to relay | no | yes | no |
