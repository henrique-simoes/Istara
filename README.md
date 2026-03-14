# 🐾 ReClaw

**Local-first AI agent for UX Research.**

ReClaw is an open-source research assistant that runs entirely on your machine. It helps UX researchers organize, analyze, and synthesize research findings using local LLMs — no data ever leaves your computer.

## ✨ Features

- **🤖 AI-Powered Analysis** — Process interview transcripts, surveys, analytics, and more
- **💎 Double Diamond Framework** — Organize work across Discover → Define → Develop → Deliver
- **🧬 Atomic Research** — Every insight traces back through Facts → Nuggets → Sources
- **📁 RAG on Local Files** — Ask questions about your research data with retrieval-augmented generation
- **📋 Kanban Task Board** — Direct the agent with interactive task cards
- **🔍 40 UXR Skills** — Built-in methods for qualitative and quantitative research
- **🖥️ Hardware-Aware** — Auto-detects your hardware and picks the best model configuration
- **🔒 Local-First** — Your data stays on your machine. Always.
- **🔄 Version History** — Every change is tracked, diffable, and rollbackable

## 🚀 Quick Start

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) (Docker Desktop or Docker Engine)

### One-Command Setup

```bash
git clone https://github.com/your-org/reclaw.git
cd reclaw
cp .env.example .env
docker compose up
```

Then open [http://localhost:3000](http://localhost:3000) in your browser.

On first run, ReClaw will:
1. Pull the Ollama container
2. Detect your hardware (RAM, GPU, CPU)
3. Download the recommended model (Qwen 3.5 by default)
4. Start the backend API and web UI

### Using the Install Script

```bash
curl -fsSL https://raw.githubusercontent.com/your-org/reclaw/main/scripts/install.sh | bash
```

## 🏗️ Architecture

```
Browser (localhost:3000)
    ↕
Frontend (Next.js) → Backend (FastAPI) → Ollama (Local LLMs)
                         ↕                    ↕
                    SQLite + LanceDB     Qwen 3.5 / etc.
```

- **Frontend:** Next.js with React, Tailwind CSS, shadcn/ui
- **Backend:** Python FastAPI (async), SQLAlchemy, LanceDB
- **LLM:** Ollama running Qwen 3.5 (auto-selected based on hardware)
- **Vector Store:** LanceDB (embedded, no extra server)
- **Database:** SQLite (metadata, projects, tasks, findings)

## 📊 UI Views

| View | Description |
|------|-------------|
| 💬 Chat | Conversational interface with RAG-augmented responses |
| 🔍 Findings | Research findings organized by phase with Atomic Research drill-down |
| 📋 Kanban | Task board for directing the agent |
| 🎙️ Interviews | Transcript viewer with auto-highlighted nuggets |
| 📊 Metrics | Quantitative benchmarks and trend tracking |
| 📂 Context | Editable company/project/guardrails context layers |
| 🔄 History | Version history with diffs and rollback |

## 🧩 Skills (40 UXR Methods)

### Discover
User Interviews • Contextual Inquiry • Diary Studies • Competitive Analysis • Stakeholder Interviews • Survey Design • Analytics Review • Desk Research • Ethnography • Accessibility Audit

### Define
Affinity Mapping • Persona Creation • Journey Mapping • Empathy Mapping • JTBD Analysis • Problem Statements (HMW) • User Flow Mapping • Thematic Analysis • Research Synthesis • Prioritization Matrix

### Develop
Usability Testing • Heuristic Evaluation • A/B Test Analysis • Card Sorting • Tree Testing • Concept Testing • Cognitive Walkthrough • Design Critique • Prototype Feedback • Workshop Facilitation

### Deliver
SUS/UMUX Scoring • NPS Analysis • Task Analysis • Impact Analysis • Design System Audit • Handoff Documentation • Repository Curation • Stakeholder Presentations • Research Retros • Longitudinal Tracking

## 🛠️ Development

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## 📄 License

MIT — see [LICENSE](LICENSE).

---

Built with 🐾 by the ReClaw community.
