# Istara Architecture

This page describes Istara's system architecture, data flow, and key design decisions.

---

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  FRONTEND (Next.js 14)                       │
│  Chat · Kanban · Findings · Documents · Skills · Agents      │
│  23 component groups · 14 Zustand stores                     │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API + WebSocket
┌────────────────────────▼────────────────────────────────────┐
│                  BACKEND (FastAPI / Python 3.11)              │
│                                                              │
│  35 route modules · 337 API endpoints · Global JWT auth      │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   CORE ENGINE                        │    │
│  │  Agent Orchestrator · Context Hierarchy · RAG        │    │
│  │  Prompt RAG · Token Counter · Self-Evolution         │    │
│  │  Resource Governor · File Watcher · Scheduler        │    │
│  └───────────────────────┬─────────────────────────────┘    │
│                          │                                   │
│  ┌───────────────────────▼─────────────────────────────┐    │
│  │                  DATA LAYER                          │    │
│  │  SQLite (51+ models) · LanceDB (vector store)        │    │
│  │  Persona Files (CORE · SKILLS · PROTOCOLS · MEMORY)  │    │
│  └───────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐   │
│  │               LLM PROVIDERS                           │   │
│  │  LM Studio · Ollama · Any OpenAI-compatible API       │   │
│  └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Design Principles

### 1. Local-First
All data — research findings, interview transcripts, agent learnings, vector embeddings — lives in SQLite and LanceDB on the user's machine. No external servers, no telemetry, no cloud sync by default.

### 2. Project-Centric Data Model
Every data entity is anchored to a **Project** with cascade delete. Deleting a project cleans up all associated tasks, findings, documents, messages, and sessions. No orphaned data.

### 3. Atomic Research Framework
Istara implements the Atomic Research methodology: every insight traces back through a 5-layer evidence chain.

```
Nugget (raw evidence)
  → Fact (verified pattern from 2+ nuggets)
    → Insight (interpreted meaning)
      → Recommendation (actionable proposal)
        → Code Application (qualitative coding audit trail)
```

### 4. Double Diamond Phase Tagging
All findings, tasks, and documents are tagged with their Double Diamond phase: `discover`, `define`, `develop`, or `deliver`.

### 5. Unified Compute Registry
A single **ComputeRegistry** manages all LLM compute resources — local nodes (LM Studio/Ollama), network nodes (other machines on LAN), and relay nodes (donated compute over WebSocket). This replaces older patterns with separate LLMRouter and ComputePool components.

### 6. Task-Driven Research
Every research activity originates as a **Task** on the Kanban board, executes a **Skill**, and produces **Findings** and **Documents**. The agent loop: pick task → load context → select skill → execute → store findings → verify → broadcast → repeat.

---

## Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | Next.js 14, React, Tailwind CSS | Rich UI, SSR, accessible design system |
| State Management | Zustand | Lightweight, TypeScript-native, no boilerplate |
| Backend | FastAPI, Python 3.11 | Native async, type-safe, best AI/ML ecosystem |
| ORM | SQLAlchemy 2.0 (async) | Type-safe models, async sessions, proper relationships |
| Database | SQLite + aiosqlite | Zero-config, local-first, ACID-compliant |
| Vector Store | LanceDB (embedded) | No extra server process, columnar storage, hybrid search |
| LLM | LM Studio / Ollama | Local inference, OpenAI-compatible APIs |
| Embeddings | nomic-embed-text | Runs on CPU, tiny memory footprint |
| Real-time | WebSocket (FastAPI) | 16 broadcast event types, full UI synchronization |
| Desktop | Tauri (Rust) | Native system tray, lightweight, cross-platform |

---

## Backend Structure

```
backend/app/
├── api/
│   ├── routes/          # 35 FastAPI route modules (agents, chat, findings, skills, ...)
│   └── websocket.py     # WebSocket connection manager + 16 broadcast functions
├── agents/
│   └── personas/        # Agent identity files (CORE.md, SKILLS.md, PROTOCOLS.md, MEMORY.md)
├── channels/            # Messaging platform adapters (Telegram, Slack)
├── core/
│   ├── agent.py         # Agent work loop
│   ├── rag.py           # Retrieval-augmented generation pipeline
│   ├── embeddings.py    # Text embedding and vector search
│   ├── scheduler.py     # Cron scheduler for recurring tasks
│   ├── evolution.py     # Self-evolution engine
│   ├── governor.py      # Resource governor (CPU/RAM management)
│   └── context_hierarchy.py  # 6-level context composition
├── mcp/                 # MCP server implementation
├── models/              # SQLAlchemy database models (51+ models)
├── services/            # Business logic (channels, surveys, deployments, a2a)
└── skills/              # Skill base class, registry, factory, system action tools
```

---

## Frontend Structure

```
frontend/src/
├── app/                 # Next.js app router (page.tsx, layout.tsx)
├── components/          # React components organized by view
│   ├── chat/           # Chat interface, message rendering, file upload
│   ├── findings/        # Evidence chain views (Nuggets, Facts, Insights, Recs)
│   ├── tasks/           # Kanban board, task editor
│   ├── skills/          # Skills browser, skill editor, evolution tracker
│   ├── agents/          # Agent management, heartbeat, A2A messages
│   └── ...              # 23 total component groups
├── stores/              # Zustand state management (14 stores)
└── lib/
    ├── api.ts           # REST API client with typed namespaces
    └── types.ts         # TypeScript interfaces for all data models
```

---

## Agent Architecture

Five specialized agents are coordinated by a **MetaOrchestrator**:

| Agent | ID | Specialty |
|-------|-----|-----------|
| Cleo | istara-main | Task execution, skill invocation, user interaction |
| Sentinel | istara-devops | Data integrity, system health, performance |
| Pixel | istara-ui-audit | WCAG compliance, Nielsen heuristics, design system |
| Sage | istara-ux-eval | Cognitive load, user journeys, workflow analysis |
| Echo | istara-sim | End-to-end testing, scenario simulation, regression |

Each agent runs an autonomous **work loop**:
1. Check resource availability (Resource Governor)
2. Pick highest-priority task (`critical > high > medium > low`)
3. Load 6-level project context
4. Select and execute appropriate skill
5. Store findings in Atomic Research chain
6. Self-verify output quality
7. Ingest artifacts into vector store (LanceDB)
8. Record learnings if errors occurred
9. Update task status and broadcast progress via WebSocket

Agents communicate via an **A2A messaging system** (database-backed, WebSocket-broadcast). Message types: `consult`, `report`, `alert`, `delegate`.

---

## Data Flow: Research Task Execution

```
User creates Task in Kanban
    ↓
Agent picks up Task (priority queue)
    ↓
Context Hierarchy loads (6 levels: platform → company → product → project → task → agent)
    ↓
Prompt RAG retrieves relevant persona sections (30-50% token savings)
    ↓
Skill factory selects and executes appropriate skill
    ↓
LLM generates structured output (JSON schema)
    ↓
Output stored as Atomic Research chain (Nugget → Fact → Insight → Recommendation)
    ↓
Artifacts ingested into LanceDB (vector embeddings for future RAG)
    ↓
WebSocket broadcast: finding_created, task_progress, document_created
    ↓
Frontend updates in real-time (no refresh needed)
```

---

## Context Hierarchy

6 levels that compose into the agent's working prompt, with higher levels overriding lower:

```
Level 0: Platform    — Istara UXR expertise (built-in, never overridden)
Level 1: Company     — Organization, product, culture, terminology
Level 2: Product     — Features, users, domain knowledge
Level 3: Project     — Research questions, goals, timeline
Level 4: Task        — Per-task instructions from Kanban cards
Level 5: Agent       — Per-agent system prompts and constraints
```

---

## Prompt Optimization for Local Models

Istara implements three complementary strategies to run efficiently on 2K–8K context windows:

### Strategy 1: Prompt RAG
Instead of loading the full agent persona into every prompt, only the sections relevant to the current query are retrieved. Uses keyword scoring (or optional embedding similarity). Identity anchor is always included. Saves 30–74% of tokens.

### Strategy 2: LLMLingua-Inspired Compression
4-phase heuristic compression pipeline: remove filler sentences, compress redundant list items, trim example overload, normalize whitespace. Saves 15–30% additional tokens without losing meaning.

### Strategy 3: Context DAG
Conversation history is never thrown away — older messages are summarized into a DAG (Directed Acyclic Graph). Agents can expand any node to recover full detail. Prevents context window overflow in long research sessions.

---

## Real-Time Communication

WebSocket server at `/ws` with 16 broadcast event types:

| Event | Source | Frontend Action |
|-------|--------|----------------|
| `agent_status` | Agent work loop | Toast: working/error/idle |
| `task_progress` | Skill execution (0.1 → 1.0) | Progress indicator |
| `file_processed` | File watcher | Toast: file indexed |
| `finding_created` | Skill output storage | Toast: new findings |
| `suggestion` | Skill health, agent recommendations | Sticky toast with actions |
| `resource_throttle` | Resource Governor (>90% RAM) | Warning toast |
| `task_queue_update` | Agent work cycle | Info toast: queue depth |
| `document_created` | File watcher, document API | Toast: navigate to Docs |

---

## Security Architecture

See the [Security](Security) page for full details.

- **Global JWT middleware**: Every `/api/*` request requires a valid JWT (except login, register, health endpoints)
- **Local-only by default**: No external network calls except to the local LLM provider
- **MCP gated**: MCP server is OFF by default; access policies control per-tool permissions
- **Field encryption**: Sensitive fields (API keys, tokens) encrypted at rest

---

## Compute and Relay Architecture

```
ComputeRegistry (single source of truth)
├── Local nodes     — LM Studio / Ollama on the same machine
├── Network nodes   — LM Studio / Ollama on LAN (auto-discovered or manually registered)
└── Relay nodes     — Donated compute via outbound WebSocket (NAT-friendly)

Request routing:
1. Filter by capability (required model, VRAM, etc.)
2. Select lowest-latency healthy node
3. On failure: automatic failover to next available node
4. Priority: user interactions > background tasks
```
