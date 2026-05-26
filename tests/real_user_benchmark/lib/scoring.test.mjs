import assert from "node:assert/strict";
import test from "node:test";

import { scoreRun } from "./scoring.mjs";

test("agentic orchestration score is capped when natural scheduler activity lacks donor usage", () => {
  const scorecard = scoreRun({
    mode: "probe",
    metrics: {},
    completedTasks: 8,
    chatTurns: 8,
    featureResults: {
      naturalComputeOrchestration: true,
      multiDonorCompute: false,
      taskReviewLoop: true,
      approvedTaskFindings: true,
    },
  });

  const dimension = scorecard.dimensions.find((item) => item.key === "agentic_orchestration");
  assert.equal(dimension.ratio, 0.65);
  assert.equal(dimension.score, 3.25);
});

test("corpus score requires representative long-form upload volume", () => {
  const tiny = scoreRun({ mode: "probe", uploadedDocuments: 20 });
  const representative = scoreRun({ mode: "probe", uploadedDocuments: 120 });

  assert.equal(tiny.dimensions.find((item) => item.key === "corpus").ratio, 0.6);
  assert.equal(representative.dimensions.find((item) => item.key === "corpus").ratio, 1);
});

test("self-improvement score requires governed telemetry and autoresearch evidence", () => {
  const weak = scoreRun({
    mode: "probe",
    featureResults: { loops: true },
  });
  const governed = scoreRun({
    mode: "probe",
    featureResults: {
      telemetryEvidence: true,
      autoresearchEvidence: true,
      selfImprovementGovernance: true,
      reasoningBankEvidence: true,
      metaHyperagentEvidence: true,
    },
  });

  assert.equal(weak.dimensions.find((item) => item.key === "loops_autoresearch").ratio, 0.65);
  assert.equal(governed.dimensions.find((item) => item.key === "loops_autoresearch").ratio, 1);
  assert.equal(governed.self_improvement_governance_verified, true);
});

test("scorecard exposes Research Spine coding and traceability evidence", () => {
  const scorecard = scoreRun({
    mode: "probe",
    featureResults: {
      codingValidation: true,
      researchSpineTraceability: true,
    },
  });

  assert.equal(scorecard.coding_validation_verified, true);
  assert.equal(scorecard.research_spine_traceability_verified, true);
});
