# Full Replacement Coverage Matrix

Scope: every current Istara agentic-management surface identified by the planning architects.
Feature-level coverage is generated in `feature-matrix.json`.

| Istara surface | Current evidence | Pi ownership target | Istara adapter/product ownership | Current verdict |
|---|---|---|---|---|
| Chat ReAct loop | `backend/app/api/routes/chat.py`; `tests/test_chat.py`; `tests/agentic_eval_contract.json` | `@earendil-works/pi-agent-core` owns turn loop, tool-call continuation, iteration stopping, streamed events | Session storage, project context, RAG/persona injection, tool authorization, fallback policy | TBD-evidence |
| Design chat ReAct loop | `backend/app/api/routes/interfaces.py`; interface feature docs | `@earendil-works/pi-agent-core` owns loop/tool events | Design-specific tools, screen data, Figma/Stitch credentials, project state | TBD-evidence |
| Agent task execution | `backend/app/core/agent_execution.py`; `tests/benchmarks/test_orchestration.py`; scenario 71 | `@earendil-works/pi-agent-core` owns plan/execute loop | Task DB, review rewards, findings writes, project authorization | TBD-evidence |
| Research spine | `backend/app/core/agent_research.py`; `tests/real_user_benchmark/*`; `scripts/run_istara_evals.py` | Pi loop drives phases through canonical tools | Research semantics, citations, findings/documents, review gates | TBD-evidence |
| System action tools | `backend/app/skills/system_actions.py`; `tests/test_agent_skill_tools.py` | Pi tool execution hooks call canonical facade | Tool schemas, ACLs, DB transactions, telemetry redaction | TBD-evidence |
| Skill execution and ranking | `backend/app/core/agent_skill_tools.py`; skill tests | Pi skills may be bridge or secondary input | Istara skill registry, proposals, ranking, output validation, memento stats | TBD-evidence |
| Model/provider routing | `backend/app/core/compute_registry*.py`; `backend/app/core/llm_router.py`; `relay/lib/llm-proxy.mjs` | `@earendil-works/pi-ai` owns provider calls and usage accounting if hooks cover policy | Compute donation auth, node eligibility, circuit breakers, retry/fallback policy, secret hygiene | Pi live path blocked until package install/local checkout gate |
| OpenAI-compatible cloud path | `deepseek-test-config.md`; Istara-compatible smoke script | Pi optional; Istara-compatible request shape verifies approved cloud route | Env-var-only secret handling and no local models | Smoke passed for direct OpenAI-compatible shape |
| Memory and RAG | `backend/app/core/rag.py`; `reasoning_bank.py`; `agent_memory.py`; `context_dag.py` | Pi may request context/memory through tool hooks | Istara remains source of truth for memory, RAG, DAG, redaction, untrusted wrapping | TBD-evidence |
| A2A orchestration | `backend/app/api/routes/a2a.py`; `backend/app/services/a2a.py`; scenario 73 | Pi may own agent handoff/session mechanics | A2A JSON-RPC auth, replay/rate/body caps, project claims, audit log | TBD-evidence |
| Agent registry and lifecycle | `backend/app/api/routes/agents.py`; `backend/app/core/agent_lifecycle.py`; agent models | Pi harness/session APIs may replace runtime control | Registry, scope, health, restart, steering queues, UI affordances | TBD-evidence |
| Steering/follow-up queues | `backend/app/api/routes/steering.py`; steering tests | Pi steering/follow-up queue is a candidate replacement | Project scoping, UI state, abort semantics | TBD-evidence |
| Channel-facing agent turns | `backend/app/channels/*`; messaging/deployment feature docs | `@earendil-works/pi-coding-agent`/sidecar and Pi chat patterns as candidate harness | Channel identity, deployment state, attachment handling, outbound safety, credentials | TBD-evidence |
| SDK/process integration | Istara backend/relay/desktop process boundaries | `@earendil-works/pi-coding-agent` CLI/RPC or sidecar | Packaging, observability, abort/retry, version pinning, rollback | TBD-evidence |
| Telemetry and trace evidence | `backend/app/core/telemetry.py`; telemetry tests; metrics schema | Pi events feed adapter trace schema | Content-free spans, capped retention, score-ready JSONL, secret redaction | TBD-evidence |
| Autoresearch/meta loops | autoresearch and meta-hyperagent feature docs/tests | Unsupported until Pi adapter proves governed experiment control | Approval gates, archives, mutation governance, standards | Unsupported pending adapter evidence |

## Coverage Notes

- A Pi replacement is acceptable only if the row's Istara adapter/product ownership remains
  intact.
- Unsupported rows are not failures yet; they are explicit evidence requirements for later
  benchmarks or adapter spikes.
- No row authorizes changes to Istara application code in this run.

