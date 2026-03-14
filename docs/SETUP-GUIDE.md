# ReClaw — Setup Guide

Step-by-step guide to get ReClaw running on your machine.

---

## Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| Docker | 24.0+ | `docker --version` |
| Docker Compose | v2+ | `docker compose version` |
| Git | 2.30+ | `git --version` |
| 8GB RAM minimum | — | — |

**Don't have Docker?**
- macOS / Windows: [Docker Desktop](https://docs.docker.com/desktop/)
- Linux: [Docker Engine](https://docs.docker.com/engine/install/)

---

## Step 1: Clone the Repository

```bash
git clone https://github.com/henrique-simoes/ReClaw.git
cd ReClaw
```

---

## Step 2: Configure Environment

```bash
cp .env.example .env
```

Edit `.env` if you want to customize:
- `OLLAMA_MODEL` — which LLM to use (default: `qwen3:latest`)
- `RAG_CHUNK_SIZE` — text chunk size for RAG (default: `512`)
- `RAG_TOP_K` — number of RAG results (default: `5`)

Most defaults work great. No API keys needed — everything runs locally.

---

## Step 3: Create Data Directories

```bash
mkdir -p data/watch data/uploads data/projects data/lance_db
```

---

## Step 4: Start ReClaw

```bash
docker compose up
```

This will:
1. Pull the Ollama container (first run only, ~2GB)
2. Build the backend (Python/FastAPI)
3. Build the frontend (Next.js)
4. Start all services

**First run takes 3-5 minutes.** Subsequent starts are fast.

### For NVIDIA GPU users:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up
```

---

## Step 5: Download a Model

In a new terminal:

```bash
# Recommended for 8GB RAM machines:
docker exec reclaw-ollama ollama pull qwen3:latest

# Or for better quality on 16GB+ RAM:
docker exec reclaw-ollama ollama pull qwen3:7b
```

ReClaw auto-detects your hardware and recommends the best model. Check Settings in the UI.

---

## Step 6: Open ReClaw

Open your browser to:

### 🌐 http://localhost:3000

You'll see the onboarding wizard that guides you through:
1. Welcome screen
2. Creating your first project
3. Setting company/research context
4. Uploading your first research files

---

## Step 7: Start Researching!

### Quick Start Workflow

1. **Create a project** — Name it after your research study
2. **Set context** — Tell ReClaw about your company and research goals
3. **Upload files** — Drop interview transcripts, survey data, notes
4. **Chat** — Ask ReClaw to analyze your data:
   - "Analyze the interview transcripts"
   - "Create a thematic analysis"
   - "Generate personas from the research"
   - "What are the main pain points?"
5. **Review findings** — Check the Findings view for organized insights
6. **Drill down** — Click any finding to see the full evidence chain

### Key Commands in Chat

| Command | What it does |
|---------|-------------|
| "Analyze interviews" | Runs User Interviews skill |
| "Create personas" | Generates evidence-based personas |
| "Run thematic analysis" | Codes data into themes |
| "Create affinity map" | Clusters nuggets into groups |
| "Generate survey" | Creates a survey from context |
| "Run usability testing" | Analyzes usability test data |
| "Calculate SUS scores" | Computes SUS from responses |

---

## Troubleshooting

### Ollama not connecting?

```bash
# Check if Ollama container is running
docker ps | grep ollama

# Check Ollama logs
docker logs reclaw-ollama

# Restart Ollama
docker restart reclaw-ollama
```

### Models not downloading?

```bash
# Pull model directly
docker exec -it reclaw-ollama ollama pull qwen3:latest

# Check available models
docker exec reclaw-ollama ollama list
```

### Frontend not loading?

```bash
# Check frontend logs
docker logs reclaw-frontend

# Rebuild
docker compose up --build frontend
```

### Out of disk space?

```bash
# Clean Docker cache
docker system prune -a

# Check ReClaw data size
du -sh data/
```

### Performance issues?

- Close heavy apps (Figma, Chrome with many tabs)
- Check Settings > Hardware to see your resource budget
- Switch to a smaller model in Settings
- ReClaw auto-throttles when resources are low

---

## Stopping ReClaw

```bash
docker compose down
```

Your data persists in Docker volumes and the `data/` directory.

---

## Updating ReClaw

```bash
git pull
docker compose up --build
```

---

## Development Setup (Contributing)

See [CONTRIBUTING.md](../CONTRIBUTING.md) for full dev setup instructions.

```bash
# Backend (Python 3.12+)
cd backend
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

# Frontend (Node 20+)
cd frontend
npm install && npm run dev

# Ollama (local, not Docker)
ollama serve
ollama pull qwen3:latest
```

---

## Architecture Quick Reference

```
localhost:3000 (Browser)
    ↕
Next.js Frontend → FastAPI Backend → Ollama (Local LLMs)
                      ↕                   ↕
              SQLite + LanceDB      Qwen 3.5 / etc.
```

- **Frontend:** React/Next.js + Tailwind + Zustand
- **Backend:** FastAPI (async) + SQLAlchemy + LanceDB
- **LLM:** Ollama (auto-selected model based on hardware)
- **Vector Store:** LanceDB (embedded, no extra server)
- **Database:** SQLite (projects, tasks, findings)

---

*Need help? Open an issue on [GitHub](https://github.com/henrique-simoes/ReClaw/issues).*
