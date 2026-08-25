import assert from "node:assert/strict";
import test from "node:test";

import { benchmarkExitCode, liveAcceptanceBlockers, scoreRun } from "./scoring.mjs";

test("a live benchmark with blockers exits nonzero", () => {
  assert.equal(benchmarkExitCode({ mode: "probe", blockers: ["research coding blocked"] }), 1);
});

test("bounded live acceptance rejects partial chat and an unapproved task workflow", () => {
  const blockers = liveAcceptanceBlockers({
    maxChatTurns: 8,
    chatTurnCount: 7,
    maxTasks: 3,
    completedTasks: 0,
    codingValidationEnabled: true,
    featureResults: {
      codingValidation: true,
      researchSpineTraceability: true,
      taskReviewLoop: false,
      approvedTaskFindings: false,
    },
  });

  assert.deepEqual(blockers, [
    "Live run completed only 7/8 requested chat turns.",
    "Live run completed no human-reviewed task approvals from 3 requested tasks.",
    "Requested task review/revision workflow did not complete.",
    "Requested task-backed Findings/report path did not complete.",
  ]);
});

test("bounded live acceptance passes a complete fail-closed Research Spine run", () => {
  assert.deepEqual(liveAcceptanceBlockers({
    maxChatTurns: 8,
    chatTurnCount: 8,
    maxTasks: 3,
    completedTasks: 1,
    codingValidationEnabled: true,
    featureResults: {
      codingValidation: true,
      researchSpineTraceability: true,
      taskReviewLoop: true,
      approvedTaskFindings: true,
    },
  }), []);
});

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
