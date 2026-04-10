# Istara vs pi-mono — Agent Orchestration, Loops, Subagents & Context Engineering

**Date:** 2026-04-08
**Istara:** `github.com/henrique-simoes/Istara` (v2026.04.08.3)
**pi-mono:** `github.com/badlogic/pi-mono` (v0.66.1)

---

## Executive Summary

This is a deep technical comparison of how Istara and pi-mono handle **agent orchestration, subagent loops, and context engineering** — the core mechanics of how AI agents reason, delegate, and maintain state across complex workflows.

**Fundamental difference:** Istara orchestrates **multiple autonomous specialist agents** that coordinate on research projects through A2A messaging and a shared skill execution system. pi-mono runs a **single coding agent** with an extensible tool system and deliberately avoids subagents, delegating orchestration to the user (via tmux, extensions, or external SDK integrations).

---

## 1. Agent Architecture

### Istara: Multi-Agent Specialist Orchestra

Istara runs **6 persistent, domain-specialized agents** that operate concurrently:

| Agent | Purpose | Autonomy Level |
|---|---|---|
| **Cleo** (`istara-main`) | Research coordinator — plans studies, assigns tasks, synthesizes findings | High — creates tasks, selects skills, coordinates other agents |
| **Sentinel** (`istara-devops`) | DevOps auditor — monitors health, catches regressions, audits deployments | Medium — runs scheduled checks, reports findings |
| **Pixel** (`istara-ui-audit`) | UI auditor — WCAG 2.2 AA, Nielsen heuristics, design system consistency | Medium — triggered by UI changes, produces audit reports |
| **Sage** (`istara-ux-eval`) | UX evaluator — usability patterns, user flow quality | Medium — evaluates UX against heuristic frameworks |
| **Echo** (`istara-sim`) | User simulator — runs Playwright scenarios simulating real user journeys | High — autonomously executes simulation scenarios |
| **Design Lead** | Design system evaluator — token usage, component consistency | Medium — evaluates design compliance |

**Orchestration Model:**
- Agents are **long-lived processes** started at backend boot (`lifespan()` in `main.py`)
- Each agent has its own **persona files** (CORE.md, SKILLS.md, PROTOCOLS.md) that define behavior
- Agents communicate via **A2A (Agent-to-Agent) messaging** — a shared message bus
- Agents share a **task queue** — tasks are created, assigned, executed, and completed
- Results flow through the **atomic evidence chain**: Nugget → Fact → Insight → Recommendation → CodeApplication
- Agents are **coordinated by Cleo** (the main agent), which plans research studies and delegates work

**Implementation:**
```
Backend startup:
  lifespan() → start all agents as async tasks
    ├── istara-main (Cleo) — main orchestrator
    ├── istara-devops (Sentinel) — scheduled health checks
    ├── istara-ui-audit (Pixel) — on-demand UI audits
    ├── istara-ux-eval (Sage) — on-demand UX evaluations
    ├── istara-sim (Echo) — simulation execution
    └── design-lead — design system evaluation

Agent execution loop:
  1. Agent picks up task from queue (or creates one)
  2. Agent selects skill from 53 available skills
  3. Skill's plan_prompt generates execution plan
  4. Skill's execute_prompt runs with LLM
  5. Results structured via output_schema
  6. Findings created (evidence chain)
  7. WebSocket broadcasts notify UI
  8. Agent reports completion or delegates to another agent
```

### pi-mono: Single Agent with Extension Tools

pi-mono has **one agent**: the coding agent. It's an interactive, single-user, terminal-based coding assistant.

**Architecture:**
```
Agent class (stateful):
  ├── Message pipeline: AgentMessage[] → transformContext() → convertToLlm() → model call
  ├── Event streaming: ordered events (agent_start/end, turn_start/end, message_*, tool_*)
  ├── Tool execution: parallel (concurrent after preflight) or sequential
  ├── State management: mutable state with copy-on-assignment for top-level arrays
  ├── Control flow: steer() (interrupts active runs), followUp() (queues post-turn work)
  ├── Lifecycle: abort() and waitForIdle()
  └── Low-level API: agentLoop/agentLoopContinue (raw streaming, no barriers)
```

**Tool System:**
- 4 built-in tools: `read`, `write`, `edit`, `bash`
- Extensible via **Extensions** (TypeScript modules):
  ```typescript
  export default function (pi: ExtensionAPI) {
    pi.registerTool({ name: "deploy", ... });
    pi.registerCommand("stats", { ... });
    pi.on("tool_call", async (event, ctx) => { ... });
  }
  ```
- **Skills** — on-demand capability packages following the Agent Skills standard
- Extensions can: add custom tools, custom commands, custom UI, sub-agents, plan mode, permission gates, MCP integration, git checkpointing

**Deliberate Omissions (by design):**
- **No sub-agents:** "Spawn pi instances via tmux, or build your own with extensions, or install a package"
- **No plan mode:** "Write plans to files, or build it with extensions"
- **No permission popups:** "Run in a container, or build your own confirmation flow"
- **No MCP:** "Build CLI tools with READMEs (Skills), or build an extension"
- **No background bash:** "Use tmux. Full observability, direct interaction"

**Key Design Philosophy:** pi is **aggressively minimal** in its core and **aggressively extensible** via the extension system. The author believes that features like subagents should be user-configurable rather than baked in.

---

## 2. Subagent / Delegation Model

### Istara: Built-In Multi-Agent Delegation

Istara has **native subagent support** through its A2A messaging system:

**How delegation works:**
1. Cleo (main agent) creates a research plan
2. Cleo creates tasks and assigns them — some to herself, some to specialist agents
3. Example: "Analyze interview transcripts" → Echo runs the analysis skill → produces findings → Cleo synthesizes
4. Agents can **consult each other** — Pixel shares UI findings with Sage for UX interpretation
5. Results flow back through the findings chain

**A2A Message Types:**
- Task assignment
- Task completion
- Findings notification
- Agent status updates
- Error reporting
- Cross-agent consultation requests

**No explicit spawning:** Agents are pre-started processes. Delegation is message-based, not process-based.

### pi-mono: No Built-In Subagents

pi-mono **explicitly rejects** built-in subagents:

> "No sub-agents. There's many ways to do this. Spawn pi instances via tmux, or build your own with extensions, or install a package that does it your way."

**How users achieve subagent-like behavior:**
1. **tmux spawning:** Run multiple pi instances in tmux panes/windows
2. **Extensions:** Write a TypeScript extension that manages subagent coordination
3. **SDK integration:** Use `createAgentSession()` / `createAgentSessionRuntime()` to embed pi in a custom orchestrator
4. **Third-party packages:** Install a pi package that implements subagent patterns

**Example SDK integration** (from the README):
```typescript
import { AuthStorage, createAgentSession, ModelRegistry, SessionManager } from "@mariozechner/pi-coding-agent";

const authStorage = AuthStorage.create();
const modelRegistry = ModelRegistry.create(authStorage);
const { session } = await createAgentSession({
  sessionManager: SessionManager.inMemory(),
  authStorage,
  modelRegistry,
});
await session.prompt("What files are in the current directory?");
```

This SDK can be used to build a **custom orchestrator** that spawns multiple agent sessions and coordinates them.

**Reference implementation:** [openclaw/openclaw](https://github.com/openclaw/openclaw) is cited as a "real-world SDK integration" — a project that uses pi's SDK to build a custom agent orchestration.

---

## 3. Agent Loops

### Istara: Task → Skill → Execution Loop

Istara's agent loop is **task-driven and skill-based**:

```
┌─────────────────────────────────────────────┐
│              Agent Execution Loop            │
│                                              │
│  1. Check task queue for pending work        │
│  2. Select skill based on task type          │
│     (53 skills across 4 Double Diamond       │
│      phases: Discover/Define/Develop/Deliver)│
│  3. Skill's plan_prompt → LLM generates plan │
│  4. Skill's execute_prompt → LLM executes    │
│  5. Output validated against output_schema   │
│  6. Findings created (evidence chain)        │
│  7. WebSocket broadcast → UI notified        │
│  8. Agent reports task completion            │
│  9. Check for follow-up tasks or delegation  │
│  10. Loop back to step 1                     │
└─────────────────────────────────────────────┘
```

**Loop characteristics:**
- **Asynchronous** — agents run as background async tasks
- **Non-interactive** — agents work autonomously without user intervention
- **Skill-gated** — each skill has plan_prompt → execute_prompt → output_schema
- **Evidence-producing** — every loop iteration creates structured findings
- **Observable** — WebSocket broadcasts at every step

### pi-mono: Interactive Turn-Based Loop

pi-mono's agent loop is **interactive and turn-based**:

```
┌─────────────────────────────────────────────┐
│          pi-mono Agent Loop (Interactive)    │
│                                              │
│  1. User types message in terminal editor    │
│  2. Messages → transformContext() pruning    │
│  3. convertToLlm() → standard LLM format     │
│  4. Model call with tools (read/write/edit/  │
│     bash + extension tools)                  │
│  5. LLM responds with tool calls             │
│  6. Tools execute (parallel or sequential)   │
│  7. Tool results sent back to LLM            │
│  8. LLM produces final response or more      │
│     tool calls (loop continues)              │
│  9. Turn ends → user sees results            │
│  10. User types next message (or queues      │
│      steering/follow-up messages)            │
│  11. Loop back to step 2                     │
└─────────────────────────────────────────────┘
```

**Loop characteristics:**
- **Interactive** — user drives each turn
- **Tool-rich** — LLM can call tools multiple times per turn
- **Streaming** — real-time event emission (message updates, tool execution)
- **Steerable** — user can queue messages mid-execution
- **Branchable** — `/tree` command lets users jump to any point and branch

**Steering vs Follow-Up:**
- **Steering** (Enter): Delivered after current turn's tool calls finish
- **Follow-Up** (Alt+Enter): Delivered only after agent finishes all work
- This is a sophisticated **mid-execution communication** mechanism that Istara doesn't have for interactive steering (Istara's agents are fully autonomous).

---

## 4. Context Engineering

This is where the two systems diverge most dramatically.

### Istara: Research-Context Architecture

Istara's context engineering is **domain-focused on research knowledge**:

| Mechanism | How It Works |
|---|---|
| **Project Context** | Company context, project goals, guardrails stored in DB — provided to agents in system prompts |
| **RAG (Retrieval-Augmented Generation)** | Documents chunked (1200 chars, 180 overlap), embedded in LanceDB, top-k=5 retrieval at 0.3 score threshold |
| **Context DAG** | `ContextDAGNode` model — DAG-based summarization for long conversations, hierarchical context organization |
| **Atomic Evidence Chain** | Nugget → Fact → Insight → Recommendation → CodeApplication — structured context that persists across sessions |
| **Findings Context** | Every finding is linked to its source (documents, interviews, surveys), providing provenance |
| **Model Context** | `ModelSkillStats` tracks which models perform best on which skills — context-aware routing |
| **Session Context** | `ChatSession` model groups messages with inference presets |
| **Task Context** | Tasks carry input/output document references, URLs, validation results |
| **Compass Context** | Generated docs provide agents with current architecture maps — agents never guess about system state |

**Context injection flow:**
```
User creates project → sets context (company, goals, guardrails)
  → Context stored in Project model
  → Agent reads context when planning tasks
  → Documents uploaded → chunked → embedded in LanceDB
  → Skill execution → RAG retrieves relevant chunks
  → Findings created → linked to source context
  → Context DAG summarizes long conversation history
```

**Context limitations in Istara:**
- No explicit context window management — relies on RAG to stay within limits
- No proactive compaction — Context DAG provides summarization but isn't triggered by window limits
- No branching — sessions are linear (no `/tree` equivalent)
- No lossy compaction tradeoff — all evidence is preserved

### pi-mono: Session Context Architecture

pi-mono's context engineering is **session-focused and developer-centric**:

| Mechanism | How It Works |
|---|---|
| **Session JSONL** | Sessions stored as JSONL files with tree structure — each entry has `id` and `parentId` for branching |
| **Context Files** | `AGENTS.md` / `CLAUDE.md` loaded from cwd up through parent directories + global (`~/.pi/agent/AGENTS.md`) |
| **System Prompt** | Replaceable via `.pi/SYSTEM.md` (project) or `~/.pi/agent/SYSTEM.md` (global), appendable via `APPEND_SYSTEM.md` |
| **Branching** | `/tree` — navigate session tree in-place, select any point, continue from there, switch between branches. All history preserved in single file |
| **Forking** | `/fork` — create new session file from current branch point |
| **Compaction** | Automatic (triggers on context overflow or proactively approaching limit) and manual (`/compact [prompt]`). Summarizes older messages, keeps recent ones. Lossy — full history remains in JSONL |
| **Context Usage Tracking** | Footer shows total token/cache usage, cost, context usage percentage |
| **Message Queue** | Steering (post-current-turn) and Follow-Up (post-all-work) messages queued during agent execution |
| **Transform Context** | `transformContext()` prunes/compacts messages before each model call — filters to standard LLM formats via `convertToLlm()` |
| **Model/Provider Context** | `/model` switches models, `/scoped-models` enables model cycling (Ctrl+P), thinking level adjustable |

**Context injection flow:**
```
User starts pi → loads AGENTS.md from cwd up + global
  → Loads skills, extensions, prompt templates, theme
  → Session created (JSONL tree)
  → User types message → @file references included
  → transformContext() prunes/compacts
  → convertToLlm() filters to LLM format
  → Model call with tools
  → Tool results added to session
  → Context approaches limit → compaction triggers
  → /tree lets user branch from any point
  → /fork creates new session from branch
```

**Context strengths in pi-mono:**
- **Branching:** Full session tree with `/tree` navigation — this is powerful context management
- **Forking:** Copy any branch into a new session for parallel exploration
- **Compaction:** Automatic and manual, with custom extension hooks
- **Message queuing:** Real-time steering and follow-up during agent execution
- **Lossy awareness:** Full history preserved in JSONL even when compacted
- **Context visibility:** Token usage, cost, and context percentage shown in footer

---

## 5. Context Engineering: Head-to-Head

| Dimension | Istara | pi-mono |
|---|---|---|
| **Context Scope** | Project-level (company, goals, guardrails) | Session-level (conversation + loaded files) |
| **RAG / Retrieval** | Yes — LanceDB vector store, chunking, top-k retrieval | No — relies on explicit file references (`@file`) |
| **Context Compaction** | Via Context DAG (summarization) | Automatic + manual `/compact` with extension hooks |
| **Context Branching** | No — linear sessions | Yes — full session tree with `/tree` navigation |
| **Context Forking** | No | Yes — `/fork` creates new session from branch |
| **Context Files** | Project context in DB | AGENTS.md/CLAUDE.md from filesystem (cwd up) |
| **System Prompt** | Agent persona files (CORE.md) | SYSTEM.md / APPEND_SYSTEM.md override |
| **Context Visibility** | Implicit — agents work autonomously | Explicit — token count, cost, context % in footer |
| **Context Pruning** | RAG retrieves only relevant chunks | `transformContext()` prunes before each call |
| **Mid-Execution Context Update** | No — agents are autonomous | Yes — steering/follow-up message queue |
| **Context Loss** | No — evidence chain is append-only | Yes — compaction is lossy (full history in JSONL) |
| **Context Persistence** | DB-backed — survives restarts | JSONL files in `~/.pi/agent/sessions/` |
| **Context Sharing** | Project members share via team mode | `/share` uploads to GitHub gist with HTML |
| **Context Publishing** | No | Publish to Hugging Face for OSS data collection |

---

## 6. Agent Orchestration: Comparison Matrix

| Capability | Istara | pi-mono |
|---|---|---|
| **Multi-agent coordination** | ✅ Native — 6 agents with A2A messaging | ❌ Deliberately omitted — use tmux/extensions/SDK |
| **Task queue** | ✅ Shared task queue with assignment | ❌ Single-user interactive |
| **Skill/Tool selection** | ✅ 53 skills, auto-selected by agent | ✅ 4 built-in + unlimited via extensions |
| **Subagent spawning** | ✅ Message-based delegation | ❌ User must spawn via tmux or build orchestrator |
| **Agent autonomy** | ✅ Fully autonomous background agents | ❌ Interactive only — user drives every turn |
| **Cross-agent consultation** | ✅ Agents share findings and consult | ❌ Single agent |
| **Scheduled execution** | ✅ Heartbeat manager, scheduled checks | ❌ No scheduling |
| **Real-time steering** | ❌ Agents work autonomously | ✅ Steering/follow-up message queue |
| **Session branching** | ❌ Linear sessions | ✅ Full session tree with `/tree` |
| **Context compaction** | Via Context DAG | Automatic + manual `/compact` |
| **RAG / retrieval** | ✅ LanceDB vector store | ❌ Manual `@file` references |
| **Evidence chain** | ✅ Nugget → Fact → Insight → Recommendation | ❌ No structured evidence |
| **Extensibility** | Via skills (JSON prompts) and personas | Via extensions (TypeScript), skills, packages |
| **Package ecosystem** | ❌ No | ✅ Pi Packages (npm/git installable) |
| **SDK for embedding** | ❌ | ✅ `createAgentSession()` API |
| **RPC mode** | ❌ | ✅ stdin/stdout JSONL for non-Node integration |

---

## 7. Design Philosophy: Why They Differ

### Istara's Philosophy: "Everything Included"

Istara assumes the user wants a **complete research platform** where agents do the work autonomously. The design choices reflect this:

- **Pre-built agents** so the user doesn't need to orchestrate anything
- **RAG built-in** so context is automatically retrieved
- **Evidence chains** so research is auditable
- **Team mode** so multiple people can use the platform
- **Security layers** because it handles sensitive research data
- **Compass** because the codebase is complex and needs architectural memory

### pi-mono's Philosophy: "Aggressively Extensible, Minimally Opinionated"

pi-mono assumes the user is a **developer who wants to shape their own workflow**. The design choices reflect this:

- **No subagents** because "there's many ways to do this" — the user decides
- **No plan mode** because "write plans to files" — simple is better
- **No permission popups** because "run in a container" — environment-level security
- **No MCP** because "build CLI tools with READMEs" — simpler abstraction
- **No background bash** because "use tmux" — existing tools are sufficient
- **Extensions for everything** — if you need it, build it or install a package

From the README: *"Pi is aggressively extensible so it doesn't have to dictate your workflow. Features that other tools bake in can be built with extensions, skills, or installed from third-party pi packages. This keeps the core minimal while letting you shape pi to fit how you work."*

---

## 8. What Each Does Better

### Istara Does Better:
- **Multi-agent orchestration** — 6 specialist agents coordinating autonomously
- **Research context** — RAG, evidence chains, provenance tracking
- **Team collaboration** — multi-user with roles, shared projects
- **Enterprise security** — 12 layers of defense-in-depth
- **Architectural memory** — Compass auto-generates docs from code
- **Compliance** — WCAG 2.2 AA, Nielsen heuristics enforced by agents
- **Structured output** — 53 skills with output_schema validation

### pi-mono Does Better:
- **Session branching** — `/tree` navigation is genuinely powerful
- **Context visibility** — real-time token/cost/context tracking
- **Mid-execution steering** — communicate with agent while it works
- **Extensibility** — TypeScript extensions can modify anything
- **Package ecosystem** — npm/git installable skills, extensions, themes
- **SDK embedding** — `createAgentSession()` API for custom integrations
- **RPC mode** — stdin/stdout JSONL for any language integration
- **Provider breadth** — 20+ providers vs Istara's Ollama/LM Studio focus
- **Developer ergonomics** — `@file` references, `!command` execution, image paste

---

## 9. Key Insight: Complementary, Not Competitive

Istara and pi-mono solve different layers of the agent stack:

```
┌───────────────────────────────────────────┐
│  Application Layer (End Users)            │
│  Istara: Research platform with agents    │
│  Users: UX researchers, product teams     │
├───────────────────────────────────────────┤
│  Agent Framework Layer (Developers)       │
│  pi-mono: Agent toolkit with extensions   │
│  Users: AI engineers, developers          │
├───────────────────────────────────────────┤
│  LLM Provider Layer                       │
│  pi-ai (pi-mono) / Ollama / OpenAI etc.   │
└───────────────────────────────────────────┘
```

**You could combine them:** Use pi-mono's coding agent to develop features for Istara, or use Istara's research platform to study the usability of pi-mono's coding agent workflows.

---

## 10. The One Thing Each Lacks That the Other Has

**Istara lacks:** Session branching, mid-execution steering, context visibility, package ecosystem, provider breadth, RPC mode, SDK embedding. All of these are areas where pi-mono excels.

**pi-mono lacks:** Multi-agent orchestration, RAG retrieval, evidence chains, team mode, structured skill execution, compliance auditing, auto-generated documentation. All of these are areas where Istara excels.
