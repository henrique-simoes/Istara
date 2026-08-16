# Missing Surface Audit For Full Istara Pi Replacement

This audit combines Compass Forge orientation, targeted impact maps, previous bridge artifacts, and source/test inspection. The existing Pi candidate proves the adapter shape, but it still mostly exercises canonical lab surfaces. The next benchmarkable candidate must make Pi drive Istara's real contracts inside the isolated replacement worktree.

## Highest-Priority Missing Wiring

1. Production chat and streaming route
- Real touchpoints: `backend/app/api/routes/chat.py`, `backend/app/api/websocket.py`, `backend/app/models/chat.py`.
- Missing: Pi is not behind the real `/chat` route, session persistence, auth/RBAC, SSE/websocket event contract, message history, tool-call filtering, or production provider routing.
- Needed: a feature-flagged `PiAgentEngine`/adapter boundary that can be selected by tests without changing the public API envelope.

2. Task, document, finding, Done/report gates
- Real touchpoints: `backend/app/api/routes/tasks.py`, `backend/app/api/routes/documents.py`, `backend/app/api/routes/findings.py`, `backend/app/core/task_review.py`, `backend/app/core/report_manager.py`, `backend/app/services/research_validity_service.py`.
- Missing: DB-backed task lifecycle, document attach/detach, evidence-source rows, review events, Done approval, and report gating are not driven by Pi.
- Needed: canonical Pi tools must call real service functions or test clients so benchmark results prove real Istara workflows, not in-memory facsimiles.

3. Memory, RAG, ReasoningBank, Memento, skills
- Real touchpoints: `backend/app/api/routes/memory.py`, `backend/app/core/rag.py`, `backend/app/core/reasoning_bank.py`, `backend/app/api/routes/reasoning_bank.py`, `backend/app/core/agent_skill_tools.py`, `backend/app/skills/*`.
- Missing: persistent memory loads/writes, LanceDB/embedding-backed retrieval, ReasoningBank governance, skill registry execution, and Memento-style learning are not wired to Pi as real tools.
- Needed: cap skill fanout to three representatives, but route those through the actual registry/service path and record memory load counts/tokens.

4. Autoresearch and governed self-improvement
- Real touchpoints: `backend/app/api/routes/autoresearch.py`, `backend/app/core/autoresearch_engine.py`, `backend/app/core/autoresearch_isolation.py`, `backend/app/core/autoresearch_runners/*`, `backend/app/core/meta_hyperagent.py`.
- Missing: Pi does not drive the real governed loop, experiment storage, rate limits, isolation, governance promotion lane, or telemetry.
- Needed: a bounded test mode where Pi owns proposal/evaluation decisions while existing governance blocks unsafe persistence.

5. A2A and agent lifecycle
- Real touchpoints: `backend/app/api/routes/a2a.py`, `backend/app/services/a2a.py`, `backend/app/core/agent_lifecycle.py`, `backend/app/agents/orchestrator.py`, `backend/app/models/agent.py`.
- Missing: live JSON-RPC A2A, agent inbox/outbox, JWT/replay behavior, lifecycle transitions, debate/report flows, and frontend-visible A2A logs.
- Needed: a credential-free local A2A harness that exercises real route/service contracts and measures fewer interactions/tool calls vs quality.

6. Channels, webhooks, and Telegram-like lifecycle
- Real touchpoints: `backend/app/api/routes/channels.py`, `backend/app/api/routes/webhooks.py`, `backend/app/channels/base.py`, `backend/app/channels/telegram.py`, `backend/app/channels/whatsapp.py`, `backend/app/channels/google_chat.py`, `backend/app/services/channel_service.py`.
- Missing: Pi is not behind the inbound/outbound channel flow; real credentials are unavailable.
- Needed: credential-free signed webhook/test adapters using real route/service validation. Live external sends remain blocked unless credentials are explicitly supplied.

7. Model routing, compute, and provider governance
- Real touchpoints: `backend/app/core/llm_router.py`, `backend/app/core/compute_registry_lifecycle.py`, `backend/app/core/compute_registry_invocation.py`, `backend/app/config.py`, `frontend/src/lib/modelProviders.*`, `relay/lib/llm-proxy.mjs`.
- Missing: Pi provider path is validated in lab, but not as the real Istara routing path for agentic loops.
- Needed: reversible model routing selection for `deepseek-v4-pro` through Pi, with token/cost accounting in the same metrics as baseline.

8. Steering, system prompt, and prompt RAG
- Real touchpoints: `backend/app/api/routes/steering.py`, `backend/app/core/prompt_rag.py`, `backend/app/core/context_policy.py`, `backend/app/core/prompt_compressor.py`.
- Missing: Pi does not consume live steering queues or prompt-RAG/compression policies inside long-running loops.
- Needed: live interrupt/steering test path or explicit local route test with Pi event updates.

9. Telemetry, tokens, and quality metrics
- Real touchpoints: `backend/app/core/telemetry.py`, `backend/app/core/token_counter.py`, `backend/app/models/model_skill_stats.py`, `tests/benchmarks/long_horizon_runner.py`.
- Missing: lab JSON metrics are not production telemetry rows/spans.
- Needed: Pi events mapped to Istara telemetry spans: tokens by step, tool calls, errors, latency, quality markers, skill adherence, system-prompt adherence, memory load, and A2A efficiency.

10. Full benchmark/eval/simulation harness fanout
- Real touchpoints: `tests/benchmarks/*`, `tests/evals/*`, `scripts/run_istara_evals.py`, `tests/agentic_eval_contract.json`, `tests/real_user_benchmark/*`, `tests/simulation/run.mjs`, `tests/simulation/scenarios/*.mjs`.
- Missing: broad live fanout has not run against a production-surface Pi candidate.
- Needed: deterministic full inventory first, then live DeepSeek slices under the remaining USD 0.4056 cap. Large fanout remains representative: max three skills or representatives per oversized scenario.

## Definition Of Done For The Next Round

- A real replacement candidate exists in the isolated worktree, not only under `labs/pi-replacement`.
- Real app route/service touchpoints can run in test mode with Pi as the selected agent loop/model/tool engine.
- No public API contracts are broken.
- Main checkout `/Users/user/Documents/Istara-main` remains unchanged except comparison artifacts.
- Raw prompts/outputs/tool calls/tokens/costs/latency/errors are captured for every live LLM call.
- Benchmark tables include both raw outputs and separate metrics for:
  tool calling, feature criteria adherence, final output, research-spine step quality, memory load, tokens by step and total, tool-call count vs quality, skills adherence, system-prompt adherence, and A2A task success.
- All harness categories are inventoried and either run, deterministically covered, blocked by a concrete external requirement, or deferred only when the spend cap would be exceeded.
