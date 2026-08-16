# Implementation Ledger

Generated: 2026-07-19T18:17:14.242Z

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

- chat_react_loop: The bridge does not invoke FastAPI /chat, database sessions, SSE streaming, auth, or production provider routing. (backend/app/api/routes/chat.py:389, backend/app/models/chat.py:1)
- autoresearch_governance: Running the real background AutoresearchEngine would mutate experiment DB state and can touch live model/provider settings; the lab only records the governed envelope. (backend/app/api/routes/autoresearch.py:582, backend/app/core/autoresearch_engine.py:35)
- plan_review_state: The lab can represent in_review/done envelopes but cannot perform a real human approval or DB-backed validity gate without changing production task state. (backend/app/api/routes/tasks.py:595, backend/app/core/task_review.py:216)
- tasks_findings_documents: The lab stores source spans in memory only; it does not write the production source-unit tables or accepted evidence-chain rows. (backend/app/api/routes/documents.py:165, backend/app/api/routes/findings.py:583)
- memory_rag_reasoning_memento_skills: The lab cannot exercise production embeddings, LanceDB/keyword indexes, admin-scoped ReasoningBank routes, or learned skill stats without credentials/DB state. (backend/app/api/routes/memory.py:74, backend/app/api/routes/reasoning_bank.py:59, backend/app/core/agent_skill_tools.py:262)
- a2a_delegation_reports: The lab does not open JSON-RPC sockets or validate JWT/network tokens/replay keys; it records the canonical delegation/report shape only. (backend/app/api/routes/a2a.py:305, backend/app/core/report_manager.py:227)
- channels_webhooks_telegram_lifecycle: Real Telegram/WhatsApp/Google Chat loops need external bot/webhook credentials and running adapters; the lab uses signed simulated inbound envelopes. (backend/app/channels/telegram.py:49, backend/app/api/routes/webhooks.py:81)
- steering_system_prompt: The lab does not interrupt a live long-running agent or SSE stream; it records queued steering/follow-up envelopes and policy-audit results. (backend/app/api/routes/steering.py:139, backend/app/api/routes/steering.py:305)
- telemetry_tokens_tool_metrics: The lab records local JSON metrics and raw LLM capture; it does not insert production TelemetrySpan or ModelSkillStats rows. (backend/app/core/telemetry.py:21, backend/app/models/model_skill_stats.py:1)
- benchmarks_evals_simulations_real_user_contract: The bridge maps benchmark contracts and executes lab scenarios; it does not run full production browser/API/live-user harnesses. (tests/real_user_benchmark/run.mjs:1, tests/benchmarks/run_benchmarks.py:67)
