# 🐾 ReClaw

**Local-first AI agent for UX Research.**

ReClaw is an open-source research assistant that runs entirely on your machine. It helps UX researchers organize, analyze, and synthesize research findings using local LLMs — no data ever leaves your computer.

> Think **OpenClaw meets Google NotebookLM meets Dovetail** — but running on your hardware, your models, your data.

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## ✨ Features

### 🤖 AI-Powered Research
- **45 UXR skills** — qualitative and quantitative methods across the full Double Diamond
- **Atomic Research** — every insight traces back: Recommendations → Insights → Facts → Nuggets → Sources
- **RAG on local files** — ask questions about your research data with retrieval-augmented generation
- **Self-checking** — the agent verifies its claims against source documents

### 🖥️ Beautiful Research UI
- **Chat** — conversational interface with skill execution ("analyze my interviews")
- **Findings** — organized by Double Diamond phase with evidence chain drill-down
- **Tasks** — Kanban board to direct the agent
- **Interviews** — transcript viewer with nugget extraction and tag filtering
- **Metrics** — SUS, NPS, task completion dashboards with benchmarks
- **Search** — ⌘K global search across all findings
- **Context** — editable company/project/guardrails layers
- **History** — version tracking with rollback

### 🔒 Local-First & Hardware-Aware
- **Data never leaves your machine** — everything runs locally
- **Auto-detects hardware** — picks the best model & quantization for your RAM/GPU
- **Resource governor** — won't overwhelm your machine, reserves resources for other apps
- **Docker one-command setup** — `docker compose up` and you're running

### 🧠 Multi-Agent System
- **Task Executor** — picks Kanban tasks, runs skills, stores findings
- **DevOps Audit** — monitors data integrity, system health
- **UI Audit** — heuristic evaluation, accessibility checking
- **UX Evaluation** — holistic platform experience assessment
- **User Simulation** — end-to-end API testing
- **Meta-Orchestrator** — coordinates all agents, prevents conflicts

---

## 🚀 Quick Start

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) (Docker Desktop or Docker Engine)
- 8GB RAM minimum (16GB recommended)

### One-Command Setup

```bash
git clone https://github.com/henrique-simoes/ReClaw.git
cd ReClaw
cp .env.example .env
mkdir -p data/watch data/uploads data/projects data/lance_db
docker compose up
```

Then open **http://localhost:3000** in your browser. 🎉

> First run takes 3-5 minutes to build. After that, starts in seconds.

📖 **[Full Setup Guide →](docs/SETUP-GUIDE.md)**

---

## 📸 UI Overview

| View | Description |
|------|-------------|
| 💬 **Chat** | Talk to the agent, drop files, trigger skills with natural language |
| 🔍 **Findings** | Atomic Research organized by Double Diamond phase, click-to-drill-down |
| 📋 **Tasks** | Kanban board with drag-and-drop, agent picks up and completes tasks |
| 🎙️ **Interviews** | Transcript viewer with auto-extracted nuggets, tags, and analysis |
| 📊 **Metrics** | SUS/NPS/task completion dashboards with industry benchmarks |
| 📂 **Context** | Edit company, project, and guardrails context that guides the agent |
| 🔄 **History** | Version timeline with diffs and rollback |
| ⚙️ **Settings** | Hardware info, model management, system status |

---

## 🧩 45 UXR Skills

### 💎 Discover (13 skills)
User Interviews • Contextual Inquiry • Diary Studies • Competitive Analysis • Stakeholder Interviews • Survey Design & Analysis • Analytics Review • Desk Research • Field Studies / Ethnography • Accessibility Audit • **Survey AI Response Detection** • **Survey Generator** • **Interview Question Generator**

### 💎 Define (12 skills)
Affinity Mapping • Persona Creation • Journey Mapping • Empathy Mapping • JTBD Analysis • HMW Statements • User Flow Mapping • Thematic Analysis • Research Synthesis • Prioritization Matrix • **Kappa Intercoder Thematic Analysis** • **Taxonomy Generator**

### 💎 Develop (10 skills)
Usability Testing • Heuristic Evaluation • A/B Test Analysis • Card Sorting • Tree Testing • Concept Testing • Cognitive Walkthrough • Design Critique • Prototype Feedback • Workshop Facilitation

### 💎 Deliver (10 skills)
SUS/UMUX Scoring • NPS Analysis • Task Analysis • Regression/Impact Analysis • Design System Audit • Handoff Documentation • Repository Curation • Stakeholder Presentations • Research Retros • Longitudinal Tracking

Skills follow the [OpenClaw AgentSkills standard](skills/README.md) — each is a self-contained directory with `SKILL.md`, references, and scripts.

---

## 📜 Context Hierarchy

6-level system that ensures agents never hallucinate or go off-track:

```
Level 0: Platform ──── ReClaw UXR expertise (built-in)
Level 1: Company ───── Organization, product, culture, terminology
Level 2: Product ───── Features, users, domain knowledge
Level 3: Project ───── Research questions, goals, timeline
Level 4: Task ──────── Per-task instructions from Kanban cards
Level 5: Agent ─────── Per-agent system prompts and constraints
```

Each level is user-editable and composes into the agent's working context. Higher levels override lower levels. This is the single most important quality control mechanism in ReClaw.

---

## 🏗️ Architecture

```
Browser (localhost:3000)
    ↕ HTTP/WebSocket
Frontend (Next.js + React + Tailwind)
    ↕ REST API + SSE Streaming
Backend (FastAPI + SQLAlchemy + LanceDB)
    ↕ Ollama API
Ollama (Local LLMs: Qwen 3.5, etc.)
```

| Component | Technology | Why |
|-----------|-----------|-----|
| Frontend | Next.js 14 + React + Tailwind + Zustand | Rich UI, SSR, great DX |
| Backend | FastAPI (async) + SQLAlchemy | Best AI/ML ecosystem, async, fast |
| Vector Store | LanceDB (embedded) | No extra server, low RAM footprint |
| Database | SQLite (via aiosqlite) | Zero config, reliable, local |
| LLM | Ollama | Hardware detection, multi-model, REST API |
| Embedding | nomic-embed-text (via Ollama) | Runs on CPU, tiny footprint |

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `⌘K` | Search findings |
| `⌘1` – `⌘5` | Switch views (Chat, Findings, Tasks, Interviews, Context) |
| `⌘.` | Toggle right panel |
| `?` | Show keyboard shortcuts |
| `Esc` | Close modal / cancel |
| `Enter` | Send message / confirm |

---

## 🛠️ Development

```bash
# Backend
cd backend && python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev

# Ollama
ollama serve && ollama pull qwen3:latest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📊 Project Stats

- **204+ files** across backend, frontend, skills, docs
- **14,000+ lines of code**
- **45 UXR skills** following OpenClaw standard
- **5 autonomous agents** with meta-orchestrator
- **6-level context hierarchy**
- **Real-time WebSocket** updates

---

## 🗺️ Roadmap

- [x] Core platform (chat, findings, tasks, skills)
- [x] 45 UXR skills across all Double Diamond phases
- [x] Multi-agent system with orchestrator
- [x] Context hierarchy and resource governor
- [x] Onboarding wizard
- [x] Atomic Research evidence chains
- [ ] URL-based routing and deep linking
- [ ] Audio playback with transcript sync
- [ ] Messaging integrations (Slack, WhatsApp, Telegram)
- [ ] Team features (auth, shared knowledge, access control)
- [ ] Native installers (dmg, exe, AppImage)
- [ ] Skill marketplace

---

## 📄 License

MIT — see [LICENSE](LICENSE).

---

Built with 🐾 by the ReClaw community.
