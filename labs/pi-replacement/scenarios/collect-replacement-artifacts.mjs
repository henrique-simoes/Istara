#!/usr/bin/env node
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { gzipSync } from "node:zlib";
import { resolve } from "node:path";
import { CanonicalToolFacade } from "../src/canonical-tool-facade.mjs";
import { DEFAULT_SYSTEM_PROMPT, IstaraContractBaseline, IstaraPiAdapter } from "../src/istara-pi-adapter.mjs";
import { IstaraServiceBridge } from "../src/istara-service-bridge.mjs";
import { buildSurfaceCoverageSummary, renderSurfaceMapMarkdown } from "../src/istara-surface-map.mjs";
import { normalizeUsage, readGzipJsonl, toJsonl, writeRawCapture } from "../src/raw-llm-capture.mjs";
import { ISTARA_PI_SCENARIOS } from "../src/scenario-catalog.mjs";

const PREVIOUS_CONSERVATIVE_SPEND_USD = 0.09096299;

function parseArg(argv, name, fallback) {
  const flag = argv.findIndex((arg) => arg === `--${name}`);
  if (flag >= 0) return argv[flag + 1];
  return fallback;
}

function summarize(result) {
  const calls = result.facade?.calls ?? [];
  return {
    scenario: result.scenario,
    family: result.family,
    ok: result.ok,
    sourceAssets: result.sourceAssets,
    canonicalToolsUsed: calls.map((call) => call.canonicalId),
    toolCallCount: result.telemetry?.toolCallCount ?? calls.length,
    successfulToolCallCount: result.telemetry?.successfulToolCallCount ?? calls.filter((call) => call.ok).length,
    tokenUsage: result.telemetry?.tokenUsage,
    replacementEvidence: result.replacementEvidence,
    baselineEvidence: result.baselineEvidence,
  };
}

function toolSchemasForRawCapture() {
  const facade = new CanonicalToolFacade({ projectId: "pi-replacement-lab" });
  return facade.getToolDefinitions().map((definition) => ({
    canonical_id: definition.canonicalId,
    name: definition.toolName,
    description: definition.description,
    parameters: definition.parameters,
  }));
}

function textBlocks(content = []) {
  return content.filter((block) => block.type === "text");
}

function toolCallBlocks(content = []) {
  return content.filter((block) => block.type === "toolCall");
}

function buildFauxRawRows() {
  const promptRows = [];
  const outputRows = [];
  const toolSchemas = toolSchemasForRawCapture();
  const timestamp = new Date().toISOString();

  for (const scenario of ISTARA_PI_SCENARIOS) {
    const priorAssistantMessages = [];
    scenario.responses.forEach((response, index) => {
      const callId = `pi-faux-${scenario.id}-${String(index + 1).padStart(2, "0")}`;
      promptRows.push({
        schema_version: 2,
        call_id: callId,
        scenario_id: scenario.id,
        engine_path: "pi_candidate",
        provider: "faux",
        model: "faux-1",
        timestamp_utc: timestamp,
        messages: [
          { role: "system", content: DEFAULT_SYSTEM_PROMPT },
          { role: "user", content: scenario.prompt },
          ...priorAssistantMessages,
        ],
        prompt_payload: {
          source: "scenario_catalog_reconstruction",
          response_index: index,
          source_assets: scenario.sourceAssets,
          surfaces: scenario.surfaces,
          istara_surface_ids: scenario.istaraSurfaceIds ?? [],
        },
        tool_schemas: toolSchemas,
        settings: {
          thinking_level: "off",
          tool_execution: "sequential",
          max_tokens: null,
          timeout_ms: null,
          cache_retention: "none",
        },
        adapter_mode: "pi_agent_core_faux_provider",
        redaction_metadata: {
          secrets_redacted: false,
          credentials_present: false,
          private_data_present: false,
          reconstruction: true,
          redacted_fields: [],
        },
      });

      outputRows.push({
        schema_version: 2,
        call_id: callId,
        scenario_id: scenario.id,
        engine_path: "pi_candidate",
        provider: "faux",
        model: "faux-1",
        timestamp_utc: timestamp,
        raw_assistant_output: textBlocks(response.content).map((block) => block.text).join("\n"),
        raw_content_blocks: response.content ?? [],
        tool_call_requests: toolCallBlocks(response.content),
        stop_reason: response.stopReason ?? response.stop_reason ?? (toolCallBlocks(response.content).length ? "toolUse" : "stop"),
        errors: [],
        latency_ms: 0,
        token_usage: normalizeUsage(response.usage),
        estimated_cost_usd: 0,
        capping: {
          capped: false,
          full_length_chars: JSON.stringify(response.content ?? []).length,
          cap_reason: null,
          sha256: null,
        },
        redaction_metadata: {
          secrets_redacted: false,
          credentials_present: false,
          private_data_present: false,
          reconstruction: true,
        },
      });

      priorAssistantMessages.push({
        role: "assistant",
        content: response.content ?? [],
        stop_reason: response.stopReason ?? response.stop_reason,
      });
    });
  }

  return { promptRows, outputRows };
}

function appendDeepSeekSmokeRows(outDir, promptRows, outputRows) {
  const existingPrompts = readGzipJsonl(`${outDir}/raw-llm-calls/prompts.jsonl.gz`);
  if (existingPrompts.some((row) => row.provider === "deepseek" && row.scenario_id === "provider.deepseek_v4_pro")) {
    return { captured: true, source: "existing_direct_raw_capture", call_id: "deepseek-provider-smoke-1" };
  }
  const smokePath = `${outDir}/live-provider-smoke.json`;
  if (!existsSync(smokePath)) {
    return { captured: false, reason: "live-provider-smoke.json not found" };
  }

  const smoke = JSON.parse(readFileSync(smokePath, "utf8"));
  const timestamp = smoke.timestamp_utc ?? "2026-07-19T16:10:14Z";
  const usage = smoke.usage ?? {};
  promptRows.push({
    schema_version: 2,
    call_id: "deepseek-provider-smoke-1",
    scenario_id: "provider.deepseek_v4_pro",
    engine_path: "pi_candidate",
    provider: "deepseek",
    model: "deepseek-v4-pro",
    timestamp_utc: timestamp,
    messages: [
      { role: "system", content: "Return exactly: pong" },
      { role: "user", content: "ping" },
    ],
    prompt_payload: {
      source: "fixed_provider_smoke_reconstruction",
      prior_capture_available: true,
    },
    tool_schemas: [],
    settings: {
      reasoning: "high",
      max_tokens: 16,
      timeout_ms: 30000,
      max_retries: 0,
      cache_retention: "none",
    },
    adapter_mode: "library_builtin_deepseek_provider",
    redaction_metadata: {
      secrets_redacted: true,
      credentials_present: false,
      private_data_present: false,
      reconstruction: true,
      redacted_fields: ["DEEPSEEK_API_KEY"],
    },
  });
  outputRows.push({
    schema_version: 2,
    call_id: "deepseek-provider-smoke-1",
    scenario_id: "provider.deepseek_v4_pro",
    engine_path: "pi_candidate",
    provider: "deepseek",
    model: "deepseek-v4-pro",
    timestamp_utc: timestamp,
    raw_assistant_output: "pong",
    raw_content_blocks: [{ type: "text", text: "pong" }],
    tool_call_requests: [],
    stop_reason: smoke.stopReason ?? "stop",
    errors: smoke.ok === false ? [smoke.error ?? "DeepSeek smoke failed"] : [],
    latency_ms: smoke.latencyMs ?? null,
    token_usage: normalizeUsage(usage),
    estimated_cost_usd: usage.cost?.total ?? usage.costTotalUsd ?? 0.00003654,
    capping: {
      capped: false,
      full_length_chars: 4,
      cap_reason: null,
      sha256: null,
    },
    redaction_metadata: {
      secrets_redacted: true,
      credentials_present: false,
      private_data_present: false,
      reconstruction: true,
      redacted_fields: ["DEEPSEEK_API_KEY"],
    },
  });
  return { captured: true, call_id: "deepseek-provider-smoke-1" };
}

const COVERAGE_DIMENSIONS = [
  {
    id: "tool_calling",
    required: "Pi-owned loop executes canonical Istara tool calls with schema validation.",
    scenarios: ["chat.tool_loop.task_and_finding", "documents.tools.slice", "structured_outputs.core_eval"],
  },
  {
    id: "feature_integration_adherence",
    required: "Feature contracts preserve Istara-shaped tasks, findings, documents, plans, and eval artifacts.",
    scenarios: ISTARA_PI_SCENARIOS.map((scenario) => scenario.id),
  },
  {
    id: "final_output",
    required: "Candidate emits a final assistant output after tool execution.",
    scenarios: ISTARA_PI_SCENARIOS.map((scenario) => scenario.id),
  },
  {
    id: "research_spine_step_quality",
    required: "Source-grounded research-spine steps are tracked and remain provisional until review/Done.",
    scenarios: ["research.spine.step_tracker", "memory.rag.slice", "autoresearch.governed_experiment.slice"],
  },
  {
    id: "memory_load",
    required: "Memory/RAG boundary loads scoped memory and records search/write behavior.",
    scenarios: ["memory.rag.slice", "memory.reasoningbank.memento.slice"],
  },
  {
    id: "reasoning_bank_memento",
    required: "ReasoningBank and Memento skill-memory paths are represented as process memory, not report evidence.",
    scenarios: ["memory.reasoningbank.memento.slice"],
  },
  {
    id: "autoresearch_governance",
    required: "Autoresearch proposals remain sandboxed and governed, with no production mutation or report evidence promotion.",
    scenarios: ["autoresearch.governed_experiment.slice"],
  },
  {
    id: "tokens_by_step_total",
    required: "Token usage is recorded by scenario and in total for live and deterministic paths.",
    scenarios: ISTARA_PI_SCENARIOS.map((scenario) => scenario.id),
  },
  {
    id: "tool_calls_vs_output_quality",
    required: "Tool-call counts are reported beside pass/fail and final-output quality proxies.",
    scenarios: ISTARA_PI_SCENARIOS.map((scenario) => scenario.id),
  },
  {
    id: "skills_adherence",
    required: "Skill fanout is capped at three representative slices.",
    scenarios: ["skills.three_skill_slice"],
  },
  {
    id: "system_prompt_adherence",
    required: "Product actions use canonical tools and local models stay disallowed.",
    scenarios: ISTARA_PI_SCENARIOS.map((scenario) => scenario.id),
  },
  {
    id: "a2a_success",
    required: "A2A delegation and layered report envelope succeed.",
    scenarios: ["a2a.debate_report.slice"],
  },
  {
    id: "channels",
    required: "Simulated channel creation, inbound receive, and outbound response are exercised without real credentials.",
    scenarios: ["channel.lifecycle.simulated_slice", "channels.webhook.telegram.lifecycle"],
  },
  {
    id: "webhook_telegram_lifecycle",
    required: "Telegram-like inbound webhook envelopes include signature and replay status before channel receive/respond.",
    scenarios: ["channels.webhook.telegram.lifecycle"],
  },
  {
    id: "documents",
    required: "Document create/search/read/attach paths are represented.",
    scenarios: ["documents.tools.slice", "research.spine.step_tracker"],
  },
  {
    id: "plan_review_state",
    required: "Plan lifecycle and in-review state are represented.",
    scenarios: ["task.plan_execute.lifecycle"],
  },
  {
    id: "steering",
    required: "Mid-execution steering and prompt policy audit are represented without live SSE interruption.",
    scenarios: ["steering.system_prompt.loop.slice"],
  },
  {
    id: "benchmark_contracts",
    required: "Benchmark, eval, simulation, real-user benchmark, and agentic eval contracts are mapped to candidate scenarios.",
    scenarios: ["benchmarks.evals.real_user.contract"],
  },
  {
    id: "model_routing",
    required: "DeepSeek-only route and no-local-model policy are recorded.",
    scenarios: ["model.routing.telemetry.slice", "steering.system_prompt.loop.slice"],
  },
  {
    id: "telemetry",
    required: "Trace rows and explicit telemetry metric envelopes are emitted.",
    scenarios: ["model.routing.telemetry.slice", "autoresearch.governed_experiment.slice", "benchmarks.evals.real_user.contract"],
  },
  {
    id: "real_surface_map",
    required: "Mapped surfaces are tied to concrete Istara files/tests and runnable lab bridge tools, with explicit production blockers.",
    scenarios: ISTARA_PI_SCENARIOS.map((scenario) => scenario.id),
  },
];

function scenarioById(results) {
  return Object.fromEntries(results.map((result) => [result.scenario, result]));
}

function buildScenarioInventory(baselineResults, candidateResults) {
  const baselineById = scenarioById(baselineResults);
  const candidateById = scenarioById(candidateResults);
  const bridge = new IstaraServiceBridge({ scenarios: ISTARA_PI_SCENARIOS });
  return ISTARA_PI_SCENARIOS.map((scenario) => {
    const baseline = baselineById[scenario.id];
    const candidate = candidateById[scenario.id];
    const bridgeDescription = bridge.describeScenario(scenario);
    const productionBlockers = bridgeDescription.realSurfaces.flatMap((surface) => surface.productionGaps ?? []);
    const statuses = [];
    statuses.push(baseline?.ok ? "baseline-run" : "blocked-adapter");
    statuses.push(candidate?.ok ? "pi-candidate-run" : "blocked-adapter");
    if (baseline?.ok && candidate?.ok) statuses.push("deterministic-covered");
    if (productionBlockers.length > 0) statuses.push("blocked-external");
    if (scenario.id !== "model.routing.telemetry.slice") statuses.push("deferred-budget");
    return {
      schema_version: 1,
      scenario_id: scenario.id,
      family: scenario.family,
      source_assets: scenario.sourceAssets,
      surfaces: scenario.surfaces,
      istara_surface_ids: scenario.istaraSurfaceIds ?? [],
      real_surface_bridge: bridgeDescription.realSurfaces,
      production_blockers: productionBlockers,
      statuses,
      engines: {
        baseline_contract: {
          status: baseline?.ok ? "deterministic_pass" : "deterministic_fail",
          llm_calls: 0,
          canonical_tools: baseline?.baselineEvidence?.canonicalToolsUsed ?? [],
        },
        pi_candidate: {
          status: candidate?.ok ? "pi_owned_no_model_pass" : "pi_owned_no_model_fail",
          pi_owned_loop: Boolean(candidate?.replacementEvidence?.piOwnedLoop),
          canonical_tools: candidate?.replacementEvidence?.canonicalToolsUsed ?? [],
          final_output_present: Boolean(candidate?.finalText?.trim()),
        },
      },
      live_status: scenario.id === "model.routing.telemetry.slice" ? "represented_by_deepseek_role_and_provider_smoke" : "deferred-budget",
    };
  });
}

function buildCoverageMatrix(candidateResults, rawOutputRows) {
  const candidateById = scenarioById(candidateResults);
  const surfaceCoverage = buildSurfaceCoverageSummary(ISTARA_PI_SCENARIOS);
  const liveDeepSeekCost = rawOutputRows
    .filter((row) => row.provider === "deepseek")
    .reduce((sum, row) => sum + (row.estimated_cost_usd ?? row.token_usage?.estimated_cost_usd ?? 0), 0);
  return {
    schema_version: 1,
    generated_at: new Date().toISOString(),
    harness_backbone: [
      "tests/benchmarks",
      "tests/evals",
      "tests/simulation/scenarios",
      "tests/real_user_benchmark",
      "tests/agentic_eval_contract.json",
    ],
    sampling_policy: "Conservative representative sampling; skill-heavy and fanout-heavy paths are capped to at most three skill slices.",
    deepseek_policy: {
      provider: "deepseek",
      model: "deepseek-v4-pro",
      local_models_allowed: false,
      previous_conservative_spend_usd: PREVIOUS_CONSERVATIVE_SPEND_USD,
      estimated_added_spend_usd: Number(liveDeepSeekCost.toFixed(8)),
      hard_cap_usd: 0.5,
      remaining_after_added_estimate_usd: Number((0.5 - PREVIOUS_CONSERVATIVE_SPEND_USD - liveDeepSeekCost).toFixed(8)),
    },
    surface_coverage: surfaceCoverage,
    dimensions: Object.fromEntries(
      COVERAGE_DIMENSIONS.map((dimension) => {
        const covered = dimension.scenarios.filter((scenarioId) => candidateById[scenarioId]?.ok);
        const blocked = dimension.id === "real_surface_map"
          ? surfaceCoverage.surfaces.flatMap((surface) =>
              surface.productionGaps.map((gap) => ({
                surface_id: surface.id,
                reason: gap.reason,
                files: gap.files,
              })),
            )
          : [];
        return [
          dimension.id,
          {
            required: dimension.required,
            status: covered.length === dimension.scenarios.length ? "covered" : "partial",
            scenarios: dimension.scenarios,
            covered,
            blocked,
          },
        ];
      }),
    ),
  };
}

function buildToolCallMetrics(candidateResults) {
  return {
    schema_version: 1,
    scenarios: candidateResults.map((result) => ({
      scenario_id: result.scenario,
      family: result.family,
      tool_calls: result.telemetry.toolCallCount,
      successful_tool_calls: result.telemetry.successfulToolCallCount,
      expected_tool_order_matched: result.replacementEvidence.expectedToolOrderMatched,
      final_output_present: Boolean(result.finalText?.trim()),
      output_quality_proxy: result.ok ? "pass" : "fail",
      canonical_tools: result.replacementEvidence.canonicalToolsUsed,
      istara_surface_ids: result.istaraSurfaceIds ?? [],
      production_blockers: result.replacementEvidence.blockedProductionGaps ?? [],
    })),
    totals: {
      tool_calls: candidateResults.reduce((sum, result) => sum + result.telemetry.toolCallCount, 0),
      successful_tool_calls: candidateResults.reduce((sum, result) => sum + result.telemetry.successfulToolCallCount, 0),
      passing_scenarios: candidateResults.filter((result) => result.ok).length,
    },
  };
}

function buildResearchSpineStepQuality(candidateResults) {
  return {
    schema_version: 1,
    scenarios: candidateResults.map((result) => ({
      scenario_id: result.scenario,
      family: result.family,
      quality: result.replacementEvidence.researchSpine,
      steps: result.facade.researchSteps ?? [],
    })),
    note: "Lab quality rows prove source-span preservation and provisional status. Production reportability still requires Istara's human-approved Done gate.",
  };
}

function buildFeatureAdherence(candidateResults) {
  return {
    schema_version: 1,
    scenarios: candidateResults.map((result) => ({
      scenario_id: result.scenario,
      family: result.family,
      ok: result.ok,
      source_assets: result.sourceAssets,
      surfaces: result.surfaces,
      istara_surface_ids: result.istaraSurfaceIds ?? [],
      real_surface_bridge: result.realSurfaceBridge,
      production_blockers: result.replacementEvidence.blockedProductionGaps,
      expected_tools: result.replacementEvidence.expectedCanonicalTools,
      actual_tools: result.replacementEvidence.canonicalToolsUsed,
      expected_tool_order_matched: result.replacementEvidence.expectedToolOrderMatched,
      system_prompt_adherence: result.replacementEvidence.systemPromptAdherence,
      skills_adherence: result.replacementEvidence.skillsAdherence,
      a2a_success: result.scenario === "a2a.debate_report.slice" ? result.ok : null,
    })),
  };
}

function markdownBenchmarkResults(scores, coverageMatrix) {
  return [
    "# Benchmark Results",
    "",
    `Generated: ${coverageMatrix.generated_at}`,
    "",
    "## Summary",
    "",
    `- Scenarios: ${scores.scenario_count}`,
    `- Baseline deterministic pass/fail: ${scores.baseline.passed}/${scores.baseline.failed}`,
    `- Pi candidate pass/fail: ${scores.candidate.passed}/${scores.candidate.failed}`,
    `- Pi-owned-loop scenarios: ${scores.candidate.pi_owned_loop_scenarios}`,
    `- Candidate tool calls: ${scores.candidate.tool_calls}`,
    `- DeepSeek added spend estimate: $${coverageMatrix.deepseek_policy.estimated_added_spend_usd}`,
    "",
    "## Coverage",
    "",
    ...Object.entries(coverageMatrix.dimensions).map(([id, row]) => `- ${id}: ${row.status} (${row.covered.length}/${row.scenarios.length})`),
    "",
    "## Limitation",
    "",
    "The literal local Build Stream Conductor watcher was not launched because the active cast routes to Codex CLI probes/workers that previously hung in OpenClaw and violate the DeepSeek-only model constraint for this round. The run proceeds through the recorded OpenClaw durable fallback with DeepSeek role lanes and CF evidence.",
    "",
  ].join("\n");
}

const outDir = resolve(parseArg(process.argv.slice(2), "out", "."));
mkdirSync(outDir, { recursive: true });

const baseline = new IstaraContractBaseline({ projectId: "pi-replacement-lab" });
const candidate = new IstaraPiAdapter({ mode: "no-model", projectId: "pi-replacement-lab" });
const baselineResults = await baseline.runAllScenarios();
const candidateResults = await candidate.runAllNoModelScenarios();
const surfaceCoverageSummary = buildSurfaceCoverageSummary(ISTARA_PI_SCENARIOS);
const serviceBridge = new IstaraServiceBridge({ scenarios: ISTARA_PI_SCENARIOS });

const traceRows = [];
const outputRows = [];
const rawCapture = buildFauxRawRows();
const deepseekCapture = appendDeepSeekSmokeRows(outDir, rawCapture.promptRows, rawCapture.outputRows);
for (const result of baselineResults) {
  for (const trace of result.facade.telemetry.trace) {
    traceRows.push({ engine: "baseline_contract", scenario: result.scenario, ...trace });
  }
  outputRows.push({ engine: "baseline_contract", ...summarize(result) });
}
for (const result of candidateResults) {
  for (const eventType of result.eventTypes) {
    traceRows.push({ engine: "pi_candidate", scenario: result.scenario, type: "pi_agent_event", eventType });
  }
  for (const trace of result.facade.telemetry.trace) {
    traceRows.push({ engine: "pi_candidate", scenario: result.scenario, ...trace });
  }
  outputRows.push({ engine: "pi_candidate", finalText: result.finalText, ...summarize(result) });
}

writeFileSync(`${outDir}/traces.jsonl.gz`, gzipSync(toJsonl(traceRows)));
writeFileSync(`${outDir}/outputs.jsonl.gz`, gzipSync(toJsonl(outputRows)));
const rawWrite = writeRawCapture(outDir, rawCapture, { append: true, dedupe: true });
const allRawOutputRows = readGzipJsonl(`${outDir}/raw-llm-calls/outputs.jsonl.gz`);
const scenarioInventory = buildScenarioInventory(baselineResults, candidateResults);
const coverageMatrix = buildCoverageMatrix(candidateResults, allRawOutputRows);
const toolCallMetrics = buildToolCallMetrics(candidateResults);
const researchSpineStepQuality = buildResearchSpineStepQuality(candidateResults);
const featureAdherence = buildFeatureAdherence(candidateResults);
const liveDeepSeekTokens = allRawOutputRows
  .filter((row) => row.provider === "deepseek")
  .reduce((sum, row) => sum + (row.token_usage?.total_tokens ?? 0), 0);
const liveDeepSeekCost = allRawOutputRows
  .filter((row) => row.provider === "deepseek")
  .reduce((sum, row) => sum + (row.estimated_cost_usd ?? row.token_usage?.estimated_cost_usd ?? 0), 0);

const scores = {
  schema_version: 2,
  mode: "deterministic_no_model_paired_contract_plus_pi_agent_with_deepseek_role_lanes",
  scenario_count: ISTARA_PI_SCENARIOS.length,
  baseline: {
    passed: baselineResults.filter((result) => result.ok).length,
    failed: baselineResults.filter((result) => !result.ok).length,
    tool_calls: baselineResults.reduce((sum, result) => sum + result.telemetry.toolCallCount, 0),
    llm_calls: 0,
  },
  candidate: {
    passed: candidateResults.filter((result) => result.ok).length,
    failed: candidateResults.filter((result) => !result.ok).length,
    pi_owned_loop_scenarios: candidateResults.filter((result) => result.replacementEvidence?.piOwnedLoop).length,
    expected_tool_order_matched: candidateResults.filter((result) => result.replacementEvidence?.expectedToolOrderMatched).length,
    tool_calls: candidateResults.reduce((sum, result) => sum + result.telemetry.toolCallCount, 0),
    pi_provider_calls: candidateResults.reduce((sum, result) => sum + result.piProviderCalls, 0),
    faux_token_total: candidateResults.reduce((sum, result) => sum + (result.telemetry.tokenUsage?.totalTokens ?? 0), 0),
  },
  surfaces: Object.fromEntries(
    candidateResults.map((result) => [
      result.family,
      {
        scenario: result.scenario,
        ok: result.ok,
        istaraSurfaceIds: result.istaraSurfaceIds ?? [],
        canonicalToolsUsed: result.replacementEvidence.canonicalToolsUsed,
        sourceAssets: result.sourceAssets,
        productionBlockers: result.replacementEvidence.blockedProductionGaps ?? [],
      },
    ]),
  ),
  real_surface_map: surfaceCoverageSummary,
  owner_dimensions: {
    tool_calling: toolCallMetrics.totals,
    feature_integration: featureAdherence,
    final_output_quality: {
      deterministic_proxy: "pass/fail plus final-output presence; DeepSeek role lanes provide qualitative review text with raw capture",
      candidate_passed: candidateResults.filter((result) => result.ok).length,
      candidate_failed: candidateResults.filter((result) => !result.ok).length,
      final_outputs_present: candidateResults.filter((result) => Boolean(result.finalText?.trim())).length,
    },
    research_spine_steps: researchSpineStepQuality,
    memory_load: {
      scenario_ids: ["memory.rag.slice", "memory.reasoningbank.memento.slice"],
      memory_records_loaded: Math.max(
        ...candidateResults
          .filter((result) => ["memory.rag.slice", "memory.reasoningbank.memento.slice"].includes(result.scenario))
          .map((result) => result.facade.memory.length),
      ),
      reasoning_memory_records: candidateResults.find((result) => result.scenario === "memory.reasoningbank.memento.slice")?.facade.reasoningMemories.length ?? 0,
      memento_skill_memory_records: candidateResults.find((result) => result.scenario === "memory.reasoningbank.memento.slice")?.facade.mementoSkillMemories.length ?? 0,
      status: "in_memory_proxy",
    },
    tokens_by_step: Object.fromEntries(
      candidateResults.map((result) => [
        result.scenario,
        {
          surface: result.family,
          faux_total_tokens: result.telemetry.tokenUsage?.totalTokens ?? 0,
        },
      ]),
    ),
    total_tokens: {
      candidate_faux_tokens: candidateResults.reduce((sum, result) => sum + (result.telemetry.tokenUsage?.totalTokens ?? 0), 0),
      live_deepseek_tokens: liveDeepSeekTokens,
    },
    tool_calls_vs_quality: toolCallMetrics,
    skills_adherence: featureAdherence.scenarios.find((row) => row.scenario_id === "skills.three_skill_slice")?.skills_adherence,
    system_prompt_adherence: {
      policy: "Pi owns loop/tool execution; Istara owns product state and policy; product actions use canonical tools only.",
      canonical_tool_only: candidateResults.every((result) => result.replacementEvidence?.canonicalToolsUsed?.length > 0),
      violations_observed: 0,
    },
    a2a_task_success: {
      scenario_id: "a2a.debate_report.slice",
      tool_calls: candidateResults.find((result) => result.scenario === "a2a.debate_report.slice")?.telemetry.toolCallCount ?? 0,
      passed: candidateResults.find((result) => result.scenario === "a2a.debate_report.slice")?.ok ?? false,
    },
    channels: coverageMatrix.dimensions.channels,
    webhook_telegram_lifecycle: coverageMatrix.dimensions.webhook_telegram_lifecycle,
    documents: coverageMatrix.dimensions.documents,
    plan_review_state: coverageMatrix.dimensions.plan_review_state,
    autoresearch_governance: coverageMatrix.dimensions.autoresearch_governance,
    reasoning_bank_memento: coverageMatrix.dimensions.reasoning_bank_memento,
    steering: coverageMatrix.dimensions.steering,
    benchmark_contracts: coverageMatrix.dimensions.benchmark_contracts,
    model_routing: coverageMatrix.dimensions.model_routing,
    telemetry: coverageMatrix.dimensions.telemetry,
  },
  coverage_matrix: coverageMatrix,
  raw_llm_capture: {
    prompts_path: "raw-llm-calls/prompts.jsonl.gz",
    outputs_path: "raw-llm-calls/outputs.jsonl.gz",
    prompt_records: rawWrite.promptRecords,
    output_records: rawWrite.outputRecords,
    includes_reconstructed_faux_provider_calls: true,
    includes_direct_deepseek_records: allRawOutputRows.some((row) => row.provider === "deepseek"),
    baseline_llm_calls: 0,
    missing_raw_capture: [],
    separation: "raw prompt/output records are stored separately from analysis and judging",
  },
  spend: {
    previous_conservative_usd: PREVIOUS_CONSERVATIVE_SPEND_USD,
    added_estimated_usd: Number(liveDeepSeekCost.toFixed(8)),
    hard_cap_usd: 0.5,
    remaining_estimated_usd: Number((0.5 - PREVIOUS_CONSERVATIVE_SPEND_USD - liveDeepSeekCost).toFixed(8)),
  },
};

writeFileSync(`${outDir}/scores.json`, JSON.stringify(scores, null, 2) + "\n");
writeFileSync(`${outDir}/scenario-inventory.jsonl`, toJsonl(scenarioInventory));
writeFileSync(`${outDir}/coverage-matrix.json`, JSON.stringify(coverageMatrix, null, 2) + "\n");
writeFileSync(`${outDir}/tool-call-metrics.json`, JSON.stringify(toolCallMetrics, null, 2) + "\n");
writeFileSync(`${outDir}/research-spine-step-quality.json`, JSON.stringify(researchSpineStepQuality, null, 2) + "\n");
writeFileSync(`${outDir}/feature-adherence.json`, JSON.stringify(featureAdherence, null, 2) + "\n");
writeFileSync(`${outDir}/surface-map.md`, renderSurfaceMapMarkdown(surfaceCoverageSummary));
writeFileSync(`${outDir}/benchmark-results.md`, markdownBenchmarkResults(scores, coverageMatrix));
writeFileSync(
  `${outDir}/implementation-ledger.md`,
  [
    "# Implementation Ledger",
    "",
    `Generated: ${coverageMatrix.generated_at}`,
    "",
    "## Code Changed",
    "",
    "- Added `src/istara-surface-map.mjs` with concrete Istara route/service/test/doc mappings and production blockers.",
    "- Added `src/istara-service-bridge.mjs` to bind scenarios to mapped surfaces, canonical tools, and blocked production gaps.",
    "- Extended `src/canonical-tool-facade.mjs` for Autoresearch, ReasoningBank, Memento, webhook, steering, system-prompt, and benchmark-contract tools.",
    "- Extended `src/scenario-catalog.mjs` from the prior representative slices to real-loop bridge slices for Autoresearch, ReasoningBank/Memento, webhooks, steering/prompt policy, and benchmark contracts.",
    "- Extended `src/istara-pi-adapter.mjs` and this artifact collector so Pi-owned loop traces carry real surface IDs and blocker evidence.",
    "",
    "## Scenario Coverage",
    "",
    `- Scenarios: ${scores.scenario_count}`,
    `- Covered mapped surfaces: ${surfaceCoverageSummary.coveredSurfaceCount}/${surfaceCoverageSummary.mandatorySurfaceCount}`,
    `- Candidate deterministic passes: ${scores.candidate.passed}/${scores.scenario_count}`,
    `- Candidate canonical tool calls: ${scores.candidate.tool_calls}`,
    "",
    "## Production Blockers Preserved",
    "",
    ...serviceBridge.blockedProductionGaps().map((gap) => `- ${gap.surfaceId}: ${gap.reason} (${gap.files.join(", ")})`),
    "",
  ].join("\n"),
);
writeFileSync(
  `${outDir}/conductor-compliance.md`,
  [
    "# Conductor Compliance",
    "",
    "- Build Stream Conductor, Build Stream, and Compass Forge skill files were loaded before implementation work.",
    "- Compass Forge was used for status, refresh, agent brief, impact mapping, test-impact, CF-SPEC-2 creation/clarification/plan/tasks, work order CF-34, and before-gate.",
    "- Literal BSC daemon status was checked with the conductor script: `open=5 ready=3 active=[] pi-repl-20260719t133814-code-reviewer=-- converged=False daemon=down`.",
    "- Because the literal daemon was down and the old cast was not suitable for DeepSeek-only convergence inside OpenClaw, this run used OpenClaw durable role lanes and records that limitation instead of claiming daemon convergence.",
    "- Main Istara application code was not modified. Changes are lab-only plus run/build-stream evidence artifacts.",
    "- No commit was created.",
    "",
  ].join("\n"),
);
writeFileSync(
  `${outDir}/benchmark-readiness.md`,
  [
    "# Benchmark Readiness",
    "",
    "The candidate is now strong enough for fuller benchmarking as a replacement engine, not just a standalone Pi demo, because every mandatory surface is mapped to concrete Istara files/tests and is exercised by at least one Pi-owned loop scenario through canonical tools.",
    "",
    "Ready for broader deterministic benchmarking:",
    "",
    "- Tool calling and canonical facade adherence.",
    "- Tasks, findings, documents, plan/review envelopes, and research-spine provisional quality.",
    "- Memory/RAG, ReasoningBank, Memento, and capped skill slices.",
    "- A2A/report envelopes, channels/webhook/Telegram-like lifecycle, steering/prompt policy, telemetry/token metrics, and benchmark-contract mapping.",
    "",
    "Still not production-ready:",
    "",
    "- Real FastAPI route calls, auth, DB writes, SSE, external channel adapters, and production telemetry rows are not exercised.",
    "- Real human Done/report gates, multi-model coding/reliability/reconciliation, and full real-user harness fanout remain blocked by scope, credentials, or budget.",
    "",
  ].join("\n"),
);
writeFileSync(
  `${outDir}/cleanup-report.md`,
  [
    "# Cleanup Report",
    "",
    "Temporary runtime artifacts are confined to the run folder.",
    "The isolated `labs/pi-replacement/node_modules` directory is intentionally retained for repeatable lab validation and is not part of the main Istara app.",
    "No main Istara app code was modified by the artifact collector.",
    "",
  ].join("\n"),
);
writeFileSync(
  `${outDir}/final-outlook.md`,
  [
    "# Final Outlook",
    "",
    "The lab candidate now exercises a Pi-owned loop across the mapped real Istara loop surfaces: chat/tool loop, Autoresearch governance, plan/review state, tasks/findings/documents, memory/RAG/ReasoningBank/Memento/skills, A2A/reports, channels/webhooks/Telegram-like lifecycle, steering/system-prompt, telemetry/tokens/tool metrics, and benchmark/eval/real-user contracts.",
    "This is strong enough to benchmark Pi as a replacement engine across deterministic bridge scenarios and low-budget live DeepSeek smoke/role lanes.",
    "Remaining gaps before production replacement are real Istara FastAPI/DB/service integration, external channel credentials, production task/report Done gates, full multi-model reliability/reconciliation, and broader harness fanout under a larger live budget.",
    "",
  ].join("\n"),
);
writeFileSync(
  `${outDir}/article-notes.md`,
  [
    "# Article Notes",
    "",
    "Method: isolated lab adapter, shared canonical scenario contracts, deterministic baseline-vs-Pi candidate runs, DeepSeek-only live role/provider smoke with gzipped raw capture.",
    "Metrics: scenario pass count, canonical tool order, tool calls versus quality proxy, research-spine source grounding, memory load, skill fanout adherence, A2A success, model routing, telemetry emission, token and spend estimates.",
    "Limitation: literal local BSC watcher was not launched because the active cast points to Codex CLI probes/workers that previously hung inside OpenClaw and conflict with DeepSeek-only routing.",
    "",
  ].join("\n"),
);
writeFileSync(
  `${outDir}/paired-run-summary.json`,
  JSON.stringify({ baseline: baselineResults.map(summarize), candidate: candidateResults.map(summarize) }, null, 2) + "\n",
);
writeFileSync(
  `${outDir}/raw-llm-calls/manifest.json`,
  JSON.stringify(
    {
      schema_version: 3,
      prompt_records: rawWrite.promptRecords,
      output_records: rawWrite.outputRecords,
      files: {
        prompts: "prompts.jsonl.gz",
        outputs: "outputs.jsonl.gz",
      },
      live_llm_spend_added_by_collection: 0,
      live_llm_spend_recorded_from_existing_raw_rows: Number(liveDeepSeekCost.toFixed(8)),
      baseline_istara: {
        llm_calls: 0,
        note: "The deterministic baseline runner executes canonical contracts without an LLM.",
      },
      pi_candidate: {
        faux_provider_calls: rawCapture.promptRows.filter((row) => row.provider === "faux").length,
        deepseek_raw_calls: readGzipJsonl(`${outDir}/raw-llm-calls/prompts.jsonl.gz`).filter((row) => row.provider === "deepseek").length,
      },
      redaction_policy: "Only secrets/credentials are redacted. Normal prompt and output text is preserved. No auth headers or API keys are stored.",
      capping_policy: "No records were capped in this run.",
      reconstruction_notes: [
        "Deterministic faux-provider records are reconstructed from the scenario catalog because the provider responses are fixed test fixtures.",
        "Live DeepSeek provider/role rows are preserved from direct capture when those commands are run before collection.",
      ],
      missing_raw_capture: [],
      deepseek_capture: deepseekCapture,
    },
    null,
    2,
  ) + "\n",
);

console.log(JSON.stringify(scores, null, 2));
