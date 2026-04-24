# Istara Technical Architecture

> **Local-first AI agents for UX Research** — autonomous, self-evolving, hardware-aware.

Istara is a production-grade agent platform designed for UX researchers who want AI that runs on their machine, learns from their work, and gets better over time — without sending data to the cloud.

---

## Why Istara's Architecture Matters

Before diving into details, here are the design decisions that make Istara a robust choice for researchers and teams who care about data ownership, cost, and reliability.

### 1. Agents That Actually Improve Themselves

Most agent frameworks treat prompts as static configuration. Istara's agents **evolve**: they record error patterns, track workflow preferences, and when patterns reach maturity thresholds (3+ occurrences, 2+ contexts, 30 days), those learnings are permanently promoted into the agent's persona files. This is not fine-tuning — it's structured prompt evolution that works with any local model.

### 2. Every Finding Is Traceable to Source

Istara implements the **Atomic Research** methodology (Nugget → Fact → Insight → Recommendation) with full evidence chains. Every insight links back through facts to the exact quote or data point that supports it. No hallucinated conclusions without provenance.

### 3. Lossless Context Memory

Conversations are never thrown away. Istara's **DAG-based context summarization** creates hierarchical summaries of older messages while preserving the originals. Agents can drill back into any conversation depth to recover details. Combined with a 6-level context hierarchy, every chat gets the right context without exceeding the model's window.

### 4. Works With Any Local Model (1.5B to 70B)

A hardware-aware **Resource Governor** monitors RAM, CPU, and GPU to prevent system overload. **Prompt RAG** dynamically retrieves only the relevant persona sections for each query (30-50% token savings). **LLMLingua-inspired compression** removes filler without losing meaning (15-30% savings). Together, these allow Istara to run meaningfully on a 3B model with a 2K context window — or scale up to use everything a 70B model offers.

### 5. 45+ Research Skills, Self-Monitoring

Each skill follows the Double Diamond methodology and produces structured outputs. A **Skill Health Monitor** tracks execution quality over time, and when a skill's performance drops below threshold, it auto-proposes prompt improvements. Skills are self-contained modules with `plan()`, `execute()`, and `validate()` methods.

### 6. Five Coordinated Agents, Not One

Istara runs a **meta-orchestrator** coordinating five specialized agents — a task executor, a DevOps auditor, a UI auditor, a UX evaluator, and a user simulator. Each has a distinct persona, and they communicate through an internal A2A messaging system. Custom agents participate in the same pipeline automatically.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (Next.js)                      │
│  Chat · Kanban · Findings · Documents · Skills · Agents     │
└────────────────────────┬────────────────────────────────────┘
                         │ REST + WebSocket
┌────────────────────────▼────────────────────────────────────┐
│                     BACKEND (FastAPI)                        │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Chat API │  │ Task API │  │ Agent API│  │ Skills API │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
│       │              │             │              │         │
│  ┌────▼──────────────▼─────────────▼──────────────▼──────┐  │
│  │              CORE ENGINE                              │  │
│  │  Agent Orchestrator · Context Hierarchy · RAG Pipeline │  │
│  │  Prompt RAG · Prompt Compressor · Token Counter        │  │
│  │  Self-Evolution · Agent Learning · Self-Check          │  │
│  │  Resource Governor · File Watcher · Scheduler          │  │
│  └───────────────────────┬───────────────────────────────┘  │
│                          │                                  │
│  ┌───────────────────────▼───────────────────────────────┐  │
│  │              DATA LAYER                               │  │
│  │  SQLite (models, findings, learnings, tasks, sessions)│  │
│  │  LanceDB (vector store — embeddings, hybrid search)   │  │
│  │  Persona Files (CORE.md, SKILLS.md, PROTOCOLS.md,     │  │
│  │                 MEMORY.md per agent)                   │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              LLM PROVIDERS                            │  │
│  │  LM Studio (default) · Ollama · OpenAI-compatible     │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | Next.js 14, React, Tailwind CSS, Zustand | Fast SSR, accessible design system, lightweight state |
| Backend | FastAPI, Python 3.11, async SQLAlchemy | Native async, type-safe, fast development |
| Database | SQLite + aiosqlite | Zero-config, local-first, ACID-compliant |
| Vector Store | LanceDB | Embedded, no server process, columnar storage |
| LLM | LM Studio / Ollama | Local inference, OpenAI-compatible APIs |
| Real-time | WebSocket (FastAPI) | 9 event types: agent status, task progress, findings, documents, queue, throttle |
| Testing | Playwright + Node.js simulation | E2E, accessibility (WCAG), Nielsen's heuristics |
| Fine-Tuning | Custom Python pipeline (`Model_Finetuning/`) | Adapters → merged nugget bank → SFT JSONL → MLX/CUDA trainers |

---

## Agent System

### Multi-Agent Architecture

Istara runs five coordinated agents managed by a **MetaOrchestrator**. Each agent has a distinct role, persona, and work pattern.

| Agent | Role | Persona | What It Does |
|-------|------|---------|-------------|
| **Istara** | Task Executor | Cleo | Primary worker. Executes all 45+ skills, produces findings |
| **Sentinel** | DevOps Audit | — | Monitors data integrity, orphaned references, system health |
| **Pixel** | UI Audit | — | Runs Nielsen's heuristics, WCAG checks, design system audits |
| **Sage** | UX Evaluation | — | Evaluates UX quality, cognitive load, journey completeness |
| **Echo** | User Simulation | — | Simulates end-user behavior, tests flows, detects friction |

**Custom agents** created by users are full participants in this system — they get auto-generated persona files and join the same evolution pipeline.

## Orchestration Audit: Istara vs. Industry Standards

Istara’s orchestration architecture is designed for **Academic Rigor** and **Local Resilience**, differing from generic frameworks in several key ways:

| Dimension | LangGraph / CrewAI | OpenAI Swarm | Anthropic Computer Use | Istara (Sentinel/Cleo) |
|-----------|-------------------|--------------|------------------------|-----------------------|
| **Planning** | Deterministic Graphs | Loose Handoffs | Multi-turn thinking | **Decomposed DAGs** |
| **Logic** | Fixed nodes/edges | dynamic routing | ReAct (XML tags) | **ReAct + Regex Fallback** |
| **Consensus** | Optional | None (one model) | None | **Mandatory (Fleiss' Kappa)** |
| **Steering** | Restart/Pause | none | Manual intervention | **Thread-safe Queues** |
| **Execution** | Cloud-first | Cloud-first | Cloud-first | **Hardware-aware (Local)** |
| **Benchmark Scorecard** | Unverified | N/A | N/A | **Layer 4: 4 benchmarks, 12 tests** |

#### Benchmark Methodology (v2.0)

Istara's orchestration is validated against a four-benchmark suite using academic metrics from Memento (Zhou et al. 2026), DeepPlanning, Claw-Eval Pass^3, and SkillsBench Avg5:

| Benchmark | Validates | Academic Reference |
|-----------|-----------|-------------------|
| **Long-Horizon DAG** | No circular deps in 10-step plans, valid topological ordering | DeepPlanning (constrained optimization) |
| **Tool-Calling Accuracy** | Schema compliance, regex fallback, hallucination filtering, MAX_ITERATION enforcement | Claw-Eval Pass^3 (trajectory consistency) |
| **A2A Mathematical Consensus** | Fleiss' Kappa ≥0.6 on clear cases, cosine similarity on embeddings | Memento (inter-rater reliability) |
| **Async Steering Responsiveness** | Atomic queue lock under concurrent injection, no state corruption | — |

All mathematical benchmarks use Istara's production consensus engine (`backend/app/core/consensus.py`) — `fleiss_kappa()`, `cosine_similarity()`, and `compute_consensus()` are NOT reimplemented.

---

### Agent Work Loop

The core agent loop (`backend/app/core/agent.py`) runs continuously:

```
┌─────────────────────────────────────────────────┐
│  1. Check resources (governor.can_start_agent()) │
│  2. Pick highest-priority task                   │
│  3. Load project context (6-level hierarchy)     │
│  4. Select skill (explicit or keyword-inferred)  │
│  5. Execute skill → SkillOutput                  │
│  6. Store findings (Nugget→Fact→Insight→Rec)     │
│  7. Self-verify output (check_findings)          │
│  8. Ingest artifacts into vector store           │
│  9. Record learnings if errors occurred          │
│  10. Update task status, broadcast progress      │
│  11. Sleep → repeat                              │
└─────────────────────────────────────────────────┘
```

Task selection uses priority ordering: `critical > high > medium > low`, with agent-assigned tasks taking precedence over unassigned ones. After completing a task, the agent checks queue depth and adjusts its sleep interval (5s when busy, 30s when idle).

### Agent Identity System

Each agent's personality is defined by four Markdown files stored at `backend/app/agents/personas/{agent_id}/`:

| File | Purpose | Compression Budget |
|------|---------|-------------------|
| **CORE.md** | Identity, personality, values, communication style | 40% (highest priority) |
| **SKILLS.md** | Technical capabilities, methodologies, tools | 25% |
| **PROTOCOLS.md** | Behavioral rules, decision-making, error handling | 25% |
| **MEMORY.md** | Persistent learnings (auto-updated by the agent) | 10% |

These files are loaded and composed into the system prompt on every interaction. When the composed identity exceeds the context budget (30% of `max_context_tokens`), compression is applied using Prompt RAG or LLMLingua-style heuristics.

### Agent-to-Agent Communication

Agents communicate through a database-backed messaging system (`services/a2a.py`):

- **Message types**: `consult`, `report`, `alert`, `delegate`
- **Broadcast**: WebSocket notifications for real-time UI updates
- **Audit trail**: All messages logged for traceability
- **A2A Protocol compatibility**: The backend exposes `/.well-known/agent.json` for standard discovery

### Real-Time Event System

All agent activity, task progress, and document changes are broadcast to the frontend via WebSocket (`/ws`). Every broadcast function on the backend has a corresponding handler in the frontend's `ToastNotification` component. This is enforced by the **Event Wiring Audit** (Scenario 30) which verifies both sides are connected.

| Event Type | Backend Source | Frontend Action |
|------------|---------------|-----------------|
| `agent_status` | Agent work loop, custom workers, specialized agents | Toast: working/error/idle status |
| `task_progress` | Skill execution stages (0.1 → 0.3 → 0.7 → 1.0) | Toast: task completion |
| `file_processed` | File watcher after ingestion | Toast: file indexed with chunk count |
| `finding_created` | `_store_findings()` after skill execution | Toast: new findings with type + count |
| `suggestion` | File watcher, skill health, agent recommendations | Sticky toast with action buttons |
| `resource_throttle` | MetaOrchestrator when CPU/RAM critical | Warning toast: agent paused |
| `task_queue_update` | Agent work cycle after task completion | Info toast: queue depth |
| `document_created` | File watcher, document API | Toast: navigate to Documents |
| `document_updated` | Document API PATCH | Toast: navigate to Documents |

**Resource Governor Lifecycle**: Agent workers register with the governor before task execution and unregister after, enforcing concurrent agent limits. The governor monitors CPU/RAM and pauses all agents when resources are critical (>90% RAM), broadcasting `resource_throttle` events.

## Executive Presentation Pipeline (Minto/SCR)

Istara bridges the gap between raw research data and executive-level presentations by implementing a specialized consulting-grade reporting pipeline.

### 1. Minto Pyramid Principle
Final reports are structured top-down:
- **Top**: Actionable recommendations (The Answer).
- **Middle**: Strategic arguments grouped by MECE (Mutually Exclusive, Collectively Exhaustive) categories.
- **Bottom**: Atomic research findings (Nuggets, Facts) providing the evidence base.

### 2. SCR (Situation-Complication-Resolution) Framework
Executive summaries follow the SCR narrative arc to ensure stakeholder alignment:
- **Situation**: Contextual baseline and agreed-upon market/UX facts.
- **Complication**: The "So-What" — what is changing or failing that necessitates action.
- **Resolution**: The proposed strategic path forward derived from research synthesis.

### 3. Slide Instruction Engine (Ghost Decking)
To facilitate presentation creation, Istara provides a "Slide Instruction" export feature. It translates the deep markdown report into a structured instruction package for external presentation AIs, enforcing:
- **Action Titles**: Full-sentence conclusions for every slide.
- **Evidence-Driven Layouts**: Direct mapping of findings to slide bullets.
- **Horizontal Flow**: Ensures the narrative story is consistent when reading slide titles alone.

| Field | Type | Purpose |
|-------|------|---------|
| `input_document_ids` | JSON array | Source materials the agent should use for this task |
| `output_document_ids` | JSON array | Artifacts the agent produces during task execution |
| `urls` | JSON array | URLs the agent should fetch and analyze |
| `instructions` | Text | User-provided per-task guidance for the agent |

**API Endpoints**:
- `POST /api/tasks/{id}/attach?document_id=X&direction=input|output` — Attach a document
- `POST /api/tasks/{id}/detach?document_id=X&direction=input|output` — Detach a document
- Standard `POST /api/tasks` and `PATCH /api/tasks/{id}` support all new fields

**Frontend Integration**: The Kanban board shows document count badges (purple) and URL count badges (blue) on task cards. The Task Editor modal provides instructions editing, URL management (add/remove), and a read-only attached documents summary.

### System Action Tools (LLM-Native Tool Selection)

Instead of hardcoded intent detection with regex/dictionaries, Istara uses **structured tool schemas** injected into the LLM's system prompt. The LLM itself decides which tool to call based on the user's natural language request.

**13 System Tools** (`backend/app/skills/system_actions.py`):

| Tool | What It Does |
|------|-------------|
| `create_task` | Create a new Kanban task with all fields |
| `search_documents` | Full-text search across project documents |
| `list_tasks` | List tasks filtered by status/project |
| `move_task` | Move a task between Kanban columns |
| `attach_document` | Link a document to a task (input/output) |
| `search_findings` | Query nuggets, facts, insights, recommendations |
| `list_project_files` | List files in a project's upload directory |
| `assign_agent` | Assign an agent to a specific task |
| `send_agent_message` | Send A2A message between agents |
| `get_document_content` | Retrieve full document content |
| `search_memory` | Search agent memory and learnings |
| `update_task` | Update task fields (title, status, URLs, etc.) |
| `sync_project_documents` | Scan project folder for new/changed files |

**Tool Schema Format**: Each tool is defined with `name`, `description`, and `parameters` (JSON Schema). The `build_tools_prompt()` function generates a compact system prompt section listing all available tools with their schemas.

**ReAct Execution Pattern**: When the LLM responds with a tool call (`{"tool": "create_task", "args": {...}}`), the backend extracts it, executes the tool, injects the result back into the conversation, and re-sends to the LLM for the next reasoning step. Maximum 3 tool iterations per message.

---

## Self-Evolution Pipeline

Istara implements an OpenClaw-inspired self-improvement system where agents literally rewrite their own personas based on accumulated experience.

### How It Works

```
┌──────────────────────────────────────────────────────────────┐
│                    LEARNING LIFECYCLE                         │
│                                                              │
│  1. Agent encounters error/pattern during skill execution    │
│  2. Learning recorded to AgentLearning table:                │
│     - category: error_pattern | workflow_pattern |            │
│       user_preference | performance_note                     │
│     - trigger, resolution, confidence (0-100)                │
│     - times_applied, times_successful                        │
│                                                              │
│  3. On future errors, agent checks for known resolutions     │
│     (keyword matching against past learnings)                │
│                                                              │
│  4. Self-evolution engine scans periodically (audit cycle)   │
│                                                              │
│  5. When promotion thresholds are met:                       │
│     ≥3 occurrences (times_applied)                           │
│     ≥2 distinct project contexts                             │
│     30-day maturity window                                   │
│     ≥70% confidence score                                    │
│     ≥60% success rate                                        │
│                                                              │
│  6. Learning is promoted to the appropriate persona file:    │
│     error_pattern     → PROTOCOLS.md                         │
│     workflow_pattern   → SKILLS.md                           │
│     user_preference    → CORE.md                             │
│     performance_note   → MEMORY.md                           │
│                                                              │
│  7. Original learning marked [PROMOTED] in DB                │
│     Agent's next load includes the new persona content       │
└──────────────────────────────────────────────────────────────┘
```

### Two Modes

- **Auto-promote** (`self_evolution_auto_promote: true`): Mature patterns are written to persona files automatically during the DevOps audit cycle.
- **User approval** (default): Candidates are surfaced via the API for human review before promotion.

### Custom Agent Evolution

When users create a custom agent, the system auto-generates all four persona files (CORE.md, SKILLS.md, PROTOCOLS.md, MEMORY.md) from the agent's name and system prompt. This means **every custom agent participates in the same self-evolution pipeline** as system agents — they learn, they mature, they evolve.

---

## Local Telemetry & Model Intelligence

Istara includes a **local-first, zero-trust observability system** that tracks model performance without ever sending data to the cloud.

### 1. Telemetry Spans & Agent Hooks

The agent execution loop is instrumented with lifecycle hooks (`agent_hooks.py`) that fire at every stage: `pre_task`, `post_task`, `post_validation`, `on_error`, and `on_completion`. When telemetry is enabled, these hooks record metadata-only **Telemetry Spans** to the local database.

- **Zero-Trust**: No user content, prompts, or responses are recorded in telemetry spans — only metadata (duration, tokens, status, error types, model/skill name).
- **Opt-in Only**: Users must explicitly enable telemetry in Settings to activate recording.

### 2. Model Intelligence Dashboard

The frontend **Ensemble Health** view features a Model Intelligence section that aggregates telemetry data into actionable insights:

- **Model Leaderboard**: Ranks model × skill combinations by quality EMA (Exponential Moving Average) and success rate.
- **Latency Percentiles**: Tracks P50, P90, and P99 latency across different models to detect hardware bottlenecks.
- **Tool Success Rates**: Monitors the reliability of MCP tools and system actions.
- **Error Taxonomy**: Categorizes failures (hallucination, timeout, tool error) to help users refine their model selection.

### 3. Self-Healing DevOps Architecture

The DevOps Agent (`Sentinel`) uses telemetry signals to perform automated remediation via **Self-Healing Rules**:

- **Circuit Breaker**: If a model × skill combination reaches a >30% error rate, the DevOps agent flags it as "Degraded" and suggests a model switch.
- **Auto-Remediation**: Transient errors (e.g., context window overflows) trigger automatic parameter adjustments (e.g., tighter compression) for the next attempt.
- **Local Export**: Users can export their telemetry data to portable JSON for deep inspection or sharing with the community.

---

## Prompt Management for Local Models

Running on local models (1.5B to 14B parameters) with limited context windows (2K to 8K tokens) requires careful prompt engineering. Istara implements three complementary strategies.

### Strategy 1: Prompt RAG (Query-Aware System Prompts)

Instead of loading the entire agent persona into every prompt, **Prompt RAG** dynamically retrieves only the sections relevant to the current query.

**How it works:**

1. Each persona file is chunked by `##` section headers into indexed `PromptSection` objects
2. An **identity anchor** (Identity, Personality, Values from CORE.md) is always included (~600 tokens)
3. The user's query is tokenized and scored against all sections using keyword overlap (or optionally embedding similarity)
4. Top-K most relevant sections are selected within the remaining token budget
5. The composed prompt is assembled: anchor + selected sections, sorted by file order

**Example impact:**

| Query | Full Identity | Prompt RAG | Savings |
|-------|--------------|-----------|---------|
| "Analyze interview transcripts" | 2,124 tokens | 1,491 tokens | 30% |
| "Help me with research" (512 budget) | 2,124 tokens | 559 tokens | 74% |
| "Run usability evaluation" | 2,124 tokens | 1,043 tokens | 51% |

**Key design decisions:**
- Identity anchor is **never** dropped, even at extreme budgets — the agent must always know who it is
- Different queries retrieve **different sections** — interview questions get interview skills, usability questions get heuristic protocols
- Keyword scoring is the default (instant, no model needed); embedding scoring is available for better accuracy

### Strategy 2: LLMLingua-Inspired Compression

When Prompt RAG alone isn't enough, a **4-phase heuristic compression pipeline** reduces the prompt further — inspired by Microsoft's LLMLingua but without requiring PyTorch or transformers.

| Phase | What It Does | Example |
|-------|-------------|---------|
| **1. Structural** | Collapse whitespace, remove markdown decorators, clean formatting | `\n\n\n` → `\n\n` |
| **2. Qualifier Removal** | Replace verbose phrases with concise equivalents | "in order to" → "to", "due to the fact that" → "because" |
| **3. Sentence-Level** | Remove lowest-importance sentences (position + domain term scoring) | Filler sentences dropped, headers and bullet points kept |
| **4. Word-Level** | Remove filler words below importance threshold | "actually", "basically", "very" removed |

**Safety guarantees:**
- At least 30% of sentences are always kept (minimum 1)
- At least 30% of words are always kept (minimum 3)
- **60+ UX research domain terms** are never compressed (usability, heuristic, nugget, persona, etc.)
- Section-type-aware budgets: Identity keeps 90%, Examples keep only 40%

**Performance:** ~5ms for a 10K-character prompt on typical hardware.

### Strategy 3: Dynamic Context Window Management

Istara now detects the loaded model's context window at startup and allocates token budgets dynamically. The hardcoded 8192 default is replaced by a **BudgetCoordinator** that scales budgets based on actual model capabilities.

**Detection chain:**
1. `main.py` startup probes LM Studio/Ollama for the loaded model name
2. `model_capabilities.py` calls `/v1/models` (LM Studio) or `/api/show` (Ollama) to read `context_length`
3. `compute_registry.check_all_health()` syncs detected capabilities to `settings.max_context_tokens`
4. `config.update_context_window()` updates the global budget if the detected value differs >2x from current

**Budget allocation (adaptive, with caps to prevent signal dilution):**

| Component | 8K Model | 80K Model | Rationale |
|-----------|----------|-----------|-----------|
| Identity (Prompt RAG) | 2,457 (30%) | 3,000 (~4%) | Caps at 3K — more persona detail isn't better beyond a point |
| RAG context | 409 (5%) | 4,000 (5%) | More retrieved chunks, compressed question-aware |
| Reply reserve | 512 | 4,000 | Allows longer outputs on big windows |
| Buffer | 0 | 4,000 | Overflow protection |
| History | 4,369 | 65,000+ | The lion's share — what users experience as "remembers more" |

Budget philosophy from industry research:
- **Liu et al. "Lost in the Middle" (2023)** — LLM accuracy drops 30% when relevant info is in the middle of long contexts. Bigger windows don't solve this; they make it worse. Chroma tested 18 frontier models and found every model's reliability declines as input length increases.
- **MyEngineeringPath (2026)** — "The skill is not filling the context window. The skill is spending each token where it matters most."
- **Quadratic attention cost** — Doubling context from 64K to 128K quadruples attention computation. More context = more noise = worse attention.

**Surplus-aware compression:** The system assesses available compute power (RAM, CPU, remote relay nodes) via the existing `ResourceGovernor` and `ComputePool` infrastructure to choose compression strategies:

| Surplus Level | RAG Compression | History Compression | Identity |
|--------------|-----------------|---------------------|----------|
| **High** (2+ remote nodes OR 12GB+ RAM) | Full question-aware (LLM scoring) | LLM summarization first | Full Prompt RAG + LLMLingua |
| **Moderate** (normal load) | Heuristic question-aware | Heuristic first, LLM fallback | Prompt RAG + LLMLingua |
| **Low** (1 agent, no remotes) | Heuristic only | Heuristic only | Prompt RAG only |
| **Constrained** (system under pressure) | None (raw, trimmed) | Hard trim only | Minimal anchor |

**Files:** `backend/app/core/budget_coordinator.py`, `backend/app/core/token_counter.py`, `backend/app/core/context_summarizer.py`, `backend/app/core/prompt_compressor.py`, `backend/app/core/compute_registry.py`, `backend/app/config.py`, `backend/app/api/routes/chat.py`, `backend/app/api/routes/interfaces.py`

### Strategy 4: Context Window Guard (Updated)

A **ContextWindowGuard** (`core/token_counter.py`) prevents prompt overflow on every request, now budget-aware:

1. Estimates total tokens: system prompt + message history + reserved reply buffer
2. Uses `budget.history_tokens` instead of raw `max_tokens` for per-component enforcement
3. If over budget, trims oldest messages first
4. Inserts a `[History trimmed for context budget]` note so the model knows context was lost
5. Works alongside DAG summarization for lossless recovery of trimmed content

### How They Work Together (Updated Pipeline)

```
User sends message
  │
  ├─ BudgetCoordinator allocates tokens based on detected context window
  │
  ├─ Prompt RAG selects relevant persona sections (within identity budget)
  │
  ├─ RAG retrieves relevant document chunks
  │   └─ compress_rag_chunks() applies question-aware compression
  │      (LongLLMLingua pattern: reorder most relevant first,
  │       differentiated compression by rank)
  │
  ├─ Context Summarizer applies cost-escalating pipeline:
  │   1. DAG-based lossless compression (if enabled)
  │   2. LLMLingua heuristic compression (~5ms, zero LLM cost)
  │   3. LLM summarization (only if heuristic isn't enough)
  │   4. Hard trim (last resort)
  │
  ├─ Context Window Guard trims history if still over budget
  │
  └─ Final prompt sent to model
```

**Academic & Industry References:**
- **LongLLMLingua** (Microsoft, ACL 2024) — Question-aware fine-grained prompt compression via contrastive perplexity achieves +21.4% accuracy with 4x fewer tokens on NaturalQuestions. LlamaIndex integration: re-rank + compress + subsequence recovery pattern.
- **Morph FlashCompact** (2026) — Prevention beats compression. Verbatim compaction at 3,300+ tok/s, 50-70% reduction, 98% accuracy, zero hallucination risk. 3-4x longer context life vs threshold-based compression.
- **Factory.ai 36K message eval** (2026) — Structured summarization scored 3.70/5 but causes re-reading loops (lost file paths, line numbers). Verbatim compaction preserves exact references.
- **JetBrains SWE-bench** (2026) — Observation masking matched LLM summarization quality at $0 cost. Once the model has acted on information, it doesn't need the raw data in subsequent turns.
- **OpenAI Codex team** (2026) — Inline compression as default primitive, not emergency fallback. Compress tool outputs before they enter context.
- **ACON Framework** (Microsoft Research, 2025) — Adaptive context control for tool observations. 26-54% token reduction with 95%+ accuracy across AppWorld, OfficeBench, Multi-obj QA.

---

## Context & Memory System

### 6-Level Context Hierarchy

Every prompt is composed from a layered context system where each level adds domain-specific knowledge:

| Level | Type | What It Contains | Example |
|-------|------|-----------------|---------|
| 0 | **Platform** | Istara defaults — UXR expertise, Atomic Research methodology | "You are a UX Research agent..." |
| 1 | **Company** | Organization culture, terminology, research standards | "Our company uses NPS > 50 as the success threshold" |
| 2 | **Product** | Product-specific knowledge, user base, competitors | "The app targets enterprise HR managers" |
| 3 | **Project** | Research questions, goals, timeline, participants | "We're studying onboarding friction for Q2" |
| 4 | **Task** | Task-specific instructions, skill parameters | "Analyze these 5 interview transcripts for..." |
| 5 | **Agent** | Agent persona (CORE/SKILLS/PROTOCOLS/MEMORY) | "You are Cleo, a meticulous researcher..." |

Contexts at each level are stored as `ContextDocument` records in the database with priority ordering and enable/disable flags. The `compose_context()` function merges them top-down for every interaction.

### DAG-Based Lossless Context Summarization

Traditional context management either truncates (lossy) or keeps everything (overflow). Istara's **Context DAG** (`core/context_dag.py`) provides a third option: hierarchical summarization with full recovery.

```
Depth 2:  [Summary of summaries: "The project explored 3 themes..."]
              │
Depth 1:  [Summary A: "Users reported      [Summary B: "Analytics showed
           friction in onboarding..."]       drop-off at step 3..."]
              │                                  │
Depth 0:  [Batch 1: msgs 1-32]  [Batch 2: msgs 33-64]  [Batch 3: msgs 65-96]
              │                      │                        │
Raw:      msg1 msg2 ... msg32    msg33 ... msg64          msg65 ... msg96
```

**How it works:**
- The **fresh tail** (last 32 messages) is always kept verbatim — these are the most relevant
- Older messages are grouped into **depth-0 nodes** (~32 messages each), each with an LLM-generated summary
- When 4+ depth-0 nodes accumulate, they roll up into a **depth-1 node** (summary of summaries)
- The process repeats at higher depths as conversations grow
- **Active recall tools** let agents drill back into any depth to recover specific details

**Result:** A 500-message conversation might use only ~2,000 tokens of context budget while preserving access to every message.

### Agent Memory System

Each agent maintains private memory through multiple mechanisms:

| System | Persistence | Purpose |
|--------|------------|---------|
| **MEMORY.md** | File (in persona dir) | Long-term learnings, error patterns, preferences |
| **AgentLearning** table | SQLite | Structured error/workflow patterns with confidence scores |
| **Agent notes** | Vector store (LanceDB) | Semantic search over agent-written observations |
| **Memory JSON** | Agent model column | Quick-access working memory (recent state) |

The **Memory View** in the frontend lets users see all agent learnings, DAG structures, and stored notes with semantic search.

---

## Skills System

### Architecture

Skills are self-contained modules that follow a consistent interface:

```python
class BaseSkill:
    name: str                    # "user-interviews"
    display_name: str            # "User Interview Analysis"
    phase: str                   # "discover" | "define" | "develop" | "deliver"
    skill_type: str              # "qualitative" | "quantitative" | "mixed"

    def plan(input: SkillInput) -> str          # Research plan
    def execute(input: SkillInput) -> SkillOutput  # Full execution
    def validate(output: SkillOutput) -> bool   # Quality check
```

**SkillOutput** produces structured findings:
- `nuggets[]` — Raw evidence (quotes, observations, data points)
- `facts[]` — Verified claims, each linking to supporting nuggets
- `insights[]` — Patterns/conclusions, each linking to supporting facts
- `recommendations[]` — Action items, each linking to supporting insights
- `artifacts{}` — Generated files (reports, matrices, maps)
- `suggestions[]` — Next-step recommendations for the researcher

### The 45+ Skills

Organized by the **Double Diamond** methodology:

| Phase | Skills | Focus |
|-------|--------|-------|
| **Discover** | User Interviews, Contextual Inquiry, Diary Studies, Field Studies, Desk Research, Stakeholder Interviews, Analytics Review, Survey Design, Survey AI Detection | Understanding the problem space |
| **Define** | Affinity Mapping, Thematic Analysis, Kappa Intercoder Reliability, Persona Creation, Journey Mapping, Empathy Mapping, JTBD Analysis, HMW Statements, Taxonomy Generator | Synthesizing and framing |
| **Develop** | Usability Testing, Heuristic Evaluation, Accessibility Audit, Card Sorting, Tree Testing, Concept Testing, Cognitive Walkthrough, A/B Testing, Prototype Feedback, Design Critique, Workshop Facilitation, User Flow Mapping | Testing and iterating |
| **Deliver** | Research Synthesis, Prioritization Matrix, NPS Analysis, SUS/UMUX Scoring, Design System Audit, Handoff Documentation, Stakeholder Presentation, Longitudinal Tracking, Research Retro, Repository Curation, Regression Impact | Communicating and measuring |

### Skill Health Monitoring

The **SkillManager** (`skills/skill_manager.py`) tracks execution quality:

- Records success/failure and quality scores for every execution
- Computes running averages: execution count, avg quality, success rate
- When a skill's `avg_quality < 0.5` after 3+ executions, auto-proposes a `SkillUpdateProposal`
- Proposals include suggested prompt improvements, viewable in the UI
- Approved proposals are versioned and applied

---

## Document System — Source of Truth

Every file a user uploads, every output an agent produces, and every task completion that generates an artifact becomes a **Document**. Documents are Istara's source of truth — the final, findable output of everything.

### Document Lifecycle

```
User uploads file → File Watcher detects → Document registered → Indexed in memory
User asks for survey → Agent picks task → Skill executes → Output saved as Document
Agent self-initiates → Atomic path tracked → Document appears in UI with lineage
```

### Key Properties

| Property | Purpose |
|----------|---------|
| **Atomic Path** | JSON lineage: step-by-step trace of how the document was created |
| **Agent IDs** | Which agents were involved in producing this document |
| **Skill Names** | Which research skills were executed |
| **Task Link** | Related Kanban task (if any) |
| **Tags** | User and auto-generated tags for filtering |
| **Phase** | Double Diamond phase (discover/define/develop/deliver) |
| **Source** | How it originated: `user_upload`, `agent_output`, `task_output`, `project_file`, `external` |
| **Content Index** | Full text indexed for search across titles, content, tags, and filenames |

### Search & Filtering

Documents support multi-dimensional discovery:

- **Full-text search**: Titles, descriptions, content, tags, and filenames
- **Phase filter**: Filter by Double Diamond phase
- **Tag filter**: Browse by project-wide unique tags
- **Source filter**: See only agent outputs, user uploads, task outputs, etc.
- **Pagination**: Large document sets handled efficiently

### Auto-Registration

Files placed in the project's upload directory are **automatically registered** as documents by the File Watcher. The sync endpoint (`POST /api/documents/sync/{project_id}`) ensures every file in the folder appears in the Documents UI instantly.

### Preview System

Document preview follows the same pattern as the Interviews view:
- Text files render with syntax highlighting
- Images display inline
- Audio/video play with native controls
- PDF/DOCX content extracted and shown as text
- Right panel shows metadata: origin description, agents, skills, tags, atomic path

### Backup Integration

Documents are included in project exports alongside findings, tasks, messages, sessions, and codebooks. The export format stores full document metadata (tags, atomic paths, agent links) for portable re-import.

---

## RAG Pipeline

### Hybrid Search

Istara's retrieval combines **vector similarity** and **keyword search** using configurable weights:

| Component | Weight | Method | Strengths |
|-----------|--------|--------|----------|
| **Vector** | 0.7 | LanceDB cosine similarity on embeddings | Semantic understanding, handles paraphrasing |
| **Keyword** | 0.3 | SQLite FTS5 BM25 scoring | Exact matches, acronyms, proper nouns |

Results are merged using **Reciprocal Rank Fusion** and filtered by a score threshold (default: 0.3).

### Ingestion Pipeline

```
File uploaded → FileProcessor extracts text
  → Chunker splits into ~1,200 char chunks (180 overlap)
    → Embeddings generated (batch, cached)
      → Chunks stored in LanceDB (per-project database)
        → FileWatcher detects new files → auto-creates research tasks
```

**Embedding caching** prevents re-embedding unchanged content, critical for local hardware where embedding is expensive.

### Self-Check (Hallucination Detection)

After skill execution, findings are verified against the project knowledge base:

```python
result = verify_claim(claim_text, project_id)
# Returns: confidence (HIGH/MEDIUM/LOW/UNVERIFIED), supporting sources
```

- `HIGH`: Multiple supporting sources found
- `MEDIUM`: Single source with partial match
- `LOW`: Weak evidence
- `UNVERIFIED`: No supporting evidence — flagged for human review

---

## Hardware Awareness

### Resource Governor

The **ResourceGovernor** (`core/resource_governor.py`) prevents Istara from overwhelming the host machine:

```python
class ResourceBudget:
    max_concurrent_agents: int    # Based on available RAM
    max_tasks_per_project: int    # Prevent runaway execution
    max_queued_requests: int      # Backpressure
    throttle_delay_seconds: float # Adaptive slowdown
```

**Behavior:**
- Before any agent work: `governor.can_start_agent()` checks RAM, CPU, disk
- If RAM > 90%: all agents paused with `resource_throttle` broadcast
- If disk > 90%: warning issued, non-critical tasks delayed
- If LLM provider is down: `critical` severity, all inference blocked
- Configurable reserves: 4GB RAM, 30% CPU kept for OS/apps

#### Maintenance Mode (Test Isolation)

The Resource Governor supports an external **maintenance mode** that completely halts all agent work and LLM operations — independent of resource pressure. This is critical for machines with limited RAM (e.g. 8GB) where loading two models simultaneously would freeze the system.

**API:**
```
POST /api/settings/maintenance/pause?reason=simulation-tests   → halts all agents + LLM
POST /api/settings/maintenance/resume                           → resumes normal operations
GET  /api/settings/maintenance                                  → check current status
```

**How it works:**
1. `governor.enter_maintenance(reason)` sets `_maintenance_mode = True`
2. `compute_budget()` detects maintenance mode and returns a fully paused budget (0 agents, 0 LLM requests, 60s throttle)
3. All agent work loops (`can_start_agent()`) immediately return `False`
4. The MetaOrchestrator force-pauses all WORKING/IDLE agents to PAUSED state
5. On resume, agents return to IDLE and the governor resumes normal resource-based scheduling

**Used by the simulation test runner** (`tests/simulation/run.mjs`) to ensure the user's configured model is exclusively available for test LLM calls — no model switching, no dual-model loading.

### Model Recommendations

Hardware detection (`core/hardware.py`) auto-recommends models:

| Available RAM | Recommended Model | Context |
|--------------|-------------------|---------|
| < 4 GB | 1.5B (Qwen2.5-1.5B) | 2K |
| 4-8 GB | 3B (Gemma-3-3B) | 4K |
| 8-12 GB | 7B (Qwen2.5-7B) | 8K |
| 12-16 GB | 14B (Qwen2.5-14B) | 8K |
| 16+ GB | 32B+ | 16K+ |

Apple Silicon MLX quantizations are detected and preferred when available.

---

## Comparison With Industry Standards

### Agent Architecture Comparison

| Capability | Istara | Google ADK | LangGraph | CrewAI | AutoGen |
|-----------|--------|-----------|-----------|--------|---------|
| **Agent identity** | 4-file MD persona + 6-level context | Description string | Prompt template | Role/goal/backstory | System message |
| **Memory persistence** | SQLite + LanceDB + MEMORY.md + DAG | SessionService | Checkpointer | Short/long/entity | Conversation only |
| **Self-evolution** | Learnings → persona promotion | None | None | None | None |
| **Multi-agent coordination** | MetaOrchestrator + A2A messaging | Sequential/Parallel/Loop | Graph state machine | Crew processes | Group chat |
| **Skill/tool system** | 45+ domain skills with health monitoring | @tool decorator | @tool + chains | LangChain tools | Function registration |
| **Local-first** | Hardware governor, model rec, compression | No (cloud-first) | No | No | Docker only |
| **Prompt optimization** | Prompt RAG + LLMLingua + Context Guard | None | Token buffer | None | Message transforms |
| **Domain expertise** | Deep UXR (Atomic Research, Double Diamond) | Generic | Generic | Generic | Code/data focus |
| **Context management** | 6-level hierarchy + DAG summarization | None special | Graph state | None | Conversation history |
| **Output structure** | Nugget→Fact→Insight→Rec (evidence chains) | Unstructured | Unstructured | Pydantic models | Unstructured |

### Protocol Compatibility

| Protocol | What It Does | Istara Status |
|----------|-------------|---------------|
| **A2A** (Google) | Agent-to-agent communication, task lifecycle | Partial — DB-backed messaging, `/.well-known/agent.json` exposed |
| **MCP** (Anthropic) | Model-tool integration (resources, tools, prompts) | Compatible — skills can be exposed as MCP tools, contexts as resources |
| **OpenAI-compatible API** | LLM provider abstraction | Full — both LM Studio and Ollama use this |

### Prompt Compression Comparison

| Approach | Method | Requirements | Speed | Compression |
|----------|--------|-------------|-------|-------------|
| **LLMLingua** (Microsoft) | GPT-2 perplexity scoring | PyTorch + GPU | ~100ms | 2-20x |
| **LLMLingua-2** | BERT token classifier | PyTorch + GPU | ~50ms | 2-10x |
| **Istara heuristic** | Word importance + domain terms + sentence scoring | None (pure Python) | ~5ms | 1.2-2x |
| **Prompt RAG** (Istara) | Query-aware section retrieval | None | ~10ms | 1.5-3x |
| **Truncation** | Cut at token limit | None | ~0ms | Variable |

Istara trades compression ratio for **zero dependencies** and **instant speed** — the right trade-off for local-first where every millisecond of inference startup matters.

### Memory System Comparison

| System | Short-term | Long-term | Structured | Self-evolving |
|--------|-----------|-----------|-----------|---------------|
| **Istara** | Message history + DAG summaries | MEMORY.md + AgentLearning DB + Vector store | 6-level hierarchy + Atomic Research | Yes (promotion pipeline) |
| **LangChain** | Buffer/summary/token memory | VectorStoreMemory | Entity memory | No |
| **CrewAI** | Conversation buffer | RAG-based long-term | Entity tracking | No |
| **AutoGen** | Conversation history | None built-in | None | No |
| **ADK** | SessionService | MemoryService | None | No |

---

## Data Flow: End-to-End Examples

### Chat Message Flow (ReAct Tool-Use Loop)

```
1. User types "Create a task to analyze interview transcripts and attach report.pdf"
2. Frontend sends POST /api/chat with message + project_id + session_id
3. Backend:
   a. Loads session → gets assigned agent (e.g., istara-main)
   b. Prompt RAG: composes query-aware agent identity
      - Identity anchor (559 tokens) always included
      - Retrieves 8 relevant sections (interview skills, methodology protocols)
      - Skips UI audit skills, error handling — not relevant to query
   c. System Action Tools injected into system prompt (13 tools, structured schemas)
   d. Context Hierarchy: merges platform + company + project contexts
   e. RAG: retrieves relevant document chunks from vector store
   f. Token Counter: verifies total fits within max_context_tokens
   g. If over budget: LLMLingua compressor trims system prompt
   h. DAG Summarizer: compresses older messages, keeps fresh tail
   i. Sends to LLM via non-streaming chat (tool detection requires full response)
   j. ReAct Loop (max 3 iterations):
      - Extracts tool call from LLM response (JSON with "tool" + "args")
      - Executes tool via system_actions.execute_tool()
      - Injects tool result into conversation as system message
      - Re-sends to LLM for next reasoning step
      - Repeats until no more tool calls or iteration limit reached
4. Final text response streamed back via SSE events
   - Includes tool_call events for each tool executed
   - done event includes tools_used list
5. Saved to DB, DAG compaction triggered asynchronously
6. WebSocket broadcasts relevant events (task_queue_update, document_created, etc.)
```

### Skill Execution Flow

```
1. Task "Analyze interview batch" created (Kanban or file watcher auto-detect)
2. Agent orchestrator picks task (highest priority, assigned agent preferred)
3. Skill selected: "user-interviews" (from task.skill_name or keyword inference)
4. SkillInput assembled:
   - Files: interview transcripts from project upload dir
   - Project context: research questions, participant demographics
   - Company context: terminology, research standards
5. Skill.execute() runs:
   - Sends structured prompt to LLM with interview analysis methodology
   - Parses response into nuggets (quotes), facts (patterns), insights, recommendations
6. Findings stored in DB with evidence chains:
   - Nugget: "P3 said 'I couldn't find the settings menu'" (source: interview_p3.txt)
   - Fact: "3/5 participants struggled with settings navigation" (nugget_ids: [n1, n3, n5])
   - Insight: "Settings discoverability is a critical friction point" (fact_ids: [f1])
   - Recommendation: "Add settings shortcut to main nav" (insight_ids: [i1])
7. Self-check verifies claims against source documents
8. Artifacts (analysis report) ingested into vector store
9. Task moved to IN_REVIEW, WebSocket broadcasts progress
10. Skill quality recorded for health monitoring
```

### Self-Evolution Flow

```
1. Agent encounters error: "CSV parsing failed for non-UTF8 file"
2. agent_learning.record_error_learning():
   - category: "error_pattern"
   - trigger: "csv_encoding_error"
   - resolution: "Try latin-1 encoding as fallback"
   - confidence: 70
3. Next time similar error occurs:
   - agent_learning.get_error_resolution("csv") finds the pattern
   - Agent applies the known resolution
   - times_applied incremented, confidence adjusted
4. After 3+ occurrences across 2+ projects over 30 days:
   - self_evolution.scan_for_promotions() identifies this as promotable
   - Pattern written to PROTOCOLS.md under "Error Handling Protocol":
     "- CSV encoding errors: try latin-1 as fallback for non-UTF8 files"
   - Learning marked [PROMOTED] in DB
5. Agent permanently knows this pattern in every future interaction
```

---

## Phase Epsilon: Resilience, Rigor, and Context Mastery

### 1. Protected Prompt Architecture
Istara uses a SOTA structural prompting protocol to ensure that critical research methodology and instructions survive context compression and RAG injection.

**Protected XML Tags**:
- `<skill_context>`: Identity and phase information.
- `<research_methodology>`: Academic citations and procedural steps.
- `<instructions>`: Chain-of-Thought requirements and format rules.
- `<thinking>`: Mandatory reasoning block before JSON output.
- `<research_data>`: Raw data source (where compression is most aggressive).

**LLMLingua Protection Layer**:
The prompt compressor (`core/prompt_compressor.py`) implements a "Protected Region" mechanism. Any content wrapped in protected tags is temporarily replaced with UUID placeholders during the heuristic pruning phase, ensuring a 1.0 importance score for critical instructions.

### 2. Native Structured Outputs (JSON Schema)
To eliminate hallucination and formatting errors, Istara leverages native schema enforcement at the LLM engine level without forcing model reloads.

- **LM Studio**: Injects `response_format: { "type": "json_schema", ... }` into the OpenAI-compatible payload.
- **Ollama**: Passes the JSON schema directly to the `format` parameter in the `/api/chat` payload.

## Phase Zeta: Context Mastery and Orchestration Refinement

### 1. Tool Output Context Protection
To prevent aggressive compression from "forgetting" critical retrieved data during multi-step reasoning, Istara implements a dedicated protection layer for tool results.

- **Protected Tag**: `<tool_output>`
- **Behavior**: The prompt compressor (`core/prompt_compressor.py`) detects this tag and preserves the enclosed content at 100% fidelity.
- **Application**: Automatically applied to data-gathering tools like `get_document_content`, `search_documents`, and `web_fetch`.

### 2. Automated JSON Schema Translation
Istara maintains an "Ease of Use" standard for skill creation by allowing `output_schema` to be defined as simple example JSON objects. A dynamic translator in `skill_factory.py` automatically converts these into strict JSON Schemas.

### 3. Layer 5 Benchmarking (Real-World Orchestration)
The orchestration architecture has been validated with a new Layer 5 benchmark (`tests/integration/test_llm_orchestration_real.py`). This suite bypasses mocks to test live LLM connectivity, verified by:
- **100% TSQ**: Tool Selection Quality on complex, ambiguous goals.
- **DAG Decomposition**: Successful planning and serial/parallel execution of dependent research steps.
- **Resilient Recovery**: Graceful handling of malformed LLM outputs and automated retry logic.

### 4. Installer Resilience
The `scripts/install-istara.sh` utility now supports persistent port overrides. Configured `FRONTEND_PORT` and `BACKEND_PORT` values are automatically saved to `backend/.env` to ensure consistent state across system restarts.

- **Standard**: Converts `{"key": "value"}` → `{"type": "object", "properties": {"key": {"type": "string"}}, ...}`.
- **Strictness**: Enforces `additionalProperties: false` and `required` arrays for all nested objects.
- **Compatibility**: Guaranteed 100% adherence for LM Studio (strict mode) and Ollama without manual schema authoring.

---

## System Metrics & Observability

Istara tracks its own performance across four functional categories. Metrics are recorded to the local database and surfaced via the **Ensemble Health** dashboard.

### 1. Orchestration & Logic Metrics
| Metric | Category | Description | Target |
|--------|----------|-------------|--------|
| `json_parse_success_rate` | Reliability | % of agent turns that produced valid, schema-compliant JSON. | > 95% |
| `consensus_score` (κ) | Quality | Inter-rater agreement (Fleiss' Kappa) between multiple models. | > 0.65 |
| `dag_compaction_ratio` | Context | % reduction in history size achieved via lossless summarization. | > 60% |
| `validation_weight` | Adaptive | Relative importance of a validation method based on historical success. | Dynamic |

### 2. Research & Skill Metrics
| Metric | Category | Description | Target |
|--------|----------|-------------|--------|
| `avg_quality_ema` | Accuracy | Exponential moving average of LLM-reflected quality scores. | > 0.70 |
| `evidence_chain_integrity` | Rigor | % of findings with valid Nugget → Fact → Insight lineage. | 100% |
| `methodological_lift` | Academic | % of skills successfully grounding responses in cited frameworks. | > 80% |
| `transcription_confidence` | Accuracy | Word Error Rate (WER) and confidence score for audio processing. | > 0.85 |
| `icr_score` | Reliability | Inter-Coder Reliability score for qualitative thematic coding. | > 0.70 |

### 3. Compute & Hardware Metrics
| Metric | Category | Description | Target |
|--------|----------|-------------|--------|
| `latency_p90_ms` | Performance | 90th percentile response time for chat and skill execution. | < 15s |
| `vram_usage_pct` | Hardware | GPU memory saturation monitored by the Resource Governor. | < 85% |
| `cpu_load_pct` | Hardware | System CPU saturation across all cores. | < 70% |
| `active_agent_count` | Load | Number of concurrent agent threads active in the system. | < 10 |

### 4. Tool & Integration Metrics
| Metric | Category | Description | Target |
|--------|----------|-------------|--------|
| `tool_success_rate` | Functionality | % of MCP and System Action calls that executed without error. | > 98% |
| `rag_hit_rate` | Retrieval | % of queries where the retrieved context contained the answer. | > 75% |
| `prompt_similarity_score`| Context | Vector distance between query and retrieved context chunks. | > 0.80 |
| `self_evolution_count` | Maturity | Number of patterns promoted from AgentLearning to Persona files. | N/A |

---

### Simulation Framework

Istara includes a comprehensive **Playwright + Node.js simulation agent** at `tests/simulation/` that runs 66 scenarios covering:

| Category | Scenarios | Checks |
|----------|----------|--------|
| System health | Health check, onboarding, settings | 24 |
| Core features | Chat, file upload, skills, findings, Kanban, sessions | 80+ |
| Agent system | Architecture, communication, identity, personas, factory | 50+ |
| Data integrity | Vector DB, findings chains, task consistency | 30+ |
| Advanced | Full pipeline, self-verification, DAG, robustness | 50+ |
| Self-evolution & compression | Evolution scan, Prompt RAG, budget compliance, domain preservation | 35 |
| Documents system | CRUD, search, filtering, sync, backup, UI navigation, keyboard shortcuts | 25 |
| Event wiring audit | WebSocket event coverage, broadcast↔handler pairing, governor lifecycle, scheduler | 15 |
| Task-document linking & tools | Task CRUD with new fields, document attach/detach, URL updates, system tools | 15 |
| Interfaces & Stitch | Mock generate, design chat, Figma import, handoff briefs, variants | 30+ |
| Loops & schedule | Agent loops, custom loops, execution history, schedule CRUD | 16 |
| Notifications & backup | Notification CRUD, preferences, backup system, restore | 30 |
| Auth & security | Auth flow, content guard, process hardening, Docker security, data security | 40+ |
| Meta-hyperagent | Self-improvement proposals, architecture evaluation | 12 |
| **Total** | **66 scenarios** | **834 checks** |

### Evaluators

Three automated evaluators run after every scenario suite:

| Evaluator | What It Checks | Target |
|-----------|---------------|--------|
| **Accessibility** | WCAG 2.1 Level A violations | 0 critical/serious |
| **Heuristics** | Nielsen's 10 Usability Heuristics (scored 1-5) | Average ≥ 4.0/5 |
| **Performance** | Page load, response times, resource usage | 12 thresholds |

### Deep Small-Model Tests (Scenario 28)

The self-evolution and prompt compression scenario includes **35 checks** specifically validating small model handling:

- Different queries retrieve different persona sections (verified per-agent)
- Identity anchor preserved even for irrelevant queries
- Budget compliance at 1024 and 512 token limits
- Domain term preservation after compression (60+ UX terms protected)
- All 5 system agents produce valid composed prompts
- Custom agents get full Prompt RAG support
- Relevance scoring: query-matched sections score higher than unrelated ones

### Test Isolation (Single-Model Guarantee)

On machines with limited RAM (8GB), LM Studio can only load one model at a time without severe performance degradation. The simulation test runner uses the **Maintenance Mode** system to guarantee exclusive model access:

1. **Before tests start:** `POST /api/settings/maintenance/pause` — halts all Istara agent work and LLM calls
2. **During tests:** Tests use the user's currently configured model (no model switching). Only test LLM calls hit the model.
3. **After tests complete:** `POST /api/settings/maintenance/resume` — agents resume normal operation
4. **Crash safety:** Signal handlers (`SIGINT`, `SIGTERM`) and the `.catch()` handler call `emergencyResume()` to ensure the backend never stays permanently paused after a test crash

### Hardened Test Runner

The simulation runner includes built-in resilience features:

- **Sleep prevention**: Spawns `caffeinate -dims` (macOS) at startup, killed on exit — prevents display, idle, disk, and system sleep during long runs
- **Per-scenario timeout**: Each scenario has a 30-minute timeout via `Promise.race()`. If a scenario hangs, it is marked `TIMEOUT` and the runner proceeds to the next
- **Playwright timeouts**: Navigation and action timeouts set to 5 minutes (up from 30s default) to handle slow LLM inference
- **No-skip guarantee**: Every scenario runs regardless of prior failures. The runner never bails early
- **Structured failure summary**: After all scenarios complete, failures are categorized (TIMED OUT, ERRORS, FAILED CHECKS) with individual check names listed
- **JWT authentication**: All API calls in scenarios use the authenticated `ctx.api` client. Bare `fetch()` calls include `api._headers()` for JWT

---

## Configuration Reference

All settings are configurable via environment variables or `.env`:

### LLM Provider

| Setting | Default | Description |
|---------|---------|-------------|
| `LLM_PROVIDER` | `lmstudio` | `"lmstudio"` or `"ollama"` |
| `LMSTUDIO_HOST` | `http://localhost:1234` | LM Studio API endpoint |
| `LMSTUDIO_MODEL` | `default` | Model name (auto-detected) |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `qwen3:latest` | Default chat model |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model |

### Context & RAG

| Setting | Default | Description |
|---------|---------|-------------|
| `MAX_CONTEXT_TOKENS` | `8192` | Context window budget |
| `RAG_CHUNK_SIZE` | `1200` | Characters per chunk |
| `RAG_CHUNK_OVERLAP` | `180` | Overlap between chunks |
| `RAG_TOP_K` | `5` | Retrieved chunks per query |
| `RAG_SCORE_THRESHOLD` | `0.3` | Minimum relevance score |
| `RAG_HYBRID_VECTOR_WEIGHT` | `0.7` | Vector search weight |
| `RAG_HYBRID_KEYWORD_WEIGHT` | `0.3` | Keyword search weight |

### DAG Summarization

| Setting | Default | Description |
|---------|---------|-------------|
| `DAG_ENABLED` | `true` | Enable DAG summarization |
| `DAG_FRESH_TAIL_SIZE` | `32` | Messages kept verbatim |
| `DAG_BATCH_SIZE` | `32` | Messages per depth-0 node |
| `DAG_ROLLUP_THRESHOLD` | `4` | Children before rollup |
| `DAG_SUMMARY_MAX_TOKENS` | `300` | Max tokens per summary |

### Self-Evolution

| Setting | Default | Description |
|---------|---------|-------------|
| `PROMPT_COMPRESSION_STRATEGY` | `llmlingua` | `"llmlingua"`, `"prompt_rag"`, `"truncate"` |
| `PROMPT_RAG_USE_EMBEDDINGS` | `true` | Use embedding similarity for Prompt RAG |
| `PROMPT_RAG_TOP_K` | `8` | Dynamic sections to retrieve |
| `SELF_EVOLUTION_ENABLED` | `true` | Enable self-evolution scans |
| `SELF_EVOLUTION_AUTO_PROMOTE` | `false` | Auto-promote vs. user approval |

### Hardware

| Setting | Default | Description |
|---------|---------|-------------|
| `RESOURCE_RESERVE_RAM_GB` | `4.0` | RAM reserved for OS/apps |
| `RESOURCE_RESERVE_CPU_PERCENT` | `30` | CPU reserved for OS/apps |

---

## Frontend UX Architecture

### View Persistence & Navigation

Istara uses a single-page architecture with **22 views** rendered via a switch in `HomeClient.tsx`. Navigation state is persisted to `localStorage` so page refresh preserves the current view. The browser `document.title` updates to reflect the active view name (e.g., "Documents — Istara").

- **Keyboard shortcuts**: Cmd+1-0 for view switching, Cmd+K for search, Cmd+. for right panel toggle, ? for shortcuts help
- **Settings** is in the primary navigation (always visible, not hidden behind "More")
- **Custom events**: Components use `window.dispatchEvent(new CustomEvent("istara:navigate", { detail }))` for cross-component navigation

### Document View Modes

The Documents menu supports 3 display modes persisted to `localStorage`:

| Mode | Description | Row Height |
|------|-------------|------------|
| **Compact** (default) | Single-line rows: icon, title, status, source, time, actions | ~40px |
| **Grid** | Fixed-height cards in responsive 3-column grid | ~140px |
| **List** | Original card layout with reduced padding | ~80px |

### Interactive Research Visualizations

- **Convergence Pyramid** (Findings > Reports): Report cards at each layer (L2-L4) are clickable. Clicking shows a detail panel with executive summary, finding counts, tags, MECE categories, and linked documents.
- **UX Laws Catalog**: Law cards display violation count badges from project compliance data. "View violations" navigates to Findings filtered by that law.
- **Task Document Attachments**: Kanban task cards show document indicators. TaskEditor provides full attach/detach management for input and output documents.

### Skills Self-Evolution UI

The Skills > Proposals tab uses a two-column layout:
- **Left**: Self-improvement proposals (current value → proposed value diffs)
- **Right**: Skill creation proposals with collapsible prompt preview, phase badge, and specialties

### Agent Error Surfacing

Agent cards display meaningful error states:
- "Heartbeat Lost" when connection fails (not misleading "0 Errors")
- "Recent Errors" section in agent detail pulls from work logs with actionable descriptions

### Project Management

Projects now support pause/resume and delete from the sidebar context menu:
- **Pause**: `POST /projects/{id}/pause` — sets `is_paused=true`, agents and loops skip paused projects
- **Resume**: `POST /projects/{id}/resume` — clears pause, normal operation resumes
- **Delete**: Full cascade deletion of all project entities
- **Owner**: `owner_id` field for per-user project ownership in team mode
- **UI**: Right-click or hover menu on project items in sidebar with Pause/Delete actions

### Team Mode

Team mode can be toggled from the Settings UI (previously required `.env` edit):
- `POST /settings/team-mode` — persists to `.env`, admin-only in team mode
- Toggle switch in Settings page with live status display
- User management via the existing `UserManagement` component

### Security Mode & Insecure Detection (v2026.04.02.10)

Istara implements an automatic security audit for "Local Mode" deployments.
- **Local Mode** (`TEAM_MODE=false`): Designed for individual use on `localhost`. Authentication is bypassed for local connections.
- **Remote Enforcement**: The `/api/auth/login` endpoint explicitly rejects remote connections in Local Mode with a `403 Forbidden` error. Remote access in Local Mode requires a valid **Connection String** redeemed via `/api/connections/redeem`.
- **Team Mode** (`TEAM_MODE=true`): Full JWT-based authentication. Required for multi-user environments or networked servers.
- **Insecure Detection**: The `GET /api/auth/team-status` endpoint flags connections as `insecure: true` if the server is in Local Mode and accessed from a non-localhost IP.
- **Frontend Warning & Flow**: When `insecure: true` is detected, the `LoginScreen` hides standard login options and forces the "Join Server" (Connection String) flow to prevent unauthorized access.
- **Session Consistency**: The `authStore.ts` now handles `401 Unauthorized` responses from `fetchMe()` by broadcasting an `istara:auth-expired` event, ensuring invalid local tokens are cleared and the user is redirected to the login screen immediately.

### Cryptographic Access & Transport Security (v2026.04.10)

Istara now implements a comprehensive defense-in-depth security architecture spanning authentication, transport, container isolation, and network segmentation.

#### Authentication — NIST SP 800-63B Rev.4 Compliant

| Layer | Mechanism | Standard |
|---|---|---|
| **Password Hashing** | Argon2id (memory-hard, 64 MB, 3 iterations, 4 parallelism) | Password Hashing Competition winner |
| **Fallback** | PBKDF2-HMAC-SHA256 at 260K iterations (OWASP 2024 minimum) | Legacy compatibility |
| **Breach Checking** | Have I Been Pwned k-anonymity API — only 5 SHA-1 chars sent, full hash never leaves machine | NIST SP 800-63B Rev.4 |
| **2FA** | TOTP (RFC 6238) via pyotp — Google/Microsoft Authenticator compatible | RFC 6238 |
| **Passkeys** | WebAuthn/FIDO2 — device-bound biometric auth (Apple Secure Enclave, Windows Hello) | NIST AAL2/AAL3 phishing-resistant |
| **Recovery Codes** | 8 cryptographic codes per user, Argon2id hashed, one-time use | GitHub/Google pattern |
| **JWT** | HMAC-SHA256 with jti (revocation), mfa_verified claim, alg:none protection | RFC 7519 |
| **Cookies** | HttpOnly, Secure, SameSite=Strict session cookies | OWASP Session Management |

**User model additions:**
```
totp_secret: VARCHAR(64)        # TOTP shared secret
totp_enabled: BOOLEAN           # 2FA active flag
recovery_codes_hashed: TEXT     # Newline-separated Argon2id hashes
passkey_enabled: BOOLEAN        # WebAuthn registered
password_hash: VARCHAR(512)     # Widened from 255 for Argon2id
email: EncryptedType            # Fernet-encrypted PII
email_hash: VARCHAR(64)         # SHA-256 for uniqueness/search
```

**2FA Login Flow (End-to-End):**
The frontend now fully supports the 2FA login flow:
1. `LoginScreen.tsx` detects `requires_2fa: true` from `/api/auth/login`
2. Displays a conditional TOTP input panel (6 digits) with recovery code fallback
3. `authStore.ts` provides `verify2FA()` to complete authentication with TOTP or recovery code
4. Backend correctly withholds the JWT token until 2FA verification succeeds

**Passkey Integration (End-to-End):**
- `@simplewebauthn/browser` handles browser-side WebAuthn API calls
- `LoginScreen.tsx` shows "Sign in with Passkey" button in team mode
- `authStore.ts` provides `loginWithPasskey()`, `registerPasskey()`, `listPasskeys()`, `deletePasskey()`
- `SettingsView` includes `PasskeyManager` for registering and revoking passkeys
- Backend `/api/webauthn/*` routes are fully wired: register/start, register/finish, authenticate/start, authenticate/finish, credentials list/revoke

#### Transport Security — TLS 1.3 + HTTP Security Headers

Caddyfile hardening (production profile):
- TLS 1.2/1.3 only with explicit cipher suites: `TLS_AES_256_GCM_SHA384`, `TLS_CHACHA20_POLY1305_SHA256`, `TLS_AES_128_GCM_SHA256`
- ECDH curves: `X25519`, `secp256r1`, `secp384r1`

Backend `SecurityHeadersMiddleware` enforces on every response:
- HSTS with preload: `max-age=31536000; includeSubDomains; preload`
- Content Security Policy: `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'`
- Permissions Policy: camera, microphone, geolocation, payment, USB all disabled
- X-Frame-Options: DENY, X-Content-Type-Options: nosniff, X-XSS-Protection: 1; mode=block
- Referrer-Policy: strict-origin-when-cross-origin

#### Container Security — CIS Docker Benchmark

All containers hardened with:
- `cap_drop: ALL` — drop all Linux capabilities
- Minimal `cap_add` — only what's needed (CHOWN, SETUID, NET_BIND_SERVICE)
- `no-new-privileges: true` — prevents privilege escalation
- `read_only: true` — root filesystem read-only for backend, frontend, postgres
- `tmpfs` with `noexec,nosuid` — executable temp space with limited size
- `pids_limit` — prevents fork bomb attacks (200 backend, 100 frontend/ollama/postgres)
- Database ports (PostgreSQL 5432, Ollama 11434) **not exposed to host**

#### Field-Level Encryption

Sensitive data at rest is encrypted using Fernet (AES-128-CBC + HMAC-SHA256):
- `ChannelInstance.config_json` — Telegram/Slack/WhatsApp tokens
- `SurveyIntegration.config_json` — OAuth tokens, API keys
- `MCPServerConfig.headers_json` — Authentication headers
- `User.email` — PII (encrypted value + SHA-256 hash for uniqueness/search)

The `EncryptedType` SQLAlchemy type decorator transparently encrypts on write and decrypts on read. For fields requiring uniqueness constraints (e.g., email), a companion `email_hash` column stores a deterministic SHA-256 hash for equality lookups while the plaintext remains encrypted.

#### Network Segmentation — Zero Trust

Three isolated Docker networks:
| Network | Members | External Access |
|---|---|---|
| `frontend-net` | Caddy, Frontend | Yes (ports 80/443) |
| `backend-net` | Backend, Caddy, Relay | No (internal) |
| `data-net` | Ollama, PostgreSQL | No (internal) |

Frontend cannot reach database or Ollama directly. Only Caddy bridges frontend↔backend.

#### Mid-Execution Steering (v2026.04.10)

A new real-time communication channel lets users inject messages to agents **while they're working**, inspired by pi-mono's steering pattern.

**Architecture:**
- `SteeringQueue` — mirrors pi-mono's `PendingMessageQueue`, supports `one-at-a-time` and `all` drain modes
- `FollowUpQueue` — messages delivered only when agent finishes all work
- **Thread-Safety**: Uses `asyncio.Lock` per agent state to synchronize API requests and the agent work loop.
- **Deferred execution**: steering messages NEVER interrupt in-progress skills; they wait for current turn to complete
- **Abort**: clears both queues, signals agent to stop (like pi-mono's Escape)
- In-memory only — no database persistence needed

**API endpoints:**
```
POST /api/steering/{agent_id}              # Queue steering message
POST /api/steering/{agent_id}/follow-up    # Queue follow-up message
POST /api/steering/{agent_id}/abort        # Abort current work
GET  /api/steering/{agent_id}/status       # Get queue counts
GET  /api/steering/{agent_id}/queues       # Get message contents
DELETE /api/steering/{agent_id}/queues     # Clear all queues
GET  /api/steering/{agent_id}/idle         # SSE: wait until agent idle
```

**Frontend:** `SteeringInput` component renders when `agent.state === 'working'`, shows queue count badge, abort button, and retrieve-queued-messages button.

#### Compass Authorship Enforcement

Pre-push hook (`.git/hooks/pre-push`) automatically rewrites author, committer, and strips `Co-authored-by` trailers before every push. Ensures only `henrique-simoes <simoeshz@gmail.com>` appears on GitHub.

### Document Organization

Documents view now includes an "Organize Files" function (ported from Interviews):
- AI-powered analysis: sends a chat request to categorize and tag project documents
- Streaming results displayed in a collapsible panel
- Does NOT rename or move files — only recommends structure

### Custom Loop Skill Selection

Custom loops now use a dropdown populated from the skill registry instead of free-text input:
- Fetches all registered skills from `/api/skills`
- Dropdown shows skill names for selection
- Description field explains what the loop will do with the selected skill

### Interfaces & Design System

The **Interfaces** menu (sidebar item 10) provides AI-powered design tools integrating Google Stitch, Figma, and automated handoff documentation.

#### Architecture

| Component | File | Purpose |
|---|---|---|
| Backend routes | `backend/app/api/routes/interfaces.py` (1615 lines) | Design chat, screen generation, Figma, handoff |
| Frontend | `frontend/src/components/interfaces/InterfacesView.tsx` | Full UI for all design features |
| API client | `frontend/src/lib/api.ts` → `interfaces.*` | 13 methods: screens, generate, variants, edit, figma, handoff, configure, designChat |
| Core service | `backend/app/services/stitch_service.py` | Google Stitch API integration |
| Design tools | `backend/app/skills/design_tools.py` | Screen generation, variant creation, editing |
| Figma client | `backend/app/services/figma_service.py` | Figma API integration (import/export/components) |
| Handoff | `backend/app/services/handoff_service.py` | Design briefs and dev spec generation |

#### Google Stitch (Generative AI Screen Design)

- **`POST /api/interfaces/screens/generate`**: Generate UI screens from text description using Stitch API
- **`POST /api/interfaces/screens/edit`**: Edit existing screens with natural language instructions
- **`POST /api/interfaces/screens/variant`**: Generate alternative design variants
- **`GET /api/interfaces/screens`**: List all generated screens
- **`DELETE /api/interfaces/screens/{screen_id}`**: Delete a screen
- Screens stored with: id, project_id, prompt, image_url, metadata (timestamps, model used)
- Screens appear in the Interfaces > Screens tab with thumbnail grid

#### Design Chat

- **`POST /api/interfaces/design-chat`**: Chat with AI about design decisions (uses RAG with project context)
- **`GET /api/interfaces/design-chat/{project_id}/history`**: Retrieve design conversation history
- Design chat uses same architecture as main chat: RAG retrieval, agent identity, budget-aware token allocation
- Pixel agent can be selected for design-specific conversations

#### Figma Integration

- **`POST /api/interfaces/figma/import`**: Import Figma designs (components, styles, frames)
- **`POST /api/interfaces/figma/export`**: Export designs back to Figma
- **`GET /api/interfaces/figma/design-system/{file_key}`**: Get design system info from Figma file
- **`GET /api/interfaces/figma/components/{file_key}`**: List components from Figma file
- Figma token stored encrypted via field encryption (`ENC:` prefix)
- Token configured via `POST /api/interfaces/configure/figma`

#### Handoff Documentation

- **`POST /api/interfaces/handoff/brief`**: Generate design brief with UX law references and evidence
- **`POST /api/interfaces/handoff/dev-spec`**: Generate developer specification document
- **`GET /api/interfaces/handoff/briefs`**: List all handoff briefs for a project
- Design briefs include: UX laws referenced (pill badges), source findings (evidence cards), recommendations with attributions
- Handoff bridges design intent to development implementation

#### Screen Generation Flow

1. User describes desired screen in Interfaces > Generate tab
2. Backend calls Stitch API (Google) or design_tools.py (local generation)
3. Generated screen stored with metadata (prompt, timestamp, model)
4. Screen appears in thumbnail grid with full-screen preview
5. User can edit screen with natural language ("make the button blue")
6. User can generate variants for A/B testing

#### Figma Import/Export Flow

1. User provides Figma file key and personal access token
2. Backend calls Figma API to fetch components, styles, frames
3. Imported components stored in project context
4. User can edit components and export changes back to Figma
5. Design system sync keeps local and remote in sync

#### Agent Integration

- **Pixel** (UI audit agent) uses `design_tools.py` for screen analysis
- **Cleo** (primary researcher) can execute design skills via task routing
- Design chat uses same agent identity system as main chat
- Screen generation triggers RAG retrieval for project-specific design context

#### Data Models

| Model | Table | Fields |
|---|---|---|
| Screen | `screens` | id, project_id, prompt, image_url, metadata, created_at, updated_at |
| Design Brief | `design_briefs` | id, project_id, content, ux_laws, source_findings, created_at |
| Handoff Spec | `handoff_specs` | id, project_id, content, dev_notes, created_at |

#### Configuration

- Google Stitch API key: `STITCH_API_KEY` in `.env` or via `POST /api/interfaces/configure/stitch`
- Figma token: `FIGMA_API_TOKEN` in `.env` or via `POST /api/interfaces/configure/figma`
- Design screens directory: `settings.design_screens_dir` (default: `./data/design_screens`)

### Google Stitch (Generative AI) Configuration

The Interfaces > Figma tab now includes Google Stitch API key configuration:
- Input field with save/status indicator (same UX pattern as Figma token)
- Link to Google AI Studio for API key generation
- Backend: `POST /interfaces/configure/stitch` persists key to `.env`

### Design Brief Evidence Display

Design Briefs in the Handoff tab now show structured evidence:
- **UX Laws Referenced**: Indigo pill badges for each law the brief considers
- **Source Findings**: Evidence cards showing finding type (nugget, insight) and text
- **Recommendations**: Bulleted list with optional UX law attribution

### Agent Heartbeat Recovery

Agents stuck in ERROR state now auto-recover:
- Backend `HeartbeatManager` resets agents to IDLE after 120s without new errors
- New `POST /agents/{id}/restart` endpoint for manual recovery (clears error counters)
- Frontend polling keeps heartbeat status current (10s interval)

### Agent Scope System

Agents have a `scope` field that determines their visibility:
- **Universal** (default for system agents): Visible across all projects
- **Project**: Scoped to a single project, only visible when that project is active

**Promotion Flow** (team mode):
- Users can request promotion of project-scoped agents to universal via `POST /agents/{id}/request-promotion`
- This creates an admin notification under the `agent_promotion` category
- Only admins can promote agents via `POST /agents/{id}/set-scope`
- System agents are always universal and cannot be demoted

**API**: `GET /agents` accepts optional `project_id` to filter — returns universal agents + project-scoped agents for that project. Without `project_id`, returns all agents (admin/global view).

**Model fields**: `scope` (VARCHAR 10, default "universal"), `project_id` (VARCHAR 36, default "")

### First-Run Onboarding

Fresh server installations follow this flow:
1. **No team mode (default)**: LoginScreen shows local-mode hint. Any credentials work. User gets admin JWT.
2. **Team mode, no users**: LoginScreen auto-switches to registration mode with "First user — you will be the admin" prompt. First registered user becomes admin.
3. **Team mode, users exist**: LoginScreen shows login form with "Create an account" toggle for new team members.
4. **Client connecting to existing server**: Login with credentials provided by admin.

The `/api/auth/team-status` endpoint returns `{team_mode, registration_enabled, has_users}` so the frontend knows which flow to show.

### Auth State Restoration

On page refresh, the JWT token persists in localStorage but the `user` object is lost. The `fetchMe()` method calls `GET /api/auth/me` to restore the full user (including `role`) from the JWT. This ensures admin UI (UserManagement, team mode toggle) is always visible to admins.

### Project Data Isolation

Views that require a project context show a "No Project Selected" prompt when no project is active, preventing cross-project data leakage. The `activeProjectId` is cleared from localStorage when all projects are deleted, preventing stale references.

Backend endpoints with optional `project_id` parameters (documents, findings, notifications, deployments) return all data when called without a project — the frontend guard prevents this in normal usage.

### Stability Fixes

- **Integrations**: Wrapped in `<ErrorBoundary>` with loading guards; error cleared on tab switch; API response unwrapping for surveys and MCP
- **Chat**: Messages container uses `h-0 flex-1` pattern for stable scrolling on session changes
- **Compute Pool**: Fully scrollable within `overflow-y-auto` container; relay capability detection on registration
- **Meta-Agent**: Long content contained with `min-w-0`, `break-all`, `truncate`
- **Sidebar**: Nav + projects share single scrollable container — "More" expansion no longer pushes projects off-screen

---

## Connection String Protocol

Tamper-proof bundles for secure client→server setup. Format: `rcl_<base64url(JSON)>.<base64url(HMAC-SHA256)>`

Payload contains: `server_url`, `ws_url` (relay WebSocket), `network_token` (NETWORK_ACCESS_TOKEN), `jwt` (pre-minted for web login), `expires_at`, `label`.

**Flow:**
1. Admin generates in Settings → `POST /connections/generate` (admin-only)
2. Client validates → `POST /connections/validate` (public, no auth required)
3. Client redeems → `POST /connections/redeem` (creates user account, returns JWT + network token)

One string gets a team member both web UI access (JWT) and relay compute donation (network token). Strings are HMAC-signed with `JWT_SECRET` — only the originating server can create valid ones.

**Token rotation:** `POST /connections/rotate-network-token` generates new NETWORK_ACCESS_TOKEN, invalidates all existing connection strings, broadcasts to connected relays.

**Files:** `backend/app/core/connection_string.py`, `backend/app/api/routes/connections.py`

## Desktop App (Tauri v2)

System tray application for macOS, Windows, and Linux. **Rust-native process management** — spawns Python/Node directly as tracked `Child` processes via `std::process::Command`. No shell script dependency. Cross-platform via `#[cfg(target_os)]` blocks.

- **Server+Client**: Spawns uvicorn backend + npm frontend directly. Menu: Open Browser, Start/Stop Server (with live port-based label), LLM Status (with donation toggle), Compute Donation, Check for Updates, Quit.
- **Client-only**: Manages relay daemon only. Menu: Connection Status, Open Browser, Compute Donation, Change Server, Check for Updates, Quit.

Built with Tauri v2 (5-15 MB binary, ~20 MB RAM). Process management via Rust `std::process::Command` with PID tracking, zombie detection (`try_wait()`), and platform-specific port cleanup. Config stored at `~/.istara/config.json`.

**macOS Tahoe (26.x) compatibility**: `SYSTEM_VERSION_COMPAT=0` env var for correct Python version detection. `build_enriched_path()` constructs PATH for GUI apps (Homebrew ARM/Intel, nvm, pyenv, fnm, system). TCC local network privacy prompt handled by keeping app alive during startup.

**Windows**: `CREATE_NO_WINDOW` flag for headless processes. Port cleanup via `netstat -ano` + `taskkill /PID /F`.

**Linux**: AppImage + .deb builds via GitHub Actions CI/CD.

**Files:** `desktop/src-tauri/src/{main,commands,process,tray,health,config,stats,path_resolver}.rs`, `desktop/src/` (HTML stats popover)

## Versioning & Auto-Updates

### CalVer Versioning
Istara uses date-based CalVer: `YYYY.MM.DD` (e.g., `2026.03.29`). Multiple builds in one day use `YYYY.MM.DD.N` (e.g., `2026.03.29.2`). Version is set across 8 files by `scripts/set-version.sh` and stored in a root `VERSION` file.

**Files updated**: `VERSION`, `desktop/src-tauri/tauri.conf.json`, `desktop/package.json`, `desktop/src-tauri/Cargo.toml`, `frontend/package.json`, `relay/package.json`, `backend/pyproject.toml`, `installer/windows/nsis-installer.nsi`

### Update Check System
- `GET /api/updates/version` — returns current version from VERSION file (public, no auth). Fixed: resolves VERSION from multiple candidate paths (parents[4], parents[3], CWD, CWD parent) to handle different install layouts.
- `GET /api/updates/check` — queries GitHub Releases API, compares CalVer strings lexicographically, returns `{update_available, latest_version, downloads, changelog}`
- `POST /api/updates/prepare` — creates pre-update backup (admin-only in team mode), returns backup ID
- `POST /api/updates/apply` — **one-click auto-update**: creates backup → generates a background shell script → stops services → `git pull` → `pip install` → `npm install && npm run build` → restarts services. The script runs in a detached process (`start_new_session=True`) that survives server shutdown. Returns immediately with `{status: "updating"}`.

### Startup Update Check
On backend startup (15s delay), `check_for_updates_on_startup()` queries GitHub API. If a newer version exists, it:
1. Broadcasts `update_available` WebSocket event to all connected clients
2. Persists an `update_available` notification to the database (category: `system`, severity: `info`, action: navigate to settings)
Notification types added to EVENT_METADATA: `update_available`, `update_started`, `update_failed`.

### CLI Update Command
`istara update` — stops services → `git pull` → updates pip deps → rebuilds frontend → starts services. Shows progress with version diff (e.g., "Updated from 2026.03.30.13 to 2026.03.30.14").

### Frontend Update Notification
`UpdateChecker` component in Settings page auto-checks on mount. Shows:
- Current version (from `/api/updates/version`)
- Update available banner with version, release name, changelog preview
- **"Update Now" button** → calls `POST /api/updates/apply` → shows progress: "Creating backup..." → "Pulling latest code..." → "Restarting server..." → polls `/api/updates/version` every 3s until server comes back → auto-reloads the page
- Fallback: if auto-update fails, shows error with suggestion to run `istara update` from terminal

### Desktop Tray Update Notification
`health.rs` checks GitHub Releases every 6 hours and emits `update-available` when a newer published release exists. The tray's "Check for Updates" menu item uses Tauri updater first for packaged installs, then GitHub Releases guidance for source installs. The old local `git fetch --tags` path was removed because tag divergence/clobbering made it unreliable in the field.

### CI/CD Release Flow
Regular CI and installer publishing are related but distinct:
- `.github/workflows/ci.yml` runs governance + build/test checks for normal development
- `.github/workflows/build-installers.yml` publishes installers/releases on **release-worthy** pushes to `main`
- tag pushes (`v*`) and manual dispatch remain available for explicit release control or rebuilds

Recommended local release prep:
```bash
./scripts/prepare-release.sh --bump
```

On a release-worthy push to `main`, tag push (`v*`), or manual dispatch:
1. `version` job determines CalVer string
2. `build-macos` + `build-windows` jobs set version, build Tauri + DMG/EXE
3. `release` job creates GitHub Release with both artifacts and auto-generated release notes

**Files**: `scripts/set-version.sh`, `scripts/prepare-release.sh`, `backend/app/api/routes/updates.py`, `frontend/src/components/settings/UpdateChecker.tsx`, `desktop/src-tauri/src/health.rs`, `.github/workflows/ci.yml`, `.github/workflows/build-installers.yml`

## Installation Methods

### Architecture: Installer vs Manager

Istara separates **installation** from **management**:
- **Installation** is handled by the shell one-liner (`install-istara.sh`) or Homebrew. The shell installer is now explicitly mode-aware: it explains Server vs Client use, explains Homebrew before installing it, helps the user choose LM Studio vs Ollama, gives first-model onboarding steps, writes `~/.istara/config.json`, and always attempts to install the desktop companion app on macOS.
- **Management** is handled by the CLI (`istara start/stop/status/update`) or the desktop tray app (`Istara.app`). The desktop app adapts to the selected mode: Server mode manages local backend/frontend/relay; Client mode opens the remote workspace from the saved `rcl_...` invite and offers invite changes plus compute donation controls.

> **Note:** The DMG/EXE native installers are currently experiencing issues and should not be used. Use Homebrew or the shell one-liner instead.

### Homebrew (macOS — Recommended)
```bash
brew install --cask henrique-simoes/istara/istara
```
Custom tap at `henrique-simoes/homebrew-istara`. Cask formula at `homebrew/istara.rb`. Uses `livecheck` with `:github_latest` strategy for version detection. `auto_updates true` since the app has built-in auto-updater. `zap` stanza cleans `~/Library/Application Support/com.istara.desktop/`, `~/.istara/`, LaunchAgent, caches.

### Shell One-Liner (macOS / Linux)
```bash
curl -fsSL https://raw.githubusercontent.com/henrique-simoes/Istara/main/scripts/install-istara.sh | bash
```
Interactive terminal wizard that:
1. Asks for mode: **Server** (full install) or **Client** (relay only)
2. Explains Homebrew if missing, then installs missing dependencies via Homebrew (Python 3.12, Node, Git)
3. Detects LM Studio / Ollama, lets the user choose the default provider, and gives first-model onboarding guidance
4. Keeps source installs on the git checkout and updates them with `git pull`
5. Creates Python venv, installs pip dependencies
6. Installs frontend dependencies, builds production Next.js
7. Generates `.env` with security keys (JWT, encryption, network token)
8. Creates `istara` CLI command in PATH
9. Automatically attempts to install `Istara.app` to `/Applications/` and uses the saved config to open in Server or Client mode
10. Offers to start the server immediately

This matters because packaged installs and source installs are different update surfaces. Packaged apps follow GitHub Releases and Tauri updater artifacts. Source installs stay on the git checkout, but Settings still checks against the latest published release before offering backup-first update orchestration.

Handles edge cases: keg-only Homebrew formulas, prompts inside `$(...)` write to `/dev/tty`, `set -eo pipefail` (not `-u`), ERR trap for debugging.

### Uninstall
```bash
curl -fsSL https://raw.githubusercontent.com/henrique-simoes/Istara/main/scripts/uninstall-istara.sh | bash
```
Interactive uninstaller: scans for all Istara files, requires typing "uninstall" to confirm, stops processes, removes LaunchAgent, desktop app, install directory, shell PATH entries, logs. Optionally removes dependencies (Python, Node, Ollama) with individual Y/n prompts defaulting to No.

### CLI Management (`istara.sh`)
```bash
istara start    # Start backend + frontend (production mode)
istara stop     # Stop both
istara restart  # Stop then start
istara status   # Show what's running + LLM connectivity
istara update   # Pull latest source, rebuild, restart
istara logs     # Tail both log files
```
- Uses venv Python (`$ROOT/venv/bin/python`) — not bare `python`
- Finds npm via `_find_npm()` checking keg-only Homebrew paths
- Uses `npm start` (production) when `.next/` build exists, `npm run dev` for development
- PID verification: checks if process died immediately after spawn, shows log tail on failure
- Health check polling: waits up to 15s for backend, 20s for frontend
- `istara update` uses the original source-update path again: stop services, `git pull`, refresh dependencies, rebuild, restart. The source install remains a git checkout, while packaged app installs remain release-artifact based.

### First-Run Auth & Onboarding Integrity
- `HomeClient` no longer treats "token exists in localStorage" as authenticated. It now checks `/api/auth/team-status`, validates the JWT via `/api/auth/me`, and only then enters the main app bootstrap. This prevents the long-standing flash where users briefly saw the main UI before being bounced to login/register.
- The onboarding/tour bootstrap now treats **zero projects** as a fresh-system signal even if the browser has stale `istara_tour_completed` state from an earlier install. This fixes the persistent case where a genuinely first-time server user failed to get the wizard because old browser state said the tour was already complete.
- `LoginScreen` now waits for the authenticated bootstrap callback to complete after register/login/join flows, so first-time users land in a verified state before the tour logic runs.

### Desktop App (Tauri v2) — Tray Manager
System tray application for macOS, Windows, and Linux. **Mode-aware manager only — does not replace the shell installer for full setup.**

**Architecture: Rust-Native Process Management** — The tray app owns all child processes (backend, frontend, relay) as Rust `Child` handles via `std::process::Command`. No shell script dependency. `istara.sh` remains as a CLI tool but the tray app operates independently.

- **Start/Stop**: `ProcessManager.start_server()` spawns Python uvicorn + npm start directly. Returns immediately (non-blocking). Port cleanup via platform-specific `kill_port_holders()`. Menu rebuilds when health loop detects port state change.
- **Path resolution**: `path_resolver.rs` finds Python/Node at venv (8 paths checked: venv/.venv at install root and backend/), Homebrew ARM/Intel, pyenv, nvm, fnm, python.org, system. `build_enriched_path()` constructs comprehensive PATH for GUI apps that don't inherit shell PATH.
- **Menu state**: Driven by port checks (`127.0.0.1:8000`, `:3000`, `:1234`, `:11434`). Labels show `● Stop` when running, `○ Start` when down.
- **Compute Donation**: Config toggle with confirmation dialog. Relay managed as Child process with zombie detection.
- **LLM Status Click**: Dialog with donation toggle or LM Studio launch.
- **Client Open Behavior**: In Client mode, "Open Istara" opens the remote `server_url` derived from the saved connection string instead of checking local ports.
- **Client Donation Guardrail**: Enabling Compute Donation in Client mode requires a saved `rcl_...` invite; otherwise the app explains how to add one.
- **Check Updates**: Three-tier (Tauri updater, git tags, GitHub releases). Always shows a result dialog and only opens GitHub Releases when the user explicitly confirms.
- **Health loop**: Polls ports every 10s, rebuilds menu on change or every 30s. Checks updates every 6h via git tags.
- **Zombie detection**: `try_wait()` on all Child handles every cycle. Dead processes cleaned up automatically.
- **Platform specifics**:
  - macOS: `SYSTEM_VERSION_COMPAT=0` for Tahoe, PATH includes `/opt/homebrew/bin`
  - Windows: `CREATE_NO_WINDOW` flag, `netstat`+`taskkill` for port cleanup
  - Linux: Standard POSIX process management, AppImage distribution
- **Config resilience**: corrupt `config.json` backed up to `.json.bak` before reset.
- Auto-start via `~/.istara/config.json` — reads `mode`, `install_dir`, `donate_compute`. Runs `istara.sh start` in background thread. Startup errors are logged (not silently discarded).
- **ANSI stripping**: `istara.sh` output contains terminal colors; `strip_ansi()` cleans output for error dialogs.

### Login UX
- **Local mode** (default, single user): "Welcome to Istara" screen with name field only, "Get Started" button, no password. Backend accepts any credentials and issues admin JWT.
- **Team mode** (multi-user): Full login/register/join-server flow. First user becomes admin. Connection strings for team members.
- **Server unreachable**: Dedicated error screen showing the API URL and `istara start` command.

### CI/CD (GitHub Actions)
`.github/workflows/build-installers.yml` handles publishing:
- On a release-worthy push to `main`: builds installers and creates GitHub Release
- On tag push (`v*`): builds installers and creates GitHub Release
- On manual dispatch: builds installers/releases on demand
- Release-worthiness is determined from changed files, not just branch name. Backend/frontend/desktop/relay/install/update changes qualify, as do Compass-critical internal agent docs and persona changes that materially alter how Istara's internal agents understand the system.
- CalVer for qualifying `main` pushes is derived from the latest existing release tag, not the committed `VERSION` file. This prevents same-day qualifying pushes from silently colliding on the same release version.

`.github/workflows/ci.yml` enforces repository governance on pushes to `main` and pull requests:
- Generated docs must be current: `python scripts/update_agent_md.py --check`
- Integrity stack must be coherent: `python scripts/check_integrity.py`
- Change obligations must be satisfied: `python scripts/check_change_obligations.py`
- That governance check fails when architecture/process/release-sensitive code changes without corresponding updates to `Tech.md`, tests, or Istara persona files

### Secret Generation
`scripts/generate-secrets.sh` generates ALL production secrets:
- `JWT_SECRET` — 32-byte base64 for token signing
- `DATA_ENCRYPTION_KEY` — 32-byte base64 for data at rest
- `NETWORK_ACCESS_TOKEN` — 32-byte for relay/network auth
- `RELAY_TOKEN` — 24-byte for relay daemon auth
- `POSTGRES_PASSWORD` — 16-byte for team mode PostgreSQL

**Files:** `scripts/install-istara.sh`, `scripts/uninstall-istara.sh`, `istara.sh`, `homebrew/istara.rb`, `.github/workflows/build-installers.yml`, `desktop/src-tauri/src/{main,commands,process,tray,health,config,stats,path_resolver}.rs`

## Browser Compute Donation

`DonateComputeToggle` component in Settings. When enabled:
1. Detects local LLM (LM Studio port 1234, Ollama port 11434)
2. Opens WebSocket to `/ws/relay` with JWT auth
3. Registers as browser compute node
4. Proxies LLM requests from server to local LLM via `fetch()`
5. Sends heartbeat every 30s

**Limitation:** Browser tabs throttle background WebSockets. Displayed note recommends desktop app for reliable donation.

**Files:** `frontend/src/components/common/DonateComputeToggle.tsx`

## InteractiveSuggestionBox

Reusable AI suggestion panel with chat session linking. Replaces static text boxes (e.g., Document "Organize" result) with an interactive component.

**Architecture:**
1. Creates a real chat session via `sessionsApi.create()` with title "Suggestion: {title}"
2. Streams the AI response via `chatApi.send(projectId, prompt, sessionId)` SSE async generator
3. Auto-scrolls as new content arrives (`useRef` + `scrollIntoView`)
4. Shows "Continue in Chat" link — dispatches `istara:navigate` with `{ view: "chat", session_id }`. HomeClient handles this by calling `selectSession(session_id)`.
5. Quick-reply input sends follow-up to the same session, streaming the response inline
6. All messages persist in the chat session — user can revisit in the Chat view

**Global Toast API:** Any component can trigger a toast via `window.dispatchEvent(new CustomEvent("istara:toast", { detail: { type, title, message } }))`. `ToastNotification.tsx` listens for these events and calls `addToast()`. Used by Documents Sync, available globally.

**Notification Bell:** Moved from sidebar nav list to sidebar header (next to dark mode toggle). Shows red unread count badge from `useNotificationStore`. Polls every 30s. WCAG: `aria-label` includes count, badge uses `aria-hidden`.

**Error Extraction Fix:** `api.ts` now handles FastAPI validation errors (422) where `detail` is an array of `{ loc, msg, type }` objects. Extracts `msg` fields and joins with semicolons instead of showing `[object Object]`.

**LLM Server API Key Support:** Settings > LLM Servers now has an optional API key field when adding servers. Keys are encrypted on save (`encrypt_field`), passed as `Authorization: Bearer` header to the LLM provider. The health check detects 401/403 auth failures and reports `health_error: "API key required"` — displayed as red text below the server entry. Relay nodes accept `--llm-api-key` flag for authenticated local LLMs. The relay admin configures the key once; users connecting via relay don't need separate keys.

**Tour Timing Fix:** `HomeClient.tsx` now waits for backend health (`GET /api/health`) with up to 15 retries (2s each) before checking projects and starting the tour. Prevents the race condition where frontend loads before backend, causing empty project list and wrong tour state or missing tour.

**Files:** `frontend/src/components/common/InteractiveSuggestionBox.tsx`, `frontend/src/components/common/ToastNotification.tsx`, `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/lib/api.ts`, `frontend/src/components/documents/DocumentsView.tsx`, `frontend/src/components/layout/HomeClient.tsx`, `frontend/src/components/common/EnsembleHealthView.tsx`, `frontend/src/components/common/SettingsView.tsx`, `backend/app/core/compute_registry.py`, `backend/app/api/routes/llm_servers.py`, `relay/lib/llm-proxy.mjs`, `relay/index.mjs`

## Chat System

### Markdown Rendering
Chat messages render markdown using `react-markdown` + `remark-gfm` with Tailwind `prose` classes. Headers, bold, code blocks, tables, and lists all render properly. User messages stay plain text; assistant messages get full markdown treatment. Streaming responses also render markdown in real-time.

### File Attachment UX
Files queue as preview chips before sending (not uploaded on select). Multiple files supported. Chips show filename + remove button. On send: files upload via `POST /api/files/upload/{project_id}`, then the message includes `[Attached files: ...]` context.

### Project Document Picker
A FolderOpen button opens a searchable dropdown of project documents (calls `GET /api/documents/list` with search param). Selected docs appear as purple reference chips alongside file chips. Referenced docs are included as `[Referenced project documents: ...]` in the message.

### Task Instructions Passthrough
The Task model's `instructions` field (Specific Instructions) is now included in LLM prompts. Previously silently dropped. Both `_execute_general_task()` and SkillInput construction include it.

**Files:** `frontend/src/components/chat/ChatView.tsx`, `backend/app/core/agent.py`

## Ensemble Validation Integration

The ensemble validation framework (5 methods: Self-MoA, Dual Run, Adversarial Review, Full Ensemble, Debate Rounds) is wired into the agent execution loop. After every skill execution in `agent.py`, the `AdaptiveSelector` picks the best validation method based on historical performance, runs it, and records the result.

**Self-MoA as default:** Works with a single LLM server by varying temperature (0.3, 0.7, 1.0). Multi-server methods (dual_run, full_ensemble) require 2+ registered servers.

**Data flow:** Skill execution → AdaptiveSelector.select_method() → validation function → consensus scoring (Fleiss' Kappa + cosine similarity) → task.validation_method/consensus_score updated → MethodMetric recorded → EnsembleHealthView displays aggregated data.

**File classification:** CSV files classified by column headers: survey keywords (SUS, rating, score, satisfaction, NPS) → `survey_data`, interview keywords → `interview_transcript`, otherwise `csv_data`. Prevents misclassification of survey CSVs as interviews.

**Files:** `backend/app/core/agent.py`, `backend/app/core/validation.py`, `backend/app/core/adaptive_validation.py`, `backend/app/core/consensus.py`, `backend/app/core/file_processor.py`

## Agent Architecture Overhaul (v2026.04.01.5)

### ReAct Tool Loop for Autonomous Tasks
The agent orchestrator now has tool-calling intelligence for general tasks (no matching skill). Uses the same 15 tools available in chat (create_task, search_documents, search_findings, search_memory, etc.) with a 5-iteration max ReAct loop. Native OpenAI tool calling with fallback to single-call on API rejection.

### RAG Before Skill Execution
Before skill selection, the agent retrieves relevant documents via `retrieve_context()`. RAG context is injected into SkillInput.user_context so skills have document awareness without loading all files.

### Timeout Protection
`skill.execute()` wrapped in `asyncio.wait_for(timeout=300)`. Skills that take >5 minutes produce a timeout SkillOutput.

### LLM Self-Reflection
Replaced heuristic `_self_verify_output()` with `_llm_reflect_on_output()`. Sends task + output to LLM with structured evaluation prompt. Checks: addresses task, evidence-based, chain complete, no hallucinations. Returns `{verified, confidence, reason}` JSON. Falls back to heuristic on failure.

### A2A Collaboration Activated
Agents now poll their A2A inbox every work cycle via `_process_a2a_inbox()`. Collaboration requests trigger expert analysis (LLM call with agent-specific system prompt + RAG context) and send `collaboration_response` back. Responses are merged into task context by the orchestrator before the primary agent processes the task. SubAgentWorker also polls A2A.

### Structured Output Validation
`base.py validate_output()` checks evidence chain integrity (insights without facts, recommendations without insights), confidence score bounds (0-1), and source attribution on facts. Warnings logged in `task.agent_notes` before storing.

### Report Pipeline Completion
- **Artifacts → Documents**: Skill artifacts now create `Document` records with `source=agent_output`, visible in Documents view. Linked to `task.output_document_ids`.
- **Ensemble confidence → Reports**: `task.consensus_score` flows to report's `content_json.avg_consensus`.
- **Executive summaries**: Auto-generated via LLM when reports reach 3+ findings.
- **MECE categorization**: Auto-generated via LLM when reports reach 5+ findings. Populates `mece_categories_json`.
- **L4 auto-generation**: When L3 synthesis reaches 10+ findings, L4 final report auto-created with template-driven document composition.
- **Template-driven L4 composition** (Elicit-style Extract→Structure→Synthesize→Compose→Cite pipeline): 8-section report template — Executive Summary, Methodology, Key Findings (evidence table), Supporting Evidence (citation table), Recommendations (priority table), MECE Analysis, Confidence & Validation (ensemble metrics), Limitations & Gaps (LLM-generated). Creates a Document record (`final_research_report.md`) visible in Documents view.
- **Circuit breaker on compute nodes**: Three-state (CLOSED/OPEN/HALF_OPEN). 5 consecutive failures → OPEN (60s cooldown). `_select_candidates()` filters out unavailable nodes. `cb_record_success/failure` called in chat routing. Agent pauses when `has_available_node()` returns false. Frontend StatusBar shows red/yellow/green banners via WebSocket events.
- **Architecture evolution tracking**: `docs/ARCHITECTURE_EVOLUTION.md` documents every version's changes with before/after tables and industry standard references.

**Complete data flow:**
```
Task → RAG retrieval → Skill execution (timeout) → Schema validation
→ Ensemble validation → LLM reflection → Store findings
→ Route to L2 report → Auto-trigger L3 synthesis → MECE categorization
→ Executive summary → Auto-trigger L4 final report
→ Artifacts → Document records → task.output_document_ids
```

**Files:** `backend/app/core/agent.py`, `backend/app/core/report_manager.py`, `backend/app/skills/base.py`, `backend/app/core/sub_agent_worker.py`, `backend/app/agents/orchestrator.py`

## Project Settings (formerly Metrics)

The Metrics view has been replaced with a comprehensive Project Settings view (`frontend/src/components/settings/ProjectSettingsView.tsx`). Combines project management with research metrics in a single scrollable page.

**Sections:**
1. **Project Header**: Inline-editable project name (pencil icon), phase badge, Pause/Resume toggle (admin only)
2. **Research Metrics**: All original MetricsView content — finding counts, atomic research breakdown, Double Diamond phase coverage, task completion circular progress
3. **Team Access** (team mode only): Per-project member management with `ProjectMember` model. Add server users to projects, set project-level roles (admin/member/viewer), view last active time, remove members
4. **Linked Folder**: Shows the watch folder path with unlink action
5. **Danger Zone**: Export project + Delete with type-name-to-confirm safety

**Data Model:** `ProjectMember` table (project_id, user_id, role, added_by, last_active) with FK cascade delete to projects. Separate from server-level user roles — a user can be "admin" on the server but "viewer" on a specific project.

**API Endpoints:**
- `GET /projects/{id}/members` — list with user info enrichment
- `POST /projects/{id}/members` — add (admin only, user must exist on server)
- `DELETE /projects/{id}/members/{user_id}` — remove
- `PATCH /projects/{id}/members/{user_id}` — change project role

**Navigation:** Moved from secondary nav ("More") to secondary nav as "Project Settings" with Settings icon. Requires active project.

**Files:** `frontend/src/components/settings/ProjectSettingsView.tsx`, `backend/app/models/project_member.py`, `backend/app/api/routes/projects.py`, `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/components/layout/HomeClient.tsx`

## Guided Onboarding Tour

Replaces the old modal OnboardingWizard with an in-app guided tour that navigates through real views.

### Architecture
- **tourStore.ts** (Zustand) — Manages tour step, conditional flags (role, team mode, LLM status), persists to localStorage
- **GuidedTour.tsx** — Orchestrator: navigates views via `setActiveView()`, renders popovers or inline cards, polls LLM status
- **TourPopover.tsx** — Floating card with spotlight overlay (box-shadow cutout), positioned via `getBoundingClientRect()`. WCAG: `role="dialog"`, keyboard nav, focus management
- **TourInlineStep.tsx** — Full-screen centered cards for steps 0-1 (folder selection + project creation) before any project exists

### Three Onboarding Paths
1. **Admin (first user)**: Folder → Project → Team Mode → Invite → Connection String → Files → Context → Tasks → LLM Check → Chat (10 steps)
2. **Team member**: Skips project creation (if projects exist) and team management. Starts at Files → Context → Tasks → LLM → Chat
3. **Returning user**: Tour completed flag in localStorage, never shows again

### Step Flow
| Step | View | Target Element | Content |
|------|------|----------------|---------|
| 0 | (inline) | — | Welcome + folder selection |
| 1 | (inline) | — | Project creation + folder linking |
| 2 | settings | #tour-target-team-mode | Enable Team Mode toggle |
| 3 | settings | #tour-target-user-management | Invite team members (conditional) |
| 4 | settings | #tour-target-connection-strings | Generate connection string (conditional) |
| 5 | (centered) | — | Add research files to folder |
| 6 | context | #tour-target-context-editor | Fill project context |
| 7 | tasks | #tour-target-kanban | Task board introduction |
| 8 | settings | #tour-target-system-status | LLM model check + polling |
| 9 | chat | — | Welcome to chat, auto-dismiss |

### Event System
- `istara:team-mode-toggled` — dispatched by SettingsView after toggle, updates tour conditional
- `istara:connection-string-generated` — dispatched by ConnectionStringPanel after generation
- LLM status polling: step 8 polls `/api/settings/status` every 3s until connected

### Pre-Login Member Guidance
LoginScreen enhanced for team mode: "Got a connection string?" banner on sign-in tab, step-by-step help text in Join Server mode, inline guidance after validation.

**Files:** `frontend/src/stores/tourStore.ts`, `frontend/src/components/onboarding/{GuidedTour,TourPopover,TourInlineStep}.tsx`, `frontend/src/components/layout/HomeClient.tsx`, `frontend/src/components/auth/LoginScreen.tsx`

## External Folder Linking

Projects can point at external folders (Google Drive, Dropbox, OneDrive, or any local directory). The FileWatcher monitors them for changes automatically.

- **Project model**: `watch_folder_path` field (nullable string)
- **API**: `POST /projects/{id}/link-folder` and `/unlink-folder`
- **FileWatcher**: Already supported arbitrary paths; now filters cloud-sync temp files (`.partial`, `.tmp`, `~$*`, `.crdownload`)
- **Folder resolution**: All file-scanning/listing/injecting code uses `_resolve_project_folder()` — returns `watch_folder_path` if set, falls back to `settings.upload_dir / project_id`
- **Sync**: `/documents/sync/{id}` uses the resolved folder (external first, internal fallback)
- **Agent tools**: `list_project_files` and `sync_project_documents` in `system_actions.py` use resolved folder
- **Chat file injection**: Both `chat.py` and `interfaces.py` inject file lists from resolved folder
- **Agent skill execution**: `agent.py` passes file list from resolved folder to skill input
- **Files endpoints**: `GET /files/{id}`, `POST /files/{id}/reprocess`, `POST /files/{id}/scan` use resolved folder
- **Documents**: External files use `DocumentSource.PROJECT_FILE`, referenced by path (not copied)
- **Upload/serve endpoints**: `POST /files/upload/{id}`, `GET /files/{id}/serve/{filename}`, `GET /files/{id}/content/{filename}` remain internal-only (correct for explicitly uploaded files)

**Files:** `backend/app/models/project.py`, `backend/app/api/routes/projects.py`, `backend/app/core/file_watcher.py`, `backend/app/api/routes/documents.py`, `backend/app/skills/system_actions.py`, `backend/app/api/routes/chat.py`, `backend/app/api/routes/interfaces.py`, `backend/app/core/agent.py`, `backend/app/api/routes/files.py`

---

## Project Structure

```
Istara-main/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app, lifespan, A2A endpoint
│   │   ├── config.py                  # Pydantic settings
│   │   ├── agents/
│   │   │   ├── orchestrator.py        # MetaOrchestrator (5 agents)
│   │   │   ├── devops_agent.py        # System integrity auditor
│   │   │   ├── ui_audit_agent.py      # Nielsen's heuristics, WCAG
│   │   │   ├── ux_eval_agent.py       # UX quality evaluator
│   │   │   ├── user_sim_agent.py      # Simulated user testing
│   │   │   ├── custom_worker.py       # Custom agent worker loop
│   │   │   └── personas/              # Agent persona MD files
│   │   │       ├── istara-main/       # Cleo's identity
│   │   │       ├── istara-devops/     # Sentinel's identity
│   │   │       ├── istara-ui-audit/   # Pixel's identity
│   │   │       ├── istara-ux-eval/    # Sage's identity
│   │   │       └── istara-sim/        # Echo's identity
│   │   ├── core/
│   │   │   ├── agent.py               # AgentOrchestrator (work loop)
│   │   │   ├── agent_identity.py      # Persona loading + compression
│   │   │   ├── agent_learning.py      # Error/pattern tracking
│   │   │   ├── agent_memory.py        # Agent note-taking + recall
│   │   │   ├── self_evolution.py      # Learning → persona promotion
│   │   │   ├── prompt_compressor.py   # LLMLingua-style heuristic
│   │   │   ├── prompt_rag.py          # Query-aware prompt composition
│   │   │   ├── prompt_compressor.py   # LLMLingua-inspired heuristic compression
│   │   │   ├── context_hierarchy.py   # 6-level context system
│   │   │   ├── context_dag.py         # DAG-based lossless summarization
│   │   │   ├── context_summarizer.py  # Cost-escalating compression pipeline
│   │   │   ├── budget_coordinator.py  # Dynamic token budget allocation
│   │   │   ├── token_counter.py       # Budget-aware context window guard
│   │   │   ├── model_capabilities.py  # Model context window detection
│   │   │   ├── rag.py                 # Vector store + hybrid retrieval
│   │   │   ├── embeddings.py          # Local embedding with caching
│   │   │   ├── self_check.py          # Hallucination detection
│   │   │   ├── resource_governor.py   # Hardware-aware throttling
│   │   │   ├── file_watcher.py        # Auto-ingest + task creation
│   │   │   ├── scheduler.py           # Async cron (no external deps)
│   │   │   ├── ollama.py              # Ollama LLM client
│   │   │   └── lmstudio.py            # LM Studio LLM client
│   │   ├── skills/
│   │   │   ├── base.py                # BaseSkill, SkillInput, SkillOutput
│   │   │   ├── registry.py            # Skill discovery + registration
│   │   │   ├── skill_manager.py       # Health monitoring + proposals
│   │   │   └── definitions/           # Canonical 50+ JSON skill definitions
│   │   ├── models/
│   │   │   ├── project.py             # Projects with Double Diamond phases
│   │   │   ├── task.py                # Kanban tasks with priority
│   │   │   ├── finding.py             # Nugget, Fact, Insight, Recommendation
│   │   │   ├── document.py            # Documents (source of truth for outputs)
│   │   │   ├── message.py             # Chat messages
│   │   │   ├── session.py             # Chat sessions + inference presets
│   │   │   ├── agent.py               # Agent records + A2A messages
│   │   │   └── context_dag.py         # DAG node model
│   │   ├── api/
│   │   │   ├── routes/                # All REST endpoints
│   │   │   └── websocket.py           # Real-time broadcasts
│   │   └── services/
│   │       ├── agent_service.py       # Agent CRUD + seeding
│   │       └── a2a.py                 # Agent-to-agent messaging
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/                       # Next.js app router
│   │   ├── components/
│   │   │   ├── layout/                # Sidebar, StatusBar, MobileNav
│   │   │   ├── documents/             # Documents view (list, preview, search)
│   │   │   ├── views/                 # Chat, Kanban, Findings, Skills, Memory, Agents
│   │   │   └── common/                # ErrorBoundary, Toast, Search, Settings
│   │   ├── stores/                    # Zustand state management
│   │   ├── hooks/                     # useWebSocket, useApiCall
│   │   └── lib/                       # Types, API client, utilities
│   └── package.json
├── tests/
│   ├── simulation/
│   │   ├── run.mjs                    # Simulation orchestrator (32 scenarios)
│   │   ├── scenarios/                 # Test scenarios (01-31)
│   │   └── evaluators/                # Accessibility, Heuristics, Performance
│   └── e2e_test.py                    # Backend integration tests
├── docker-compose.yml                 # Standard deployment
├── docker-compose.gpu.yml             # GPU-accelerated deployment
└── Tech.md                            # This document
```

---

## Design Principles

1. **Local-first, always.** Data never leaves the machine unless the user explicitly exports it. No cloud dependencies for core functionality.

2. **Evidence over opinion.** Every finding traces back to source data. Hallucination detection flags ungrounded claims. The Atomic Research hierarchy enforces rigor.

3. **Agents should get better, not just older.** The self-evolution pipeline ensures that an agent that's been running for 6 months is meaningfully more capable than one that started yesterday.

4. **Hardware is a first-class constraint.** The resource governor, prompt compression, and model recommendations exist because local hardware varies wildly. A researcher with a MacBook Air deserves the same quality as one with a workstation.

5. **Structured outputs, not just text.** Skills produce nuggets, facts, insights, and recommendations — not paragraphs. This makes findings searchable, filterable, and composable across projects.

6. **Async everything.** All database access, LLM calls, file operations, and agent work loops are async. The UI never freezes waiting for a model to respond.

7. **Fail gracefully, learn from failures.** Every error is caught, logged, and turned into a learning opportunity. Agents record error patterns and apply known resolutions automatically.

---

---

## Distributed Platform Architecture

### Multi-User Team Mode

Istara supports both local (single-user, no auth) and team modes:

- **Local mode** (default): No authentication, single implicit "local" user with admin privileges.
- **Team mode** (`TEAM_MODE=true`): JWT-based authentication with role-based access control (admin, researcher, viewer). First registered user becomes admin.
- **User model**: `users` table with username, email, PBKDF2-hashed password, role, and JSON preferences (theme, UI density, shortcuts).
- **Auth middleware**: `get_current_user()` FastAPI dependency — returns local user in local mode, verifies JWT in team mode.
- **Preferences**: Stored per-user as JSON, covering theme, keyboard shortcuts, and UI customization.

**Files**: `backend/app/models/user.py`, `backend/app/core/auth.py`, `backend/app/api/routes/auth.py`, `backend/app/api/middleware/auth.py`

### Task Locking

Pessimistic locking prevents multiple users/agents from working on the same task:

- **Lock columns**: `locked_by`, `locked_at`, `lock_expires_at` on the Task model.
- **Auto-expiry**: Locks expire after 30 minutes (configurable).
- **Lock owner**: Only the lock holder can unlock; admins can force-unlock.
- **Agent awareness**: `_pick_next_task()` skips locked tasks.
- **Endpoints**: `POST /tasks/{id}/lock`, `POST /tasks/{id}/unlock`.

### LLM Router

> **Note:** As of the ComputeRegistry unification, `llm_router.py` and `compute_pool.py` are thin wrappers over `compute_registry.py`. See the "ComputeRegistry — Single Source of Truth" section for the current architecture.

A provider-agnostic routing layer that supports Ollama, LM Studio, and any OpenAI-compatible endpoint:

- **LLMRouter**: Same interface as `OllamaClient` (`health()`, `chat()`, `chat_stream()`, `embed()`) — drop-in replacement.
- **Priority-based routing**: Requests go to the highest-priority healthy server with automatic failover.
- **Background health checks**: Every 60 seconds across all registered servers.
- **On-demand health re-probe**: `GET /api/settings/status` calls `check_all_health()` before returning, so the status is always fresh rather than reading the cached 60-second flag.
- **CRUD API**: `GET/POST/PATCH/DELETE /llm-servers` for managing external endpoints.
- **LLMServer model**: Stored in DB with provider_type, host, API key, priority, health status, and latency.

**Files**: `backend/app/core/llm_router.py`, `backend/app/models/llm_server.py`, `backend/app/api/routes/llm_servers.py`

### Network LLM Server Discovery

Automatic discovery of LLM servers (LM Studio, Ollama, OpenAI-compatible) on the local network:

- **Subnet scanning**: Detects the local /24 subnet and probes all 254 hosts on ports 1234 (LM Studio), 11434 (Ollama), and 8080 (OpenAI-compat).
- **Model-aware routing**: Each discovered server's available models are captured. The router picks the correct model per server — if the configured model isn't available on a remote server, it uses whatever model is loaded there.
- **Startup integration**: Discovery runs at startup before `auto_detect_provider`, so network servers are available immediately when the local LLM is down.
- **Persistence**: Discovered servers are saved to the DB and registered with the LLM Router. Duplicates (by host URL) are skipped.
- **On-demand rescan**: `POST /api/llm-servers/discover` triggers a new network scan at any time.
- **No hardcoded IPs**: Works on any subnet — detects the local network automatically via `socket.getaddrinfo` and UDP connect trick.

**Files**: `backend/app/core/network_discovery.py`, `backend/app/main.py` (startup integration)

### Istara Relay Daemon

A Node.js daemon that allows team members to donate LLM compute:

- **Outbound WebSocket**: Connects from the relay machine to the server — no inbound ports needed (NAT-friendly).
- **State machine**: CONNECTING → IDLE → DONATING → USER_ACTIVE → DISCONNECTED.
- **Heartbeat**: System stats (RAM, CPU, GPU, loaded models) sent every 30 seconds.
- **LLM proxy**: Receives requests from the server, forwards to local Ollama/LM Studio, returns results.
- **Priority queue**: P0 (user chat) > P1 (user tasks) > P2 (agent work) > P3 (background validation).
- **Auto-reconnect**: Exponential backoff with max 60-second delay.

**Files**: `relay/` directory — `index.mjs`, `lib/connection.mjs`, `lib/state-machine.mjs`, `lib/heartbeat.mjs`, `lib/llm-proxy.mjs`

### Compute Pool

> **Note:** As of the ComputeRegistry unification, `llm_router.py` and `compute_pool.py` are thin wrappers over `compute_registry.py`. See the "ComputeRegistry — Single Source of Truth" section for the current architecture.

Server-side registry of connected relay nodes:

- **Node scoring**: `score = 100 - (active_requests*15) - (latency/10) - priority + (ram_available*2)`
- **Capacity tracking**: Total RAM, CPU cores, available models across the pool.
- **Best-node selection**: For any given model request, selects the node with the highest score.
- **WebSocket endpoint**: `/ws/relay` for relay node connections.
- **Relay host resolution**: Relay nodes report `provider_host` as `localhost`; on registration the backend resolves this to the relay's actual IP address so HTTP streaming can reach the relay's LM Studio directly.
- **Capability detection for relays**: The health loop detects model capabilities (tool support, context length, vision) via HTTP probe for relay nodes, not just local/network nodes.
- **Network/Relay deduplication**: When a relay registers, any network-discovered node pointing to the same `host:port` is automatically removed. Relay is the preferred connection path. Capabilities are transferred from the network node before removal.
- **Tool filter fallback**: Nodes whose capabilities haven't been detected yet are included in the tool-support filter rather than excluded, preventing "No compute nodes available" errors on freshly registered relays.
- **Network discovery skip**: `discover_and_register()` skips hosts already covered by an active relay connection.

**Files**: `backend/app/core/compute_pool.py`, `backend/app/core/compute_registry.py`, `backend/app/api/routes/compute.py`, `backend/app/core/network_discovery.py`

### Consensus Engine

Academic-grade inter-rater reliability for multi-model validation:

- **Fleiss' Kappa**: Categorical agreement among multiple raters — measures whether models agree on themes and labels.
- **Cosine similarity**: Semantic agreement via embedding comparison — measures whether responses mean the same thing.
- **Composite scoring**: Weighted combination (40% Kappa + 60% cosine similarity).
- **Tiered thresholds by finding type**: Nuggets (κ≥0.70), Facts (κ≥0.65), Insights (κ≥0.55), Recommendations (κ≥0.50).
- **No extra LLM cost**: Uses existing embedding infrastructure for semantic comparison.

**Files**: `backend/app/core/consensus.py`

### Validation Patterns

Five validation strategies, each grounded in academic research:

1. **Dual-run**: Two models, same prompt — basic inter-rater reliability.
2. **Adversarial review**: One model critiques another's output (Du et al., ICML 2024).
3. **Full ensemble**: 3+ models with Fleiss' Kappa scoring (Wang et al., ICLR 2025).
4. **Self-MoA**: Same model, temperature variation (0.3, 0.7, 1.0) — Li et al. (2025).
5. **Debate rounds**: Iterative refinement between models (Du et al., ICML 2024).

**Files**: `backend/app/core/validation.py`

### Adaptive Method Learning

The system learns which validation method works best per context:

- **Method metrics**: Tracks success rate, consensus score, and recency for each (project, skill, agent, method) combination.
- **Recency-weighted scoring**: Exponential decay with 30-day half-life — recent results matter more.
- **Automatic selection**: `AdaptiveSelector.select_method()` picks the best method based on historical performance.
- **Default fallback**: `self_moa` for new/unknown combinations (zero extra infrastructure needed).

**Files**: `backend/app/models/method_metric.py`, `backend/app/core/adaptive_validation.py`

### Dynamic Swarm Orchestration

The MetaOrchestrator scales agent count based on available compute:

- **Swarm tiers**: full_swarm (8+ nodes) → standard (4-7) → conservative (2-3) → minimal (1) → paused (0).
- **Compute-aware budgeting**: `ResourceGovernor.compute_budget()` adds remote node capacity to local resources.
- **Orchestration cycle**: Every 60 seconds, syncs agent states, checks for conflicts, distributes pending tasks.

### Docker & Infrastructure

- **PostgreSQL**: Added as a service with `team` profile — only started when `TEAM_MODE=true`.
- **Relay service**: Added with `relay` profile for compute donation.
- **GPU override**: `docker-compose.gpu.yml` for NVIDIA GPU passthrough.
- **NAT-friendly**: Backend exposes single port (8000) for both HTTP and WebSocket. Relay uses outbound connections only.
- **LM Studio access**: `host.docker.internal` mapping for accessing host machine's LM Studio from containers.

### Action Feedback & WCAG 2.2 / Nielsen Heuristics Compliance (April 2026)

Comprehensive audit and fix of all async actions across Documents and Interviews views to meet WCAG 2.2 Level AA and Nielsen's 10 Usability Heuristics:

**WCAG 2.2 4.1.3 Status Messages**: Every async action now dispatches `istara:toast` notifications on success and failure. Users are informed of state changes without needing to find the information themselves. All toasts use semantic types (`success`, `warning`, `info`) with appropriate icons and colors.

**Nielsen H1 — Visibility of System Status**: All actions show loading indicators (spinners, progress text, "Starting..." messages) rather than disappearing or doing nothing. The "Analyze this file" button now shows a spinner with "Analyzing..." text instead of vanishing from the DOM. Upload button shows per-file progress ("Uploading 2/5"). Delete button shows "Deleting..." with spinner.

**Nielsen H5 — Error Prevention**: Tag creation now shows a visible warning toast when the API fails, instead of silently falling back to local-only state (which would lose data on refresh). All empty catch blocks in Quick Actions and Organize Files have been replaced with proper error handling.

**Nielsen H6 — Recognition Rather Than Recall**: SSE `tool_call` events are now displayed inline during analysis ("▸ Running: search_files...") so users see what the agent is doing instead of staring at a blank streaming box. The `done` event triggers a completion toast showing tools used.

**Nielsen H8 — Help Users Recognize, Diagnose, and Recover from Errors**: File preview in Interviews now has an explicit back button (`ArrowLeft` with `aria-label="Back to file list"`), matching the DocumentsView pattern. Preview content fetch failures now show a toast with the error reason instead of silently showing "No preview available."

**Nielsen H3 — User Control and Freedom**: The back button gives users an explicit escape route from the file preview, replacing the previous trap where the only way out was to click a different file tab or navigate to another view.

**Unified stream handler**: All 7 chat-based actions in Interviews (Analyze This File, Analyze All, Organize Files, 4 Quick Actions) now use a shared `handleChatStream()` helper that processes `chunk`, `tool_call`, `error`, and `done` SSE events consistently.

**Files**: `frontend/src/components/interviews/InterviewView.tsx`, `frontend/src/components/documents/DocumentsView.tsx`, `backend/app/api/routes/files.py`

### UX Bug Fixes & WCAG Compliance (March 2026)

Major UX overhaul addressing WCAG compliance, Nielsen's heuristics violations, and usability issues:

- **Notification Center**: Full notification center (like GitHub/LinkedIn) with bell icon, unread badge, notification history (max 50), mark-all-as-read, clear-all. All notification backgrounds use solid opacity (≥80%) for WCAG contrast compliance. Every notification navigates to its relevant page on click.
- **Chat Agent Identity**: Chat bubbles now show the actual agent name (not hardcoded "Istara") during both message history and streaming responses. Agent names are resolved from the session's agent_id against the agent store.
- **Settings Model/Server Display**: Each model now shows its provider server name and type (Ollama, LM Studio, OpenAI Compatible) as inline badges. Backend enriches model data with server metadata from the LLM Router.
- **Ensemble Health Explanations**: Added expandable explanations for Fleiss' Kappa, per-method methodology descriptions (accordion pattern), metric tooltips on hover, and a color legend for confidence score interpretation. All on-demand to avoid overcrowding.
- **Agent Status Polling**: Agent store now polls every 10 seconds + listens for WebSocket `agent_status` events in real-time. Agents correctly show WORKING/IDLE/PAUSED states instead of always "idle".
- **Agent Memory Synchronization**: AgentsView Memory tab now shows BOTH the agent's state memory (JSON dict) AND the RAG-stored notes (same data as Memory menu), fixing the inconsistency between the two menus.
- **Self-Evolution Skills UI**: Current/Proposed fields are now full-width stacked (not cramped side-by-side), with readable font sizes (14px content, 12px labels), 256px max-height, and minimum height for empty fields. Backend no longer truncates values to 200 characters.
- **Interviews Layout**: Right panel narrowed from 320px to 256px. File tabs switched to compact horizontal wrap. Added collapsible toggle for the tags/nuggets panel so users can maximize content reading space.
- **Documents Layout**: Metadata panel narrowed from 288px to 256px. Removed XL-only breakpoint (always visible). Added collapsible toggle for metadata panel. More compact document list cards.
- **Atomic Research Path Tracking**: Empty state in AtomicDrilldown now explains the atomic research chain (Nuggets → Facts → Insights → Recommendations) with a visual pyramid. Added "Link Evidence" buttons for manual evidence linking. New `PATCH /api/findings/{type}/{id}/link` endpoint for adding evidence links. FindingsView shows link count badges on each finding.
- **Auth Store Fix**: Fixed pre-existing TypeScript error in `getAuthHeaders()` return type.

**Files**: All frontend components in `components/`, stores in `stores/`, backend routes in `api/routes/`, `skill_manager.py`

### Multi-Agent Task Routing & Architecture (March 2026)

Istara is now a **true multi-agent system** where tasks are automatically routed to the best-matching agent based on specialty domains. Previously, all tasks went to the main Istara agent — now the intelligent task router analyzes each task's keywords, skill requirements, and description to determine which agent(s) should handle it.

**Task Router** (`backend/app/core/task_router.py`):
- **Specialty-based routing**: Each agent has defined specialties (research, devops, ui, ux, simulation). The router matches task keywords against specialty domains.
- **Multi-specialty detection**: Tasks that require multiple domains (e.g., "accessibility audit of user journey") are assigned a primary agent and collaboration requests are sent to secondary agents via A2A.
- **User-created agent support**: Custom agents define their specialties in the `specialties` JSON column on the Agent model. The router considers all active agents — system and user-created.
- **Explicit assignment respected**: If a task is manually assigned to an agent, the router respects that assignment.
- **Graceful fallback**: If the target agent is inactive, tasks fall back to istara-main.

**Sub-Agent Task Execution** (`backend/app/core/sub_agent_worker.py`):
- All 4 sub-agents (Sentinel, Pixel, Sage, Echo) now have dual duties: their original monitoring/audit cycles PLUS task execution for their specialty domain.
- `SubAgentWorker` provides a shared work loop: check for assigned tasks → execute using the main skill pipeline → store findings → report results.
- Each sub-agent checks for tasks every 30 seconds between their audit cycles.

**A2A Collaboration Protocol** (`backend/app/services/a2a.py`):
- New `send_task_request()` function creates tasks assigned to target agents with A2A notification.
- `collaboration_request` message type for multi-specialty task coordination.
- Sub-agents check their A2A inbox for collaboration requests as part of their work cycle.

**Agent Specialties** (`backend/app/models/agent.py`):
- New `specialties` JSON column on the Agent model.
- System agents seeded with domain specialties: istara-main=research, istara-devops=devops, istara-ui-audit=ui, istara-ux-eval=ux, istara-sim=simulation.
- User-created agents can set specialties at creation or via memory.

### Agent Identity UI & Persona System (March 2026)

Agent persona files (CORE.md, SKILLS.md, PROTOCOLS.md, MEMORY.md) are now fully visible and editable in the frontend.

**Backend**:
- `PUT /api/agents/{id}/identity` — Save updated persona MD files with validation (only allowed filenames accepted)
- `scaffold_persona()` in `agent_identity.py` — Auto-generates skeleton persona files when new agents are created
- Cache invalidation: Identity cache is cleared immediately on save so changes take effect without restart

**Frontend** (`AgentsView.tsx`):
- New **Identity tab** in agent detail showing all 4 persona files
- Each file displayed with: filename header, budget weight badge (40%/25%/25%/10%), description, full content
- **Read/Edit toggle**: Markdown preview mode by default, click Edit for a large textarea (min-height 300px, proper fonts and contrast)
- **Save/Cancel** with immediate persistence
- WCAG compliant: dark mode backgrounds at 80%+ opacity, proper text contrast, keyboard accessible

**Enriched Persona Files**:
- All 5 system agents now have deeply detailed persona files (80-120 lines in CORE.md vs ~33 before)
- CORE.md covers: identity, personality, communication style, values, domain expertise, collaboration patterns, edge case handling
- SKILLS.md covers: capability categories, tool access, skill chains, quality criteria
- PROTOCOLS.md covers: decision frameworks, error handling, communication patterns, A2A collaboration

### Database Migration & Data Integrity (March 2026)

Switching between SQLite (local mode) and PostgreSQL (team mode) no longer risks data loss.

**Data Migration** (`backend/app/core/data_migration.py`):
- `export_full_database()` — Dumps all tables to portable JSON structure with metadata and filesystem reference catalog
- `import_full_database()` — Imports JSON dump into any target database, handles foreign key ordering
- API endpoints: `POST /api/settings/export-database`, `POST /api/settings/import-database`

**Data Integrity Checks** (`backend/app/core/data_integrity.py`):
- Runs automatically on startup (lightweight, <2s)
- Checks: LanceDB dirs ↔ DB projects, keyword indexes ↔ DB projects, upload dirs ↔ documents, persona dirs ↔ agents
- Logs warnings for orphaned data (does NOT delete — user decides)
- API endpoint: `GET /api/settings/data-integrity`
- Startup warning if orphaned LanceDB data detected after database switch

**Data Storage Architecture** (reference):
| Data | Storage | Survives DB Switch? |
|------|---------|-------------------|
| Projects, Tasks, Messages, Findings | SQLite/PostgreSQL | Requires export/import |
| Vector Embeddings | LanceDB (filesystem) | Yes (needs project refs) |
| Keyword Indexes | Separate SQLite files | Yes (needs project refs) |
| Uploaded Files | Filesystem | Yes (needs document refs) |
| Agent Personas | MD files on filesystem | Yes |

### Content Guard & Prompt Injection Protection

- 5 threat pattern categories: instruction overrides, role impersonation, invisible unicode, credential exfiltration, hidden markup
- `ScanResult` dataclass with `clean` / `threat_level` / `threats` / `cleaned_text`
- 6 pipeline integration points: file_processor, rag, context_hierarchy, agent_memory, chat, files
- Untrusted content wrapping with XML delimiters

### Automatic Agent Creation (Memento-inspired)

- `AgentFactory` class with `detect_capability_gap()` and `propose_agent_creation()`
- Capability gap detection: if best agent coverage < 60% of needed specialties
- `AgentCreationProposal` with approve/reject workflow
- Triggered in `MetaOrchestrator` during task distribution
- Reference: Zhou et al. (2026). "Memento-Skills: Let Agents Design Agents." arXiv:2603.18743

### Autonomous Skill Creation

- `SkillCreationProposal` class parallel to existing `SkillUpdateProposal`
- Trigger: quality_score >= 0.8, >= 3 findings, agent maturity >= 5 tasks
- ContentGuard validation of proposed prompts
- Approval workflow with runtime registry registration
- Inspired by Hermes Agent skill creation and Memento-Skills reflective learning

### Read-Write Reflective Learning

- Utility scoring on `AgentLearning` model (0.0-1.0, exponential moving average)
- Structured failure attribution via `reflect_on_failure()` — 4 categories: skill_gap, skill_weakness, agent_gap, transient
- Auto-archive low-utility learnings (< 0.2 after 5+ applications)
- Semantic skill routing fallback using embedding similarity

### Process Hardening

- `TaskCheckpoint` model for crash recovery (5 phases: started -> skill_selected -> executing -> findings_stored -> verified)
- Startup recovery: `recover_incomplete()` returns orphaned tasks to BACKLOG
- Exponential backoff retry: 5s, 15s, 45s, 120s (max 3 retries)
- Atomic file writes: write-tmp-then-rename pattern for all JSON persistence
- Scheduler deduplication: `is_running` flag prevents concurrent execution
- Graceful shutdown: 30s drain period for in-flight tasks

### Voice Transcription Pipeline (v2026.04.14)

Istara now supports voice input across the entire platform with automatic transcription, inter-coder reliability scoring, and atomic research chain integration.

**Components:**
- `backend/app/core/transcription.py` — Whisper-based local transcription with ICR consensus
- `POST /api/chat/voice` — Chat voice input endpoint
- `backend/app/channels/telegram.py` — Auto-transcribes Telegram voice messages
- `backend/app/channels/whatsapp.py` — Auto-transcribes WhatsApp audio messages
- `frontend/src/components/chat/ChatView.tsx` — Mic button on chat input
- `frontend/src/lib/api.ts` → `chat.transcribeVoice()` — Voice upload API client

**Pipeline:** Audio input → format conversion (OGG/MP3→WAV 16kHz mono) → Whisper transcription (base model) → alternative transcription (tiny model) → ICR consensus (Fleiss' Kappa + cosine similarity) → auto-tagging → review flagging if needed → store in Interviews + Documents → feed into Atomic Research chain.

**Inter-Coder Reliability (mandatory):** Every transcription passes through ICR with Fleiss' Kappa between primary and alternative transcriptions. If confidence is "low" or "insufficient", the transcription is flagged for human review with `needs_review: true`.

**Dependencies:** `openai-whisper>=20240930`, `pydub>=0.25.1`, `ffmpeg` (system, preferred) or pydub fallback.

### Browser UX Research Skills (v2026.04.15)

Three skill definitions that wrap the existing `browse_website` system action into structured UX research workflows. When a user creates a task with URLs, those URLs are passed through the `SkillInput.urls` field to the skill's prompt templates.

**Skills:**
- `browser-ux-audit` (develop/mixed) — Navigate target URLs → evaluate against Nielsen's 10 heuristics, WCAG 2.2 AA, and Laws of UX → produce severity-rated findings with evidence chains
- `browser-competitive-benchmark` (discover/mixed) — Browse 2-5 competitor URLs → capture UX patterns, heuristic scores, feature matrices → produce gap-opportunity analysis with Blue Ocean Strategy canvas
- `browser-accessibility-check` (develop/quantitative) — Navigate target site → systematic WCAG 2.2 criterion-by-criterion check → severity classification → prioritized remediation plan

**Architecture:** Skills use `{urls}` and `{urls_section}` template placeholders. The skill factory (`skill_factory.py`) substitutes these from `SkillInput.urls`, which is populated from `task.get_urls()` in the agent's `_execute_task()`. The agent uses `browse_website` system action at execution time.

**SCOPE_MAP entries:** `browser-ux-audit` → Usability Study, `browser-accessibility-check` → Usability Study, `browser-competitive-benchmark` → Competitive Analysis

**Task routing aliases:** `ux audit` → `browser-ux-audit`, `site audit` → `browser-ux-audit`, `accessibility check` → `browser-accessibility-check`, `wcag` / `a11y` → `browser-accessibility-check`, `competitive benchmark` / `competitor audit` → `browser-competitive-benchmark`

### Research Quality Evaluation (v2026.04.15)

Formalizes Istara's existing LLM-as-Judge validation pipeline (AdaptiveSelector, ValidationExecutor, Fleiss' Kappa consensus) into a callable user-facing skill and visible metrics.

**Skill: `research-quality-evaluation`** (deliver/mixed)
- Invokes the existing validation pipeline: adversarial review (5-dimension rubric), dual-run consistency, self-MoA RAG verification, debate consensus
- Assesses chain integrity (nuggets → facts → insights → recommendations), completeness, methodology quality
- Uses adaptive method selection via `AdaptiveSelector` — the system learns which validation strategy works best per project/skill/agent
- SCOPE_MAP: `research-quality-evaluation` → `Quality Evaluation`

**API: `GET /api/metrics/{project_id}/validation`**
- Returns per-method adaptive validation stats from `MethodMetric` model (success_rate, avg_consensus_score, weight, last_used)
- Returns recent per-task validations (validation_method, consensus_score, skill_name)
- Returns confidence thresholds by finding type (nugget 0.70, fact 0.65, insight 0.55, rec 0.50)

**Frontend visibility:**
- EnsembleHealthView: wired to real `/api/metrics/{id}/validation` data instead of stub
- KanbanBoard task cards: color-coded consensus badge (green ≥ 70%, yellow ≥ 50%, orange ≥ 30%, red < 30%) with tooltip showing validation method + κ score
- Task type in `types.ts`: added `validation_method` and `consensus_score` fields

### Game-Theory Participant Simulation (v2026.04.15)

Enhances the `istara-sim` (Echo) persona with game-theory behavioral models for simulating participant behavior in UX research scenarios.

**Architecture:** `backend/app/core/participant_simulation.py` provides:
- 7 behavioral strategies: cooperative, selfish, reciprocating, random, satisficing (Simon 1956), social_desirability, adversarial
- Prisoner's Dilemma payoff matrix (T > R > P > S, 2R > T + S)
- Stag Hunt payoff matrix (Rousseau/Skyrms 2004 coordination game)
- `ParticipantProfile` dataclass with behavioral traits: patience, honesty_bias, social_desirability_bias, tech_savviness, engagement_level, risk_aversion, satisficing_threshold
- `choose_action()` implements bounded rationality — noise proportional to `(1 - engagement) × (1 - patience)`
- `simulate_response_mode()` determines how a participant responds: honest, strategic, biased, withheld, exaggerated
- `generate_participant_cohort()` creates diverse cohorts with configurable strategy distributions

**Skill:** `participant-simulation` (define/mixed) maps game-theory constructs to UX research implications — Nash equilibrium analysis, satisficing behavior detection, social desirability bias identification, engagement decay tracking.

**SCOPE_MAP:** `participant-simulation` → `Simulation Analysis`
**Task routing aliases:** `participant simulation`, `game theory`, `simulation`

### Audit Log Middleware (v2026.04.15)

General-purpose audit trail for all API requests. Fills the gap where only MCP tool calls had logging (`mcp_audit_log`).

**Model:** `AuditLog` (SQLite `audit_log` table) captures: `user_id`, `method`, `path`, `status_code`, `duration_ms`, `ip_address`, `project_id`, `timestamp`. No user content stored.

**Middleware:** `AuditLogMiddleware` registered in `main.py` as FastAPI middleware. Skips `/docs`, `/health`, `/openapi.json`, OPTIONS requests, and MCP server paths.

**API:** `GET /api/audit/logs?limit=100&offset=0&user_id=&project_id=&method=&path_prefix=` returns paginated, filterable audit entries.

### Observability: Telemetry Spans & Agent Hooks (v2026.04.15)

Local-first, zero-trust observability system. **No phone-home by default.** All telemetry data stays on the user's machine.

**Architecture:**
- `TelemetrySpan` model (SQLite): stores operational metadata per span — operation, skill, model, timing, status, quality score, consensus score, error type. **No prompts, responses, user content, or files.**
- `AgentHooks`: composable async lifecycle hooks (pre_task, post_task, post_validation, on_error, on_completion) — fire-and-forget via `asyncio.create_task()`. Built-in hooks for telemetry and model performance recording.
- `TelemetryRecorder`: writes spans to `telemetry_spans` table and upserts `ModelSkillStats` from production path (previously only written by autoresearch)

**Model Intelligence Production Path:**
Every skill execution now creates a `ModelSkillStats` row with `source="production"` alongside the existing autoresearch `source="autoresearch"`. This means the autoresearch leaderboard shows both real-world usage data and experiment data.

**API: `GET /api/metrics/{project_id}/model-intelligence`**
- Leaderboard: best model+temperature per skill from both production and autoresearch
- Error taxonomy: structured error types per model and skill
- Tool success rates: per-tool success rate, average duration, P50/P90 latency
- Latency percentiles: P50/P90/P99 response time per model

**Agent lifecycle instrumentation in `_execute_task()`:**
- `pre_task`: records start timestamp and creates initial span
- `post_task`: records skill execution outcome and writes ModelSkillStats
- `post_validation`: records validation method, consensus score
- `on_error`: records structured error type and truncated message
- `on_completion`: records final quality score and total duration

The Interfaces menu creates a bridge between UX Research and Product Design within Istara. It provides:

- **Design Chat**: An AI design assistant (Design Lead agent) with automatic research context injection via RAG. Uses the same SSE streaming and ReAct tool loop as the main Chat, with design-specific tools (generate_screen, edit_screen, create_variant, search_findings_for_design, create_design_brief, import_from_figma, list_screens). Messages are scoped to a design-specific `ChatSession` (`session_type="design"`) so they never mix with regular chat messages.

- **Session scoping**: Both Chat and Design Chat now create/find their own sessions automatically when `session_id` is not provided. Chat uses the default session; Design Chat creates/reuses a `session_type="design"` session. This prevents cross-contamination where chat messages appeared in the Design Chat history.

- **Screen Generation**: Text-to-UI generation via Google Stitch SDK integration. Supports device types (Mobile/Desktop/Tablet/Agnostic) and AI model selection. Screens can be seeded from research findings for evidence-grounded design.

- **Figma Integration**: REST API proxy for Figma v1 API. Import designs from Figma URLs, export generated screens, and extract design systems (components + styles).

- **Design Handoff**: Automated design brief generation from project Insights and Recommendations. Dev spec generation from generated screen HTML.

- **First-Time Onboarding**: Setup modal guides users through Stitch/Figma API key configuration with privacy warnings about external data sharing.

### Atomic Research Extension — DesignDecision

The Atomic Research evidence chain extends into design:
```
Nugget → Fact → Insight → Recommendation → DesignDecision → DesignScreen
```

DesignDecision is a new finding type that links Recommendations to design screens, maintaining full evidence traceability from raw research data to generated UI.

### Google Stitch Integration (Apache 2.0)

Istara integrates with Google Stitch via a Python httpx wrapper (backend/app/services/stitch_service.py). The SDK is TypeScript-only, so the backend calls Stitch's REST API directly. All generated HTML is scanned through ContentGuard for prompt injection protection.

Four Stitch Skills are imported as Istara skill definitions (Apache 2.0 license):
- stitch-design: Prompt enhancement + screen generation
- stitch-enhance-prompt: Design prompt refinement
- stitch-react-components: HTML→React conversion
- stitch-design-system: Design system synthesis

### Figma MCP Integration

Istara proxies Figma's REST API v1 (api.figma.com) via backend/app/services/figma_service.py. Supports: file retrieval, node inspection, image export, component listing, style extraction, and design system synthesis.

### Privacy & Local-First Considerations

Both Stitch and Figma integrations break Istara's local-first approach by sending data to external services. The system provides:
- First-time onboarding with explicit privacy warnings
- Per-session privacy acknowledgment banners before external API calls
- Clear visual indicators when data leaves the local environment
- All API keys stored in .env, never in database

### Loops & Schedule

The Loops & Schedule menu provides centralized monitoring and control for all automated processes in Istara:

- **Loop Overview Dashboard**: Real-time health monitoring of all background processes (agent loops, orchestrator, meta-orchestrator, heartbeat, scheduler). Status indicators show active/paused/behind-schedule/stopped states with interval and last-run timestamps. The `/api/loops/overview` endpoint returns agents, schedules, and a consolidated `health_summary` with per-status counts.

- **Cron Scheduler**: Full CRUD for cron-scheduled tasks with visual cron builder. Supports 5-field cron expressions with preset buttons and next-5-runs preview. Schedules can target specific skills and projects. The `/api/schedules` endpoints provide create, list, get, update (PATCH), and delete operations.

- **Agent Loop Configuration**: Per-agent runtime control of loop intervals, pause/resume toggles, and skill assignments. Changes apply immediately to running agent singletons without restart. The `/api/loops/agents/{id}/config` endpoint supports GET and PATCH, while `/api/loops/agents/{id}/pause` and `/resume` toggle agent state.

- **Custom Loops**: User-created loops combining skills + projects + intervals. Extends the scheduler with `loop_type=custom` for flexible automation. The `POST /api/loops/custom` endpoint accepts an interval in seconds or a cron expression and creates a `ScheduledTask` record.

- **Execution History**: Unified timeline of all loop/schedule executions with status, duration, findings count, and error messages. Paginated with filters by source type (agent/schedule), status, and source ID. The `/api/loops/executions` and `/api/loops/executions/stats` endpoints provide history and aggregated statistics.

- **Health Dashboard**: The `/api/loops/health` endpoint returns per-source health items including `source_type`, `source_id`, `status`, `interval_seconds`, `last_execution_at`, `next_expected_at`, and `behind_by_seconds` for identifying stale or failing processes.

### Notifications

The Notifications menu replaces the ephemeral toast-based notification system with a persistent, filterable notification center:

- **Persistent Storage**: Every WebSocket broadcast event is automatically persisted to the `notifications` table via a non-blocking hook in `ConnectionManager.broadcast()`. Events like `heartbeat_batch` are excluded to avoid noise. Each notification stores `type`, `title`, `message`, `category`, `severity`, `agent_id`, `project_id`, `action_type`, `action_target`, and `metadata_json`.

- **Filtering & Search**: Notifications can be filtered by `category` (agent_status, task_progress, finding_created, etc.), `severity` (info/warning/error/success), `agent_id`, `project_id`, `date_from`, `date_to`, `read` state, and full-text `search` across title and message fields. The `GET /api/notifications` endpoint supports all filters with pagination.

- **Read/Unread State**: Mark individual notifications as read via `POST /api/notifications/{id}/read` or mark all via `POST /api/notifications/read-all` (optionally scoped to a project). The `GET /api/notifications/unread-count` endpoint returns the current unread badge count.

- **Notification Preferences**: Per-category toggles for Show Toast (`show_toast`), Show in Notification Center (`show_center`), and Email Forward (`email_forward`). The `GET /api/notifications/preferences` and `PUT /api/notifications/preferences` endpoints allow users to customize which events they see where.

- **Action Notifications**: Some notifications carry actions (e.g., suggestions with "Navigate to chat" action, task completions with "View findings"). The `action_type` and `action_target` fields are preserved and rendered as clickable buttons in the notification center UI.

- **Lifecycle Management**: Individual notifications can be deleted via `DELETE /api/notifications/{id}` (returns 204). The `NotificationPreference` model supports per-agent scoping for fine-grained control over notification routing.

### Automated Backup System

Istara includes a comprehensive backup system that protects all user data with minimal configuration:

- **10-Component Coverage**: Every backup captures all data components — SQLite database, agent personas, skill definitions, project files, vector store, configuration, logs, documents, memory indices, and meta-overrides. Each component is tracked in the backup manifest with individual checksums.

- **Full + Incremental Strategy**: Full backups capture the complete system state. Incremental backups record only changes since the last full backup, reducing storage and time. The `backup_type` field on each `BackupRecord` distinguishes the two modes. A configurable `backup_full_interval_days` controls how frequently full backups occur.

- **SQLite Safe Copy**: The database is copied using `VACUUM INTO` to produce a consistent snapshot without locking the live database. This avoids WAL-mode corruption risks that plague naive file copies.

- **Scheduled Automatic Backups**: When `backup_enabled` is true, the system automatically creates backups at the interval specified by `backup_interval_hours`. A retention policy (`backup_retention_count`) automatically prunes older backups beyond the configured limit.

- **One-Click Restore**: Any backup can be restored via `POST /api/backups/{id}/restore`. The restore process verifies the backup checksum before applying, and creates a pre-restore snapshot so the user can roll back if needed.

- **Verification & Checksums**: `POST /api/backups/{id}/verify` recomputes the manifest checksum against the stored backup and confirms integrity. Verified backups are marked with `status="verified"` and a `verified_at` timestamp.

- **BackupRecord Tracking**: Every backup is tracked in the database with fields for `id`, `filename`, `backup_type`, `parent_id` (for incremental chains), `size_bytes`, `file_count`, `status`, `error_message`, `components`, `checksum`, `created_at`, and `verified_at`.

### Meta-Hyperagent (Experimental)

The Meta-Hyperagent is an experimental self-improvement layer inspired by the Hyperagents paper (DGM-H) on metacognitive self-modification. It observes Istara's own subsystems and proposes parameter optimizations:

- **5 Observed Subsystems**: The meta-hyperagent monitors routing (task-to-agent matching accuracy), evolution (prompt promotion rate and quality), skill selection (skill-task match rate), quality evaluation (verification pass rate), and agent capabilities (capability utilization and error rates).

- **Evidence-Based Proposals**: Each `MetaProposal` includes the `target_system`, `parameter_path`, `current_value`, `proposed_value`, a human-readable `reason`, an `evidence` array of supporting data points, a `confidence` score (0-1), and an `expected_impact` description.

- **User Approval Required**: No parameter change is auto-applied. All proposals enter a `pending` state and require explicit user approval via `POST /api/meta-hyperagent/proposals/{id}/approve`. This ensures the human operator retains full control over system behavior.

- **MetaVariant Tracking**: When a proposal is approved, a `MetaVariant` is created that records `old_value`, `new_value`, `applied_at`, `metrics_before`, and begins an observation window (`observation_window_hours`). During this window, `metrics_after` is populated. Variants can be reverted with one click (`POST /api/meta-hyperagent/variants/{id}/revert`) or confirmed (`POST /api/meta-hyperagent/variants/{id}/confirm`).

- **Confirmed Overrides**: When a variant is confirmed, the parameter override is persisted to `_meta_overrides.json` and loaded at startup, making the optimization permanent until manually removed.

- **Safety Mechanisms**: Value bounds prevent parameters from being set outside safe ranges. Rate limiting caps active variants at 3 simultaneously to prevent cascading instability. A full audit trail logs every proposal, approval, rejection, application, revert, and confirmation with timestamps.

### Academic References

| Method | Paper | Venue |
|--------|-------|-------|
| Mixture-of-Agents | Wang et al. (2025) | ICLR 2025 |
| Self-MoA | Li et al. (2025) | arXiv 2025 |
| LLM-Blender | Jiang et al. (2023) | ACL 2023 |
| Multi-Agent Debate | Du et al. (2024) | ICML 2024 |
| LLM-as-Judge | Zheng et al. (2023) | NeurIPS 2023 |
| Petals (distributed inference) | Borzunov et al. (2023) | ACL + NeurIPS 2023 |
| Hive (volunteer computing) | - | SoftwareX 2025 |
| BOINC (distributed compute) | Anderson (2020) | - |
| Multi-LLM Thematic Analysis | Jain et al. (2025) | arXiv 2025 |

---

## Messaging Integration System

### Multi-Instance Channel Architecture

Istara supports multiple messaging channel instances per platform (e.g., two Telegram bots for different studies).

| Platform | Transport | Auth | Features |
|----------|-----------|------|----------|
| Telegram | Long polling | Bot token | Text, voice, photos, docs, inline keyboards |
| Slack | Socket Mode | Bot token + signing secret | Text, files, Block Kit, threads |
| WhatsApp | Webhooks | Phone number ID + access token | Text, audio, images, templates, 24h window |
| Google Chat | Webhooks | Service account / webhook URL | Text, Cards v2 |

**Architecture**: `ChannelInstance` (DB) ↔ `ChannelAdapter` (in-memory) ↔ Platform API. The `ChannelRouter` manages all adapters keyed by `instance_id` (UUID).

**API**: Full CRUD at `/api/channels/*` — create, start, stop, health, messages, conversations, send.

### Webhook Router

Dedicated `/webhooks/*` router for inbound platform events (separate from `/api/` for different security policies):
- `POST /webhooks/whatsapp/{instance_id}` — WhatsApp message events
- `POST /webhooks/google-chat/{instance_id}` — Google Chat events
- `POST /webhooks/survey/{integration_id}` — Survey response events

---

## Survey Platform Integration

### Supported Platforms

| Platform | Auth | Webhooks | Create Surveys |
|----------|------|----------|----------------|
| SurveyMonkey | OAuth 2.0 | response_completed | Yes (POST /v3/surveys) |
| Google Forms | Service account | No (polling via Loops) | Yes (POST /v1/forms) |
| Typeform | API token | HMAC-SHA256 | Yes (POST /forms) |
| Microsoft Forms | N/A | N/A | Not supported (no API) |

### Response Ingestion Pipeline

Survey responses flow into the Atomic Research chain: Response → Parse Q&A → Create Nuggets (source = survey name) → Optionally trigger analysis skills → Update response counts.

**API**: `/api/surveys/integrations/*` for platform connections, `/api/surveys/links/*` for survey-project linkage.

---

## Research Deployment System

### Deployment via Messaging

Deploy interviews, surveys, and diary studies through messaging channels with adaptive questioning.

**Deployment Types**: Interview (structured/semi-structured), Survey (questionnaire via chat), Diary Study (longitudinal).

**Lifecycle**: Draft → Active → [Paused] → Completed → Analysis triggered.

### Adaptive Interview Engine (AURA-Style)

- Conversation state machine per participant: intro → questions → probing → wrap-up
- LLM-driven follow-up generation based on conversation history + research goals
- Configurable branching rules, rate limiting, completion criteria
- Audio message support with transcription
- All responses automatically create Nuggets in real-time

### Analytics Dashboard

- Per-question stats: response count, skip count, avg response time
- Participant tracker: status, current question, stall detection
- Findings pipeline: real-time Nuggets → Facts → Insights visualization
- Channel performance comparison across platforms
- Timeline with projected vs actual completion

**API**: Full CRUD + analytics at `/api/deployments/*`.

---

## MCP Integration (Model Context Protocol)

### SECURITY: Local-First Boundary

MCP is the only Istara subsystem that allows external access to local data. It is:
- **OFF by default** — requires explicit user activation
- **Gated by MCPAccessPolicy** — granular per-tool, per-resource, per-project permissions
- **Fully audited** — every request logged with caller info

### MCP Server (Istara as Provider)

Exposes Istara capabilities via FastMCP at `/mcp` when enabled.

| Tool | Risk | Default |
|------|------|---------|
| list_skills | LOW | ON |
| list_projects | LOW | ON |
| get_deployment_status | LOW | ON |
| get_findings | SENSITIVE | OFF |
| search_memory | SENSITIVE | OFF |
| execute_skill | HIGH | OFF |
| create_project | HIGH | OFF |
| deploy_research | HIGH | OFF |

### MCP Client Registry

Connect external MCP servers to augment Istara's capabilities. Discover tools, cache them, invoke on demand.

**API**: `/api/mcp/server/*` for server management, `/api/mcp/clients/*` for client registry.

---

## System Documentation Layer

### AGENT.md — Universal Agent-Readable Spec

Root-level file any AI agent can discover and parse. Contains system identity, architecture, capabilities catalog (auto-generated), agent interaction guide, security boundaries.

### Planner.md — Compass Workflow Control

`planner.md` is tracked as part of Compass. Agents use it for planned, multi-agent, branch-review, stale-branch, and correction workflows. It requires role declaration, repository intelligence checks, protected Compass file preservation, correction/re-review loops when real defects are found, and a final user teaching report when the completed work changes a feature, command, output, or process.

### Auto-Update Script

`scripts/update_agent_md.py` regenerates the Capabilities Catalog by scanning API routes, skills, agents, menus, models, and MCP tools. Run after every feature addition.

### Feature Documentation

`docs/features/` contains detailed guides for messaging-integrations, survey-integrations, mcp-integration, research-deployments, and system-overview.

---

## Laws of UX Knowledge Layer

### 30 Laws in 4 Clusters

Based on Jon Yablonski's *Laws of UX* (2nd Edition, O'Reilly, 2024) — lawsofux.com (CC BY-SA 4.0).

| Cluster | Count | Key Laws |
|---------|-------|----------|
| **Perception** | 6 | Proximity, Similarity, Common Region, Uniform Connectedness, Pragnanz, Aesthetic-Usability |
| **Cognitive** | 7 | Miller's Law, Cognitive Load, Working Memory, Chunking, Hick's Law, Selective Attention, Mental Model |
| **Behavioral** | 9 | Goal-Gradient, Zeigarnik, Peak-End Rule, Flow, Paradox of Active User, Pareto, Parkinson's, Von Restorff, Serial Position |
| **Principles** | 8 | Jakob's Law, Fitts's Law, Doherty Threshold, Tesler's Law, Occam's Razor, Postel's Law, Choice Overload, Cognitive Bias |

### Architecture

```
laws_of_ux.json (knowledge base, 30 laws with detection_keywords)
       |
       v
LawsOfUXService (pure Python, no LLM — keyword matching, scoring)
       |
       +-- Finding Enrichment (auto-tags nuggets with ux-law:{id})
       +-- Compliance Scoring (aggregate per-law scores from tagged nuggets)
       +-- API (/api/laws, /api/laws/compliance/{project_id})
       +-- Skill Execution (laws embedded in skill prompts)
       +-- Agent Knowledge (all 5 agents understand laws)
```

### Finding Enrichment

Every nugget created by any skill is automatically checked against the 30 laws' `detection_keywords` using Jaccard-like overlap scoring. Matching laws are appended as `ux-law:{id}` tags. Zero LLM cost — pure string operations.

### Compliance Profile

Aggregates all `ux-law:*` tagged nuggets in a project into per-law scores (0-100). Laws with no violations score 100. Scores degrade proportionally to violation count. Produces radar chart data grouped by the 4 categories.

### Nielsen Heuristic Cross-Reference

Each law maps to related Nielsen heuristics (H1-H10). This enables the "why" layer: heuristic violations are connected to the psychological principles that explain them.

### Skill Integration

The UX Law Compliance Audit skill evaluates interfaces against all 30 laws (following the heuristic-evaluation pattern). Additionally, 6 existing skills reference relevant laws in their execute_prompts: heuristic-evaluation, design-critique, cognitive-walkthrough, usability-testing, survey-design, interview-question-generator.

---

## Featured MCP Servers

### MCP Brasil (mcp-brasil)

Pre-configured MCP server available for one-click connection in the MCP tab.

- **Source**: [github.com/jxnxts/mcp-brasil](https://github.com/jxnxts/mcp-brasil) (MIT)
- **Tools**: 213 across 28 Brazilian government APIs
- **Categories**: Economics (BCB, IBGE), Legislation (Câmara, Senado), Transparency (Portal, TCU), Judiciary (DataJud), Elections (TSE), Environment (INPE, ANA), Health (DataSUS/CNES), Public Procurement (PNCP)
- **Auth**: 26 of 28 APIs need no authentication. Only Portal da Transparência and DataJud need free API keys.
- **Install**: `pip install mcp-brasil`
- **Connection**: Featured Servers section in MCP tab → one-click Connect

The `featured_mcp_servers.json` knowledge file stores pre-configured server definitions. New featured servers can be added by extending this file — the API auto-discovers them.

---

## Docker & Security Infrastructure

### Deployment Modes

| Mode | Command | TLS | Auth | Use Case |
|------|---------|-----|------|----------|
| Local Dev | `uvicorn` + `npm run dev` | No | No | Development |
| Docker Local | `docker compose up` | No | Optional | Single-user containers |
| Docker Team | `--profile team` | No | JWT | Multi-user with PostgreSQL |
| Production | `--profile production` | Auto (Caddy) | JWT | Server deployment |

### Caddy Reverse Proxy

Optional Caddy service (profile: `production`) provides automatic TLS via Let's Encrypt. Routes `/api/*`, `/webhooks/*`, `/mcp/*`, `/ws/*` to backend; everything else to frontend. Enables webhook accessibility for WhatsApp, Google Chat, and survey platforms.

### ComputeRegistry — Single Source of Truth

`compute_registry.py` (1010 lines) replaces both `LLMRouter` and `ComputePool` as the single authority for all LLM compute. If a node isn't in the registry, it doesn't exist to Istara.

**Node sources**:
- **Local**: Server machine's LM Studio/Ollama (auto-registered at startup, priority=1)
- **Network**: Discovered via subnet scanning (ports 1234, 11434, 8080, priority=10)
- **Relay**: Team members running the relay daemon (WebSocket, priority=20)
- **Browser**: Users donating compute via login (browser-based WebSocket relay)

**Routing algorithm**: capability filter → score (health, active requests, latency, priority, RAM) → retry 3x → cooldown 60s → failover to next node.

**Capability-aware**: When tools are needed, registry filters for nodes with 4B+ tool-capable models. Small models (1-2B) without tool support are deprioritized automatically.

**Backward compatible**: `from app.core.ollama import ollama`, `from app.core.llm_router import llm_router`, and `from app.core.compute_pool import compute_pool` all return the same `compute_registry` singleton. No existing code changes needed.

**Model warnings**: `/api/compute/model-warnings` flags capability limitations.

**Browser compute donation**: Users with LM Studio/Ollama can donate compute by logging in — the `useLocalLLM` hook detects localhost:1234/11434 and offers a "Donate AI compute" toggle. Works through NAT/corporate firewalls (outbound WebSocket only).

### Research Integrity System

Istara's qualitative research pipeline follows academic gold standards — Braun & Clarke (2006) reflexive thematic analysis, Saldaña (2021) coding manual, O'Connor & Joffe (2020) ICR guidelines, Krippendorff (2004) content analysis, Lincoln & Guba (1985) trustworthiness framework, Minto Pyramid Principle (MECE), Weick (1995) sensemaking, and Denzin (1978) triangulation.

**Core Principle**: Every finding must be traceable to exact source text — no hallucinated conclusions.

#### Mandatory Source Citation

All 5 qualitative skill definitions (thematic-analysis, user-interviews, usability-testing, contextual-inquiry, diary-studies) require chain-of-thought coding per nugget:

| Field | Purpose | Example |
|-------|---------|---------|
| `text` | Exact verbatim quote (3-300 words) | "I couldn't find where the export button was hidden" |
| `source` | Filename or participant ID | interview_p1_sarah.txt |
| `source_location` | Line, timestamp, or section | line:42-44 |
| `tags` | Applied codes | ["NAV_CONFUSION", "FEATURE_DISCOVERABILITY"] |
| `coding_reasoning` | Why this code applies (1-2 sentences) | "Participant describes inability to locate a UI element" |
| `confidence` | high / medium / low | high |

The agent pipeline (`_store_findings()`) maps confidence strings to floats (high→0.9, medium→0.6, low→0.3) and stores `source_location` on every Nugget.

#### Codebook System (Saldaña 2021)

Persistent versioned codebooks. Each code has 6 components: label, brief_definition, full_definition, exclusion_criteria, typical_example, boundary_example. `CodebookVersion` model stores `codes_json` with version tracking and changelog. Supports reflexive_ta, codebook_ta, and grounded_theory methodologies.

#### Code Application Audit Trail (O'Connor & Joffe 2020)

Every time a code is applied to source data, a `CodeApplication` record is created: project_id, code_id, source_text, source_location, coder_id, coder_type (llm/human/llm_reviewed), confidence, reasoning, review_status (pending/approved/rejected/modified), reviewed_by, reviewed_at. This creates a full Lincoln & Guba audit trail from recommendation back to exact source text.

**Human Review Queue**: LLM-applied codes land as `pending`. API endpoints:
- `GET /api/code-applications/{project_id}/pending` — sorted by confidence (lowest first)
- `PATCH /api/code-applications/{id}/review` — approve/reject/modify with reviewer ID
- `POST /api/code-applications/{project_id}/bulk-approve?min_confidence=0.9` — auto-approve high-confidence

#### Validation Gates

The `ValidationExecutor` runs multi-pass validation BEFORE findings are stored:

| Method | What It Does | Pass Threshold |
|--------|-------------|---------------|
| `adversarial_review` | LLM-as-judge rates code quality, evidence grounding, chain integrity, hallucination risk, depth (1-5 each) | Overall ≥ 3/5 |
| `dual_run` | Checks tag consistency across adjacent nuggets (Jaccard overlap) | Avg overlap ≥ 0.15 |
| `self_moa` | Verifies insights against RAG knowledge base | ≥ 30% verified |
| `debate_rounds` | Internal consistency check across insights | Basic coherence |

If validation fails → task stays `IN_REVIEW`, findings are NOT stored. The `AdaptiveValidation` system selects the best method based on historical performance per skill.

#### Document Convergence (Four-Layer Pyramid)

Skill outputs don't create new documents — they UPDATE existing reports via `ReportManager`:

```
L4: Final Deliverable (1-2 per project)     — MECE-structured, all stakeholders
 ↑
L3: Research Synthesis (auto-triggers)       — Cross-method triangulation
 ↑
L2: Study Analysis (1 per method)            — "Interview Analysis", "Usability Study", etc.
 ↑
L1: Raw artifacts (codebooks, intermediates)  — Feeds RAG, not user-facing
```

**`SCOPE_MAP`** routes 25 skills to report scopes: thematic-analysis → "Interview Analysis", usability-testing → "Usability Study", survey-design → "Survey Analysis", etc.

**Auto-synthesis**: When 2+ L2 reports exist, `_check_synthesis_trigger()` auto-creates/updates an L3 "Research Synthesis" report, aggregating all L2 finding IDs. Triangulated findings (confirmed by 2+ methods) get higher confidence.

**MECE Restructuring**: Findings organized into mutually exclusive, collectively exhaustive categories using the Minto Pyramid Principle — bottom-up analysis, top-down presentation.

#### Intercoder Reliability

`KappaIntercoderSkill` (v3.1.0) runs a true dual-coding pipeline:
1. **Coder A** — LLM open-codes data (temp=0.3)
2. **Coder B** — Independent LLM re-codes using Coder A's codebook (temp=0.3)
3. **Python computes both metrics** (no LLM math):
   - **Cohen's Kappa**: Binary agreement per code, macro-averaged. Landis & Koch scale (poor/slight/fair/moderate/substantial/almost_perfect).
   - **Krippendorff's Alpha**: Handles N coders, missing data, nominal metric. Scale: reliable (≥0.800), tentatively acceptable (≥0.667), unreliable (<0.667).
4. **Reconciliation**: Third LLM pass resolves disagreements, refines codebook definitions

Both metrics reported with per-code breakdowns. Low-agreement codes flagged for codebook refinement.

#### Evidence Chain

Full audit trail: `Recommendation → Insight → Fact → Nugget → source_text + source_location + coding_reasoning → CodeApplication (who, what, where, why, reviewed?)`

#### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/reports/{project_id}` | GET | Project reports (convergence pyramid) |
| `/api/codebook-versions/{project_id}` | GET | Codebook version history |
| `/api/codebook-versions/{project_id}/latest` | GET | Latest codebook |
| `/api/codebook-versions` | POST | Create new codebook version |
| `/api/code-applications/{project_id}` | GET | All code applications |
| `/api/code-applications/{project_id}/pending` | GET | Pending human review |
| `/api/code-applications/{id}/review` | PATCH | Approve/reject code |
| `/api/code-applications/{project_id}/bulk-approve` | POST | Bulk-approve high-confidence |

#### Testing

56 pytest tests covering: CodebookVersion model (4), CodeApplication model (4), Cohen's Kappa math (10), Krippendorff's Alpha math (12), ValidationExecutor (10), ReportManager (6+), ProjectReport model (7+). All use in-memory async SQLite. Simulation scenario 70 covers end-to-end API testing.

### Native Tool Calling

Istara uses native OpenAI-compatible function calling via the `tools` API parameter. LM Studio and Ollama both support this format. Tools are defined in `OPENAI_TOOLS` (system_actions.py) with JSON Schema parameters.

**15 system tools**: create_task, search_documents, list_tasks, move_task, attach_document, search_findings, list_project_files, assign_agent, send_agent_message, get_document_content, search_memory, update_task, sync_project_documents, **web_fetch**, **browse_website**.

**browse_website**: AI-powered browser agent (via browser-use library) that can navigate websites, click elements, fill forms, and extract content. Uses LM Studio/Ollama as the LLM provider. For competitor analysis, usability testing, form evaluation. Optional dependency.

**Playwright MCP**: Available as a featured MCP server (21 browser control tools). Uses accessibility trees (2-5KB text) for page analysis — works with any text model, no vision required. For precise browser automation and accessibility auditing.

**web_fetch**: Agents can fetch any public URL, convert HTML to readable text (via html2text), and analyze the content. Private/internal IPs are blocked for security.

**Multi-step reasoning**: The chat ReAct loop supports up to 8 tool iterations per turn. The model decides when to stop calling tools.

**Fallback**: If the LLM doesn't support native tools, falls back to text-based tool parsing (legacy).

### Security Architecture (Production-Grade)

**Global Authentication**: `SecurityAuthMiddleware` enforces JWT on ALL endpoints. No route can bypass it — auth is checked before any route handler runs. 150+ endpoints protected by a single middleware.

**Auth Flow**: Login → JWT issued → included in all API calls (`Authorization: Bearer`) + WebSocket connections (`?token=`). Token expiration: configurable (default 24h).

**Admin Bootstrap**: On first startup, admin user auto-created. Credentials printed to server console and persisted to `.env`.

**Exempt Paths** (no auth required): `/api/health`, `/api/auth/login`, `/api/auth/register`, `/api/settings/status`, `/webhooks/*`.

**Admin-Only Operations**: Backup download/restore/delete, MCP server toggle/policy, settings modification, system agent deletion.

### Security Layers

| Layer | Implementation | Scope |
|-------|---------------|-------|
| Global JWT Auth | `SecurityAuthMiddleware` | ALL endpoints (150+) |
| Security Headers | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, etc. | ALL responses |
| CORS | Configurable origins, restricted methods/headers | Browser requests |
| Rate Limiting | slowapi token bucket per IP | API endpoints |
| Network Access Token | Additional token for non-localhost connections | LAN/remote |
| WebSocket Auth | JWT via `?token=` query param | `/ws`, `/ws/relay` |
| Admin Role Check | `require_admin_from_request()` | Sensitive operations |
| MCP Access Policy | Per-tool permissions with audit log | MCP server |
| Relay Auth | Network token + JWT (always, not just team mode) | Compute relay |
| Field Encryption | Fernet (AES-128-CBC + HMAC-SHA256) | Channel creds, API keys, survey tokens |
| Filesystem Hardening | Data dir 0700, DB files 0600, backups 0600 | All data files |
| PostgreSQL SSL | `ssl=prefer` on asyncpg connections | Team mode |

### Data Encryption

Sensitive fields in the database are encrypted at rest using Fernet symmetric encryption (`cryptography` library):
- `ChannelInstance.config_json` (Telegram tokens, Slack secrets, WhatsApp tokens)
- `SurveyIntegration.config_json` (OAuth tokens, API keys)
- `MCPServerConfig.headers_json` (authorization headers)

Encrypted fields use `ENC:` prefix for gradual migration — existing unencrypted data works, new data gets encrypted. The encryption key (`DATA_ENCRYPTION_KEY`) is auto-generated on first startup and persisted to `.env`. If lost, encrypted data is unrecoverable — by design.

### Admin User Management

Users are managed exclusively through the UI (Settings → Team Members) or authenticated API. No direct database manipulation.

**UI**: "Invite Member" form with display name, username, email, temporary password, and role selector. Success shows copyable credentials. Non-admins see read-only user list.

**API**:
- `GET /api/auth/users` — list all users (admin only)
- `POST /api/auth/users` — create user (admin only, works regardless of TEAM_MODE)
- `DELETE /api/auth/users/{id}` — delete user (admin only, cannot delete self)
- `PATCH /api/auth/users/{id}/role` — change role (admin only)

**Roles**: Admin (full access), Researcher (create/edit projects), Viewer (read-only)

### Container Health Checks

Backend: `curl -f http://localhost:8000/api/health` (30s). Frontend: Node.js fetch (30s). Compose uses `condition: service_healthy` for dependency ordering.

### Multi-Stage Builds

Backend: Builder (compile wheels) → Runtime (slim, non-root user). Frontend: Deps → Build → Runner (Next.js standalone, ~100MB).

---

## Autoresearch System (Karpathy Pattern)

Inspired by [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) (MIT license). Implements a greedy hill-climbing optimization loop adapted for 6 UX research domains.

### Architecture

```
AutoresearchEngine (core loop)
    |
    +-- BaseLoopRunner (interface)
    |       |
    |       +-- ModelTempRunner (Loop 6: grid search models × temperatures)
    |       +-- RAGParamsRunner (Loop 4: chunk size, overlap, hybrid weights)
    |       +-- SkillPromptRunner (Loop 1: skill prompt mutation + eval)
    |       +-- PersonaRunner (Loop 5: agent persona optimization)
    |       +-- QuestionBankRunner (Loop 3: interview question refinement)
    |       +-- UISimRunner (Loop 2: accessibility + usability via simulation)
    |
    +-- Isolation Layer (contextvars — prevents experiment pollution)
    +-- Rate Limiter (daily/per-skill experiment caps)
    +-- Persona Lock (prevents concurrent persona file modifications)
```

### The Loop (per iteration)

1. Check rate limits and mutual exclusion with Meta-Hyperagent
2. Runner generates hypothesis (LLM-powered for Loops 1, 3, 5; grid-based for Loop 6)
3. Runner applies mutation (code edit, config change, or parameter swap)
4. Runner measures score (quality metric specific to loop type)
5. If score > best: **KEEP** (new baseline). Else: **REVERT** (undo mutation)
6. Log experiment to `autoresearch_experiments` table
7. Broadcast progress via WebSocket

### Conflict Isolation

| Existing System | Isolation Mechanism |
|---|---|
| Self-Evolution | Guard clauses skip learning records; trigger prefix filter in promotion scan |
| Agent Learning | `is_autoresearch_active()` returns early in all record methods |
| Meta-Hyperagent | Stats filtered in observe cycle; mutual exclusion before experiments |
| Skill Manager | Guard in record_execution; autoresearch uses own ModelSkillStats |
| Prompt RAG | Cache invalidated after persona mutations |

### Model/Temperature Leaderboard

The `model_skill_stats` table tracks quality per (skill, model, temperature). Loop 6 grid-searches all available models × temperatures [0.1, 0.3, 0.5, 0.7, 0.9]. The leaderboard shows the best configuration per skill.

### Academic References

| Method | Paper | Venue |
|--------|-------|-------|
| Autoresearch | Karpathy (2026) | github.com/karpathy/autoresearch (MIT) |
| AURA Adaptive Questioning | arXiv 2510.27126 | 2025 |
| Prompt Mutation Operators | Kosuri (2026) | Medium |

---

## ADVANCED CAPABILITIES (v2026.04.15)

### 1. Synthetic Browser Research
Istara wraps raw browser automation (`browser-use`) in structured UXR methodologies. The `competitive-analysis`, `accessibility-audit`, and `heuristic-evaluation` skills now support automated data collection from live URLs before synthesis.

### 2. Formal Evaluation Framework (LLM-as-Judge)
The `evaluate-research` skill provides a standalone rigor benchmark. It utilizes multi-model adversarial review (Du et al., 2024) and full-ensemble scoring with Fleiss' Kappa reliability to grade research outputs against academic standards.

### 3. Game Theory Participant Simulation
Participant simulations are enhanced with game-theory strategies (`SimulationStrategy`). Personas like 'The Satisficer' (low effort) and 'The Skeptic' (adversarial) allow researchers to stress-test their instruments against realistic behavioral biases.

### 4. Local-First OpenTelemetry & Tracing
For high-compliance environments, Istara supports local-only OTLP tracing via a bundled `otel-collector` and `jaeger` instance. This allows full lifecycle tracing of research tasks (Request -> RAG -> Skill -> Verification) with zero cloud dependency.

---

## Orchestration Benchmarks & Academic Lineage (v2026.04.17)

Istara is evaluated against the 2026 **SOTA Agentic Benchmarks** to ensure its orchestration logic meets global standards for autonomous systems.

| Benchmark | Focus Area | Istara Implementation |
| :--- | :--- | :--- |
| **DeepPlanning** | Global Optimization | Evaluated in Layer 4 via DAG decomposition logic (`AgentOrchestrator`). |
| **Claw-Eval** | Trajectory Consistency | Evaluated via `Pass^3` consensus variance across audit traces. |
| **SkillsBench** | Modular Proficiency | Measures the success "lift" provided by the 53 domain-specific skills. |
| **Memento** | Self-Evolution | Tests the efficacy of the Agent Factory in proposing valid specialized personas. |
| **NL2Repo** | Workspace Seeding | Measures the ability to generate complex research project structures from briefs. |
| **TAU3-Bench** | Policy Reasoning | Evaluates reasoning over the **30 Laws of UX** policy document tree. |
| **MCP-Atlas** | Tool Coordination | Tests the simultaneous orchestration of multiple independent MCP servers. |

These benchmarks are automated in the **Layer 4: Orchestration Suite** (`tests/benchmarks/run_benchmarks.py`).

---

*Istara is open-source and built for researchers who believe AI should work for them — on their machine, on their terms.*

---

## Phase Zeta: Orchestration Refinement (April 2026)

Phase Zeta focuses on reaching **Layer 5 Orchestration Maturity** through real-world behavioral validation and architectural unification of the compute layer.

### 1. Layer 5 Benchmarking (Real-World Orchestration)
The orchestration architecture is validated with a zero-mock integration suite (`tests/integration/test_llm_orchestration_real.py`). This ensures:
- **100% TSQ**: Tool Selection Quality on complex, multi-stage research goals.
- **DAG Decomposition**: Successful planning and execution of serial/parallel dependent steps.
- **Resilient Recovery**: Graceful handling of malformed LLM outputs via automated retry and re-planning logic.

### 2. Unified Compute Registry & Empirical Probing
Istara consolidates all LLM management into a single `ComputeRegistry`, replacing fragmented routing and pool systems.
- **RFC 3986 Compliance**: Strict URI normalization ensures consistent routing to generic OpenAI-compatible providers, eliminating 404 errors on varied `base_url` formats.
- **Empirical Evaluation**: Instead of relying on brittle metadata, Istara uses **Dynamic Probing** (Berkeley Function Calling Leaderboard pattern) to actively verify model capabilities like tool-calling and streaming support using standardized test payloads.

### 3. Installer Resilience
The `scripts/install-istara.sh` utility supports persistent port overrides. Configured `FRONTEND_PORT` and `BACKEND_PORT` values are automatically saved to `backend/.env` to ensure consistent state across system updates and restarts.

---

## Integration Surface Area & Resilience (April 2026)

Istara's Integrations menu connects research workflows to external messaging, survey, and MCP platforms. Every integration follows a uniform resilience pattern.

### Messaging Channels
| Platform | Adapter | Transport | Resilience |
|---|---|---|---|
| **Telegram** | `TelegramAdapter` | python-telegram-bot v22+ async polling | Retry + circuit breaker |
| **WhatsApp** | `WhatsAppAdapter` | Meta Graph API v22.0 webhook | Retry + circuit breaker + webhook idempotency |
| **Slack** | `SlackAdapter` | slack-bolt Socket Mode / HTTP | Retry + circuit breaker |
| **Google Chat** | `GoogleChatAdapter` | Webhook / service account | Retry + circuit breaker |

### Resilience Patterns
All outbound channel calls are protected by:
- **Exponential backoff retry** (3 retries, 1s base, full jitter) — recovers from transient API failures.
- **Circuit breaker** (5 failures / 60s recovery) — prevents cascading overload to degraded upstream APIs.
- **Webhook idempotency** (WhatsApp) — deduplicates retried webhook deliveries by `external_message_id`, capping cache at 10K entries.

### Survey Platforms
| Platform | Module | Status |
|---|---|---|
| **Google Forms** | `services/survey_platforms/google_forms.py` | Active |
| **SurveyMonkey** | `services/survey_platforms/surveymonkey.py` | Active |
| **Typeform** | `services/survey_platforms/typeform.py` | Active |

### MCP (Model Context Protocol)
- **Server exposure**: Configurable via `MCPAccessPolicy` with risk-level gating (low / sensitive / high).
- **Audit logging**: Every tool invocation recorded in `MCPAuditEntry` with arguments, caller, policy, and duration.
- **Rate limiting**: High-risk tools (`execute_skill`, `create_project`, `deploy_research`) capped per hour.
- **Client registry**: External MCP servers registered with encrypted headers (`encrypt_field`).
