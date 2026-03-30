# Istara Agentic Architecture — Complete Pipeline Documentation

## Overview

Istara's agent system operates through two parallel pipelines: **interactive chat** (user-driven, real-time) and **autonomous work** (background, task-driven). Both share the same tool ecosystem, memory systems, and finding storage.

---

## Pipeline 1: Interactive Chat

```
User Message
    |
    v
[1] POST /api/chat (chat.py)
    |
    v
[2] Context Composition
    ├── Agent Identity (agent_identity.py → Prompt RAG)
    │   ├── CORE.md (personality, values)
    │   ├── SKILLS.md (capabilities — only relevant sections via Prompt RAG)
    │   ├── PROTOCOLS.md (behavioral rules — query-aware retrieval)
    │   └── MEMORY.md (learned patterns)
    ├── Context Hierarchy (context_hierarchy.py)
    │   ├── Level 0: Platform defaults (always present)
    │   ├── Level 1: Company context
    │   ├── Level 2: Product context
    │   ├── Level 3: Project context
    │   └── Level 4: Task context
    ├── RAG Context (rag.py)
    │   └── Hybrid search: vector similarity (70%) + BM25 keyword (30%)
    └── Conversation History (with DAG compaction)
    |
    v
[3] LLM Call with Native Tool Calling
    ├── Provider: LM Studio or Ollama (compute_registry.py → lmstudio.py)
    ├── tools=OPENAI_TOOLS (14 tools in JSON Schema format)
    ├── Streaming: token-by-token to frontend via SSE
    └── Model selection: priority-based from healthy servers
    |
    v
[4] ReAct Tool Loop (up to 8 iterations)
    ├── Model returns tool_calls → execute tool → inject result
    ├── Tools: create_task, search_findings, web_fetch, etc.
    ├── role: "tool" messages with tool_call_id
    └── Loop until model stops calling tools
    |
    v
[5] Response Streamed to Frontend
    ├── SSE chunks via EventSourceResponse
    ├── WebSocket broadcast: finding_created events
    └── Context summarization triggered asynchronously (DAG compaction)
```

### Key Files
| Step | File | Function |
|------|------|----------|
| 1 | `api/routes/chat.py` | `chat_endpoint()` |
| 2 | `core/agent_identity.py` | `compose_identity()` |
| 2 | `core/prompt_rag.py` | `compose_dynamic_prompt()` |
| 2 | `core/context_hierarchy.py` | `compose_context()` |
| 2 | `core/rag.py` | `retrieve_context()` |
| 3 | `core/compute_registry.py` | `ComputeRegistry.chat_stream()` — LLM routing engine |
| 3 | `core/lmstudio.py` | `LMStudioClient.chat_stream()` |
| 3 | `core/llm_router.py` | Backward-compat wrapper (delegates to `compute_registry`) |
| 3 | `core/compute_pool.py` | Backward-compat wrapper (delegates to `compute_registry`) |
| 4 | `skills/system_actions.py` | `OPENAI_TOOLS`, `execute_tool()` |
| 5 | `core/context_summarizer.py` | `summarize_if_needed()` |

---

## Pipeline 2: Autonomous Work

```
[1] AgentOrchestrator._work_cycle() — polls every 5s (active) / 30s (idle)
    |
    v
[2] _pick_next_task()
    ├── Priority ordering: critical > high > medium > low
    ├── Assigned-first: tasks assigned to this agent take precedence
    └── Resource check: governor may pause if under pressure
    |
    v
[3] _execute_task()
    |
    v
[4] _select_skill()
    ├── Explicit: task.skill_name matches registry → use it
    ├── Keyword: 50+ hardcoded keyword mappings → best match
    └── Semantic fallback: embed task + skill descriptions → cosine similarity > 0.6
    |
    v
[5] Skill Execution
    ├── Build SkillInput (project_context, files, parameters)
    ├── Call skill.execute(input) → LLM generates analysis
    ├── Parse structured output (nuggets, facts, insights, recommendations)
    └── Skill quality recorded in SkillManager
    |
    v
[6] _store_findings()
    ├── Create Nuggets (with Laws of UX auto-tagging via keyword matching)
    ├── Create Facts (linked to nugget IDs)
    ├── Create Insights (linked to fact IDs)
    ├── Create Recommendations (linked to insight IDs)
    └── WebSocket broadcast: finding_created events
    |
    v
[7] _self_verify_output()
    ├── Check for empty results, error patterns
    ├── Minimum finding count validation
    ├── Quality score: 0.8 (success) / 0.2 (failure)
    └── Record to SkillManager for self-evolution tracking
    |
    v
[8] Post-Task
    ├── Suggest next steps based on research gaps
    ├── Record learnings (agent_learning.py)
    ├── Maybe propose new skill (_maybe_propose_skill)
    └── Loop back to [1]
```

---

## Pipeline 3: Meta-Orchestration

```
MetaOrchestrator (orchestrator.py)
    |
    ├── Distributes tasks across 5 agents via task_router.py
    │   ├── DevOps (Sentinel): audit, health, integrity tasks
    │   ├── UI Audit (Pixel): WCAG, Nielsen, design system tasks
    │   ├── UX Eval (Sage): usability, journey, cognitive tasks
    │   ├── Simulation (Echo): testing, simulation tasks
    │   └── Main (Cleo): everything else
    |
    ├── Monitors agent health via heartbeat_manager
    |
    └── Coordinates via A2A messages (database-stored)
```

---

## Pipeline 4: Self-Evolution

```
SkillManager tracks execution quality
    |
    v
quality < 0.5 after 3+ runs → propose improvement
    |
    v
Self-Evolution scans for promotable learnings
    ├── min_occurrences >= 3
    ├── min_confidence >= 70
    ├── min_success_rate >= 0.6
    └── within 30-day window
    |
    v
Promote to persona files (PROTOCOLS.md, SKILLS.md, MEMORY.md)
    |
    v
Meta-Hyperagent observes subsystem metrics (every 6h)
    ├── Proposes parameter changes (thresholds, keywords)
    ├── MAX 3 active variants
    └── All changes require user approval
    |
    v
Autoresearch loops (6 types, overnight)
    ├── Skill prompt optimization
    ├── Model/temperature grid search
    ├── RAG parameter tuning
    ├── Agent persona optimization
    ├── Question bank optimization
    └── UI simulation optimization
```

---

## Academic References & Inspirations

| Component | Inspiration | Paper/Source | Location in Code |
|-----------|------------|-------------|-----------------|
| **Tool-calling loop** | ReAct | Yao et al. (2022), "ReAct: Synergizing Reasoning and Acting in Language Models" | `chat.py` ReAct loop, 8 iterations |
| **Ensemble validation** | Mixture-of-Agents | Wang et al. (2025), ICLR 2025 | `adaptive_validation.py` |
| **Self-verification** | Self-MoA | Li et al. (2025) | `agent.py` `_self_verify_output()` |
| **Adversarial review** | Multi-Agent Debate | Du et al. (2024), ICML 2024 | `adaptive_validation.py` debate_rounds |
| **Prompt compression** | LLMLingua | Jiang et al. (2023) | `agent_identity.py` llmlingua strategy |
| **Query-aware prompts** | Prompt RAG | Novel (Istara) | `prompt_rag.py` |
| **Optimization loops** | Autoresearch | Karpathy (2026), MIT | `autoresearch_engine.py`, 6 runners |
| **Skill self-improvement** | Memento-Skills | "Let Agents Design Agents" (2025) | `skill_manager.py`, `agent_factory.py` |
| **Heuristic evaluation** | Nielsen's 10 | Nielsen & Molich (1990), CHI | `heuristic-evaluation.json` skill |
| **UX psychology** | Laws of UX | Yablonski (2024), O'Reilly | `laws_of_ux.json`, 30 laws |
| **Evidence chain** | Atomic Research | Polaris/WeWork (2018) | `finding.py` Nuggets→Facts→Insights→Recs |
| **Research phases** | Double Diamond | UK Design Council (2005) | Skill phases: Discover→Define→Develop→Deliver |
| **Adaptive interviews** | AURA | arXiv 2510.27126 (2025) | `adaptive_interview.py` |
| **Quality scoring** | SUS/UMUX | Brooke (1996) / Finstad (2010) | `sus-umux-scoring.json` skill |
| **Intercoder reliability** | Fleiss' Kappa | Fleiss (1971) | Ensemble validation scoring |
| **Accessibility** | WCAG 2.2 | W3C (2023) | `accessibility.mjs` evaluator |
| **Cognitive engineering** | Gerhardt-Powals | Gerhardt-Powals (1996) | `heuristic-evaluation.json` Phase 4 |
| **Usability inspection** | Cockton & Woolrych | Cockton & Woolrych (2001) | Heuristic eval methodology |
| **LLM-as-Judge** | LLM-as-Judge | Zheng et al. (2023), NeurIPS | `_self_verify_output()` |
| **Parameter tuning** | Hyperagents (DGM-H) | Hyperagents paper (2025) | `meta_hyperagent.py` |
| **Multi-LLM thematic** | Multi-LLM Analysis | Jain et al. (2025) | Ensemble thematic analysis |
| **Distributed compute** | BOINC/Petals | Anderson (2020) / Borzunov (2023) | `compute_pool.py`, relay nodes |
| **ISO usability** | ISO 9241 | ISO 9241-11:2018, ISO 9241-210:2019 | Referenced in skill prompts |
| **Native tool calling** | OpenAI Function Calling | OpenAI (2023) / LM Studio docs | `system_actions.py` OPENAI_TOOLS |

---

## Browser UI Automation (Implemented)

### Playwright MCP — Precise Browser Control
- Microsoft's official `@playwright/mcp` server — available as featured MCP server in Istara
- 21 tools: navigate, click, type, screenshot, accessibility tree, network, console, JS eval
- Uses accessibility trees (2-5KB text) — works with any text model, no vision required
- Install: `npx @playwright/mcp@latest --port 3100` → connect in MCP tab
- Use case: precise automation, accessibility auditing, form testing

### browser-use — Autonomous Browsing
- AI-powered browser agent via `browse_website` system action tool
- Agent navigates, clicks, fills forms, extracts content autonomously
- Compatible with LM Studio AND Ollama via OpenAI-compatible API
- Optional dep: `pip install browser-use langchain-openai`
- Use case: competitor analysis, content extraction, usability evaluation

### Vision — Screenshot Analysis
- Qwen 3.5 models on LM Studio accept vision input
- browser-use can send screenshots to the model for visual analysis
- Enables: design critique, visual accessibility audit, layout evaluation

---

## Benchmark vs Reference Platforms

| Capability | Istara | OpenClaw | Hermes | Claude Code |
|---|---|---|---|---|
| Native Tool Calling | ✅ Full (OpenAI format) | ✅ Full | ✅ Full | ✅ Full |
| Multi-Step Reasoning | ✅ 8-iter ReAct | ✅ Full | ✅ Full | ✅ Full |
| Web Browsing | ✅ browser-use + Playwright MCP | ✅ Full | ⚠️ Partial | ✅ Full |
| Autonomous Work | ⚠️ Skill execution only | ✅ Heartbeat daemon | ⚠️ Reactive | ❌ User-initiated |
| Inter-Agent Comms | ⚠️ DB messages (unread) | ✅ Hierarchical | ❌ Single agent | ⚠️ Sub-agent reports |
| Persona System | ✅ Best in class | ⚠️ Config dirs | ⚠️ 2 MD files | ⚠️ CLAUDE.md |
| Self-Evolution | ⚠️ Proposals + learning DB | ✅ Self-extending | ✅ Skill evolution | ❌ None |
| Atomic Research | ✅ Unique | ❌ None | ❌ None | ❌ None |
| Laws of UX | ✅ Unique (30 laws) | ❌ None | ❌ None | ❌ None |
| Resource Governance | ✅ Hardware-aware | ⚠️ Partial | ❌ None | ❌ None |

### Remaining Gaps
| Gap | Priority | Status |
|-----|----------|--------|
| A2A messages unread by agents | P1 | Planned |
| Autonomous task decomposition | P1 | Planned |
| LLM-based task routing | P2 | Planned |

### Reference Tools
| Tool | Stars | Approach | Local LLM Support |
|------|-------|----------|-------------------|
| browser-use | 78K+ | Playwright + vision | Yes (LM Studio + Ollama) |
| Playwright MCP | Official | Accessibility tree | Yes (any text model) |
| Stagehand v3 | 15K+ | CDP-native | Partial |
| OpenClaw | 90K+ | Playwright/CDP + AI Snapshot | Yes |
