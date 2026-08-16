# Compass Forge Dependency Maps

Run: `20260719T120128-0300-replacement-worktree`
Remediation pass: `2026-07-19T12:12:49-03:00`

## CF Commands Used

- `compass-forge status`
- `compass-forge next`
- `compass-forge agent-brief --request "Pi replacement worktree: map Istara chat/tool loop, task planning/execution, model/provider routing, memory/RAG, and A2A/channel dependencies for isolated Pi adapter insertion" --compact --max-seconds 120`
- `compass-forge context "Pi replacement dependency map for chat tool loop, task planning execution, model provider routing, memory RAG, A2A channels" --pack-type standard`
- `compass-forge intelligence impact --path backend/app/api/routes/chat.py --request "Pi replacement insertion for chat ReAct tool loop through canonical tools"`
- `compass-forge intelligence impact --path backend/app/core/agent_execution.py --request "Pi replacement insertion for task planning and execution"`
- `compass-forge intelligence impact --path backend/app/core/llm_router.py --request "Pi replacement insertion for model provider routing through pi-ai"`
- `compass-forge intelligence impact --path backend/app/core/rag.py --request "Pi replacement insertion for memory and RAG actions through Istara adapters"`
- `compass-forge intelligence impact --path backend/app/api/routes/a2a.py --request "Pi replacement insertion for A2A canonical action and agent delegation"`
- `compass-forge intelligence impact --path backend/app/api/routes/channels.py --request "Pi replacement insertion for channel-facing turns through Istara channel adapters"`
- `compass-forge gate after --summary`

## CF State Limitation

`compass-forge status` reported `registered: false`, no recorded snapshot, and
`staleness.state: unknown`. `compass-forge next` recommended repository initialization.
The compact agent brief and impact commands still returned useful tree-sitter maps, route
contracts, likely tests, docs, and hotspot risk. Because graph retrieval reported no
durable index run, each map below pairs CF output with explicit source inspection.

`compass-forge gate after --summary` returned `warn` with zero failures, zero new failures,
zero route/type/contract/generated drift, and zero security findings. The warnings were the
existing complexity warnings for `SYSTEM_INTEGRITY_GUIDE.md`, `Tech.md`,
`tests/real_user_benchmark/run.mjs`, and `tests/simulation/run.mjs`.

## Selected Lab Insertion Point

The sidecar remains the narrowest safe insertion point:

`/Users/user/Documents/Istara-main-pi-replacement/labs/pi-replacement`

Reason: CF ranked `backend/app/api/routes/chat.py`, `backend/app/core/agent_execution.py`,
`backend/app/core/llm_router.py`, `backend/app/core/rag.py`, `backend/app/api/routes/a2a.py`,
and `backend/app/api/routes/channels.py` as high-impact surfaces with production routes,
project permissions, persisted stores, telemetry, and broad tests. A removable sidecar lets
Pi own a candidate loop without mutating those production contracts.

## Chat And Tool Loop Map

CF seed and source anchors:

- Primary route: `backend/app/api/routes/chat.py`
- Contracts: `POST /chat`, `GET /chat/history/{project_id}`, `POST /chat/voice`,
  `POST /chat/voice-transcribe`
- Imports and owned dependencies: project scope checks, session/message persistence,
  Prompt RAG, RAG retrieval, thinking controls, `ollama`, `SYSTEM_TOOLS`, `OPENAI_TOOLS`,
  and `execute_tool`
- Native loop anchor: file header describes `LLM -> tool_calls -> execute -> tool results -> LLM`
  with max 8 iterations; implementation enters `_generate_native_tools` from the SSE
  generator and falls back to text tool parsing when native tools are rejected
- Frontend/docs surface: `frontend/src/components/chat/ChatView.tsx`,
  `frontend/src/stores/chatStore.ts`, `frontend/src/lib/chatApi.ts`,
  `docs/features/content/chat/overview/architecture.md`,
  `docs/features/content/chat/model-controls/architecture.md`
- Likely tests: `tests/test_chat.py`, `tests/test_integration_chat_flow.py`,
  `tests/simulation/scenarios/05-chat-interaction.mjs`,
  `tests/simulation/scenarios/12-chat-sessions.mjs`,
  `tests/simulation/scenarios/31-task-documents-tools.mjs`,
  `tests/agentic_eval_contract.json`

Adapter implication:

`CanonicalToolFacade.toPiAgentTools()` exposes Istara product actions as Pi tools, and
`IstaraPiAdapter.runNoModelChatToolLoop()` proves the chat/tool-loop shape through Pi
`Agent` events without replacing the production SSE route.

## Task Planning And Execution Map

CF seed and source anchors:

- Primary engine: `backend/app/core/agent_execution.py`
- Inbound owner: `backend/app/core/agent.py` inherits `AgentExecutionMixin`
- Direct dependencies: websocket broadcasts, checkpoints, context hierarchy, embeddings,
  `retrieve_context`, task/finding models, skill registry, skill manager, telemetry,
  steering, hooks, and `ollama`
- Execution anchors: `_execute_task()` moves task state, retrieves RAG context, optionally
  creates a research plan, selects a skill, executes skill output, validates, stores findings,
  writes agent memory, verifies findings, marks review state, and records reasoning memory
- A2A task adjacency: borderline consensus triggers `_initiate_debate`
- Likely tests: `tests/benchmarks/test_orchestration.py`,
  `tests/simulation/scenarios/31-task-documents-tools.mjs`,
  `tests/simulation/scenarios/38-task-routing.mjs`,
  `tests/simulation/scenarios/71-plan-and-execute.mjs`,
  `tests/test_agents.py`, `tests/test_agent_skill_tools.py`, `tests/test_tasks.py`

Adapter implication:

The lab implements only the first replacement slice: a Pi-owned loop can call
`tasks.create` and `findings.create` canonical actions and preserve project state. Full
replacement still needs real DB/service adapters for task lifecycle, plan steps, review
state, hooks, telemetry, and reasoning memory.

## Model And Provider Routing Map

CF seed and source anchors:

- Compatibility wrapper: `backend/app/core/llm_router.py` delegates all routing to
  `compute_registry`
- Core routing dependencies: `backend/app/core/compute_registry.py`,
  `backend/app/core/compute_registry_routing.py`,
  `backend/app/core/compute_registry_helpers.py`,
  `backend/app/core/model_capabilities.py`, `backend/app/core/ollama.py`, `relay/index.mjs`,
  `relay/lib/llm-proxy.mjs`
- Route contracts: `/settings/model`, `/settings/provider`, `/settings/models`,
  `/settings/status`, `/compute/nodes`, `/compute/stats`, `/compute/model-warnings`
- Frontend controls: `frontend/src/lib/modelProviders.ts`,
  `frontend/src/components/common/SettingsView.tsx`,
  `frontend/src/components/common/ComputePoolView.tsx`
- Likely tests: `frontend/src/lib/modelProviders.test.ts`,
  `tests/test_model_provider_contract.py`, `tests/test_llm_schema_adapter.py`,
  `tests/test_compute_registry_model_loading.py`, `tests/compute_cases/routing.py`,
  `tests/integration/test_llm_orchestration_real.py`

Adapter implication:

The sidecar does not alter Istara compute routing. It separately proves the candidate Pi
provider boundary by using `@earendil-works/pi-ai` `deepseekProvider()` and
`deepseek-v4-pro`, with the key read only from Keychain into `DEEPSEEK_API_KEY` inside the
smoke process.

## Memory And RAG Map

CF seed and source anchors:

- Primary RAG engine: `backend/app/core/rag.py`
- Store boundary: LanceDB path per project, `TextChunk`, `embed_text`, `embed_chunks`,
  hybrid search, keyword fallback, content guard wrapping, and `RAGContext`
- Inbound callers: `backend/app/api/routes/chat.py`, `backend/app/api/routes/documents.py`,
  `backend/app/api/routes/files.py`, `backend/app/api/routes/findings.py`,
  `backend/app/api/routes/interfaces.py`, `backend/app/api/routes/memory.py`,
  `backend/app/core/agent_execution.py`, `backend/app/core/agent_memory.py`
- Scenario/eval surface: `scripts/run_istara_evals.py`, `tests/evals/registry.json`,
  `tests/evals/cases/core_eval_cases.json`, `tests/real_user_benchmark/run.mjs`,
  `tests/simulation/scenarios/23-memory-view.mjs`
- Likely tests: `tests/test_memory.py`, `tests/test_project_scope_contracts.py`,
  `tests/test_channel_file_security.py`, `tests/test_agent_skill_tools.py`

Adapter implication:

`memory.search` exists in `CanonicalToolFacade` as a schema/result envelope, but the smoke
does not yet call a real Istara memory/RAG backend. Future replacement scoring must keep
Istara as source of truth for project memory, RAG grounding, content-guard wrapping, and
document citations.

## A2A And Channel Map

CF seed and source anchors:

- A2A routes/services: `backend/app/api/routes/a2a.py`, `backend/app/services/a2a.py`
- A2A contracts: `GET /.well-known/agent.json`, `POST /a2a`, `GET /agents/a2a/log`,
  agent message endpoints under `/agents/{agent_id}/messages`
- A2A dependencies: agent models, project-scope validation, A2A message row/metadata
  ownership resolution, message type allowlist, rate limiting, and security tests
- Channel routes/services: `backend/app/api/routes/channels.py`,
  `backend/app/services/channel_service.py`, `backend/app/channels/base.py`
- Channel contracts: create/list/update/delete/start/stop/health/history/send under
  `/channels`
- Channel dependencies: encrypted channel config, `ChannelInstance`, `ChannelMessage`,
  `ChannelConversation`, adapters for Telegram, Slack, WhatsApp, and Google Chat
- Likely tests: `tests/test_a2a_security.py`, `tests/test_a2a_service_scope.py`,
  `tests/test_a2a_project_claims.py`, `tests/test_channels.py`,
  `tests/test_channel_inbound.py`, `tests/test_channel_resilience.py`,
  `tests/test_channel_file_security.py`, `tests/simulation/scenarios/53-channel-lifecycle.mjs`,
  `tests/simulation/scenarios/73-a2a-debate-and-reports.mjs`

Adapter implication:

`a2a.delegate` exists as a canonical action in the sidecar, but channel-facing turns are
not implemented. A replacement benchmark must keep channel credentials, lifecycle,
inbound auth, message persistence, and project scoping inside Istara adapters while letting
Pi own only the candidate turn loop behind those adapters.

## Coverage Backbone Mapping

The replacement denominator remains the Istara scenario/test backbone, not standalone Pi:

- `tests/simulation/scenarios/31-task-documents-tools.mjs`: Pi candidate has a deterministic
  sidecar equivalent for task/finding tool envelopes, but not documents.
- `tests/simulation/scenarios/53-channel-lifecycle.mjs`: blocked pending channel adapter.
- `tests/simulation/scenarios/71-plan-and-execute.mjs`: partially represented by
  `tasks.create`; blocked for real plan lifecycle and review state.
- `tests/simulation/scenarios/73-a2a-debate-and-reports.mjs`: partially represented by
  `a2a.delegate` schema only; blocked for actual service behavior and reporting.
- `tests/simulation/scenarios/76-long-horizon-trajectory.mjs`: deferred until memory,
  task lifecycle, and recovery adapters exist.
- `tests/real_user_benchmark/run.mjs`: deferred until paired benchmark cost cap is set.
- `tests/evals/registry.json` and `tests/evals/cases/core_eval_cases.json`: blocked for
  RAG, ReasoningBank, Memento/skills, DAG/ReAct, and structured-output adapters.

## Remediation From CF Review

Source inspection during this CF pass found one secret-lifecycle defect in the sidecar:
`runDeepSeekProviderSmoke()` set `process.env.DEEPSEEK_API_KEY` before checking whether
`deepseek-v4-pro` resolved. If that branch returned early, the key stayed in process env.
The adapter now wraps provider setup, model resolution, and completion in one `try/finally`
that deletes the env var on all keyed paths.
