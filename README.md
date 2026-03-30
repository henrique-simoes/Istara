🇧🇷 [Leia em Português](README.pt-BR.md)

<div align="center">

# Istara

**Local-first AI for UX Research — agents that learn, evolve, and work for you.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-2026.03.29-brightgreen.svg)](VERSION)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-lightgrey.svg)](installer/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](backend/)
[![Node](https://img.shields.io/badge/node-18%2B-green.svg)](frontend/)

[**Get Started**](#quick-start) · [**Architecture**](#architecture) · [**Skills**](#53-research-skills) · [**Agents**](#5-ai-agents) · [**Contributing**](CONTRIBUTING.md)

---

*Your research data never leaves your machine. Your agents get smarter every day.*

</div>

---

## What is Istara?

Istara is a **self-evolving AI research platform** that runs entirely on your hardware. It ships with five specialized AI agents, 53 UX research skills, and a complete evidence-chain methodology — all backed by local LLM inference (LM Studio or Ollama).

There is no cloud. No subscription. No vendor lock-in. Every insight, every transcript, every finding lives in your database.

The agents improve themselves over time. Skills track their own performance. The platform learns your workflow preferences. And it gets better the more you use it.

---

## Why Istara Is Different

| Feature | Istara | Typical AI Research Tools |
|---|---|---|
| Data privacy | 100% local — data never leaves | Cloud-uploaded |
| Agent memory | Persistent, evolving personas | Stateless sessions |
| Research methodology | Atomic Research chain (Nuggets → Recommendations) | Ad-hoc |
| Skill improvement | Auto-evolving quality scores | Static prompts |
| Agent creation | Factory — create agents at runtime | Fixed set |
| UX compliance | 30 Laws of UX auditing | Not available |
| Team compute | Donate GPU capacity via WebSocket relay | Pay per API call |
| Price | Free, open source | Paid SaaS |

---

## Core Highlights

### 🧠 5 AI Agents With Persistent Identities

Meet your research team — agents with names, memories, and specializations:

| Agent | Name | Role |
|---|---|---|
| `istara-main` | **Cleo** | Primary researcher. Executes all 53 skills, leads projects, talks to you |
| `istara-devops` | **Sentinel** | Data integrity guardian. Monitors health, audits orphaned records |
| `istara-ui-audit` | **Pixel** | WCAG compliance expert. Nielsen heuristics, accessibility scoring |
| `istara-ux-eval` | **Sage** | Cognitive load analyst. User journeys, workflow friction detection |
| `istara-sim` | **Echo** | End-to-end tester. Simulates users, runs regression scenarios |

Each agent carries four persona files — **CORE.md** (identity), **SKILLS.md** (capabilities), **PROTOCOLS.md** (behavior rules), **MEMORY.md** (accumulated learnings) — and all four evolve as the agent works.

### 🔁 Agents That Create Other Agents

Istara includes an **Agent Factory**: create custom research agents at runtime through the UI, define their persona, assign skills, and they join the orchestration pipeline immediately. No code changes. No restarts.

The MetaOrchestrator coordinates all agents through an A2A messaging protocol with typed message routing.

### 📈 53 Research Skills That Self-Improve

Skills are not static prompts. Each skill:
- Has a `plan()` → `execute()` → `validate()` lifecycle
- Tracks execution quality per model × skill combination
- Surfaces a **Skill Health Monitor** score in the UI
- Auto-proposes prompt improvements when quality drops below threshold

Skills cover the full **Double Diamond** methodology:

**Discover** — User Interviews, Contextual Inquiry, Survey Design, Survey Generator, Competitive Analysis, Diary Studies, Field Studies, Analytics Review, Accessibility Audit, Desk Research, Stakeholder Interviews, Interview Question Generator, Channel Research Deployment, Survey AI Detection

**Define** — Thematic Analysis, Kappa Thematic Analysis, Affinity Mapping, Empathy Mapping, Persona Creation, Journey Mapping, HMW Statements, JTBD Analysis, Research Synthesis, Taxonomy Generator, Prioritization Matrix, User Flow Mapping

**Develop** — Usability Testing, Heuristic Evaluation, Cognitive Walkthrough, Concept Testing, Card Sorting, Tree Testing, AB Test Analysis, Design Critique, Prototype Feedback, Workshop Facilitation

**Deliver** — Design System Audit, SUS/UMUX Scoring, NPS Analysis, Stakeholder Presentation, Handoff Documentation, Regression Impact, Task Analysis Quant, Repository Curation, Research Retro, Longitudinal Tracking

### 🔗 Atomic Research Evidence Chain

Every finding is traceable from raw source to final recommendation:

```
Quote / observation (Nugget)
       ↓
Verified pattern from 2+ nuggets (Fact)
       ↓
Interpreted meaning — "so what?" (Insight)
       ↓
Actionable proposal with priority (Recommendation)
```

No insight without provenance. Every recommendation links back through the chain to the exact quote that supports it.

### 🔍 Hybrid RAG: Vector + Keyword Search

Retrieval uses a weighted blend:
- **70% vector similarity** (LanceDB embeddings)
- **30% BM25 keyword search**

This means Istara finds both semantically similar content and exact terminology matches. Switch to pure vector or pure keyword mode per-query when you need it.

### 🔒 Your Data, Your Hardware

- Local LLMs via **LM Studio** (default) or **Ollama**
- SQLite database — a single file, fully portable
- LanceDB vector store — embedded, no separate process
- MCP server is **OFF by default** — enable only when you need external agent access
- All file uploads processed locally

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      FRONTEND (Next.js 14)                   │
│   Chat · Kanban · Findings · Documents · Skills · Agents     │
│   22 views · Contextual onboarding · Dark/light mode         │
└────────────────────────┬─────────────────────────────────────┘
                         │ REST + WebSocket (16 event types)
┌────────────────────────▼─────────────────────────────────────┐
│                      BACKEND (FastAPI)                        │
│                                                              │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────┐  │
│  │ 337 REST  │ │ WebSocket │ │ MCP Server│ │ A2A Protocol│  │
│  │ endpoints │ │  Manager  │ │ (optional)│ │  Discovery  │  │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └──────┬──────┘  │
│        └─────────────┴─────────────┴───────────────┘        │
│                               │                              │
│  ┌────────────────────────────▼──────────────────────────┐   │
│  │                     CORE ENGINE                       │   │
│  │  MetaOrchestrator · Context Hierarchy (6 levels)      │   │
│  │  Hybrid RAG (LanceDB + BM25) · Prompt Compressor      │   │
│  │  Self-Evolution · Skill Health Monitor                │   │
│  │  Resource Governor · DAG Context Summarizer           │   │
│  └────────────────────────────┬──────────────────────────┘   │
│                               │                              │
│  ┌─────────────────┐  ┌───────▼──────────┐  ┌────────────┐  │
│  │  Agent Personas │  │   Data Layer     │  │  LLM Layer │  │
│  │  CORE · SKILLS  │  │  SQLite (51+     │  │ LM Studio  │  │
│  │  PROTOCOLS      │  │  models)         │  │ Ollama     │  │
│  │  MEMORY         │  │  LanceDB         │  │ Any OpenAI │  │
│  └─────────────────┘  └──────────────────┘  │ compatible │  │
│                                              └────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, React, Tailwind CSS, Zustand |
| Backend | FastAPI, Python 3.11+, async SQLAlchemy |
| Database | SQLite + aiosqlite (zero-config, ACID) |
| Vector Store | LanceDB (embedded, no server process) |
| Desktop App | Tauri v2 (system tray, process management) |
| Real-time | WebSocket — 16 broadcast event types |
| LLM Providers | LM Studio · Ollama · OpenAI-compatible APIs |
| Installers | macOS DMG · Windows NSIS EXE |

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node 18+
- [LM Studio](https://lmstudio.ai) or [Ollama](https://ollama.ai)

### Option A: Desktop App (Recommended)

Download the installer for your platform from [Releases](https://github.com/henrique-simoes/Istara/releases):

- **macOS**: `Istara-2026.03.29.dmg`
- **Windows**: `Istara-Setup-2026.03.29.exe`

The setup wizard walks you through LLM configuration, creates your first project, and launches the system tray agent.

### Option B: Run From Source

```bash
git clone https://github.com/henrique-simoes/Istara.git
cd Istara

# Start LM Studio and load a model, then:

# Backend
cd backend
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Option C: Docker

```bash
docker-compose up
```

---

## Platform Features

### Team Mode

Share Istara across your research team with a single connection string:

```
istara://team@yourserver:8000?token=JWT_HERE
```

Paste the string in the onboarding wizard — it configures the backend URL and authenticates automatically.

### Compute Donation

Team members can donate spare GPU capacity to the shared pool. The **Compute Relay** (WebSocket-based) routes inference requests to available nodes with automatic capability detection and failover. No cloud required — your team's hardware becomes the cluster.

### Research Integrations

| Integration | What It Does |
|---|---|
| **SurveyMonkey** | Auto-deploy surveys, pull responses |
| **Google Forms** | Create and distribute forms |
| **Typeform** | Deploy conversational surveys |
| **Figma** | Extract design system tokens and decisions |
| **Google Stitch MCP** | AI-generated screen designs |
| **Slack / Telegram / WhatsApp** | Receive findings as messages |

### Document Intelligence

Drop any file into Istara — PDF, DOCX, transcript, spec:
- Auto-classifies document type
- Extracts nuggets and creates tasks
- Links findings back to source passages
- Supports folder watching for continuous ingestion
- Link external folders without copying files

### 30 Laws of UX Auditing

Run a compliance check against all 30 Laws of UX (Jakob's Law, Fitts's Law, Hick's Law, and 27 more) directly on any design or interface description. Get a scored report with evidence and recommendations.

### Contextual Onboarding

Every one of Istara's 22 views has its own onboarding flow. First time in the Skills view? A contextual guide explains what skills do and how to run one. It adapts to what you have already set up.

---

## Screenshots

<!-- TODO: Add screenshots after first public deployment -->
*Screenshots coming soon — see [docs/](docs/) for architecture diagrams.*

---

## Agent Self-Evolution: How It Works

```
User interaction
      ↓
Agent records error pattern or workflow preference
      ↓
Pattern tracked: occurrences · contexts · time
      ↓
Threshold reached: 3+ occurrences, 2+ contexts, 30 days
      ↓
Learning promoted → written into agent's MEMORY.md
      ↓
Agent persona updated permanently
      ↓
Next conversation starts with improved agent
```

This is not fine-tuning. It is structured prompt evolution — it works with any local model, including 3B parameter models on modest hardware.

---

## Skill Performance Tracking

Every skill invocation is recorded per model × skill combination:

```python
ModelSkillStats(
    model_name="llama-3.2-3b",
    skill_name="thematic_analysis",
    success_rate=0.94,
    avg_quality_score=4.2,
    execution_count=47,
    last_improvement_proposed="2026-03-15"
)
```

When quality drops below threshold, Istara surfaces an improvement proposal in the UI — a diff between the current skill prompt and the proposed revision. You approve or reject it. Skills that consistently perform well on your hardware earn a higher health score and get priority routing.

---

## MCP Server and Agent-to-Agent Protocol

Istara exposes two interoperability interfaces:

**MCP Server** (disabled by default, `http://localhost:8001/mcp` when enabled):
```
list_skills()       list_projects()     get_findings()
search_memory()     execute_skill()     deploy_research()
create_project()    get_deployment_status()
```

**A2A Protocol** discovery endpoint at `/.well-known/agent.json` — standard agent interoperability for external tools and agent frameworks.

Both are gated by granular `MCPAccessPolicy` with per-tool permissions and full audit logging.

---

## Contributing

Istara is MIT-licensed and welcomes contributions. The most impactful areas:

- **New skills** — Add a `SKILL.md` + JSON definition, no Python required for most skills
- **LLM adapters** — New local inference backends
- **Channel integrations** — Messaging platforms (Discord, Teams, etc.)
- **UI components** — Accessibility improvements, new views
- **Research methodology** — Improve prompts, add validation logic to existing skills

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions and code style guide.

```bash
# Run the test suite
pytest tests/

# Run the 66-scenario simulation agent
node tests/simulation/run.mjs

# Verify system integrity before committing
python scripts/check_integrity.py
```

---

## Repository Structure

```
istara/
├── backend/          # FastAPI backend (Python 3.11+)
│   └── app/
│       ├── api/      # 337 REST endpoints + WebSocket
│       ├── agents/   # Agent personas (CORE, SKILLS, PROTOCOLS, MEMORY)
│       ├── core/     # Orchestrator, RAG, evolution engine
│       ├── models/   # 51+ SQLAlchemy models
│       ├── services/ # Survey, MCP, channel integrations
│       └── skills/   # Skill base class, factory, implementations
├── frontend/         # Next.js 14 (React, Tailwind, Zustand)
├── desktop/          # Tauri v2 system tray app
├── installer/        # macOS DMG + Windows NSIS build configs
├── relay/            # Compute donation WebSocket relay
├── skills/           # Skill definition files (SKILL.md per skill)
├── tests/
│   └── simulation/   # 66-scenario E2E test suite
└── scripts/          # Integrity checks, agent md updates
```

---

## License

MIT © 2026 Istara Contributors — see [LICENSE](LICENSE).

---

<div align="center">

Built for researchers who believe their data should stay theirs.

[GitHub](https://github.com/henrique-simoes/Istara) · [Issues](https://github.com/henrique-simoes/Istara/issues) · [Discussions](https://github.com/henrique-simoes/Istara/discussions)

</div>
