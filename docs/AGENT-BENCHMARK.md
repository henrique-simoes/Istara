# ReClaw Agent Architecture Benchmark

Pre-release internal assessment. Brutally honest comparison against reference platforms.

**Date**: 2026-03-28
**Assessed by**: Automated code path analysis + external documentation review

---

## How ReClaw's Agents ACTUALLY Work

### Tool Use: Text-Parsing, NOT Native Function Calling

ReClaw injects tool descriptions as markdown into the system prompt, asks the LLM to output JSON like `{"tool": "tool_name", "params": {...}}`, and parses it with regex. Every other platform (OpenClaw, Hermes, Claude Code) uses native API-level tool calling.

**Impact**: Unreliable invocation, wasted context tokens, can't leverage model fine-tuning for tools. The regex misses malformed JSON. The LLM hallucinate tool names.

**Fix**: Use the OpenAI-compatible `/v1/chat/completions` `tools` parameter that LM Studio already supports.

### Multi-Step Reasoning: Limited ReAct Loop

Chat has a 3-iteration ReAct loop (LLM -> tool call -> result -> LLM again). The autonomous work cycle (`_execute_task()`) does ONE skill call. No plan-then-execute pattern. No task decomposition.

**Impact**: Can't handle complex multi-step research workflows autonomously.

### Context Management: Solid

This is a genuine strength. Prompt RAG (query-aware persona retrieval), DAG-based context summarization, LLMLingua-style compression, token budgeting. Limited by local model context windows (4K-32K) vs cloud (200K+).

### Agent Autonomy: Real But Basic

Background Kanban task loop runs genuinely. Polls for tasks, picks by priority, executes skills, has wake signals. But agents only execute predefined skills or do single LLM calls. No creative initiative.

### Inter-Agent Communication: Decorative

A2A messages are written to the DB and broadcast on WebSocket, but **no agent's work loop reads or reacts to them**. The MetaOrchestrator assigns tasks but doesn't inject collaboration context. Messages exist for UI display only.

### Memory: Multi-Layered But Uneven

Three systems: MEMORY.md files, vector store notes, learning DB. The learning system looks up past error resolutions before retrying. But MEMORY.md is only loaded into chat context — the autonomous orchestrator uses skills, not personas, so memory is partially disconnected.

### Streaming: Misleading

Tool-calling turns buffer the full response before processing. Only the final non-tool response streams. Users see loading then full text for tool turns.

---

## Benchmark Table

| Capability | ReClaw | OpenClaw | Hermes Agent | Claude Code | Claude Cowork |
|---|---|---|---|---|---|
| **Native Tool Calling** | Stub (regex) | Full | Full | Full | Full |
| **Multi-Step Reasoning** | Partial (3-iter chat, 1-shot autonomous) | Full | Full | Full | Full |
| **Context Management** | Partial (solid but small windows) | Full | Partial | Full (200K) | Full (200K) |
| **Autonomous Work** | Partial (skill execution only) | Full (heartbeat daemon) | Partial (reactive) | Missing (user-initiated) | Partial |
| **Inter-Agent Comms** | Stub (DB messages unread) | Full (hierarchical delegation) | Missing (single agent) | Partial (sub-agent reports) | Full (peer messaging) |
| **Memory Persistence** | Partial (3 systems, unevenly connected) | Full (MD + SQLite + ClawHub) | Partial (bounded MD files) | Partial (CLAUDE.md) | Partial |
| **Error Recovery** | Partial (backoff + learning DB) | Full (idempotent + branching) | Full | Full | Partial |
| **Streaming** | Partial (final turn only) | Full | Full | Full | Full |
| **Task Routing** | Partial (keyword matching) | Full (LLM-powered) | N/A | Full (model decides) | Full |
| **Multi-Agent Orchestration** | Partial (5 roles, keyword routing) | Full (gateway + delegation) | Missing | Partial (1-level sub-agents) | Full (lead + teammates) |
| **Persona/Identity System** | Full (4-file MD, compression, Prompt RAG) | Partial (config dirs) | Partial (2 MD files) | Partial (CLAUDE.md) | Partial |
| **Self-Evolution** | Partial (proposals, learning DB) | Full (self-extending skills) | Full (skill doc evolution) | Missing | Missing |
| **Channel Integration** | Stub (adapters exist, not used in chat) | Full (50+ channels) | Full (6 backends) | Partial (CLI + IDE) | Partial |
| **Multimodal** | Missing | Partial (browser) | Partial (vision) | Full | Full |
| **Atomic Research Model** | Full (unique differentiator) | Missing | Missing | Missing | Missing |
| **Resource Governance** | Full (hardware-aware throttling) | Partial | Missing | Missing | Missing |
| **Laws of UX Knowledge** | Full (30 laws, auto-tagging) | Missing | Missing | Missing | Missing |

---

## Strengths (Where ReClaw Leads)

1. **Persona system**: 4-file MD structure with query-aware Prompt RAG compression. More sophisticated than any comparison platform's identity system.

2. **Self-evolution infrastructure**: Skill health tracking, improvement proposals, autonomous skill creation proposals, agent learning DB with error pattern matching. The foundations are real even if partially connected.

3. **Atomic Research data model**: Nuggets -> Facts -> Insights -> Recommendations with evidence chain linking. Domain-specific and genuinely useful. No comparison platform has this.

4. **Laws of UX knowledge layer**: 30 psychological principles auto-tagged on every finding. Unique domain knowledge architecture.

5. **Resource governance**: Hardware-aware agent throttling with configurable budgets. Production infrastructure most frameworks lack.

6. **Error recovery with learned resolutions**: Recording errors, looking up known resolutions before retry, exponential backoff.

---

## Critical Gaps (Must Fix)

| Priority | Gap | Impact | Fix |
|----------|-----|--------|-----|
| P0 | Text-based tool calling (regex parsing) | Unreliable invocation, wasted tokens | Switch to native `tools` API parameter |
| P0 | A2A messages decorative (unread by agents) | No real multi-agent coordination | Inject A2A context into work cycle |
| P1 | Single-shot autonomous reasoning | Can't handle complex workflows | Add planning step + port ReAct loop |
| P1 | Keyword-based task routing | Misroutes novel task descriptions | LLM-based routing |
| P2 | No multimodal capabilities | Can't analyze screenshots/wireframes | Add vision support |
| P2 | Misleading streaming | UX degradation on tool-calling turns | Stream tool turns progressively |

---

## Additional Inspirations Tracked

From ReClaw's memory and development history:

| Source | What ReClaw Adopted | Gap Remaining |
|---|---|---|
| **Hyperagents Paper (DGM-H)** | Meta-Hyperagent for parameter tuning | Metacognitive self-modification not recursive |
| **Memento-Skills Paper** | Skill creation proposals, agent factory | Skills don't self-modify at execution time |
| **Karpathy Autoresearch** | 6 optimization loops, isolation layer | Greedy ratchet only, no exploration |
| **OpenClaw Architecture** | 8 patterns tracked (see project memory) | Channel routing, plugin ecosystem, heartbeat daemon |
| **AURA Framework** | Adaptive interview engine | No RL-based question optimization yet |
| **Fleiss Kappa / Multi-LLM** | Ensemble validation system | Ensemble data collection not triggering |
| **Nielsen Heuristics** | Heuristic evaluation skill, Pixel agent | Need deeper integration with Laws of UX |
| **ISO 9241** | Usability standards referenced in skills | Not formally codified as compliance checklist |

---

## Verdict

ReClaw invested heavily in **infrastructure** (personas, skills, memory, orchestration, resource governance) and **domain knowledge** (Atomic Research, Laws of UX, 50+ UXR skills). The domain-specific value is a genuine differentiator.

The gap is in **agent primitives**: tool calling, reasoning loops, inter-agent coordination. These are the foundations that OpenClaw and Claude Code got right first. ReClaw's infrastructure is solid but built on a weak core loop.

**Path to competitive parity**:
1. Native function calling via tools API
2. ReAct loop in autonomous work cycle
3. A2A messages influence agent behavior
4. LLM-based task planning and routing
5. Multimodal support (screenshots, wireframes)
