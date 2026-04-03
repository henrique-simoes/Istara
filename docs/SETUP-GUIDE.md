# Istara Setup Guide

> Status: Product/setup reference.
> Authority: This is not part of the canonical development-governance stack. For development workflow and architecture-preserving changes, start with `AGENT_ENTRYPOINT.md`.

## Installation Options

### Option 1: Homebrew (macOS — Recommended)

```bash
brew install --cask henrique-simoes/istara/istara
```

### Option 2: Shell One-Liner (macOS)

```bash
curl -fsSL https://raw.githubusercontent.com/henrique-simoes/Istara/main/scripts/install-istara.sh | sh
```

The shell installer is the most guided path today:
- choose **Server** or **Client** mode up front
- get a plain-language explanation of Homebrew if it must be installed
- choose **LM Studio** or **Ollama** with first-model guidance
- sync the source install to the newest published GitHub Release instead of cloning raw `main`
- save client `rcl_...` invites directly into the desktop app config
- automatically attempt to install `Istara.app` on macOS so the menu-bar companion is ready immediately

### Option 3: Native Installer

Download the latest installer from [GitHub Releases](https://github.com/henrique-simoes/Istara/releases):
- **macOS**: `Istara-YYYY.MM.DD.dmg` — drag to Applications, launch, follow the setup wizard
- **Windows**: `Istara_x64-setup.exe` — run installer, choose mode, follow wizard

All installation methods:
- Set up the desktop companion app / system tray icon for easy management
- Detect and install missing dependencies (Python 3.12, Node.js 20, Git, local LLM tooling)
- Generate security keys automatically
- Auto-check for updates on startup

### Option 2: Docker (Recommended for servers)

```bash
git clone https://github.com/henrique-simoes/Istara.git
cd Istara
cp .env.example .env
mkdir -p data
docker compose up -d

# Pull LLM model (first run only)
docker exec istara-ollama ollama pull qwen3:latest
docker exec istara-ollama ollama pull nomic-embed-text
```

### Option 3: Bare Metal (Development)

```bash
# Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev

# LLM Provider (new terminal)
lms server start   # LM Studio (recommended)
# OR: ollama serve  # Ollama
```

---

## Prerequisites

| Dependency | Required For | Version |
|-----------|-------------|---------|
| Python 3.11+ | Server (backend) | 3.12 recommended |
| Node.js 18+ | Server (frontend + relay) | 20 recommended |
| LM Studio OR Ollama | LLM inference | Latest |
| Docker 24.0+ | Containerized deployment | Optional |

---

## First Run

After first authenticated access on a fresh server, Istara shows a 6-step onboarding wizard:

1. **Welcome** — Introduction to Istara
2. **LLM Check** — Detects if Ollama or LM Studio is running
3. **Create Project** — Name your first research project
4. **Link Folder** (optional) — Point at a Google Drive, Dropbox, or local research folder
5. **Set Context** — Describe your company and research goals
6. **Upload Files** — Upload interview transcripts, survey data, etc.

If users do not see the onboarding on a genuinely fresh system, treat that as a bug. The current app logic is supposed to show onboarding whenever the authenticated system has no projects, even if the browser has stale localStorage from an older install.

---

## Team Mode

Enable multi-user collaboration:

1. Toggle Team Mode in Settings (or set `TEAM_MODE=true` in `.env`)
2. First registered user becomes admin
3. Admin generates connection strings in Settings → Connection Strings
4. Team members paste the connection string on the login page ("Join Server")

### Connection Strings

Admin generates a `rcl_...` connection string that bundles:
- Server URL and WebSocket URL
- Network access token for relay auth
- Pre-minted JWT for web UI access
- Expiry date and label

Team members paste it on the login page or in the desktop app to connect.

---

## Compute Donation

Team members can donate their local LLM compute to the server:

### Via Desktop App (Recommended)
- Install Istara in "Client Only" mode
- Paste the `rcl_...` connection string in the desktop app
- Toggle "Compute Donation" in the tray menu

### Via Browser
- Enable "Donate Compute" toggle in Settings
- Detects local LLM (LM Studio or Ollama)
- Opens WebSocket relay from browser to server

### Via CLI
```bash
cd relay && npm install
node index.mjs --connection-string rcl_...
```

---

## Production Deployment (Docker + TLS)

```bash
# Generate security keys
./scripts/generate-secrets.sh
source .env.secrets

# Configure domain
# Edit .env:
CADDY_DOMAIN=your-domain.com
CORS_ORIGINS=https://your-domain.com
NEXT_PUBLIC_API_URL=https://your-domain.com
NEXT_PUBLIC_WS_URL=wss://your-domain.com/ws

# Start with TLS
docker compose --profile production up -d
```

### Webhook URLs

| Platform | URL |
|----------|-----|
| WhatsApp | `https://domain.com/webhooks/whatsapp/{instance_id}` |
| Google Chat | `https://domain.com/webhooks/google-chat/{instance_id}` |
| SurveyMonkey | `https://domain.com/webhooks/survey/surveymonkey/{id}` |
| Typeform | `https://domain.com/webhooks/survey/typeform/{id}` |

Telegram and Slack work behind NAT (no public URL needed).

### MCP Server

Enable: `MCP_SERVER_ENABLED=true` in `.env`. External agents connect at `https://domain.com/mcp`.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Backend won't start | `docker compose logs backend` — check Ollama health |
| Blank frontend | Verify `NEXT_PUBLIC_API_URL` and `CORS_ORIGINS` match |
| "No compute nodes" | Check Compute Pool in Settings — is LLM running? |
| Webhooks not received | Check domain DNS, Caddy logs, platform webhook settings |
| Rate limiting | Adjust `RATE_LIMIT_DEFAULT=500/minute` or disable |
| JWT errors | Run `./scripts/generate-secrets.sh` and restart |
| Skills show stale % | Clear `_usage_stats.json` or restart with fresh database |
| Team mode not showing | Toggle in Settings, then refresh — `fetchMe()` restores user role |

---

## Health Checks

```bash
# Docker
docker compose ps

# Bare metal
curl http://localhost:8000/api/health
curl http://localhost:3000

# LLM
curl http://localhost:1234/v1/models   # LM Studio
curl http://localhost:11434/api/tags   # Ollama
```
