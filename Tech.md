# ReClaw Technical Architecture

> **Local-first AI agents for UX Research** — autonomous, self-evolving, hardware-aware.

ReClaw is a production-grade agent platform designed for UX researchers who want AI that runs on their machine, learns from their work, and gets better over time — without sending data to the cloud.

---

## Why ReClaw's Architecture Matters

Before diving into details, here are the design decisions that make ReClaw a robust choice for researchers and teams who care about data ownership, cost, and reliability.

### 1. Agents That Actually Improve Themselves

Most agent frameworks treat prompts as static configuration. ReClaw's agents **evolve**: they record error patterns, track workflow preferences, and when patterns reach maturity thresholds (3+ occurrences, 2+ contexts, 30 days), those learnings are permanently promoted into the agent's persona files. This is not fine-tuning — it's structured prompt evolution that works with any local model.

### 2. Every Finding Is Traceable to Source

ReClaw implements the **Atomic Research** methodology (Nugget → Fact → Insight → Recommendation) with full evidence chains. Every insight links back through facts to the exact quote or data point that supports it. No hallucinated conclusions without provenance.

### 3. Lossless Context Memory

Conversations are never thrown away. ReClaw's **DAG-based context summarization** creates hierarchical summaries of older messages while preserving the originals. Agents can drill back into any conversation depth to recover details. Combined with a 6-level context hierarchy, every chat gets the right context without exceeding the model's window.

### 4. Works With Any Local Model (1.5B to 70B)

A hardware-aware **Resource Governor** monitors RAM, CPU, and GPU to prevent system overload. **Prompt RAG** dynamically retrieves only the relevant persona sections for each query (30-50% token savings). **LLMLingua-inspired compression** removes filler without losing meaning (15-30% savings). Together, these allow ReClaw to run meaningfully on a 3B model with a 2K context window — or scale up to use everything a 70B model offers.

### 5. 45+ Research Skills, Self-Monitoring

Each skill follows the Double Diamond methodology and produces structured outputs. A **Skill Health Monitor** tracks execution quality over time, and when a skill's performance drops below threshold, it auto-proposes prompt improvements. Skills are self-contained modules with `plan()`, `execute()`, and `validate()` methods.

### 6. Five Coordinated Agents, Not One

ReClaw runs a **meta-orchestrator** coordinating five specialized agents — a task executor, a DevOps auditor, a UI auditor, a UX evaluator, and a user simulator. Each has a distinct persona, and they communicate through an internal A2A messaging system. Custom agents participate in the same pipeline automatically.

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

---

## Agent System

### Multi-Agent Architecture

ReClaw runs five coordinated agents managed by a **MetaOrchestrator**. Each agent has a distinct role, persona, and work pattern.

| Agent | Role | Persona | What It Does |
|-------|------|---------|-------------|
| **ReClaw** | Task Executor | Cleo | Primary worker. Executes all 45+ skills, produces findings |
| **Sentinel** | DevOps Audit | — | Monitors data integrity, orphaned references, system health |
| **Pixel** | UI Audit | — | Runs Nielsen's heuristics, WCAG checks, design system audits |
| **Sage** | UX Evaluation | — | Evaluates UX quality, cognitive load, journey completeness |
| **Echo** | User Simulation | — | Simulates end-user behavior, tests flows, detects friction |

**Custom agents** created by users are full participants in this system — they get auto-generated persona files and join the same evolution pipeline.

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

### Task-Document Linking

Tasks support bidirectional document linking, allowing users and agents to attach source materials (inputs) and track produced artifacts (outputs).

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

Instead of hardcoded intent detection with regex/dictionaries, ReClaw uses **structured tool schemas** injected into the LLM's system prompt. The LLM itself decides which tool to call based on the user's natural language request.

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

ReClaw implements an OpenClaw-inspired self-improvement system where agents literally rewrite their own personas based on accumulated experience.

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

## Prompt Management for Local Models

Running on local models (1.5B to 14B parameters) with limited context windows (2K to 8K tokens) requires careful prompt engineering. ReClaw implements three complementary strategies.

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

### Strategy 3: Context Window Guard

A **ContextWindowGuard** (`core/token_counter.py`) prevents prompt overflow on every request:

1. Estimates total tokens: system prompt + message history + reserved reply buffer (512 tokens)
2. If over budget, trims oldest messages first
3. Inserts a `[History trimmed for context budget]` note so the model knows context was lost
4. Works alongside DAG summarization for lossless recovery of trimmed content

### How They Work Together

```
User sends message
  │
  ├─ Prompt RAG selects relevant persona sections (30-50% savings)
  │
  ├─ Context Hierarchy composes 6-level system prompt
  │
  ├─ RAG retrieves relevant document chunks
  │
  ├─ If over budget → LLMLingua compressor reduces further (15-30%)
  │
  ├─ Context Window Guard trims history if still over
  │
  └─ Final prompt sent to local model
```

---

## Context & Memory System

### 6-Level Context Hierarchy

Every prompt is composed from a layered context system where each level adds domain-specific knowledge:

| Level | Type | What It Contains | Example |
|-------|------|-----------------|---------|
| 0 | **Platform** | ReClaw defaults — UXR expertise, Atomic Research methodology | "You are a UX Research agent..." |
| 1 | **Company** | Organization culture, terminology, research standards | "Our company uses NPS > 50 as the success threshold" |
| 2 | **Product** | Product-specific knowledge, user base, competitors | "The app targets enterprise HR managers" |
| 3 | **Project** | Research questions, goals, timeline, participants | "We're studying onboarding friction for Q2" |
| 4 | **Task** | Task-specific instructions, skill parameters | "Analyze these 5 interview transcripts for..." |
| 5 | **Agent** | Agent persona (CORE/SKILLS/PROTOCOLS/MEMORY) | "You are Cleo, a meticulous researcher..." |

Contexts at each level are stored as `ContextDocument` records in the database with priority ordering and enable/disable flags. The `compose_context()` function merges them top-down for every interaction.

### DAG-Based Lossless Context Summarization

Traditional context management either truncates (lossy) or keeps everything (overflow). ReClaw's **Context DAG** (`core/context_dag.py`) provides a third option: hierarchical summarization with full recovery.

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

Every file a user uploads, every output an agent produces, and every task completion that generates an artifact becomes a **Document**. Documents are ReClaw's source of truth — the final, findable output of everything.

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

ReClaw's retrieval combines **vector similarity** and **keyword search** using configurable weights:

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

The **ResourceGovernor** (`core/resource_governor.py`) prevents ReClaw from overwhelming the host machine:

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

| Capability | ReClaw | Google ADK | LangGraph | CrewAI | AutoGen |
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

| Protocol | What It Does | ReClaw Status |
|----------|-------------|---------------|
| **A2A** (Google) | Agent-to-agent communication, task lifecycle | Partial — DB-backed messaging, `/.well-known/agent.json` exposed |
| **MCP** (Anthropic) | Model-tool integration (resources, tools, prompts) | Compatible — skills can be exposed as MCP tools, contexts as resources |
| **OpenAI-compatible API** | LLM provider abstraction | Full — both LM Studio and Ollama use this |

### Prompt Compression Comparison

| Approach | Method | Requirements | Speed | Compression |
|----------|--------|-------------|-------|-------------|
| **LLMLingua** (Microsoft) | GPT-2 perplexity scoring | PyTorch + GPU | ~100ms | 2-20x |
| **LLMLingua-2** | BERT token classifier | PyTorch + GPU | ~50ms | 2-10x |
| **ReClaw heuristic** | Word importance + domain terms + sentence scoring | None (pure Python) | ~5ms | 1.2-2x |
| **Prompt RAG** (ReClaw) | Query-aware section retrieval | None | ~10ms | 1.5-3x |
| **Truncation** | Cut at token limit | None | ~0ms | Variable |

ReClaw trades compression ratio for **zero dependencies** and **instant speed** — the right trade-off for local-first where every millisecond of inference startup matters.

### Memory System Comparison

| System | Short-term | Long-term | Structured | Self-evolving |
|--------|-----------|-----------|-----------|---------------|
| **ReClaw** | Message history + DAG summaries | MEMORY.md + AgentLearning DB + Vector store | 6-level hierarchy + Atomic Research | Yes (promotion pipeline) |
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
   a. Loads session → gets assigned agent (e.g., reclaw-main)
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

## Testing & Quality Assurance

### Simulation Framework

ReClaw includes a comprehensive **Playwright + Node.js simulation agent** at `tests/simulation/` that runs 32 scenarios covering:

| Category | Scenarios | Checks |
|----------|----------|--------|
| System health | Health check, onboarding, settings | 24 |
| Core features | Chat, file upload, skills, findings, Kanban, sessions | 80+ |
| Agent system | Architecture, communication, identity, personas | 50+ |
| Data integrity | Vector DB, findings chains, task consistency | 30+ |
| Advanced | Full pipeline, self-verification, DAG, robustness | 50+ |
| **Self-evolution & compression** | Evolution scan, Prompt RAG, budget compliance, domain preservation | **35** |
| **Documents system** | CRUD, search, filtering, sync, backup, UI navigation, keyboard shortcuts | **25** |
| **Event wiring audit** | WebSocket event coverage, broadcast↔handler pairing, governor lifecycle, scheduler | **15** |
| **Task-document linking & tools** | Task CRUD with new fields, document attach/detach, URL updates, system tools, frontend JS verification | **15** |

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

1. **Before tests start:** `POST /api/settings/maintenance/pause` — halts all ReClaw agent work and LLM calls
2. **During tests:** Tests use the user's currently configured model (no model switching). Only test LLM calls hit the model.
3. **After tests complete:** `POST /api/settings/maintenance/resume` — agents resume normal operation
4. **Crash safety:** Signal handlers (`SIGINT`, `SIGTERM`) and the `.catch()` handler call `emergencyResume()` to ensure the backend never stays permanently paused after a test crash

This replaces the previous approach of switching to a separate `gemma-3-1b-it-qat` test model, which caused LM Studio to load both models simultaneously and freeze the system.

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

## Project Structure

```
ReClaw-main/
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
│   │   │       ├── reclaw-main/       # Cleo's identity
│   │   │       ├── reclaw-devops/     # Sentinel's identity
│   │   │       ├── reclaw-ui-audit/   # Pixel's identity
│   │   │       ├── reclaw-ux-eval/    # Sage's identity
│   │   │       └── reclaw-sim/        # Echo's identity
│   │   ├── core/
│   │   │   ├── agent.py               # AgentOrchestrator (work loop)
│   │   │   ├── agent_identity.py      # Persona loading + compression
│   │   │   ├── agent_learning.py      # Error/pattern tracking
│   │   │   ├── agent_memory.py        # Agent note-taking + recall
│   │   │   ├── self_evolution.py      # Learning → persona promotion
│   │   │   ├── prompt_compressor.py   # LLMLingua-style heuristic
│   │   │   ├── prompt_rag.py          # Query-aware prompt composition
│   │   │   ├── context_hierarchy.py   # 6-level context system
│   │   │   ├── context_dag.py         # DAG-based lossless summarization
│   │   │   ├── context_summarizer.py  # LLM-powered message compression
│   │   │   ├── token_counter.py       # Context window guard
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
│   │   │   └── definitions/           # 45+ skill definitions
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

ReClaw supports both local (single-user, no auth) and team modes:

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

A provider-agnostic routing layer that supports Ollama, LM Studio, and any OpenAI-compatible endpoint:

- **LLMRouter**: Same interface as `OllamaClient` (`health()`, `chat()`, `chat_stream()`, `embed()`) — drop-in replacement.
- **Priority-based routing**: Requests go to the highest-priority healthy server with automatic failover.
- **Background health checks**: Every 60 seconds across all registered servers.
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

### ReClaw Relay Daemon

A Node.js daemon that allows team members to donate LLM compute:

- **Outbound WebSocket**: Connects from the relay machine to the server — no inbound ports needed (NAT-friendly).
- **State machine**: CONNECTING → IDLE → DONATING → USER_ACTIVE → DISCONNECTED.
- **Heartbeat**: System stats (RAM, CPU, GPU, loaded models) sent every 30 seconds.
- **LLM proxy**: Receives requests from the server, forwards to local Ollama/LM Studio, returns results.
- **Priority queue**: P0 (user chat) > P1 (user tasks) > P2 (agent work) > P3 (background validation).
- **Auto-reconnect**: Exponential backoff with max 60-second delay.

**Files**: `relay/` directory — `index.mjs`, `lib/connection.mjs`, `lib/state-machine.mjs`, `lib/heartbeat.mjs`, `lib/llm-proxy.mjs`

### Compute Pool

Server-side registry of connected relay nodes:

- **Node scoring**: `score = (model_capability * 0.4) + (1 - load) * 0.3 + (1/latency) * 0.2 + (ram) * 0.1`
- **Capacity tracking**: Total RAM, CPU cores, available models across the pool.
- **Best-node selection**: For any given model request, selects the node with the highest score.
- **WebSocket endpoint**: `/ws/relay` for relay node connections.

**Files**: `backend/app/core/compute_pool.py`, `backend/app/api/routes/compute.py`

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

### UX Bug Fixes & WCAG Compliance (March 2026)

Major UX overhaul addressing WCAG compliance, Nielsen's heuristics violations, and usability issues:

- **Notification Center**: Full notification center (like GitHub/LinkedIn) with bell icon, unread badge, notification history (max 50), mark-all-as-read, clear-all. All notification backgrounds use solid opacity (≥80%) for WCAG contrast compliance. Every notification navigates to its relevant page on click.
- **Chat Agent Identity**: Chat bubbles now show the actual agent name (not hardcoded "ReClaw") during both message history and streaming responses. Agent names are resolved from the session's agent_id against the agent store.
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

ReClaw is now a **true multi-agent system** where tasks are automatically routed to the best-matching agent based on specialty domains. Previously, all tasks went to the main ReClaw agent — now the intelligent task router analyzes each task's keywords, skill requirements, and description to determine which agent(s) should handle it.

**Task Router** (`backend/app/core/task_router.py`):
- **Specialty-based routing**: Each agent has defined specialties (research, devops, ui, ux, simulation). The router matches task keywords against specialty domains.
- **Multi-specialty detection**: Tasks that require multiple domains (e.g., "accessibility audit of user journey") are assigned a primary agent and collaboration requests are sent to secondary agents via A2A.
- **User-created agent support**: Custom agents define their specialties in the `specialties` JSON column on the Agent model. The router considers all active agents — system and user-created.
- **Explicit assignment respected**: If a task is manually assigned to an agent, the router respects that assignment.
- **Graceful fallback**: If the target agent is inactive, tasks fall back to reclaw-main.

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
- System agents seeded with domain specialties: reclaw-main=research, reclaw-devops=devops, reclaw-ui-audit=ui, reclaw-ux-eval=ux, reclaw-sim=simulation.
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

### Interfaces Menu & Research→Design Bridge

The Interfaces menu creates a bridge between UX Research and Product Design within ReClaw. It provides:

- **Design Chat**: An AI design assistant (Design Lead agent) with automatic research context injection via RAG. Uses the same SSE streaming and ReAct tool loop as the main Chat, with design-specific tools (generate_screen, edit_screen, create_variant, search_findings_for_design, create_design_brief, import_from_figma, list_screens).

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

ReClaw integrates with Google Stitch via a Python httpx wrapper (backend/app/services/stitch_service.py). The SDK is TypeScript-only, so the backend calls Stitch's REST API directly. All generated HTML is scanned through ContentGuard for prompt injection protection.

Four Stitch Skills are imported as ReClaw skill definitions (Apache 2.0 license):
- stitch-design: Prompt enhancement + screen generation
- stitch-enhance-prompt: Design prompt refinement
- stitch-react-components: HTML→React conversion
- stitch-design-system: Design system synthesis

### Figma MCP Integration

ReClaw proxies Figma's REST API v1 (api.figma.com) via backend/app/services/figma_service.py. Supports: file retrieval, node inspection, image export, component listing, style extraction, and design system synthesis.

### Privacy & Local-First Considerations

Both Stitch and Figma integrations break ReClaw's local-first approach by sending data to external services. The system provides:
- First-time onboarding with explicit privacy warnings
- Per-session privacy acknowledgment banners before external API calls
- Clear visual indicators when data leaves the local environment
- All API keys stored in .env, never in database

### Loops & Schedule

The Loops & Schedule menu provides centralized monitoring and control for all automated processes in ReClaw:

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

ReClaw includes a comprehensive backup system that protects all user data with minimal configuration:

- **10-Component Coverage**: Every backup captures all data components — SQLite database, agent personas, skill definitions, project files, vector store, configuration, logs, documents, memory indices, and meta-overrides. Each component is tracked in the backup manifest with individual checksums.

- **Full + Incremental Strategy**: Full backups capture the complete system state. Incremental backups record only changes since the last full backup, reducing storage and time. The `backup_type` field on each `BackupRecord` distinguishes the two modes. A configurable `backup_full_interval_days` controls how frequently full backups occur.

- **SQLite Safe Copy**: The database is copied using `VACUUM INTO` to produce a consistent snapshot without locking the live database. This avoids WAL-mode corruption risks that plague naive file copies.

- **Scheduled Automatic Backups**: When `backup_enabled` is true, the system automatically creates backups at the interval specified by `backup_interval_hours`. A retention policy (`backup_retention_count`) automatically prunes older backups beyond the configured limit.

- **One-Click Restore**: Any backup can be restored via `POST /api/backups/{id}/restore`. The restore process verifies the backup checksum before applying, and creates a pre-restore snapshot so the user can roll back if needed.

- **Verification & Checksums**: `POST /api/backups/{id}/verify` recomputes the manifest checksum against the stored backup and confirms integrity. Verified backups are marked with `status="verified"` and a `verified_at` timestamp.

- **BackupRecord Tracking**: Every backup is tracked in the database with fields for `id`, `filename`, `backup_type`, `parent_id` (for incremental chains), `size_bytes`, `file_count`, `status`, `error_message`, `components`, `checksum`, `created_at`, and `verified_at`.

### Meta-Hyperagent (Experimental)

The Meta-Hyperagent is an experimental self-improvement layer inspired by the Hyperagents paper (DGM-H) on metacognitive self-modification. It observes ReClaw's own subsystems and proposes parameter optimizations:

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

ReClaw supports multiple messaging channel instances per platform (e.g., two Telegram bots for different studies).

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

MCP is the only ReClaw subsystem that allows external access to local data. It is:
- **OFF by default** — requires explicit user activation
- **Gated by MCPAccessPolicy** — granular per-tool, per-resource, per-project permissions
- **Fully audited** — every request logged with caller info

### MCP Server (ReClaw as Provider)

Exposes ReClaw capabilities via FastMCP at `/mcp` when enabled.

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

Connect external MCP servers to augment ReClaw's capabilities. Discover tools, cache them, invoke on demand.

**API**: `/api/mcp/server/*` for server management, `/api/mcp/clients/*` for client registry.

---

## System Documentation Layer

### AGENT.md — Universal Agent-Readable Spec

Root-level file any AI agent can discover and parse. Contains system identity, architecture, capabilities catalog (auto-generated), agent interaction guide, security boundaries.

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

### Native Tool Calling

ReClaw uses native OpenAI-compatible function calling via the `tools` API parameter. LM Studio and Ollama both support this format. Tools are defined in `OPENAI_TOOLS` (system_actions.py) with JSON Schema parameters.

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

*ReClaw is open-source and built for researchers who believe AI should work for them — on their machine, on their terms.*
