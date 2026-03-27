# MCP Integration

ReClaw supports the Model Context Protocol (MCP) as both a **server** (exposing capabilities to external agents) and a **client** (connecting to external MCP servers).

## SECURITY WARNING

The MCP Server allows external AI agents to access your local research data. This breaks ReClaw's local-only boundary. It is:
- **OFF by default** and must be explicitly enabled
- **Gated by granular access policy** with per-tool permissions
- **Fully audited** — every request is logged

## MCP Server (ReClaw as Provider)

When enabled, exposes ReClaw capabilities at `http://localhost:{port}/mcp`.

### Tools (Risk Levels)

| Tool | Risk | Default | Description |
|------|------|---------|-------------|
| `list_skills()` | LOW | ON | Skill catalog |
| `list_projects()` | LOW | ON | Project names only |
| `get_deployment_status()` | LOW | ON | Deployment progress |
| `get_findings()` | SENSITIVE | OFF | Research findings |
| `search_memory()` | SENSITIVE | OFF | RAG search |
| `execute_skill()` | HIGH | OFF | Run skills on data |
| `create_project()` | HIGH | OFF | Create new projects |
| `deploy_research()` | HIGH | OFF | Deploy to messaging |

### Access Policy

The MCPAccessPolicy controls:
- **Per-tool toggles**: Enable/disable each tool individually
- **Project scope**: Which projects are visible (none by default)
- **Rate limits**: Max skill executions per hour, max findings per request
- **Risk badges**: Visual indicators (green/amber/red) in the UI

### Audit Log

Every MCP request is logged with: timestamp, tool called, arguments, caller info, access decision (granted/denied), result summary, duration.

## MCP Client (External Servers)

Connect external MCP servers to augment ReClaw's capabilities.

### API Endpoints

**Server Management:**
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/mcp/server/status | Server status |
| POST | /api/mcp/server/toggle | Enable/disable |
| GET | /api/mcp/server/policy | Access policy |
| PATCH | /api/mcp/server/policy | Update policy |
| GET | /api/mcp/server/audit | Audit log |
| GET | /api/mcp/server/exposure | Exposure summary |

**Client Registry:**
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/mcp/clients | List servers |
| POST | /api/mcp/clients | Register server |
| DELETE | /api/mcp/clients/{id} | Remove |
| POST | /api/mcp/clients/{id}/discover | Discover tools |
| GET | /api/mcp/clients/{id}/tools | Cached tools |
| POST | /api/mcp/clients/{id}/call | Call tool |
