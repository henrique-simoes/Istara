# Istara Surface Map

Mapped surfaces: 10/10.
Covered by runnable lab scenarios: 10/10.
Canonical tools represented: 29.

This is a lab bridge map. It proves the Pi candidate can own the loop and canonical tool execution against Istara-shaped surfaces; it does not claim production FastAPI/database/channel integration.

## Chat Routes And ReAct Tool Loop
- id: chat_react_loop
- category: agent_loop
- bridge_status: runnable_lab_adapter
- covered: yes
- scenarios: chat.tool_loop.task_and_finding, documents.tools.slice, research.spine.step_tracker
- bridge_tools: tasks.create, documents.search, findings.create, research.record_step, telemetry.record_metric, models.route
- missing_bridge_tools: none
- real_files:
  - backend/app/api/routes/chat.py:1 - Chat route is documented as Prompt RAG plus native tool-calling ReAct loop.
  - backend/app/api/routes/chat.py:71 - Research-spine chat contract blocks reportable claims from raw model/RAG/tool output.
  - backend/app/api/routes/chat.py:123 - Native tool call loop filters hallucinated tools and executes canonical Istara tools.
  - backend/app/api/routes/chat.py:389 - POST /chat owns the session/message streaming lifecycle.
- real_tests:
  - tests/agentic_eval_contract.json
  - tests/benchmarks/test_orchestration.py
  - tests/simulation/scenarios/31-task-documents-tools.mjs
- production_gaps:
  - The bridge does not invoke FastAPI /chat, database sessions, SSE streaming, auth, or production provider routing. (backend/app/api/routes/chat.py:389, backend/app/models/chat.py:1)

## Autoresearch Routes And Governed Experiment Loop
- id: autoresearch_governance
- category: self_improvement
- bridge_status: runnable_lab_adapter_with_production_blockers
- covered: yes
- scenarios: autoresearch.governed_experiment.slice
- bridge_tools: autoresearch.propose_experiment, autoresearch.record_measurement, research.record_step, telemetry.record_metric
- missing_bridge_tools: none
- real_files:
  - backend/app/api/routes/autoresearch.py:45 - Experiment requests include loop type, metric target, max iterations, and project scope.
  - backend/app/api/routes/autoresearch.py:582 - POST /autoresearch/start starts a background engine loop after project/settings checks.
  - backend/app/core/autoresearch_engine.py:20 - Autoresearch policy says experiment artifacts are governed proposals, not report evidence.
  - backend/app/core/autoresearch_isolation.py:1 - Isolation context prevents sandbox experiments from leaking into live skill/self-evolution state.
- real_tests:
  - tests/test_autoresearch.py
  - tests/simulation/scenarios/61-autoresearch-isolation.mjs
  - tests/agentic_eval_contract.json
- production_gaps:
  - Running the real background AutoresearchEngine would mutate experiment DB state and can touch live model/provider settings; the lab only records the governed envelope. (backend/app/api/routes/autoresearch.py:582, backend/app/core/autoresearch_engine.py:35)

## Plan, Review, And Human Done Gates
- id: plan_review_state
- category: task_lifecycle
- bridge_status: runnable_lab_adapter_with_governance_warning
- covered: yes
- scenarios: task.plan_execute.lifecycle, research.spine.step_tracker
- bridge_tools: tasks.create, plans.create, tasks.update_lifecycle, research.record_step
- missing_bridge_tools: none
- real_files:
  - backend/app/api/routes/tasks.py:277 - Task approval blocks research artifacts until validity says report_allowed.
  - backend/app/core/task_review.py:82 - Atomic review snapshot captures documents, findings, reports, coding runs, and validity preview.
  - backend/app/core/task_review.py:216 - Review events transition In Review to Done only through explicit review actions.
  - backend/app/core/task_contracts.py:1 - Shared task/document contracts normalize priorities and evidence attachments.
- real_tests:
  - tests/test_tasks.py
  - tests/test_research_validity_contract.py
  - tests/simulation/scenarios/71-plan-and-execute.mjs
- production_gaps:
  - The lab can represent in_review/done envelopes but cannot perform a real human approval or DB-backed validity gate without changing production task state. (backend/app/api/routes/tasks.py:595, backend/app/core/task_review.py:216)

## Tasks, Findings, Documents, And Source Evidence
- id: tasks_findings_documents
- category: research_artifacts
- bridge_status: runnable_lab_adapter
- covered: yes
- scenarios: chat.tool_loop.task_and_finding, documents.tools.slice, research.spine.step_tracker
- bridge_tools: tasks.create, tasks.attach_document, documents.create, documents.search, documents.read, findings.create, research.record_step
- missing_bridge_tools: none
- real_files:
  - backend/app/api/routes/tasks.py:61 - TaskCreate captures project, skill, user context, documents, URLs, instructions, and labels.
  - backend/app/api/routes/documents.py:165 - Document creation persists source units used by research validity.
  - backend/app/api/routes/findings.py:583 - Finding evidence-chain endpoint exposes research-spine provenance.
  - backend/app/services/finding_validity_service.py:1 - Finding validity service distinguishes provisional and reportable artifacts.
- real_tests:
  - tests/test_documents.py
  - tests/test_findings.py
  - tests/test_tasks.py
  - tests/simulation/scenarios/31-task-documents-tools.mjs
- production_gaps:
  - The lab stores source spans in memory only; it does not write the production source-unit tables or accepted evidence-chain rows. (backend/app/api/routes/documents.py:165, backend/app/api/routes/findings.py:583)

## Memory, RAG, ReasoningBank, Memento, And Skills
- id: memory_rag_reasoning_memento_skills
- category: memory_and_skills
- bridge_status: runnable_lab_adapter_with_production_blockers
- covered: yes
- scenarios: memory.rag.slice, skills.three_skill_slice, memory.reasoningbank.memento.slice
- bridge_tools: memory.search, memory.write, reasoning_bank.store, reasoning_bank.retrieve, memento.record_skill_memory, skills.apply
- missing_bridge_tools: none
- real_files:
  - backend/app/api/routes/memory.py:74 - Memory search retrieves scoped hybrid RAG context.
  - backend/app/core/rag.py:457 - Hybrid search fuses vector and keyword rankings by provenance.
  - backend/app/api/routes/reasoning_bank.py:59 - ReasoningBank memories are admin-only because traces can be sensitive.
  - backend/app/core/reasoning_bank.py:122 - ReasoningBank stores process memory and tags process-only source kinds.
  - backend/app/core/agent_skill_tools.py:262 - Skill ranking combines explicit task skill, keywords, usage stats, telemetry, and reasoning memory.
- real_tests:
  - tests/evals/cases/core_eval_cases.json
  - tests/evals/registry.json
  - tests/agentic_eval_contract.json
  - tests/simulation/scenarios/20-all-skills-comprehensive.mjs
  - tests/simulation/scenarios/23-memory-view.mjs
- production_gaps:
  - The lab cannot exercise production embeddings, LanceDB/keyword indexes, admin-scoped ReasoningBank routes, or learned skill stats without credentials/DB state. (backend/app/api/routes/memory.py:74, backend/app/api/routes/reasoning_bank.py:59, backend/app/core/agent_skill_tools.py:262)

## A2A Delegation And Reports
- id: a2a_delegation_reports
- category: delegation
- bridge_status: runnable_lab_adapter_with_production_blockers
- covered: yes
- scenarios: a2a.debate_report.slice
- bridge_tools: a2a.delegate, a2a.report, tasks.update_lifecycle, telemetry.record_metric
- missing_bridge_tools: none
- real_files:
  - backend/app/api/routes/a2a.py:263 - A2A agent-card endpoint advertises Istara capabilities.
  - backend/app/api/routes/a2a.py:305 - JSON-RPC /a2a enforces auth, rate limits, body size, and replay protection.
  - backend/app/core/report_manager.py:227 - Reports only route task findings after human-approved Done and reportable evidence.
  - backend/app/api/routes/reports.py:13 - Reports API exposes project report envelopes.
- real_tests:
  - tests/test_a2a.py
  - tests/benchmarks/test_orchestration.py
  - tests/simulation/scenarios/73-a2a-debate-and-reports.mjs
- production_gaps:
  - The lab does not open JSON-RPC sockets or validate JWT/network tokens/replay keys; it records the canonical delegation/report shape only. (backend/app/api/routes/a2a.py:305, backend/app/core/report_manager.py:227)

## Channels, Webhooks, And Telegram-Like Lifecycle
- id: channels_webhooks_telegram_lifecycle
- category: channels
- bridge_status: runnable_lab_adapter_with_credentials_blocked
- covered: yes
- scenarios: channel.lifecycle.simulated_slice, channels.webhook.telegram.lifecycle
- bridge_tools: channels.create, webhooks.receive, channels.receive, channels.respond
- missing_bridge_tools: none
- real_files:
  - backend/app/api/routes/channels.py:79 - Channel route lists project-scoped channel instances.
  - backend/app/api/routes/channels.py:189 - Channel instances start/stop concrete adapters.
  - backend/app/api/routes/webhooks.py:81 - Inbound WhatsApp webhook checks signatures and replay protection.
  - backend/app/channels/telegram.py:49 - Telegram adapter requires a bot token and external dependency availability.
- real_tests:
  - tests/test_channel_inbound.py
  - tests/test_webhooks_security.py
  - tests/simulation/scenarios/53-channel-lifecycle.mjs
  - tests/real_user_benchmark/lib/persona.mjs
- production_gaps:
  - Real Telegram/WhatsApp/Google Chat loops need external bot/webhook credentials and running adapters; the lab uses signed simulated inbound envelopes. (backend/app/channels/telegram.py:49, backend/app/api/routes/webhooks.py:81)

## Steering And System Prompt Policy
- id: steering_system_prompt
- category: runtime_control
- bridge_status: runnable_lab_adapter_with_production_blockers
- covered: yes
- scenarios: steering.system_prompt.loop.slice
- bridge_tools: steering.queue, system_prompt.audit, models.route, telemetry.record_metric
- missing_bridge_tools: none
- real_files:
  - backend/app/api/routes/steering.py:139 - Steering route queues mid-execution messages to a project-scoped agent.
  - backend/app/api/routes/steering.py:171 - Follow-up route queues messages for the moment an agent would stop.
  - backend/app/core/prompt_rag.py:430 - Dynamic prompt composition protects identity anchors, token budget, and research-spine notices.
  - backend/app/api/routes/chat.py:71 - Chat prompt includes protected research-spine policy.
- real_tests:
  - tests/benchmarks/test_orchestration.py
  - tests/simulation/scenarios/70-mid-execution-steering.mjs
- production_gaps:
  - The lab does not interrupt a live long-running agent or SSE stream; it records queued steering/follow-up envelopes and policy-audit results. (backend/app/api/routes/steering.py:139, backend/app/api/routes/steering.py:305)

## Telemetry, Token Budgets, Tool Metrics, And Model Routes
- id: telemetry_tokens_tool_metrics
- category: observability
- bridge_status: runnable_lab_adapter
- covered: yes
- scenarios: model.routing.telemetry.slice, benchmarks.evals.real_user.contract
- bridge_tools: telemetry.record_metric, models.route, benchmarks.map_contract
- missing_bridge_tools: none
- real_files:
  - backend/app/core/telemetry.py:21 - Telemetry spans record operation, model, project, route, research validity, tool, and duration fields.
  - backend/app/api/routes/chat.py:535 - Chat allocates context budget and token buckets before model execution.
  - backend/app/core/token_counter.py:1 - Context guards keep prompts within provider window limits.
  - tests/benchmarks/long_horizon_runner.py:111 - Benchmark runner tracks tool calls and token-like streaming deltas.
- real_tests:
  - tests/test_telemetry.py
  - tests/benchmarks/long_horizon_runner.py
  - tests/evals/registry.json
- production_gaps:
  - The lab records local JSON metrics and raw LLM capture; it does not insert production TelemetrySpan or ModelSkillStats rows. (backend/app/core/telemetry.py:21, backend/app/models/model_skill_stats.py:1)

## Benchmarks, Evals, Simulations, Real User Benchmark, And Eval Contract
- id: benchmarks_evals_simulations_real_user_contract
- category: verification
- bridge_status: runnable_lab_adapter
- covered: yes
- scenarios: benchmarks.evals.real_user.contract
- bridge_tools: benchmarks.map_contract, evals.emit_structured, telemetry.record_metric
- missing_bridge_tools: none
- real_files:
  - tests/benchmarks/run_benchmarks.py:67 - Benchmark registry includes long horizon, tool-calling, A2A, and async steering checks.
  - tests/evals/registry.json:1 - Core eval registry covers provider compatibility, Prompt RAG, memory, skills, and orchestration.
  - tests/real_user_benchmark/benchmark-registry.json:1 - Real-user benchmark registry keeps credential and artifact safety policies.
  - tests/agentic_eval_contract.json:1 - Agentic eval contract enumerates release-facing evidence for autoresearch, ReasoningBank, Memento, tool calling, and UI.
- real_tests:
  - tests/benchmarks
  - tests/evals
  - tests/simulation/scenarios
  - tests/real_user_benchmark
  - tests/agentic_eval_contract.json
- production_gaps:
  - The bridge maps benchmark contracts and executes lab scenarios; it does not run full production browser/API/live-user harnesses. (tests/real_user_benchmark/run.mjs:1, tests/benchmarks/run_benchmarks.py:67)

