# Istara — Agent-Readable System Specification

## System Identity

**Istara** is a local-first, privacy-first AI agent for UX Research. It runs entirely on the user's machine with local LLMs (via LM Studio or Ollama), ensuring research data never leaves the user's control.

- **Version**: 2026.03.30 (CalVer)
- **License**: MIT, open source
- **Philosophy**: Local-first, privacy-first, open research methodology
- **Stack**: Next.js frontend + FastAPI backend + SQLite + LanceDB + WebSocket
- **Install**: `curl -fsSL .../install-istara.sh | bash` or `brew install --cask henrique-simoes/istara/istara`
- **Manage**: Desktop tray app (Tauri v2) or CLI (`istara start/stop/status`)

## Architecture

```
Frontend (Next.js 14+, Tailwind CSS, Zustand)
    |
    v
Backend (FastAPI, Python 3.11+)
    |
    +-- Core Engine (agent orchestrator, skills, RAG, self-evolution)
    +-- API Routes (REST + WebSocket)
    +-- Channel Adapters (Telegram, Slack, WhatsApp, Google Chat)
    +-- Services (survey platforms, MCP, deployments)
    |
    v
Data Layer
    +-- SQLite (main DB: projects, tasks, findings, agents, messages)
    +-- LanceDB (vector store: embeddings for RAG retrieval)
    +-- Filesystem (uploads, agent personas, skill definitions)
    |
    v
LLM Providers (LM Studio or Ollama — local inference)
```

## Agent System

Istara has 5 specialized agents:

| Agent | Role | Specialty |
|-------|------|-----------|
| **Cleo** (istara-main) | Task Executor | Research execution, skill invocation, user interaction |
| **Sentinel** (istara-devops) | DevOps Audit | Data integrity, system health, performance monitoring |
| **Pixel** (istara-ui-audit) | UI Audit | WCAG compliance, Nielsen heuristics, design system |
| **Sage** (istara-ux-eval) | UX Evaluation | Cognitive load, user journeys, workflow analysis |
| **Echo** (istara-sim) | User Simulation | End-to-end testing, scenario simulation, regression |

Each agent has 4 persona files: CORE.md (identity), SKILLS.md (capabilities), PROTOCOLS.md (behavior), MEMORY.md (learnings).

## Research Methodology

Istara implements the **Atomic Research** evidence chain:
- **Nuggets**: Raw evidence (quotes, observations, data points) from sources
- **Facts**: Verified patterns derived from 2+ nuggets
- **Insights**: Interpreted meanings answering "so what?"
- **Recommendations**: Actionable proposals with priority and feasibility

Research phases follow the **Double Diamond**: Discover -> Define -> Develop -> Deliver

## Security Boundaries

- **Local-only by default**: All data stays on the user's machine
- **MCP Server**: OFF by default. When enabled, allows external agents to query local data. Gated by granular MCPAccessPolicy with per-tool permissions and audit logging.
- **Channel adapters**: Send/receive messages on user's behalf but don't expose internal data
- **Survey integrations**: Pull data in (not push data out)

## Agent Interaction Guide

### Via MCP (when enabled)
External agents can connect to Istara's MCP server at `http://localhost:8001/mcp` (if enabled). Available tools depend on the user's access policy configuration.

### Via A2A Protocol
Istara exposes an A2A Protocol discovery endpoint at `/.well-known/agent.json`.

### Via REST API
Full REST API at `http://localhost:8000/api/` with endpoints for projects, tasks, findings, skills, channels, deployments, surveys, and MCP management.

## File Organization

```
backend/
  app/
    api/routes/       # FastAPI route handlers
    agents/personas/  # Agent identity files (CORE, SKILLS, PROTOCOLS, MEMORY)
    channels/         # Messaging platform adapters
    core/             # Engine: agent, RAG, embeddings, scheduler, evolution
    models/           # SQLAlchemy database models
    mcp/              # MCP server implementation
    services/         # Business logic (channels, surveys, deployments, MCP)
    skills/           # Skill base class, registry, factory, implementations
frontend/
  src/
    components/       # React components by view
    stores/           # Zustand state management
    lib/              # API client, types, utilities
skills/               # Skill definition files (SKILL.md per skill)
tests/simulation/     # Numbered test scenarios
docs/                 # Documentation
```

## Development Patterns

When adding new features, follow this pattern:
1. **Model** (`backend/app/models/`) — SQLAlchemy model with `to_dict()`
2. **Service** (`backend/app/services/`) — Business logic functions
3. **API Route** (`backend/app/api/routes/`) — FastAPI endpoints
4. **Types** (`frontend/src/lib/types.ts`) — TypeScript interfaces
5. **API Client** (`frontend/src/lib/api.ts`) — Fetch wrappers
6. **Store** (`frontend/src/stores/`) — Zustand state management
7. **Components** (`frontend/src/components/`) — React UI

Register models in `database.py`, routes in `main.py`, nav items in `Sidebar.tsx` and `HomeClient.tsx`.

## Commands

```bash
# Production (after install)
istara start          # Start backend + frontend
istara stop           # Stop both
istara status         # Show running processes + LLM connectivity

# Development (from source)
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
cd frontend && npm run dev

# LLM
lms server start      # LM Studio
ollama serve          # Ollama
```

<!-- CAPABILITIES_START -->
<!-- Auto-generated by scripts/update_agent_md.py -- DO NOT EDIT MANUALLY -->
<!-- Run: python scripts/update_agent_md.py to regenerate -->

## Capabilities Catalog

### Navigation Menu
- Chat, Findings, UX Laws, Tasks, Interviews, Documents, Context, Skills, Agents, Memory, Interfaces, Integrations, Loops, Settings, Autoresearch, Backup, Meta-Agent, Compute Pool, Ensemble Health, Project Settings, History

### Agents
- **design-lead**: Design Lead -- Istara Interface Agent
- **istara-devops**: Sentinel -- DevOps Audit Agent
- **istara-main**: Istara Research Coordinator
- **istara-sim**: Echo -- User Simulation Agent
- **istara-ui-audit**: Pixel -- UI Audit Agent
- **istara-ux-eval**: Sage -- UX Evaluation Agent

### Skills
- **Define**: Affinity Mapping, Empathy Mapping, Hmw Statements, Journey Mapping, Jtbd Analysis, Kappa Thematic Analysis, Persona Creation, Prioritization Matrix, Research Synthesis, Taxonomy Generator, Thematic Analysis, User Flow Mapping
- **Deliver**: Design System Audit, Handoff Documentation, Longitudinal Tracking, Nps Analysis, Regression Impact, Repository Curation, Research Retro, Stakeholder Presentation, Sus Umux Scoring, Task Analysis Quant
- **Develop**: Ab Test Analysis, Card Sorting, Cognitive Walkthrough, Concept Testing, Design Critique, Heuristic Evaluation, Prototype Feedback, Tree Testing, Usability Testing, Workshop Facilitation
- **Discover**: Accessibility Audit, Analytics Review, Channel Research Deployment, Competitive Analysis, Contextual Inquiry, Desk Research, Diary Studies, Field Studies, Interview Question Generator, Stakeholder Interviews, Survey Ai Detection, Survey Design, Survey Generator, User Interviews

### Data Models
- Agent, A2AMessage, AgentLoopConfig, AutoresearchExperiment, BackupRecord, ChannelConversation, ChannelInstance, ChannelMessage, CodeApplication, Codebook, Code, CodebookVersion, ContextDAGNode, DesignScreen, DesignBrief, DesignDecision, Document, Nugget, Fact, Insight, Recommendation, LLMServer, LoopExecution, MCPAccessPolicy, MCPAuditEntry, MCPServerConfig, Message, MethodMetric, ModelSkillStats, Notification, NotificationPreference, Project, ProjectMember, ProjectReport, ResearchDeployment, ChatSession, SurveyIntegration, SurveyLink, Task, User

### MCP Server Tools
- `list_skills()`
- `list_projects()`
- `get_deployment_status()`
- `get_findings()`
- `search_memory()`
- `execute_skill()`
- `create_project()`
- `deploy_research()`

### API Endpoints (342 total)
Run `python scripts/update_agent_md.py --verbose` for full list.

<!-- CAPABILITIES_END -->
