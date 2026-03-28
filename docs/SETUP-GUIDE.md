# ReClaw Setup Guide

## Prerequisites

- **Python 3.11+** (backend)
- **Node.js 18+** (frontend)
- **LM Studio** or **Ollama** (local LLM inference)
- **Docker 24.0+** (optional, for containerized deployment)

---

## 1. Local Development (Bare Metal)

The simplest way to run ReClaw for development.

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"

# Optional: install channel support
pip install -e ".[channels]"

# Optional: install MCP server
pip install -e ".[mcp]"

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### LLM Provider

**LM Studio** (recommended):
```bash
lms server start
```

**Ollama**:
```bash
ollama serve
ollama pull qwen3:latest
ollama pull nomic-embed-text
```

### Verify

- Frontend: http://localhost:3000
- Backend: http://localhost:8000/api/health

---

## 2. Docker (Local)

```bash
git clone https://github.com/henrique-simoes/ReClaw.git
cd ReClaw
cp .env.example .env
mkdir -p data
docker compose up -d

# Pull LLM model
docker exec reclaw-ollama ollama pull qwen3:latest
docker exec reclaw-ollama ollama pull nomic-embed-text
```

### Health Checks

```bash
docker compose ps  # Shows healthy/unhealthy status
```

### GPU Support

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

### Team Mode

```bash
./scripts/generate-secrets.sh
source .env.secrets
# Set TEAM_MODE=true and DATABASE_URL in .env
docker compose --profile team up -d
```

---

## 3. Production (Docker + TLS)

For server deployment with automatic HTTPS via Caddy.

```bash
./scripts/generate-secrets.sh
source .env.secrets
```

Configure `.env`:
```
CADDY_DOMAIN=your-domain.com
CORS_ORIGINS=https://your-domain.com
NEXT_PUBLIC_API_URL=https://your-domain.com
NEXT_PUBLIC_WS_URL=wss://your-domain.com/ws
```

```bash
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

- **Backend won't start**: `docker compose logs backend` — check Ollama health
- **Blank frontend**: Verify `NEXT_PUBLIC_API_URL` and `CORS_ORIGINS` match
- **Webhooks not received**: Check domain DNS, Caddy logs, platform webhook settings
- **Rate limiting**: Adjust `RATE_LIMIT_DEFAULT=500/minute` or disable with `RATE_LIMIT_ENABLED=false`
- **JWT errors**: Secret auto-generates on first run. If `.env` lost, regenerate with `./scripts/generate-secrets.sh`
