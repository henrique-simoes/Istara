import assert from "node:assert/strict";
import test from "node:test";
import { CanonicalToolFacade } from "../src/canonical-tool-facade.mjs";
import { IstaraContractBaseline, IstaraPiAdapter } from "../src/istara-pi-adapter.mjs";
import {
  ISTARA_SURFACE_MAP,
  MANDATORY_ISTARA_SURFACE_IDS,
  buildSurfaceCoverageSummary,
} from "../src/istara-surface-map.mjs";
import { ISTARA_PI_SCENARIOS } from "../src/scenario-catalog.mjs";

test("canonical facade validates schemas and returns Istara result envelopes", () => {
  const facade = new CanonicalToolFacade({ projectId: "test-project" });

  const ok = facade.call("istara_create_task", { title: "Wire Pi", priority: "high" });
  assert.equal(ok.ok, true);
  assert.equal(ok.action, "tasks.create");
  assert.equal(ok.data.projectId, "test-project");
  assert.equal(ok.data.status, "open");

  const bad = facade.call("istara_create_finding", { title: "Missing severity", evidence: "x" });
  assert.equal(bad.ok, false);
  assert.equal(bad.error.code, "invalid_arguments");
});

test("IstaraPiAdapter routes an Istara scenario through Pi-owned Agent tool execution", async () => {
  const adapter = new IstaraPiAdapter({ mode: "no-model", projectId: "test-project" });
  const result = await adapter.runNoModelChatToolLoop("Create task and finding through tools.");

  assert.equal(result.ok, true);
  assert.equal(result.replacementEvidence.piOwnedLoop, true);
  assert.deepEqual(result.replacementEvidence.canonicalToolsUsed, [
    "tasks.create",
    "findings.create",
  ]);
  assert.equal(result.replacementEvidence.istaraProductStatePreserved.taskCount, 1);
  assert.equal(result.replacementEvidence.istaraProductStatePreserved.findingCount, 1);
  assert.equal(result.piProviderCalls, 2);
  assert.ok(result.eventTypes.includes("tool_execution_start"));
  assert.match(result.finalText, /Created a task and finding/);
});

test("Pi candidate runs representative Istara surfaces through Pi Agent loops", async () => {
  const adapter = new IstaraPiAdapter({ mode: "no-model", projectId: "test-project" });
  const results = await adapter.runAllNoModelScenarios();

  assert.equal(results.length, ISTARA_PI_SCENARIOS.length);
  assert.equal(results.every((result) => result.ok), true);
  assert.equal(results.every((result) => result.replacementEvidence.piOwnedLoop), true);
  assert.equal(results.every((result) => result.replacementEvidence.expectedToolOrderMatched), true);
  assert.deepEqual(
    results.map((result) => result.scenario),
    ISTARA_PI_SCENARIOS.map((scenario) => scenario.id),
  );

  const byScenario = Object.fromEntries(results.map((result) => [result.scenario, result]));
  assert.equal(byScenario["task.plan_execute.lifecycle"].facade.plans.length, 1);
  assert.equal(byScenario["documents.tools.slice"].facade.documents.length, 2);
  assert.ok(
    byScenario["documents.tools.slice"].replacementEvidence.canonicalToolsUsed.includes("documents.search"),
  );
  assert.ok(
    byScenario["documents.tools.slice"].replacementEvidence.canonicalToolsUsed.includes("documents.read"),
  );
  assert.ok(byScenario["memory.rag.slice"].facade.memory.length >= 3);
  assert.equal(byScenario["skills.three_skill_slice"].facade.skillRuns.length, 3);
  assert.equal(byScenario["a2a.debate_report.slice"].facade.reports.length, 1);
  assert.equal(byScenario["channel.lifecycle.simulated_slice"].facade.channelMessages.length, 2);
  assert.equal(byScenario["structured_outputs.core_eval"].facade.evalArtifacts[0].json_validity, true);
  assert.equal(byScenario["research.spine.step_tracker"].facade.researchSteps.length, 4);
  assert.equal(
    byScenario["research.spine.step_tracker"].replacementEvidence.researchSpine.reportableDoneGate,
    false,
  );
  assert.equal(byScenario["autoresearch.governed_experiment.slice"].facade.autoresearchExperiments.length, 1);
  assert.equal(
    byScenario["autoresearch.governed_experiment.slice"].facade.autoresearchExperiments[0].report_evidence,
    false,
  );
  assert.equal(byScenario["memory.reasoningbank.memento.slice"].facade.reasoningMemories.length, 1);
  assert.equal(byScenario["memory.reasoningbank.memento.slice"].facade.mementoSkillMemories.length, 1);
  assert.equal(byScenario["channels.webhook.telegram.lifecycle"].facade.webhookEvents[0].accepted, true);
  assert.equal(byScenario["channels.webhook.telegram.lifecycle"].facade.channelMessages.length, 2);
  assert.equal(byScenario["steering.system_prompt.loop.slice"].facade.steeringEvents.length, 1);
  assert.equal(byScenario["steering.system_prompt.loop.slice"].facade.systemPromptAudits[0].passed, true);
  assert.equal(byScenario["benchmarks.evals.real_user.contract"].facade.benchmarkContracts.length, 1);
  assert.equal(byScenario["model.routing.telemetry.slice"].facade.modelRoutes[0].model, "deepseek-v4-pro");
  assert.equal(byScenario["model.routing.telemetry.slice"].facade.metrics.length, 2);
});

test("surface map covers mandatory Istara real-loop touchpoints with concrete blockers", () => {
  const summary = buildSurfaceCoverageSummary(ISTARA_PI_SCENARIOS);

  assert.equal(summary.mappedSurfaceCount, MANDATORY_ISTARA_SURFACE_IDS.length);
  assert.deepEqual(summary.uncoveredMandatorySurfaceIds, []);
  assert.equal(summary.surfaces.every((surface) => surface.covered), true);
  assert.equal(summary.surfaces.every((surface) => surface.realFiles.length > 0), true);
  assert.equal(summary.surfaces.every((surface) => surface.realTests.length > 0), true);
  assert.equal(
    summary.surfaces.every((surface) =>
      surface.productionGaps.every((gap) => gap.files.every((file) => file.includes(":"))),
    ),
    true,
  );
  assert.deepEqual(
    ISTARA_SURFACE_MAP.map((surface) => surface.id),
    MANDATORY_ISTARA_SURFACE_IDS,
  );
});

test("deterministic contract baseline uses the same canonical scenario contracts without Pi", async () => {
  const baseline = new IstaraContractBaseline({ projectId: "test-project" });
  const results = await baseline.runAllScenarios();

  assert.equal(results.length, ISTARA_PI_SCENARIOS.length);
  assert.equal(results.every((result) => result.ok), true);
  assert.equal(results.every((result) => result.baselineEvidence.deterministicOnly), true);
  assert.equal(results[0].baselineEvidence.canonicalToolsUsed[0], "tasks.create");
});
