# Architect A: Istara Surfaces And Evaluation Assets

Scope: planning-only Istara architecture/evaluation pass for later comparison against Pi. No Istara code changes, no local model runs, and no cloud LLM tests in this round.

## Surfaces To Compare

- Chat ReAct: `backend/app/api/routes/chat.py`
  - Native tool calling, fallback JSON parsing, tool iteration limits, project/file/RAG context, Prompt RAG persona injection.
- Design Chat ReAct: `backend/app/api/routes/interfaces.py`
  - Design-specific tools, raw-JSON fallback handling, design persona and RAG context.
- Agent research/task execution: `backend/app/core/agent_execution.py`, `backend/app/core/agent_research.py`
  - Plan-and-execute path, ranked skill use, general ReAct task loop, research plan schema, ReasoningBank trace storage.
- Tool and skill layer: `backend/app/skills/system_actions.py`, `backend/app/core/agent_skill_tools.py`, `backend/app/skills/design_tools.py`
  - System tools, design tools, ranked `run_skill` enum, skill telemetry, memento/reasoning boosts.
- Model management: `backend/app/core/compute_registry*.py`, `backend/app/core/lmstudio.py`, `relay/lib/llm-proxy.mjs`, `frontend/src/lib/modelProviders.ts`
  - Capability-aware routing, provider inference, relay/browser node authorization, tool/response_format passthrough, retries/fallbacks.
- Memory/research context: `backend/app/core/rag.py`, `backend/app/core/reasoning_bank.py`, `backend/app/core/agent_memory.py`, `backend/app/core/prompt_rag.py`, `backend/app/core/context_hierarchy.py`
  - RAG retrieval, untrusted context wrapping, memory redaction, project scoping, persona/system prompt composition.
- A2A: `backend/app/api/routes/a2a.py`, `backend/app/services/a2a.py`, `backend/app/api/routes/agents.py`, `backend/app/models/agent.py`
  - JSON-RPC A2A, internal agent messages, project authorization, replay/rate/body caps, message audit log.
- Telemetry/evals: `backend/app/models/telemetry_span.py`, `backend/app/core/telemetry.py`, `scripts/run_istara_evals.py`, `tests/evals/*`
  - Content-free spans, eval manifests, JSONL results, aggregate model/tool/error metrics.

## Istara Success Criteria

- ReAct engine:
  - Preserves native tool calls across providers.
  - Rejects hallucinated tool names.
  - Produces valid fallback tool JSON only when needed.
  - Recovers from invalid arguments or empty tool calls.
  - Stops within configured iteration caps: chat 8, design 3, agent task 5.
  - Grounds final answers in tool/RAG results without exposing hidden prompt text.
- Model management:
  - Selects only nodes matching required tools, vision, context, model, and project authorization.
  - Keeps relay/browser donated compute project-scoped.
  - Passes `tools` and `response_format` through OpenAI-compatible, Anthropic, Ollama, and relay paths where supported.
  - Records routing failures without leaking prompts, responses, files, or secrets.
- Research spine:
  - Produces structured plans with ordered steps, dependencies, skill names, ReAct flags, and success criteria.
  - Distinguishes research, synthesis, validation, and reporting steps.
  - Stores useful traces in ReasoningBank only after redaction/content guards.
  - Cites retrieved evidence instead of fabricating claims.
- Memory:
  - RAG fallback works when vector search is unavailable.
  - Retrieved memory is project-scoped by default, with explicit global opt-in.
  - Prompt-injection-like memory is wrapped as untrusted context.
  - ReasoningBank redacts secrets and retrieves relevant prior traces.
  - Agent notes do not contaminate unrelated projects.
- Tool/skill calling:
  - `run_skill` schema constrains skill names to ranked candidates.
  - System tools return structured `<tool_output>` payloads.
  - Skill ranking reflects lexical match, memento usage, telemetry, and reasoning-memory boosts.
  - Tool calls preserve project/task/agent scope.
- System/skill prompt adherence:
  - Prompt RAG anchors identity/persona.
  - Dynamic prompt sections stay relevant to the query.
  - Instruction boundaries are respected.
  - User/task instructions survive into agent skill execution.
  - The model does not repeat hidden system/skill prompts.
- A2A:
  - Requires `project_id` for task/message flows.
  - Enforces auth, replay protection, rate limits, body caps, metadata caps, and allowed message types.
  - Excludes messages with conflicting project claims from project views.
  - Supports debate/report workflows with auditable logs.

## Existing Assets To Reuse

- Eval contracts: `tests/agentic_eval_contract.json`
- Eval registry/cases: `tests/evals/registry.json`, `tests/evals/cases/core_eval_cases.json`, `tests/evals/README.md`
- Eval runner: `scripts/run_istara_evals.py`
- ReAct/orchestration: `tests/benchmarks/test_orchestration.py`, `tests/integration/test_llm_orchestration_real.py`
- Chat/tools: `tests/test_chat.py`, `tests/test_agent_skill_tools.py`
- Memory/RAG: `tests/test_reasoning_bank.py`, `tests/test_rag_resilience.py`
- Model/provider contracts: `tests/test_model_provider_contract.py`, `relay/lib/llm-proxy.test.mjs`
- Telemetry: `tests/test_telemetry.py`
- Simulations: `tests/simulation/scenarios/71-plan-and-execute.mjs`, `tests/simulation/scenarios/73-a2a-debate-and-reports.mjs`, `tests/simulation/scenarios/22-architecture-evaluation.mjs`
- Real-user benchmark plan: `tests/real_user_benchmark/system-prompt.md`, `tests/real_user_benchmark/benchmark-plan.md`
- Strategy docs: `testing/AI_EVALS_STRATEGY.md`, `Tech.md`

## Risks

- Existing deterministic tests are mostly mocks/static; live quality comparison needs approved cloud LLM access.
- Pi and Istara expose different primitives, so scoring must normalize capabilities rather than compare raw implementation details.
- Telemetry is content-free; wrapper metrics may be needed for token/cost/tool-step detail.
- Design/Figma/Stitch surfaces may require external credentials and should be separated from core ReAct tests.
- Compass Forge status showed stale/no recorded snapshot; avoid relying on snapshot freshness until refreshed in a later approved round.
