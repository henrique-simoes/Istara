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
│   │   ├── run.mjs                    # Simulation orchestrator (30 scenarios)
│   │   ├── scenarios/                 # Test scenarios (01-29)
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

*ReClaw is open-source and built for researchers who believe AI should work for them — on their machine, on their terms.*
