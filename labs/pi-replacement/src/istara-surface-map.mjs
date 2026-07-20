export const MANDATORY_ISTARA_SURFACE_IDS = [
  "chat_react_loop",
  "autoresearch_governance",
  "plan_review_state",
  "tasks_findings_documents",
  "memory_rag_reasoning_memento_skills",
  "a2a_delegation_reports",
  "channels_webhooks_telegram_lifecycle",
  "steering_system_prompt",
  "telemetry_tokens_tool_metrics",
  "benchmarks_evals_simulations_real_user_contract",
];

export const ISTARA_SURFACE_MAP = [
  {
    id: "chat_react_loop",
    label: "Chat Routes And ReAct Tool Loop",
    category: "agent_loop",
    realFiles: [
      { path: "backend/app/api/routes/chat.py", line: 1, evidence: "Chat route is documented as Prompt RAG plus native tool-calling ReAct loop." },
      { path: "backend/app/api/routes/chat.py", line: 71, evidence: "Research-spine chat contract blocks reportable claims from raw model/RAG/tool output." },
      { path: "backend/app/api/routes/chat.py", line: 123, evidence: "Native tool call loop filters hallucinated tools and executes canonical Istara tools." },
      { path: "backend/app/api/routes/chat.py", line: 389, evidence: "POST /chat owns the session/message streaming lifecycle." },
    ],
    realTests: [
      "tests/agentic_eval_contract.json",
      "tests/benchmarks/test_orchestration.py",
      "tests/simulation/scenarios/31-task-documents-tools.mjs",
    ],
    bridgeTools: [
      "tasks.create",
      "documents.search",
      "findings.create",
      "research.record_step",
      "telemetry.record_metric",
      "models.route",
    ],
    candidateScenarios: [
      "chat.tool_loop.task_and_finding",
      "documents.tools.slice",
      "research.spine.step_tracker",
    ],
    bridgeStatus: "runnable_lab_adapter_plus_production_hook",
    productionGaps: [
      {
        reason: "The replacement worktree now has an opt-in FastAPI /chat Pi candidate hook that preserves SSE/tool contracts and registers DeepSeek at runtime; full production live coverage still needs the DeepSeek key and broader endpoint fanout.",
        files: ["backend/app/api/routes/chat.py:123", "backend/app/core/pi_replacement.py:1"],
      },
    ],
  },
  {
    id: "autoresearch_governance",
    label: "Autoresearch Routes And Governed Experiment Loop",
    category: "self_improvement",
    realFiles: [
      { path: "backend/app/api/routes/autoresearch.py", line: 45, evidence: "Experiment requests include loop type, metric target, max iterations, and project scope." },
      { path: "backend/app/api/routes/autoresearch.py", line: 582, evidence: "POST /autoresearch/start starts a background engine loop after project/settings checks." },
      { path: "backend/app/core/autoresearch_engine.py", line: 20, evidence: "Autoresearch policy says experiment artifacts are governed proposals, not report evidence." },
      { path: "backend/app/core/autoresearch_isolation.py", line: 1, evidence: "Isolation context prevents sandbox experiments from leaking into live skill/self-evolution state." },
    ],
    realTests: [
      "tests/test_autoresearch.py",
      "tests/simulation/scenarios/61-autoresearch-isolation.mjs",
      "tests/agentic_eval_contract.json",
    ],
    bridgeTools: [
      "autoresearch.propose_experiment",
      "autoresearch.record_measurement",
      "research.record_step",
      "telemetry.record_metric",
    ],
    candidateScenarios: ["autoresearch.governed_experiment.slice"],
    bridgeStatus: "runnable_lab_adapter_with_production_blockers",
    productionGaps: [
      {
        reason: "Running the real background AutoresearchEngine would mutate experiment DB state and can touch live model/provider settings; the lab only records the governed envelope.",
        files: ["backend/app/api/routes/autoresearch.py:582", "backend/app/core/autoresearch_engine.py:35"],
      },
    ],
  },
  {
    id: "plan_review_state",
    label: "Plan, Review, And Human Done Gates",
    category: "task_lifecycle",
    realFiles: [
      { path: "backend/app/api/routes/tasks.py", line: 277, evidence: "Task approval blocks research artifacts until validity says report_allowed." },
      { path: "backend/app/core/task_review.py", line: 82, evidence: "Atomic review snapshot captures documents, findings, reports, coding runs, and validity preview." },
      { path: "backend/app/core/task_review.py", line: 216, evidence: "Review events transition In Review to Done only through explicit review actions." },
      { path: "backend/app/core/task_contracts.py", line: 1, evidence: "Shared task/document contracts normalize priorities and evidence attachments." },
    ],
    realTests: [
      "tests/test_tasks.py",
      "tests/test_research_validity_contract.py",
      "tests/simulation/scenarios/71-plan-and-execute.mjs",
    ],
    bridgeTools: [
      "tasks.create",
      "plans.create",
      "tasks.update_lifecycle",
      "research.record_step",
    ],
    candidateScenarios: [
      "task.plan_execute.lifecycle",
      "research.spine.step_tracker",
    ],
    bridgeStatus: "runnable_lab_adapter_with_governance_warning",
    productionGaps: [
      {
        reason: "The lab can represent in_review/done envelopes but cannot perform a real human approval or DB-backed validity gate without changing production task state.",
        files: ["backend/app/api/routes/tasks.py:595", "backend/app/core/task_review.py:216"],
      },
    ],
  },
  {
    id: "tasks_findings_documents",
    label: "Tasks, Findings, Documents, And Source Evidence",
    category: "research_artifacts",
    realFiles: [
      { path: "backend/app/api/routes/tasks.py", line: 61, evidence: "TaskCreate captures project, skill, user context, documents, URLs, instructions, and labels." },
      { path: "backend/app/api/routes/documents.py", line: 165, evidence: "Document creation persists source units used by research validity." },
      { path: "backend/app/api/routes/findings.py", line: 583, evidence: "Finding evidence-chain endpoint exposes research-spine provenance." },
      { path: "backend/app/services/finding_validity_service.py", line: 1, evidence: "Finding validity service distinguishes provisional and reportable artifacts." },
    ],
    realTests: [
      "tests/test_documents.py",
      "tests/test_findings.py",
      "tests/test_tasks.py",
      "tests/simulation/scenarios/31-task-documents-tools.mjs",
    ],
    bridgeTools: [
      "tasks.create",
      "tasks.attach_document",
      "documents.create",
      "documents.search",
      "documents.read",
      "findings.create",
      "research.record_step",
    ],
    candidateScenarios: [
      "chat.tool_loop.task_and_finding",
      "documents.tools.slice",
      "research.spine.step_tracker",
    ],
    bridgeStatus: "runnable_lab_adapter",
    productionGaps: [
      {
        reason: "The lab stores source spans in memory only; it does not write the production source-unit tables or accepted evidence-chain rows.",
        files: ["backend/app/api/routes/documents.py:165", "backend/app/api/routes/findings.py:583"],
      },
    ],
  },
  {
    id: "memory_rag_reasoning_memento_skills",
    label: "Memory, RAG, ReasoningBank, Memento, And Skills",
    category: "memory_and_skills",
    realFiles: [
      { path: "backend/app/api/routes/memory.py", line: 74, evidence: "Memory search retrieves scoped hybrid RAG context." },
      { path: "backend/app/core/rag.py", line: 457, evidence: "Hybrid search fuses vector and keyword rankings by provenance." },
      { path: "backend/app/api/routes/reasoning_bank.py", line: 59, evidence: "ReasoningBank memories are admin-only because traces can be sensitive." },
      { path: "backend/app/core/reasoning_bank.py", line: 122, evidence: "ReasoningBank stores process memory and tags process-only source kinds." },
      { path: "backend/app/core/agent_skill_tools.py", line: 262, evidence: "Skill ranking combines explicit task skill, keywords, usage stats, telemetry, and reasoning memory." },
    ],
    realTests: [
      "tests/evals/cases/core_eval_cases.json",
      "tests/evals/registry.json",
      "tests/agentic_eval_contract.json",
      "tests/simulation/scenarios/20-all-skills-comprehensive.mjs",
      "tests/simulation/scenarios/23-memory-view.mjs",
    ],
    bridgeTools: [
      "memory.search",
      "memory.write",
      "reasoning_bank.store",
      "reasoning_bank.retrieve",
      "memento.record_skill_memory",
      "skills.apply",
    ],
    candidateScenarios: [
      "memory.rag.slice",
      "skills.three_skill_slice",
      "memory.reasoningbank.memento.slice",
    ],
    bridgeStatus: "runnable_lab_adapter_with_production_blockers",
    productionGaps: [
      {
        reason: "The lab cannot exercise production embeddings, LanceDB/keyword indexes, admin-scoped ReasoningBank routes, or learned skill stats without credentials/DB state.",
        files: ["backend/app/api/routes/memory.py:74", "backend/app/api/routes/reasoning_bank.py:59", "backend/app/core/agent_skill_tools.py:262"],
      },
    ],
  },
  {
    id: "a2a_delegation_reports",
    label: "A2A Delegation And Reports",
    category: "delegation",
    realFiles: [
      { path: "backend/app/api/routes/a2a.py", line: 263, evidence: "A2A agent-card endpoint advertises Istara capabilities." },
      { path: "backend/app/api/routes/a2a.py", line: 305, evidence: "JSON-RPC /a2a enforces auth, rate limits, body size, and replay protection." },
      { path: "backend/app/core/report_manager.py", line: 227, evidence: "Reports only route task findings after human-approved Done and reportable evidence." },
      { path: "backend/app/api/routes/reports.py", line: 13, evidence: "Reports API exposes project report envelopes." },
    ],
    realTests: [
      "tests/test_a2a.py",
      "tests/benchmarks/test_orchestration.py",
      "tests/simulation/scenarios/73-a2a-debate-and-reports.mjs",
    ],
    bridgeTools: ["a2a.delegate", "a2a.report", "tasks.update_lifecycle", "telemetry.record_metric"],
    candidateScenarios: ["a2a.debate_report.slice"],
    bridgeStatus: "runnable_lab_adapter_plus_production_hook",
    productionGaps: [
      {
        reason: "The replacement worktree now records Pi candidate telemetry after real JSON-RPC tasks/send auth, rate, and replay gates; full report synthesis still depends on production Done/report approval state.",
        files: ["backend/app/api/routes/a2a.py:305", "backend/app/core/pi_replacement.py:1", "backend/app/core/report_manager.py:227"],
      },
    ],
  },
  {
    id: "channels_webhooks_telegram_lifecycle",
    label: "Channels, Webhooks, And Telegram-Like Lifecycle",
    category: "channels",
    realFiles: [
      { path: "backend/app/api/routes/channels.py", line: 79, evidence: "Channel route lists project-scoped channel instances." },
      { path: "backend/app/api/routes/channels.py", line: 189, evidence: "Channel instances start/stop concrete adapters." },
      { path: "backend/app/api/routes/webhooks.py", line: 81, evidence: "Inbound WhatsApp webhook checks signatures and replay protection." },
      { path: "backend/app/channels/telegram.py", line: 49, evidence: "Telegram adapter requires a bot token and external dependency availability." },
    ],
    realTests: [
      "tests/test_channel_inbound.py",
      "tests/test_webhooks_security.py",
      "tests/simulation/scenarios/53-channel-lifecycle.mjs",
      "tests/real_user_benchmark/lib/persona.mjs",
    ],
    bridgeTools: [
      "channels.create",
      "webhooks.receive",
      "channels.receive",
      "channels.respond",
    ],
    candidateScenarios: [
      "channel.lifecycle.simulated_slice",
      "channels.webhook.telegram.lifecycle",
    ],
    bridgeStatus: "runnable_lab_adapter_plus_production_hook_with_credentials_blocked",
    productionGaps: [
      {
        reason: "The replacement worktree now has a credential-free pi_local adapter through the real channel router/inbound processor; real Telegram/WhatsApp/Google Chat loops still need external bot/webhook credentials.",
        files: ["backend/app/channels/pi_local.py:1", "backend/app/services/inbound_processor.py:89", "backend/app/channels/telegram.py:49", "backend/app/api/routes/webhooks.py:81"],
      },
    ],
  },
  {
    id: "steering_system_prompt",
    label: "Steering And System Prompt Policy",
    category: "runtime_control",
    realFiles: [
      { path: "backend/app/api/routes/steering.py", line: 139, evidence: "Steering route queues mid-execution messages to a project-scoped agent." },
      { path: "backend/app/api/routes/steering.py", line: 171, evidence: "Follow-up route queues messages for the moment an agent would stop." },
      { path: "backend/app/core/prompt_rag.py", line: 430, evidence: "Dynamic prompt composition protects identity anchors, token budget, and research-spine notices." },
      { path: "backend/app/api/routes/chat.py", line: 71, evidence: "Chat prompt includes protected research-spine policy." },
    ],
    realTests: [
      "tests/benchmarks/test_orchestration.py",
      "tests/simulation/scenarios/70-mid-execution-steering.mjs",
    ],
    bridgeTools: [
      "steering.queue",
      "system_prompt.audit",
      "models.route",
      "telemetry.record_metric",
    ],
    candidateScenarios: ["steering.system_prompt.loop.slice"],
    bridgeStatus: "runnable_lab_adapter_with_production_blockers",
    productionGaps: [
      {
        reason: "The lab does not interrupt a live long-running agent or SSE stream; it records queued steering/follow-up envelopes and policy-audit results.",
        files: ["backend/app/api/routes/steering.py:139", "backend/app/api/routes/steering.py:305"],
      },
    ],
  },
  {
    id: "telemetry_tokens_tool_metrics",
    label: "Telemetry, Token Budgets, Tool Metrics, And Model Routes",
    category: "observability",
    realFiles: [
      { path: "backend/app/core/telemetry.py", line: 21, evidence: "Telemetry spans record operation, model, project, route, research validity, tool, and duration fields." },
      { path: "backend/app/api/routes/chat.py", line: 535, evidence: "Chat allocates context budget and token buckets before model execution." },
      { path: "backend/app/core/token_counter.py", line: 1, evidence: "Context guards keep prompts within provider window limits." },
      { path: "tests/benchmarks/long_horizon_runner.py", line: 111, evidence: "Benchmark runner tracks tool calls and token-like streaming deltas." },
    ],
    realTests: [
      "tests/test_telemetry.py",
      "tests/benchmarks/long_horizon_runner.py",
      "tests/evals/registry.json",
    ],
    bridgeTools: [
      "telemetry.record_metric",
      "models.route",
      "benchmarks.map_contract",
    ],
    candidateScenarios: [
      "model.routing.telemetry.slice",
      "benchmarks.evals.real_user.contract",
    ],
    bridgeStatus: "runnable_lab_adapter_plus_production_hook",
    productionGaps: [
      {
        reason: "The replacement worktree now inserts production TelemetrySpan rows for Pi chat/tool/A2A/channel hooks; full ModelSkillStats and broad production benchmark telemetry remain outside this bounded wiring round.",
        files: ["backend/app/core/pi_replacement.py:1", "backend/app/core/telemetry.py:21", "backend/app/models/model_skill_stats.py:1"],
      },
    ],
  },
  {
    id: "benchmarks_evals_simulations_real_user_contract",
    label: "Benchmarks, Evals, Simulations, Real User Benchmark, And Eval Contract",
    category: "verification",
    realFiles: [
      { path: "tests/benchmarks/run_benchmarks.py", line: 67, evidence: "Benchmark registry includes long horizon, tool-calling, A2A, and async steering checks." },
      { path: "tests/evals/registry.json", line: 1, evidence: "Core eval registry covers provider compatibility, Prompt RAG, memory, skills, and orchestration." },
      { path: "tests/real_user_benchmark/benchmark-registry.json", line: 1, evidence: "Real-user benchmark registry keeps credential and artifact safety policies." },
      { path: "tests/agentic_eval_contract.json", line: 1, evidence: "Agentic eval contract enumerates release-facing evidence for autoresearch, ReasoningBank, Memento, tool calling, and UI." },
    ],
    realTests: [
      "tests/benchmarks",
      "tests/evals",
      "tests/simulation/scenarios",
      "tests/real_user_benchmark",
      "tests/agentic_eval_contract.json",
    ],
    bridgeTools: [
      "benchmarks.map_contract",
      "evals.emit_structured",
      "telemetry.record_metric",
    ],
    candidateScenarios: ["benchmarks.evals.real_user.contract"],
    bridgeStatus: "runnable_lab_adapter_plus_production_hook",
    productionGaps: [
      {
        reason: "The bridge maps benchmark contracts, executes lab scenarios, and now has targeted production-hook regression tests; full browser/API/live-user harness fanout remains deferred by budget and external runtime setup.",
        files: ["tests/test_pi_replacement_candidate.py:1", "tests/real_user_benchmark/run.mjs:1", "tests/benchmarks/run_benchmarks.py:67"],
      },
    ],
  },
];

export function surfaceById(surfaceId) {
  return ISTARA_SURFACE_MAP.find((surface) => surface.id === surfaceId);
}

export function scenarioSurfaceIds(scenario) {
  if (Array.isArray(scenario?.istaraSurfaceIds)) return scenario.istaraSurfaceIds;
  return [];
}

export function buildSurfaceCoverageSummary(scenarios = []) {
  const scenarioIds = new Set(scenarios.map((scenario) => scenario.id));
  const covered = new Set();
  const toolSet = new Set();

  for (const scenario of scenarios) {
    for (const surfaceId of scenarioSurfaceIds(scenario)) covered.add(surfaceId);
    for (const toolId of scenario.requiredTools ?? scenario.expectedCanonicalTools ?? []) toolSet.add(toolId);
  }

  const surfaces = ISTARA_SURFACE_MAP.map((surface) => {
    const candidateScenarios = surface.candidateScenarios.filter((scenarioId) => scenarioIds.has(scenarioId));
    return {
      id: surface.id,
      label: surface.label,
      category: surface.category,
      bridgeStatus: surface.bridgeStatus,
      covered: covered.has(surface.id) && candidateScenarios.length > 0,
      bridgeTools: surface.bridgeTools,
      missingBridgeTools: surface.bridgeTools.filter((toolId) => !toolSet.has(toolId)),
      candidateScenarios,
      realFiles: surface.realFiles,
      realTests: surface.realTests,
      productionGaps: surface.productionGaps,
    };
  });

  return {
    mandatorySurfaceCount: MANDATORY_ISTARA_SURFACE_IDS.length,
    mappedSurfaceCount: ISTARA_SURFACE_MAP.length,
    coveredSurfaceCount: surfaces.filter((surface) => surface.covered).length,
    runnableSurfaceCount: surfaces.filter((surface) => surface.bridgeStatus.startsWith("runnable_lab_adapter")).length,
    blockedProductionGapCount: surfaces.reduce((sum, surface) => sum + surface.productionGaps.length, 0),
    coveredSurfaceIds: [...covered].sort(),
    uncoveredMandatorySurfaceIds: MANDATORY_ISTARA_SURFACE_IDS.filter((surfaceId) => !covered.has(surfaceId)),
    canonicalToolCount: toolSet.size,
    canonicalTools: [...toolSet].sort(),
    surfaces,
  };
}

export function renderSurfaceMapMarkdown(summary = buildSurfaceCoverageSummary()) {
  const lines = [
    "# Istara Surface Map",
    "",
    `Mapped surfaces: ${summary.mappedSurfaceCount}/${summary.mandatorySurfaceCount}.`,
    `Covered by runnable lab scenarios: ${summary.coveredSurfaceCount}/${summary.mandatorySurfaceCount}.`,
    `Canonical tools represented: ${summary.canonicalToolCount}.`,
    "",
    "This map combines the lab bridge and the replacement worktree's opt-in production hooks. It proves the Pi candidate can own the loop and canonical tool execution against Istara-shaped surfaces, and identifies which real FastAPI/service hooks are now wired versus which credentials, human gates, and broad harness fanout remain external.",
    "",
  ];

  for (const surface of summary.surfaces) {
    lines.push(`## ${surface.label}`);
    lines.push(`- id: ${surface.id}`);
    lines.push(`- category: ${surface.category}`);
    lines.push(`- bridge_status: ${surface.bridgeStatus}`);
    lines.push(`- covered: ${surface.covered ? "yes" : "no"}`);
    lines.push(`- scenarios: ${surface.candidateScenarios.join(", ") || "none"}`);
    lines.push(`- bridge_tools: ${surface.bridgeTools.join(", ")}`);
    lines.push(`- missing_bridge_tools: ${surface.missingBridgeTools.join(", ") || "none"}`);
    lines.push("- real_files:");
    for (const file of surface.realFiles) {
      lines.push(`  - ${file.path}:${file.line} - ${file.evidence}`);
    }
    lines.push("- real_tests:");
    for (const test of surface.realTests) {
      lines.push(`  - ${test}`);
    }
    lines.push("- production_gaps:");
    for (const gap of surface.productionGaps) {
      lines.push(`  - ${gap.reason} (${gap.files.join(", ")})`);
    }
    lines.push("");
  }

  return `${lines.join("\n")}\n`;
}
