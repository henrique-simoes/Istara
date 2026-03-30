---
title: Istara Knowledge Base
description: Comprehensive reference of all Istara features, agents, skills, and capabilities for use by the Istara Assistant agent.
version: "2026.03.29"
---

# Istara Knowledge Base

## What Is Istara?

Istara is a **local-first, privacy-first AI agent platform for UX Research**. It runs entirely on the user's machine using local LLMs (via LM Studio or Ollama). Research data never leaves the user's computer.

**Core philosophy**: Think "OpenClaw meets Google NotebookLM meets commercial UXR platforms — but running on your hardware, your models, your data."

**Current version**: 2026.03.29 (CalVer format: YYYY.MM.DD)

---

## Installation

### System Requirements
- Python 3.11+
- Node.js 18+
- 8 GB RAM minimum (16 GB recommended for 7B+ models)
- macOS, Windows, or Linux

### LLM Provider (choose one)
- **LM Studio** (recommended): https://lmstudio.ai — GUI-based, easy model management
- **Ollama**: https://ollama.ai — CLI-based, lightweight

### Quick Setup (Source)
```bash
git clone https://github.com/henrique-simoes/Istara.git
cd Istara
cd backend && pip install -e ".[dev]" && cd ..
cd frontend && npm install && cd ..
cp .env.example .env
# Edit .env: set LLM_PROVIDER=lmstudio or LLM_PROVIDER=ollama
```

### Running
```bash
lms server start          # Start LM Studio (or: ollama serve)
python -m uvicorn app.main:app --port 8000 --app-dir backend
cd frontend && npm run dev
# Open http://localhost:3000
```

### Docker
```bash
cp .env.example .env
mkdir -p data/watch data/uploads data/projects data/lance_db
docker compose up
```

### Desktop App
Istara ships a **Tauri-based desktop application** (system tray app + setup wizard) for macOS and Windows.
- macOS: `.dmg` installer
- Windows: NSIS installer (`.exe`)
- The desktop app manages the backend process and provides a setup wizard for first-time configuration
- Available from the Releases page on GitHub

---

## The 5 AI Agents

Istara includes 5 specialized agents, each with a distinct role and personality:

### Cleo — istara-main (Task Executor)
The primary research coordinator. Executes all 53 UXR skills, synthesizes findings, and is the main conversational interface. Communicates like a senior UX researcher (10+ years experience). Delegates to specialists and never duplicates their work.

### Sentinel — istara-devops (DevOps Audit)
Monitors data integrity, system health, and performance. Runs scheduled audits, checks for orphaned references in the database, and surfaces system health issues. Also drives the skill self-evolution pipeline.

### Pixel — istara-ui-audit (UI Audit)
Runs Nielsen's 10 heuristics evaluations, WCAG accessibility audits, and design system consistency checks. Evaluates UI screenshots and design files. Flags usability issues with severity ratings.

### Sage — istara-ux-eval (UX Evaluation)
Holistic UX evaluation agent. Assesses cognitive load, user journey completeness, workflow efficiency, and platform experience quality. Provides strategic UX assessments rather than tactical bug reports.

### Echo — istara-sim (User Simulation)
End-to-end testing agent. Simulates user behavior through the UI, runs test scenarios, detects regressions, and validates that research workflows function correctly. Runs 66 numbered test scenarios.

### Agent Personas
Each agent has 4 persona files:
- **CORE.md** — Identity, personality, values, communication style
- **SKILLS.md** — Technical capabilities and methodologies
- **PROTOCOLS.md** — Behavioral rules and decision-making
- **MEMORY.md** — Persistent learnings that auto-update over time

### Custom Agents
Users can create custom agents with a name, system prompt, and capabilities. Custom agents automatically get generated persona files and participate in the same self-evolution pipeline as system agents.

---

## Self-Evolution System

Agents learn from experience and improve over time:

1. When an agent encounters an error or pattern, it records a **learning** (category: error_pattern, workflow_pattern, user_preference, or performance_note)
2. Learnings that meet promotion thresholds are automatically written into the agent's persona files:
   - ≥3 occurrences
   - ≥2 distinct project contexts
   - 30-day maturity window
   - ≥70% confidence score
   - ≥60% success rate
3. Users can review and approve proposed changes before they are applied (default mode) or enable auto-promote

---

## 53 Research Skills

Skills follow the **Double Diamond** methodology and are organized into 4 phases:

### Discover Phase (14 skills)
Understand the problem space before defining it.
- **User Interviews** — Structured 1-on-1 research conversations
- **Contextual Inquiry** — Observe users in their natural environment
- **Diary Studies** — Longitudinal self-reporting by participants
- **Competitive Analysis** — Systematic competitor evaluation
- **Stakeholder Interviews** — Internal knowledge gathering
- **Survey Design** — Questionnaire construction with bias avoidance
- **Survey Generator** — AI-assisted survey question generation
- **Survey AI Detection** — Detect AI-generated survey responses
- **Analytics Review** — Behavioral data interpretation
- **Desk Research** — Secondary research synthesis
- **Field Studies** — Ethnographic observation in context
- **Accessibility Audit** — WCAG compliance and assistive technology testing
- **Interview Question Generator** — Generate targeted interview guides
- **Channel Research Deployment** — Deploy research via Telegram/Slack channels

### Define Phase (12 skills)
Synthesize discoveries into a clear problem definition.
- **Affinity Mapping** — Cluster observations into themes
- **Persona Creation** — Evidence-based user archetype development
- **Journey Mapping** — End-to-end user experience visualization
- **Empathy Mapping** — Emotional and behavioral user profiling
- **JTBD Analysis** — Jobs-to-Be-Done framework application
- **HMW Statements** — How Might We generative framing
- **User Flow Mapping** — Task flow diagramming
- **Thematic Analysis** — Qualitative coding and theme extraction
- **Kappa Thematic Analysis** — Inter-rater reliability with Fleiss' Kappa
- **Research Synthesis** — Cross-method finding consolidation
- **Prioritization Matrix** — Impact vs. effort opportunity ranking
- **Taxonomy Generator** — Information architecture classification

### Develop Phase (10 skills)
Generate and evaluate solutions.
- **Usability Testing** — Task-based evaluation with participants
- **Heuristic Evaluation** — Nielsen's 10 heuristics expert review
- **A/B Test Analysis** — Statistical comparison of design variants
- **Card Sorting** — Information architecture validation
- **Tree Testing** — Navigation structure evaluation
- **Concept Testing** — Early-stage idea validation
- **Cognitive Walkthrough** — Step-by-step usability inspection
- **Design Critique** — Structured design review against principles
- **Prototype Feedback** — Iterative prototype evaluation
- **Workshop Facilitation** — Collaborative design session guidance

### Deliver Phase (10 skills)
Measure outcomes and communicate findings.
- **SUS/UMUX Scoring** — System Usability Scale calculation and benchmarking
- **NPS Analysis** — Net Promoter Score interpretation
- **Task Analysis (Quant)** — Completion rates, time-on-task, error rates
- **Regression/Impact Analysis** — Before/after design change measurement
- **Design System Audit** — Component library consistency review
- **Handoff Documentation** — Developer-ready specification generation
- **Repository Curation** — Research repository organization and tagging
- **Stakeholder Presentation** — Executive-ready findings packaging
- **Research Retro** — Research process retrospective
- **Longitudinal Tracking** — Trend analysis across time periods

### Skill Format (OpenClaw AgentSkills Standard)
Each skill is a self-contained directory:
```
skill-name/
├── SKILL.md       # YAML frontmatter + instructions
├── scripts/       # Optional Python scripts
├── references/    # Optional reference documents
└── assets/        # Optional templates
```

### Self-Evolving Skills
The **Skill Health Monitor** tracks execution quality. When a skill's performance drops below threshold, Istara auto-proposes prompt improvements via the Meta-Agent view.

---

## Atomic Research Evidence Chain

Every finding in Istara traces back through a 5-layer evidence chain:

```
Nugget (raw quote/observation/data point)
  → Fact (verified pattern from 2+ nuggets)
    → Insight (interpreted meaning — answers "so what?")
      → Recommendation (actionable proposal with priority/feasibility)
        → Code Application (coded qualitative evidence with full audit trail)
```

All findings are tagged with a **Double Diamond phase**: discover / define / develop / deliver.

**Convergence Pyramid** for reports: Research reports synthesize from L1 raw artifacts through L4 final deliverable.

---

## Views and Navigation

Istara has 22+ views accessible from the sidebar:

| View | Purpose |
|------|---------|
| **Chat** | Conversational research assistant — talk to Cleo, trigger skills, upload files |
| **Findings** | Atomic Research evidence chain — Nuggets, Facts, Insights, Recommendations |
| **Documents** | Uploaded files, interview transcripts, research artifacts |
| **Tasks** | Kanban board — create tasks, agent picks them up and runs skills |
| **Interviews** | Transcript viewer with nugget extraction and tag filtering |
| **UX Laws** | 40+ cognitive psychology laws mapped to findings (Fitts's Law, Hick's Law, etc.) |
| **Skills** | Browse 53 skills, edit prompts, track self-evolution, create custom skills |
| **Agents** | Manage the 5 system agents + custom agents, view heartbeat and A2A messages |
| **Memory** | Agent memory and learnings — view, search, promote, or delete learnings |
| **Interfaces** | Design system integrations (Figma, Stitch) — import screens, generate briefs |
| **Integrations** | Survey platforms (Typeform, SurveyMonkey), Slack, Telegram, channel configs |
| **Loops** | Automated recurring research tasks with cron scheduling |
| **Notifications** | Real-time activity feed with notification preferences |
| **Settings** | Hardware info, model management, LLM provider config, data management |
| **Compute Pool** | LLM compute node management — local, network, relay nodes |
| **Context** | 6-layer context hierarchy editor (platform → company → product → project → task → agent) |
| **History** | Version tracking with rollback for findings and documents |
| **Metrics** | SUS, NPS, task completion dashboards with benchmarks |
| **Autoresearch** | Automated research experiment loops |
| **Backup** | Manual and scheduled backup management |
| **Meta-Agent** | Review and approve/reject agent self-evolution proposals |
| **Ensemble Health** | Multi-model consensus validation status |

### Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| `Cmd+K` | Global search across all findings |
| `Cmd+1` to `Cmd+6` | Switch views |
| `Cmd+.` | Toggle right panel |
| `?` | Show keyboard shortcuts |
| `Esc` | Close modal / cancel |

---

## Team Mode and Connection Strings

### Team Mode
Istara supports team collaboration with authentication:
- **Local mode** (default): Single-user, no authentication required
- **Team mode**: Multi-user with JWT authentication, role-based access (admin/user)

### Connection Strings
Team members can connect to a shared Istara instance using a **connection string**. The connection string encodes the server URL and authentication token so users can paste one string to join a shared research environment.

### External Folder Linking
Projects can be linked to external folders (Google Drive sync folder, Dropbox, local directory). Istara watches the folder with a **File Watcher** and automatically ingests new or changed files into the project's knowledge base.

---

## Local-First Privacy Architecture

- All data stays on the user's machine in SQLite (structured data) and LanceDB (vector embeddings)
- No telemetry, no cloud sync, no external API calls by default
- LLM inference runs locally via LM Studio or Ollama
- **MCP Server** is OFF by default. When enabled, allows external agents to query local data with granular access policies and full audit logging
- **Channel adapters** (Telegram, Slack) receive/send messages on behalf of the user but do not expose internal research data

---

## LLM Provider Configuration

### LM Studio (Recommended)
1. Download from https://lmstudio.ai
2. Download a model (recommended: Qwen2.5-7B-Instruct or Llama-3.1-8B-Instruct)
3. Start the local server: `lms server start` or use the GUI
4. Set in `.env`: `LLM_PROVIDER=lmstudio`, `LM_STUDIO_URL=http://localhost:1234`

### Ollama
1. Install from https://ollama.ai
2. Pull a model: `ollama pull qwen3:latest`
3. Start: `ollama serve`
4. Set in `.env`: `LLM_PROVIDER=ollama`, `OLLAMA_URL=http://localhost:11434`

### Hardware Recommendations
| RAM | Recommended Model |
|-----|------------------|
| 8 GB | Qwen2.5-3B-Instruct (Q4) |
| 16 GB | Qwen2.5-7B-Instruct (Q4) or Llama-3.1-8B |
| 32 GB | Qwen2.5-14B or Mistral-7B (Q8) |
| 64 GB+ | Qwen2.5-32B or Llama-3.1-70B |

Istara auto-detects hardware and recommends appropriate models and quantization levels.

---

## Compute Pool and Relay Nodes

Istara supports **distributed compute** via relay nodes:
- Team members can donate LLM compute over outbound WebSocket connections (NAT-friendly — no inbound ports required)
- A priority queue ensures live user interactions take precedence over background work
- The **ComputeRegistry** is the single source of truth for all compute nodes (local, network, relay)
- Node health is checked automatically with failover

---

## Multi-Model Consensus Validation

Istara implements academic-grade validation for research findings:
- **Fleiss' Kappa** for categorical agreement across multiple model runs
- **Cosine similarity** for semantic agreement
- Tiered confidence thresholds: Nuggets κ≥0.70, Facts κ≥0.65, Insights κ≥0.55, Recommendations κ≥0.50
- 5 validation strategies: dual-run, adversarial review, full ensemble, Self-MoA (temperature variation), debate rounds
- Adaptive learning: tracks which strategy works best per project/skill

---

## CalVer Versioning and Auto-Updates

- Istara uses **CalVer** versioning in `YYYY.MM.DD` format (e.g., `2026.03.29`)
- The app checks for updates automatically at startup
- Before applying updates, a **pre-update backup** is created automatically
- Update channel can be configured in Settings

---

## API and Integrations

### REST API
Full REST API at `http://localhost:8000/api/` covering:
- Projects, Tasks, Findings (Nuggets/Facts/Insights/Recommendations)
- Documents, Interviews, Skills, Agents
- Channels, Surveys, Deployments
- Settings, Compute, MCP

### WebSocket
Real-time updates via WebSocket at `/ws` — covers agent status, task progress, findings creation, document changes, resource throttle events.

### MCP Server (optional)
When enabled, Istara exposes an MCP server at `http://localhost:8001/mcp` with tools: `list_skills`, `list_projects`, `get_findings`, `search_memory`, `execute_skill`, `create_project`, `deploy_research`.

### A2A Protocol
Istara exposes `/.well-known/agent.json` for A2A Protocol agent card discovery.

### Survey Integrations
- Typeform
- SurveyMonkey
- Custom webhook receiver

### Channel Integrations
- Telegram bot
- Slack bot
- Custom webhook channels

---

## Common Troubleshooting Topics

### "No models found"
- Ensure LM Studio or Ollama is running and the server is started
- Check `.env` for correct `LLM_PROVIDER`, `LM_STUDIO_URL`, or `OLLAMA_URL`
- LM Studio default: `http://localhost:1234` — Ollama default: `http://localhost:11434`

### "Backend not starting"
- Ensure Python 3.11+ is installed: `python --version`
- Install dependencies: `pip install -e ".[dev]"` from the `backend/` directory
- Check that port 8000 is not in use: `lsof -i :8000`

### "Frontend not loading"
- Ensure Node.js 18+ is installed: `node --version`
- Run `npm install` from the `frontend/` directory
- Frontend runs on port 3000 by default

### "Skills not appearing"
- Skills are auto-discovered on startup. Restart the backend after adding new skill files.
- Check that the `SKILL.md` frontmatter is valid YAML.

### "Agent stuck in WORKING state"
- Use Settings > Data Integrity to check for orphaned tasks
- Restart the agent from the Agents view
- Check the backend logs for errors

### "Database migration issues"
- Istara uses SQLite with auto-migration on startup. If the schema is out of date, restart the backend.
- For manual reset: stop the backend, delete `data/istara.db`, restart (loses all data — backup first).
