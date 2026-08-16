# Implementation Ledger

Generated: 2026-07-19T19:03:22.187Z

## Code Changed

- Added `src/istara-surface-map.mjs` with concrete Istara route/service/test/doc mappings and production blockers.
- Added `src/istara-service-bridge.mjs` to bind scenarios to mapped surfaces, canonical tools, and blocked production gaps.
- Extended `src/canonical-tool-facade.mjs` for Autoresearch, ReasoningBank, Memento, webhook, steering, system-prompt, and benchmark-contract tools.
- Extended `src/scenario-catalog.mjs` from the prior representative slices to real-loop bridge slices for Autoresearch, ReasoningBank/Memento, webhooks, steering/prompt policy, and benchmark contracts.
- Extended `src/istara-pi-adapter.mjs` and this artifact collector so Pi-owned loop traces carry real surface IDs and blocker evidence.

## Scenario Coverage

- Scenarios: 15
- Covered mapped surfaces: 10/10
- Candidate deterministic passes: 15/15
- Candidate canonical tool calls: 56

## Production Blockers Preserved

- chat_react_loop: The replacement worktree now has an opt-in FastAPI /chat Pi candidate hook that preserves SSE/tool contracts and registers DeepSeek at runtime; full production live coverage still needs the DeepSeek key and broader endpoint fanout. (backend/app/api/routes/chat.py:123, backend/app/core/pi_replacement.py:1)
- autoresearch_governance: Running the real background AutoresearchEngine would mutate experiment DB state and can touch live model/provider settings; the lab only records the governed envelope. (backend/app/api/routes/autoresearch.py:582, backend/app/core/autoresearch_engine.py:35)
- plan_review_state: The lab can represent in_review/done envelopes but cannot perform a real human approval or DB-backed validity gate without changing production task state. (backend/app/api/routes/tasks.py:595, backend/app/core/task_review.py:216)
- tasks_findings_documents: The lab stores source spans in memory only; it does not write the production source-unit tables or accepted evidence-chain rows. (backend/app/api/routes/documents.py:165, backend/app/api/routes/findings.py:583)
- memory_rag_reasoning_memento_skills: The lab cannot exercise production embeddings, LanceDB/keyword indexes, admin-scoped ReasoningBank routes, or learned skill stats without credentials/DB state. (backend/app/api/routes/memory.py:74, backend/app/api/routes/reasoning_bank.py:59, backend/app/core/agent_skill_tools.py:262)
- a2a_delegation_reports: The replacement worktree now records Pi candidate telemetry after real JSON-RPC tasks/send auth, rate, and replay gates; full report synthesis still depends on production Done/report approval state. (backend/app/api/routes/a2a.py:305, backend/app/core/pi_replacement.py:1, backend/app/core/report_manager.py:227)
- channels_webhooks_telegram_lifecycle: The replacement worktree now has a credential-free pi_local adapter through the real channel router/inbound processor; real Telegram/WhatsApp/Google Chat loops still need external bot/webhook credentials. (backend/app/channels/pi_local.py:1, backend/app/services/inbound_processor.py:89, backend/app/channels/telegram.py:49, backend/app/api/routes/webhooks.py:81)
- steering_system_prompt: The lab does not interrupt a live long-running agent or SSE stream; it records queued steering/follow-up envelopes and policy-audit results. (backend/app/api/routes/steering.py:139, backend/app/api/routes/steering.py:305)
- telemetry_tokens_tool_metrics: The replacement worktree now inserts production TelemetrySpan rows for Pi chat/tool/A2A/channel hooks; full ModelSkillStats and broad production benchmark telemetry remain outside this bounded wiring round. (backend/app/core/pi_replacement.py:1, backend/app/core/telemetry.py:21, backend/app/models/model_skill_stats.py:1)
- benchmarks_evals_simulations_real_user_contract: The bridge maps benchmark contracts, executes lab scenarios, and now has targeted production-hook regression tests; full browser/API/live-user harness fanout remains deferred by budget and external runtime setup. (tests/test_pi_replacement_candidate.py:1, tests/real_user_benchmark/run.mjs:1, tests/benchmarks/run_benchmarks.py:67)
