# Istara Architecture Evolution

Tracking the progression of Istara's agentic architecture from initial implementation through successive overhauls. Each version documents what changed, why, the industry standard referenced, and the before/after state.

---

## v2026.03.30 — Initial Audit Baseline

### Architecture State
- 5 agents running (main, devops, ui-audit, ux-eval, sim)
- 50 pre-built skills with plan/execute/validate
- 6-level context hierarchy with ContentGuard
- Prompt RAG for query-aware persona loading
- Chat endpoint with 13-tool ReAct loop (8 iterations)
- Agent orchestrator with single-call skill execution (no tools)
- A2A infrastructure built but dormant
- Ensemble validation defined but not wired
- Report pipeline: L2/L3 auto-trigger, no content generation

### Gaps Identified (16 total)
1. Agent has no ReAct loop (chat does, agent doesn't)
2. No RAG retrieval before task execution
3. No timeout on skill execution
4. Self-verification is heuristic only
5. A2A messages sent but never read
6. Task instructions field silently dropped
7. CSV files always classified as "csv_data"
8. Ensemble validation not wired into execution
9. MECE categories field empty
10. L4 final report never generated
11. Executive summaries never written
12. Artifacts don't become Documents
13. task.output_document_ids never set
14. Ensemble confidence not in reports
15. No file attachment preview in chat
16. Chat renders plain text, not markdown

---

## v2026.04.01 — Tray + Installer Fixes

### Changes
- Tray app: shell delegation to istara.sh (single source of truth)
- Backend: SyntaxError in updates.py fixed
- istara.sh: stale port cleanup (_free_port)
- Auto-update: handles dirty working tree (git checkout before pull)
- PATH fix for Homebrew in non-interactive shells

### Industry Standard
- Unix philosophy: one tool does one thing well (istara.sh manages processes, tray delegates)

---

## v2026.04.01.3 — Chat UX + Agent Pipeline

### Changes
- Chat messages render markdown (react-markdown + remark-gfm)
- File upload shows preview chips before sending
- Project document picker in chat (FolderOpen button)
- Task instructions field passed to LLM prompts
- CSV file classification by column headers (survey vs interview)
- Ensemble validation wired into agent execution loop
- Self-MoA as default validation (single-server compatible)

### Before → After
| Capability | Before | After |
|-----------|--------|-------|
| Chat rendering | Plain text | Full markdown |
| File upload | Immediate upload, no preview | Preview chips, upload on send |
| Task instructions | Silently dropped | Included in prompts |
| Ensemble validation | Defined but not called | Runs after every skill execution |
| CSV classification | Always "csv_data" | Header-aware (survey/interview/generic) |

### Industry Standard
- Ensemble validation: Fleiss' Kappa + cosine similarity (inter-rater reliability from psychometrics)
- File classification: content-aware chunking (Elicit, Semantic Scholar)

---

## v2026.04.01.5 — Agent Overhaul v1

### Changes
- ReAct tool loop for general tasks (5 iterations, 15 tools)
- RAG retrieval before skill execution
- Timeout protection on skills (5 minutes)
- LLM self-reflection replaces heuristic verification
- A2A collaboration activated (inbox polling, response generation)
- Structured output validation (evidence chain, confidence bounds)
- Artifacts create Document records (source=agent_output)
- task.output_document_ids populated
- Ensemble confidence flows to reports
- Executive summaries auto-generated (3+ findings)
- MECE categories auto-generated (5+ findings)
- L4 final report auto-created (10+ L3 findings)

### Before → After
| Capability | Before | After |
|-----------|--------|-------|
| General task execution | Single LLM call | 5-iteration ReAct with tools |
| RAG before tasks | None | Top-5 document retrieval |
| Skill timeout | None (could block forever) | 5-minute asyncio.wait_for |
| Self-verification | Heuristic (error patterns, count) | LLM structured reflection |
| A2A collaboration | Messages sent, never read | Active polling + expert responses |
| Artifacts | RAG-indexed only | Also Document records |
| L4 reports | Never generated | Auto-triggered at 10+ findings |
| MECE | Empty field | LLM-categorized at 5+ findings |

### Industry Standard
- ReAct: Yao et al. (2023) — Reasoning + Acting in LLMs
- Self-reflection: Shinn et al. (2023) — Reflexion
- Evidence chain validation: Atomic Research methodology (Tomer Sharon)

---

## v2026.04.02 — Agent Overhaul v2

### Changes
- Plan-and-Execute architecture for complex tasks
- A2A multi-turn conversation threads (context_id)
- Agent Capability Cards (A2A-style JSON from personas)
- Circuit breaker on compute nodes (CLOSED/OPEN/HALF_OPEN)
- LLM health notifications (red/yellow/green banners)
- Agent pauses when LLM unavailable
- Skill auto-deprecation (utility < 0.2 after 10 runs)
- LLM-based skill improvement proposals on failure
- Template-driven L4 report composition (8 sections)
- L4 creates Document record (final_research_report.md)
- Circuit breaker integrated into compute routing
- Gaps analysis section in L4 reports via LLM

### Before → After
| Capability | Before | After |
|-----------|--------|-------|
| Task planning | None — immediate execution | 2-5 step plan with replan checks |
| A2A conversations | Fire-and-forget | Multi-turn threads with history |
| Agent discovery | Persona files only | Queryable capability cards |
| LLM failure handling | Silent catch | Circuit breaker + user notification |
| Skill evolution | Static JSON files | Auto-deprecate + LLM improvement proposals |
| L4 reports | Metadata only | Full template-driven document |
| Report as document | Not created | Document record with full markdown |
| Compute routing | Score-based only | Score + circuit breaker availability |

### Industry Standard
- Plan-and-Execute: LangGraph (2024), LLMCompiler (ICML 2024)
- A2A Protocol: Google Agent-to-Agent (April 2025)
- Agent Cards: A2A specification — capability discovery
- Circuit Breaker: Martin Fowler's pattern, liteLLM, Portkey
- Skill lifecycle: Memento-Skills (March 2025) — utility scoring + write-back
- Document generation: Elicit pipeline — Extract→Structure→Synthesize→Compose→Cite

---

## v2026.04.02.3 — Final Architecture Gaps Closed

### Changes
- DAG-parallel step execution in research plans (asyncio.gather for independent steps)
- Proactive A2A debate: uncertain ensemble consensus (0.4-0.6) triggers inter-agent critique
- Skill self-verification gate: Voyager-style auto-test before human approval
- L4 iterative refinement: LLM scores sections, re-composes weakest, converges at quality ≥7
- Agent progress streaming: broadcast_agent_thinking + broadcast_plan_progress events
- StatusBar shows real-time step-by-step execution progress

### Before → After
| Capability | Before | After |
|-----------|--------|-------|
| Plan execution | Sequential loop | DAG-parallel (independent steps run concurrently) |
| A2A debate | Reactive only (respond to requests) | Proactive (initiate debate on uncertain consensus) |
| Skill creation | Human approval only | Auto-test → human approval (Voyager gate) |
| L4 report | Single-pass composition | Iterative refinement (max 2 passes, convergence check) |
| Agent progress UI | Percentage + status text | Step-by-step thinking with plan progress events |

### Industry Standard
- DAG parallelism: LLMCompiler (ICML 2024) — 3.7x speedup on independent tasks
- A2A debate: AutoGen (Microsoft, 2024) — multi-agent debate for consensus
- Skill verification: Voyager (MineDojo) — self-verification before library addition
- Report refinement: Elicit — iterative extraction with quality scoring
- Progress streaming: Claude Agent SDK — real-time thinking visibility

## Remaining Gaps (Post v2026.04.02.3)

1. **Cross-project learning** — Intentionally deferred. Projects stay isolated.
2. **Full MCTS action search** — LATS-style tree search for novel research questions (future)
3. **Full PRISMA workflow** — Medical review methodology, not needed for general UX research
4. **Multi-region compute routing** — Not needed for local-first architecture

---

## Architecture Diagram (Current)

```
User → Chat (ReAct, 13 tools, 8 iterations, markdown rendering)
         ↓
Task Created → Agent Orchestrator
         ↓
    [Plan-and-Execute]
    ├─ Create research plan (2-5 steps via LLM)
    ├─ For each step:
    │   ├─ RAG retrieval (top-5 documents)
    │   ├─ Skill selection (keyword → semantic → ReAct fallback)
    │   ├─ Execute skill (5min timeout)
    │   ├─ Schema validation (evidence chain, confidence bounds)
    │   ├─ Ensemble validation (Self-MoA / Dual Run / Adversarial)
    │   ├─ LLM self-reflection (structured JSON verification)
    │   └─ Replan check
    ├─ A2A collaboration (inbox polling, multi-turn threads)
    └─ Store findings (Nuggets → Facts → Insights → Recommendations)
         ↓
    Report Pipeline
    ├─ L2: Per-method analysis (auto-created per skill)
    ├─ L3: Cross-method synthesis (auto at 2+ L2 reports)
    ├─ L4: Final report (auto at 10+ L3 findings)
    │   ├─ Executive Summary (LLM-generated)
    │   ├─ Methodology (skills used)
    │   ├─ Key Findings (evidence table with citations)
    │   ├─ Supporting Evidence (nuggets + facts table)
    │   ├─ Recommendations (priority table)
    │   ├─ MECE Analysis (LLM-categorized)
    │   ├─ Confidence & Validation (ensemble metrics)
    │   └─ Limitations & Gaps (LLM analysis)
    └─ Document record created → visible in Documents view
         ↓
    Circuit Breaker
    ├─ CLOSED → normal operation
    ├─ OPEN → 5 failures, 60s cooldown, agent pauses
    ├─ HALF_OPEN → one probe request
    └─ Status bar: red (down) / yellow (slow) / green (ok)
```
