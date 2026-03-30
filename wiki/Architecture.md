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
| Desktop | Tauri v2 (Rust) | Thin GUI tray, delegates to `istara.sh` for process management |

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

---

## Research Foundations

The following academic works directly inform Istara's architecture and feature design.

### Agent Design & Self-Evolution

1. **Zhou et al. (2026)** — "Memento-Skills: Let Agents Design Agents." Informs the Agent Factory, self-evolving skill system, and Meta-Agent view. The core principle of agent-generated skill definitions is implemented in Istara's skill evolution pipeline.

2. **Zhang et al. (2026)** — "Hyperagents: DGM-H Metacognitive Self-Modification, Cross-Domain Transfer, and Recursive Improvement." Informs the recursive self-improvement model, cross-domain skill transfer, and the Ensemble Health adaptive learning system.

### Multi-Model Validation & Consensus

3. **Wang et al. (2024)** — "Mixture-of-Agents Enhances Large Language Model Capabilities" (MoA). Foundation for Istara's multi-model consensus validation, where outputs from multiple local models are aggregated to improve reliability.

4. **Du et al. (2024)** — "Improving Factuality and Reasoning in Language Models through Multiagent Debate." Informs the debate-style validation strategy used in Ensemble Health, where agents challenge each other's outputs.

5. **Li et al. (2025)** — "Self-MoA: Self-Mixture of Agents." Extends the MoA pattern to single-agent self-ensemble, used in Istara's adaptive validation strategy selection.

6. **Fleiss, J. L. (1971)** — "Measuring Nominal Scale Agreement Among Many Raters." *Psychological Bulletin*, 76(5), 378–382. Provides the statistical basis for Kappa Thematic Analysis and the Fleiss' Kappa scores in Ensemble Health.

### Memory & Context Compression

7. **Jiang et al. (2023)** — "LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models." arXiv:2310.05736. Inspires Istara's LLMLingua-style 4-phase heuristic compression pipeline, achieving 15–30% additional token savings on local 2K–8K context models.

8. **Chen et al. (2023)** — "MemWalker: Interactive Memory Management and Traversal for Long Contexts." arXiv:2310.05029. Inspires the Context DAG (Directed Acyclic Graph) that summarizes older conversation turns without discarding them.

### Retrieval-Augmented Generation

9. **Lewis et al. (2020)** — "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks." *Advances in Neural Information Processing Systems (NeurIPS 2020)*, 33, 9459–9474. The foundational RAG architecture implemented in Istara's document ingestion and retrieval pipeline.

10. **Cormack, G. V., Clarke, C. L. A., & Buettcher, S. (2009)** — "Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods." *Proceedings of SIGIR 2009*, 758–759. The RRF algorithm used in Istara's multi-source document ranking.

### Distributed Compute

11. **Borzunov et al. (2022)** — "Petals: Collaborative Inference and Fine-tuning of Large Models." arXiv:2209.01188. Inspires Istara's relay node architecture, enabling users to donate and consume distributed LLM compute over WebSocket connections.

### Automated Research

12. **Karpathy, A. (2026)** — "Software 2.0 and the Autonomous Research Loop." Informs Istara's Autoresearch view: automated experiment loops, model leaderboards, and multi-configuration output comparison.

### Atomic Research Methodology

13. **Sharon, T. & Gadbaw, D. (2018)** — "Atomic Research: The molecule approach to UX research data." Defines the 5-layer evidence chain (Nugget → Fact → Insight → Recommendation → Code Application) implemented throughout Istara's Findings system.

### UX Design Principles

14. **Yablonski, J. (2020)** — *Laws of UX: Using Psychology to Design Better Products & Services.* O'Reilly Media, ISBN 978-1492055310. The theoretical basis for Istara's UX Laws view (40+ heuristics) and the compliance radar chart.

### AI-Assisted Interview Analysis

15. **AURA: AI-Powered User Research Assistant (2025)** — arXiv:2510.27126. Grounds Istara's AI-assisted interview analysis, inline nugget extraction, and automated transcript coding features.

### Output Grounding & Quality Evaluation

16. **Zheng et al. (2023)** — "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena." arXiv:2306.05685. Informs Istara's LLM-as-Judge grounding strategy used in Autoresearch and the Ensemble Health validation pipeline to assess output quality without human annotation.

---

### Full Bibliography (APA Format)

Borzunov, A., Baranchuk, D., Dettmers, T., Ryabinin, M., Belkada, Y., Chumachenko, M., ... & Babenko, A. (2022). *Petals: Collaborative inference and fine-tuning of large models.* arXiv:2209.01188.

Chen, H., Pasunuru, R., Weston, J., & Celikyilmaz, A. (2023). *MemWalker: Interactive memory management and traversal for long contexts.* arXiv:2310.05029.

Cormack, G. V., Clarke, C. L. A., & Buettcher, S. (2009). Reciprocal rank fusion outperforms Condorcet and individual rank learning methods. *Proceedings of the 32nd International ACM SIGIR Conference on Research and Development in Information Retrieval*, 758–759.

Du, Y., Li, S., Torralba, A., Tenenbaum, J. B., & Mordatch, I. (2024). *Improving factuality and reasoning in language models through multiagent debate.* Proceedings of ICML 2024.

Fleiss, J. L. (1971). Measuring nominal scale agreement among many raters. *Psychological Bulletin*, 76(5), 378–382.

Jiang, H., Wu, Q., Lin, C.-Y., Yang, P., & Qiu, X. (2023). *LLMLingua: Compressing prompts for accelerated inference of large language models.* arXiv:2310.05736.

Karpathy, A. (2026). *Software 2.0 and the autonomous research loop.*

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., ... & Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. *Advances in Neural Information Processing Systems (NeurIPS 2020)*, 33, 9459–9474.

Li, M., et al. (2025). *Self-MoA: Self-mixture of agents.*

Sharon, T. & Gadbaw, D. (2018). *Atomic research: The molecule approach to UX research data.*

Wang, J., Wang, J., Athiwaratkun, B., Zhang, C., & Zou, J. (2024). *Mixture-of-agents enhances large language model capabilities.* arXiv:2406.04692.

Yablonski, J. (2020). *Laws of UX: Using psychology to design better products & services.* O'Reilly Media.

Zhang, et al. (2026). *Hyperagents: DGM-H metacognitive self-modification, cross-domain transfer, and recursive improvement.*

Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., ... & Stoica, I. (2023). *Judging LLM-as-a-judge with MT-Bench and Chatbot Arena.* arXiv:2306.05685.

Zhou, et al. (2026). *Memento-Skills: Let agents design agents.*

*AURA: AI-Powered User Research Assistant.* (2025). arXiv:2510.27126.
