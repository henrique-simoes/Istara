# Compass Forge Impact Summary

CF request:

Audit remaining gaps to wire all Istara agentic-loop production surfaces to the Pi replacement candidate in the isolated replacement worktree, then hand off to Build Stream Conductor roles for implementation and full benchmarking under the existing DeepSeek spend cap.

Classification:
- Kind: `security_or_architecture`
- Blast radius: `full`
- Recommended checks: architecture gate, security-sensitive surface review, broad verification for touched layers

Targeted impact maps run:
- `backend/app/api/routes/chat.py`
- `backend/app/api/routes/tasks.py`
- `backend/app/core/rag.py`
- `backend/app/api/routes/a2a.py`
- `backend/app/api/routes/channels.py`

Key CF-discovered route/contract clusters:
- Chat: `/chat`, `/chat/history/{project_id}`, voice routes, websocket/SSE-adjacent event paths.
- Tasks/documents: task CRUD, review/approve/request-revision, verify, move, lock/unlock, attach/detach, reports, document CRUD/search/sync/content.
- Agents/A2A: A2A JSON-RPC, agent cards, agents CRUD/status/messages/memory/evolution, orchestration/lifecycle services.
- Channels: channel CRUD, start/stop/health, send, conversations/messages.
- Memory/RAG/skills: RAG core, agent skill tools, loops, MCP server, agent services, skills views, eval runner.

Likely affected tests/harnesses repeatedly surfaced by CF:
- `labs/pi-replacement/test/adapter.test.mjs`
- `scripts/test_llm_integration.py`
- `tests/benchmarks/run_benchmarks.py`
- `tests/benchmarks/test_orchestration.py`
- `tests/benchmarks/long_horizon_runner.py`
- `tests/test_agentic_eval_contract.py`
- `tests/test_istara_eval_runner.py`
- `tests/test_tasks.py`
- `tests/test_findings.py`
- `tests/test_agents.py`
- `tests/test_channels.py`
- `tests/test_channel_resilience.py`
- `tests/test_webhooks_security.py`
- `tests/test_research_validity_contract.py`
- `tests/test_agent_skill_tools.py`
- `tests/real_user_benchmark/run.mjs`
- `tests/real_user_benchmark/lib/*`
- `tests/simulation/run.mjs`
- `tests/simulation/scenarios/*.mjs`

Gate notes:
- The latest CF gate still fails on inherited `unexpected_large_files` and warns on inherited complexity.
- Next conductor must distinguish inherited gate debt from new drift introduced by Pi wiring.
- Any new gate failure caused by this work must be fixed, explicitly suppressed with expiry/reason, or recorded as a blocker.
