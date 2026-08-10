import { Agent } from "@earendil-works/pi-agent-core";
import {
  createModels,
  fauxProvider,
} from "@earendil-works/pi-ai";
import { deepseekProvider } from "@earendil-works/pi-ai/providers/deepseek";
import { spawnSync } from "node:child_process";
import { CanonicalToolFacade } from "./canonical-tool-facade.mjs";
import {
  buildOutputRecord,
  buildPromptRecord,
  estimateDeepSeekCostUsd,
  normalizeUsage,
  writeRawCapture,
} from "./raw-llm-capture.mjs";
import { IstaraServiceBridge } from "./istara-service-bridge.mjs";
import { buildSurfaceCoverageSummary } from "./istara-surface-map.mjs";
import { getScenarioDefinition, ISTARA_PI_SCENARIOS } from "./scenario-catalog.mjs";

export const DEFAULT_SYSTEM_PROMPT = [
  "You are running inside Istara as the candidate replacement agentic core.",
  "Pi owns the loop and tool execution.",
  "Istara owns projects, permissions, memory, tasks, findings, and telemetry policy.",
  "Use only canonical Istara tools for product actions.",
  "Research Spine artifacts remain provisional until source-grounded reliability, reconciliation, and human Done gates accept them.",
  "No local models are allowed in this lab candidate.",
].join("\n");

function textFromAssistant(message) {
  return (message?.content ?? [])
    .filter((block) => block.type === "text")
    .map((block) => block.text)
    .join("\n");
}

function usageOrZero(message) {
  return message?.usage ?? {
    input: 0,
    output: 0,
    cacheRead: 0,
    cacheWrite: 0,
    totalTokens: 0,
    cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
  };
}

function contentBlocks(message) {
  return message?.content ?? [];
}

function textBlocks(message) {
  return contentBlocks(message)
    .filter((block) => block.type === "text")
    .map((block) => block.text);
}

function toolCallBlocks(message) {
  return contentBlocks(message).filter((block) => block.type === "toolCall");
}

function scoreResearchSpine(facade) {
  const steps = facade.researchSteps ?? [];
  const grounded = steps.filter((step) => ["source_grounded", "validated"].includes(step.grounding_status)).length;
  const validated = steps.filter((step) => step.grounding_status === "validated").length;
  const provisional = steps.filter((step) => step.grounding_status === "candidate_only").length;
  const qualityScores = steps.map((step) => step.quality_score).filter((score) => typeof score === "number");
  const averageQuality = qualityScores.length
    ? Number((qualityScores.reduce((sum, score) => sum + score, 0) / qualityScores.length).toFixed(3))
    : null;
  return {
    stepCount: steps.length,
    groundedStepCount: grounded,
    validatedStepCount: validated,
    provisionalStepCount: provisional,
    averageQuality,
    sourceSpanPreserved: steps.every((step) => !step.source_document_id || Boolean(step.source_span)),
    reportableDoneGate: false,
    doneGateReason: "Lab-only candidate records source-grounded/provisional spine steps but does not bypass Istara's human Done gate.",
  };
}

function scenarioQuality(result, scenario) {
  const canonicalTools = result.replacementEvidence?.canonicalToolsUsed ?? [];
  const expected = scenario.expectedCanonicalTools ?? [];
  const expectedMatched = result.replacementEvidence?.expectedToolOrderMatched ?? false;
  const toolAccuracy = expected.length
    ? Number((canonicalTools.filter((tool, index) => tool === expected[index]).length / expected.length).toFixed(3))
    : 1;
  return {
    finalOutputPresent: Boolean(result.finalText?.trim()),
    expectedToolOrderMatched: expectedMatched,
    toolNameAccuracy: toolAccuracy,
    featureAdherence: result.ok && expectedMatched,
  };
}

export function readDeepSeekKeyFromKeychain() {
  const result = spawnSync(
    "security",
    ["find-generic-password", "-a", "openclaw", "-s", "istara-pi-deepseek", "-w"],
    { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] },
  );
  if (result.status !== 0) {
    return undefined;
  }
  return result.stdout.trim() || undefined;
}

export class IstaraPiAdapter {
  constructor(options = {}) {
    this.mode = options.mode ?? "no-model";
    this.projectId = options.projectId ?? "lab-project";
    this.sessionId = options.sessionId ?? `istara-pi-${Date.now()}`;
    this.facade = options.facade ?? new CanonicalToolFacade({ projectId: this.projectId });
    this.events = [];
    this.models = createModels();
  }

  prepareRun(manifest = {}) {
    return {
      ok: true,
      adapter: "IstaraPiAdapter",
      adapterMode: this.mode === "deepseek" ? "library_builtin_deepseek_provider" : "pi_agent_core_faux_provider",
      piPackages: {
        "@earendil-works/pi-agent-core": "0.80.10",
        "@earendil-works/pi-ai": "0.80.10",
      },
      modelPolicy: {
        provider: this.mode === "deepseek" ? "deepseek" : "faux",
        model: this.mode === "deepseek" ? "deepseek-v4-pro" : "faux-1",
        localModelsAllowed: false,
      },
      harnessBackbone: [
        "tests/benchmarks",
        "tests/evals",
        "tests/simulation/scenarios",
        "tests/real_user_benchmark",
        "tests/agentic_eval_contract.json",
      ],
      surfaceCoverage: buildSurfaceCoverageSummary(ISTARA_PI_SCENARIOS),
      manifest,
    };
  }

  createNoModelAgent(scenario) {
    const faux = fauxProvider({ tokensPerSecond: 0 });
    faux.setResponses(scenario.responses);
    this.models.setProvider(faux.provider);
    const model = faux.getModel();
    const agent = new Agent({
      initialState: {
        systemPrompt: DEFAULT_SYSTEM_PROMPT,
        model,
        thinkingLevel: "off",
        tools: this.facade.toPiAgentTools(),
      },
      streamFn: this.models.streamSimple.bind(this.models),
      sessionId: this.sessionId,
      toolExecution: "sequential",
    });
    agent.subscribe((event) => {
      this.events.push({
        type: event.type,
        toolName: event.toolName,
        isError: event.isError,
        messageRole: event.message?.role,
      });
    });
    return { agent, faux };
  }

  async runNoModelScenario(scenarioId, promptOverride) {
    const scenario = getScenarioDefinition(scenarioId);
    const bridge = new IstaraServiceBridge({ facade: this.facade, scenarios: [scenario] });
    const { agent, faux } = this.createNoModelAgent(scenario);
    const started = Date.now();
    await agent.prompt(promptOverride ?? scenario.prompt);
    await agent.waitForIdle();
    const assistantMessages = agent.state.messages.filter((message) => message.role === "assistant");
    const finalAssistant = assistantMessages.at(-1);
    const facade = this.facade.snapshot();
    const canonicalToolsUsed = facade.calls.map((call) => call.canonicalId);
    const missingExpectedTools = scenario.expectedCanonicalTools.filter((tool, index) => canonicalToolsUsed[index] !== tool);
    const researchSpine = scoreResearchSpine(facade);
    return {
      ok: agent.state.errorMessage === undefined,
      scenario: scenario.id,
      family: scenario.family,
      sourceAssets: scenario.sourceAssets,
      surfaces: scenario.surfaces,
      istaraSurfaceIds: scenario.istaraSurfaceIds ?? [],
      realSurfaceBridge: bridge.describeScenario(scenario),
      replacementEvidence: {
        piOwnedLoop: true,
        canonicalToolsUsed,
        expectedCanonicalTools: scenario.expectedCanonicalTools,
        expectedToolOrderMatched: missingExpectedTools.length === 0,
        surfaceCoverage: bridge.coverageSummary([scenario]),
        blockedProductionGaps: bridge.blockedProductionGaps([scenario]),
        traceEmission: {
          piEvents: this.events.length,
          canonicalTraceRows: facade.telemetry.trace.length,
          rawCaptureRequiredForLiveCalls: true,
        },
        modelRouting: {
          recordedRoutes: facade.modelRoutes,
          deepseekOnlyPolicy: true,
          localModelsAllowed: false,
        },
        researchSpine,
        memoryLoad: {
          recordsAvailable: facade.memory.length,
          searchCalls: facade.calls.filter((call) => call.canonicalId === "memory.search").length,
          reasoningMemoryCount: facade.reasoningMemories.length,
          mementoSkillMemoryCount: facade.mementoSkillMemories.length,
        },
        skillsAdherence: {
          maxRepresentativeSkillSlices: 3,
          skillCalls: facade.skillRuns.length,
          adhered: facade.skillRuns.length <= 3,
        },
        systemPromptAdherence: {
          canonicalToolsOnly: facade.calls.every((call) => call.ok && call.canonicalId !== "unknown"),
          localModelsAllowed: false,
          policy: "Pi owns loop/tool execution; Istara owns product state and policy.",
          promptAudits: facade.systemPromptAudits,
          promptAuditPassed: facade.systemPromptAudits.every((audit) => audit.passed),
        },
        istaraProductStatePreserved: {
          projectId: this.projectId,
          taskCount: this.facade.tasks.length,
          findingCount: this.facade.findings.length,
          documentCount: this.facade.documents.length,
          memoryCount: this.facade.memory.length,
          channelCount: this.facade.channels.length,
          researchStepCount: this.facade.researchSteps.length,
          modelRouteCount: this.facade.modelRoutes.length,
          autoresearchExperimentCount: this.facade.autoresearchExperiments.length,
          reasoningMemoryCount: this.facade.reasoningMemories.length,
          mementoSkillMemoryCount: this.facade.mementoSkillMemories.length,
          webhookEventCount: this.facade.webhookEvents.length,
          steeringEventCount: this.facade.steeringEvents.length,
          benchmarkContractCount: this.facade.benchmarkContracts.length,
        },
      },
      finalText: textFromAssistant(finalAssistant),
      eventTypes: this.events.map((event) => event.type),
      piProviderCalls: faux.state.callCount,
      usage: usageOrZero(finalAssistant),
      telemetry: {
        latencyMs: Date.now() - started,
        piEventCount: this.events.length,
        toolCallCount: facade.telemetry.toolCallCount,
        successfulToolCallCount: facade.telemetry.successfulToolCallCount,
        tokenUsage: usageOrZero(finalAssistant),
        tokensByStep: {
          [scenario.id]: normalizeUsage(usageOrZero(finalAssistant)),
        },
        toolCallsVsQuality: {
          toolCallCount: facade.telemetry.toolCallCount,
          outputQualityProxy: scenarioQuality(
            {
              ok: agent.state.errorMessage === undefined,
              finalText: textFromAssistant(finalAssistant),
              replacementEvidence: {
                canonicalToolsUsed,
                expectedToolOrderMatched: missingExpectedTools.length === 0,
              },
            },
            scenario,
          ),
        },
      },
      facade,
    };
  }

  async runNoModelChatToolLoop(prompt) {
    return this.runNoModelScenario("chat.tool_loop.task_and_finding", prompt);
  }

  async runAllNoModelScenarios() {
    const results = [];
    for (const scenario of ISTARA_PI_SCENARIOS) {
      const adapter = new IstaraPiAdapter({
        mode: "no-model",
        projectId: this.projectId,
        sessionId: `${this.sessionId}-${scenario.id}`,
      });
      results.push(await adapter.runNoModelScenario(scenario.id));
    }
    return results;
  }

  async runDeepSeekProviderSmoke(options = {}) {
    const key = readDeepSeekKeyFromKeychain();
    const deepseekKeyPresent = Boolean(key);
    if (!deepseekKeyPresent) {
      return {
        ok: false,
        scenario: "provider.deepseek_v4_pro",
        deepseek_key_present: false,
        error: "DeepSeek key unavailable in macOS Keychain.",
      };
    }

    const started = Date.now();
    let response;
    const timestampUtc = new Date().toISOString();
    const messages = [{ role: "user", content: "ping", timestamp: Date.now() }];
    const systemPrompt = "Return exactly: pong";
    const settings = {
      reasoning: "high",
      maxTokens: 16,
      timeoutMs: 30000,
      maxRetries: 0,
      cacheRetention: "none",
    };
    try {
      process.env.DEEPSEEK_API_KEY = key;
      this.models.setProvider(deepseekProvider());
      const model = this.models.getModel("deepseek", "deepseek-v4-pro");
      if (!model) {
        return {
          ok: false,
          scenario: "provider.deepseek_v4_pro",
          deepseek_key_present: true,
          error: "Pi deepseekProvider() did not expose deepseek-v4-pro.",
        };
      }

      response = await this.models.completeSimple(
        model,
        {
          systemPrompt,
          messages,
        },
        settings,
      );
    } finally {
      delete process.env.DEEPSEEK_API_KEY;
    }

    const latencyMs = Date.now() - started;
    const usage = usageOrZero(response);
    const estimatedCostUsd = estimateDeepSeekCostUsd(usage);
    if (options.outDir) {
      const callId = options.callId ?? `deepseek-provider-smoke-${timestampUtc.replace(/[:.]/g, "-")}`;
      writeRawCapture(options.outDir, {
        promptRows: [
          buildPromptRecord({
            callId,
            scenarioId: "provider.deepseek_v4_pro",
            enginePath: "pi_candidate",
            provider: "deepseek",
            model: "deepseek-v4-pro",
            timestampUtc,
            systemPrompt,
            messages,
            settings,
            adapterMode: "library_builtin_deepseek_provider",
            redactionSummary: "DEEPSEEK_API_KEY omitted from prompt record; no prompt text redacted.",
          }),
        ],
        outputRows: [
          buildOutputRecord({
            callId,
            scenarioId: "provider.deepseek_v4_pro",
            enginePath: "pi_candidate",
            provider: "deepseek",
            model: "deepseek-v4-pro",
            timestampUtc,
            rawAssistantOutput: textBlocks(response).join("\n"),
            rawContentBlocks: contentBlocks(response),
            toolCallRequests: toolCallBlocks(response),
            stopReason: response.stopReason,
            errors: response.error ? [String(response.error)] : [],
            latencyMs,
            usage,
            estimatedCostUsd,
            redactionSummary: "DEEPSEEK_API_KEY omitted from output record; output text preserved.",
          }),
        ],
      });
    }

    return {
      ok: response.stopReason === "stop",
      scenario: "provider.deepseek_v4_pro",
      deepseek_key_present: true,
      provider: response.provider,
      model: "deepseek-v4-pro",
      responseModel: response.responseModel,
      stopReason: response.stopReason,
      latencyMs,
      usage,
      estimatedCostUsd,
      cappedText: textFromAssistant(response).slice(0, 120),
    };
  }

  async runDeepSeekRoleRound({ role, prompt, outDir, settings = {} }) {
    const key = readDeepSeekKeyFromKeychain();
    if (!key) {
      return {
        ok: false,
        role,
        scenario: `role.${role}`,
        error: "DeepSeek key unavailable in macOS Keychain.",
      };
    }
    const timestampUtc = new Date().toISOString();
    const systemPrompt = [
      "You are a role-separated Build Stream Conductor lane for the Istara Pi replacement round.",
      "Use DeepSeek only. Return concise JSON or markdown as requested. Do not ask for secrets.",
      "Judge the candidate as an Istara replacement candidate, not as standalone Pi.",
    ].join("\n");
    const messages = [{ role: "user", content: prompt, timestamp: Date.now() }];
    const callSettings = {
      reasoning: settings.reasoning ?? "medium",
      maxTokens: settings.maxTokens ?? 320,
      timeoutMs: settings.timeoutMs ?? 45000,
      maxRetries: 0,
      cacheRetention: "none",
    };
    const started = Date.now();
    let response;
    try {
      process.env.DEEPSEEK_API_KEY = key;
      this.models.setProvider(deepseekProvider());
      const model = this.models.getModel("deepseek", "deepseek-v4-pro");
      if (!model) {
        return {
          ok: false,
          role,
          scenario: `role.${role}`,
          error: "Pi deepseekProvider() did not expose deepseek-v4-pro.",
        };
      }
      response = await this.models.completeSimple(model, { systemPrompt, messages }, callSettings);
    } finally {
      delete process.env.DEEPSEEK_API_KEY;
    }

    const latencyMs = Date.now() - started;
    const usage = usageOrZero(response);
    const estimatedCostUsd = estimateDeepSeekCostUsd(usage);
    const callId = `deepseek-role-${role}-${timestampUtc.replace(/[:.]/g, "-")}`;
    if (outDir) {
      writeRawCapture(outDir, {
        promptRows: [
          buildPromptRecord({
            callId,
            scenarioId: `role.${role}`,
            enginePath: "build_stream_openclaw_fallback",
            provider: "deepseek",
            model: "deepseek-v4-pro",
            timestampUtc,
            systemPrompt,
            messages,
            settings: callSettings,
            adapterMode: "deepseek_role_lane",
            sourceAssets: ["docs/build-stream/2026-07-19-pi-agentic-core-replacement.md"],
            surfaces: ["Build Stream Conductor fallback role lane"],
            redactionSummary: "DEEPSEEK_API_KEY omitted from prompt record; no prompt text redacted.",
          }),
        ],
        outputRows: [
          buildOutputRecord({
            callId,
            scenarioId: `role.${role}`,
            enginePath: "build_stream_openclaw_fallback",
            provider: "deepseek",
            model: "deepseek-v4-pro",
            timestampUtc,
            rawAssistantOutput: textBlocks(response).join("\n"),
            rawContentBlocks: contentBlocks(response),
            toolCallRequests: toolCallBlocks(response),
            stopReason: response.stopReason,
            errors: response.error ? [String(response.error)] : [],
            latencyMs,
            usage,
            estimatedCostUsd,
            redactionSummary: "DEEPSEEK_API_KEY omitted from output record; output text preserved.",
          }),
        ],
      });
    }

    return {
      ok: response.stopReason === "stop",
      role,
      scenario: `role.${role}`,
      provider: "deepseek",
      model: "deepseek-v4-pro",
      stopReason: response.stopReason,
      latencyMs,
      usage,
      estimatedCostUsd,
      text: textFromAssistant(response),
    };
  }
}

export class IstaraContractBaseline {
  constructor(options = {}) {
    this.projectId = options.projectId ?? "lab-project";
  }

  prepareRun(manifest = {}) {
    return {
      ok: true,
      adapter: "IstaraContractBaseline",
      adapterMode: "deterministic_contract_baseline_no_model",
      modelPolicy: {
        provider: "none",
        model: "none",
        localModelsAllowed: false,
      },
      manifest,
    };
  }

  async runScenario(scenarioId) {
    const scenario = getScenarioDefinition(scenarioId);
    const facade = new CanonicalToolFacade({ projectId: this.projectId, actor: "istara-baseline-contract" });
    const started = Date.now();
    for (const response of scenario.responses) {
      for (const block of response.content ?? []) {
        if (block.type === "toolCall") {
          facade.call(block.name, block.arguments ?? {}, { baseline: true, toolCallId: block.id });
        }
      }
    }
    const snapshot = facade.snapshot();
    const canonicalToolsUsed = snapshot.calls.map((call) => call.canonicalId);
    return {
      ok: snapshot.calls.every((call) => call.ok),
      scenario: scenario.id,
      family: scenario.family,
      sourceAssets: scenario.sourceAssets,
      istaraSurfaceIds: scenario.istaraSurfaceIds ?? [],
      baselineEvidence: {
        nativeIstaraContractSource: scenario.sourceAssets,
        canonicalToolsUsed,
        expectedCanonicalTools: scenario.expectedCanonicalTools,
        deterministicOnly: true,
        surfaceCoverage: buildSurfaceCoverageSummary([scenario]),
      },
      telemetry: {
        latencyMs: Date.now() - started,
        toolCallCount: snapshot.telemetry.toolCallCount,
        successfulToolCallCount: snapshot.telemetry.successfulToolCallCount,
        tokenUsage: usageOrZero(),
      },
      facade: snapshot,
    };
  }

  async runAllScenarios() {
    const results = [];
    for (const scenario of ISTARA_PI_SCENARIOS) {
      results.push(await this.runScenario(scenario.id));
    }
    return results;
  }
}
