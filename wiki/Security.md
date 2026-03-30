# Security

Istara is designed with a **local-first, privacy-first** security model. This page documents the security architecture, authentication system, and best practices for securing your Istara installation.

---

## Core Security Model

### Local-First by Default
All data stays on your machine. Istara makes no external network calls by default:
- Research data is stored in local SQLite and LanceDB
- LLM inference runs locally via LM Studio or Ollama
- No telemetry, analytics, or usage data is transmitted
- No cloud sync, backup service, or external API

The only optional external connections are:
- LLM provider if you configure a remote API endpoint
- Telegram/Slack channel adapters (receive/send messages — do not expose research data)
- Survey platform integrations (pull data in — do not push data out)
- Auto-update checks (check for new versions — can be disabled in Settings)

---

## Authentication

### Local Mode (Default)
In local mode (single user, no team features), Istara still uses JWT for API authentication. A local admin account is created on first run. The JWT issued is valid for 24 hours and is stored in the browser's local storage.

**Default credentials**: Set via the first-run wizard or environment variables:
```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<set a strong password>
```

### Team Mode
Team mode activates full multi-user authentication:
- **JWT with configurable expiry** (default: 24 hours)
- **Role-based access control**: `admin` and `user` roles
- **User management**: Admins create and delete accounts via `POST /api/auth/register`
- **Token refresh**: Clients can refresh tokens before expiry

### JWT Implementation
- Algorithm: HS256
- Secret key: Set via `JWT_SECRET_KEY` in `.env` — generate a strong random key
- Every request to `/api/*` passes through global JWT middleware
- Public endpoints (no auth required): `POST /api/auth/login`, `POST /api/auth/register`, `GET /api/health`, `GET /api/settings/status`

### Connection Strings
Team connection strings encode the server URL and a user token in a single shareable string. They use base64 encoding and are not encrypted — treat them like passwords. Revoke them by invalidating the underlying token.

---

## API Security

### Global JWT Middleware
Every request to any `/api/*` endpoint (except those listed above) requires a valid, non-expired JWT in the `Authorization: Bearer <token>` header. Requests without a valid token receive `401 Unauthorized`.

### CORS Configuration
The backend is configured to accept requests from `http://localhost:3000` by default. In team mode, update `ALLOWED_ORIGINS` in `.env` to include any additional frontend URLs.

### Rate Limiting
Istara does not implement rate limiting by default (it's a single-user local application). In team deployments, consider putting a reverse proxy (e.g., Caddy — a `Caddyfile` is included) in front with rate limiting configured.

---

## Data Security

### Field Encryption
Sensitive fields stored in the database are encrypted at rest:
- API keys (Telegram bot tokens, Slack tokens, survey platform keys)
- Authentication tokens for external services

The encryption key is derived from `SECRET_KEY` in `.env`. **Back up your `.env` file** — if you lose the key, encrypted fields cannot be recovered.

### Data at Rest
Istara's primary database (`data/istara.db`) and vector store (`data/lance_db/`) are **not encrypted by default**. They store:
- Research findings, interview transcripts, and uploaded documents in plaintext
- Agent learnings and persona files in plaintext

**Recommendation**: For sensitive research data (healthcare, finance, legal), encrypt the disk partition where Istara data is stored using:
- **macOS**: FileVault
- **Windows**: BitLocker
- **Linux**: LUKS or VeraCrypt

### Data in Transit
In local mode (all traffic stays on localhost), no encryption is needed. In team mode, configure TLS:
1. Use the included `Caddyfile` with automatic TLS via Let's Encrypt (for internet-accessible servers)
2. Or configure your own reverse proxy (nginx, Caddy) with TLS certificates

---

## MCP Server Security

The Model Context Protocol (MCP) server is **disabled by default**. When enabled, it allows external AI agents and MCP clients (e.g., Claude Desktop) to access Istara's data.

### Access Policies
Each MCP tool has a separate access policy. Configure via Settings > Integrations > MCP, or via the API:
```
POST /api/mcp/servers/{id}/policies
{
  "tool_name": "get_findings",
  "allowed": true,
  "rate_limit_per_minute": 10
}
```

### Audit Log
Every MCP tool call is logged in `MCPAuditEntry` with:
- Timestamp
- Tool called
- Arguments passed
- Requesting agent identity
- Response status

View the audit log at: `GET /api/mcp/audit-log`

### Recommendation
Only enable MCP if you specifically need external agent access. When enabled:
- Allow only the specific tools you need (deny by default)
- Review the audit log regularly
- Disable MCP when not in active use

---

## Network Security

### Default Binding
The backend binds to `0.0.0.0:8000` by default (all network interfaces). In single-user mode, consider binding to localhost only:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Firewall Recommendations
- **Local mode**: Block port 8000 and 3000 from external network access using your OS firewall
- **Team mode (LAN)**: Allow only your internal network subnet
- **Team mode (Internet)**: Use a reverse proxy with TLS and consider VPN access

### Relay Nodes
Relay nodes connect to a coordinator over **outbound** WebSocket (NAT-friendly, no inbound ports required). The relay daemon (`relay/`) uses token-based authentication. Relay connections only carry LLM inference requests — they do not expose research data.

---

## Environment Variable Security

The `.env` file contains sensitive credentials. It is listed in `.gitignore` and must never be committed to source control.

**Critical variables to secure**:
```env
JWT_SECRET_KEY=<generate with: openssl rand -hex 32>
SECRET_KEY=<generate with: openssl rand -hex 32>
ADMIN_PASSWORD=<strong random password>
```

**Permissions**: On Unix systems, restrict `.env` file permissions:
```bash
chmod 600 .env
```

---

## Security Best Practices

### For Individual Researchers
1. Use a strong admin password (set during first run)
2. Enable disk encryption (FileVault, BitLocker) for sensitive research data
3. Keep Istara updated (auto-update creates pre-update backups)
4. Disable MCP server unless actively needed
5. Use a dedicated LLM model for research work — don't share the LM Studio instance

### For Team Deployments
1. Generate strong random secrets for `JWT_SECRET_KEY` and `SECRET_KEY`
2. Configure TLS using the included Caddyfile or your own reverse proxy
3. Bind the backend to a specific network interface rather than `0.0.0.0`
4. Enable team mode with proper role assignment (minimal admin accounts)
5. Regularly rotate connection strings and JWT secrets
6. Review MCP audit logs if MCP is enabled
7. Consider VPN access for remote team members rather than exposing Istara to the internet

### For Research with Human Participants
Istara follows research ethics principles by design:
- Participant IDs (P01, P02, etc.) are used throughout — never real names in outputs
- The system flags uploaded content that may contain PII
- All data stays local — no risk of cloud provider data exposure
- Backups are stored locally and under your control

---

## Responsible Disclosure

If you discover a security vulnerability in Istara, please report it via GitHub Issues (use the security issue template) or by contacting the maintainers directly. Do not disclose vulnerabilities publicly until they have been addressed.
