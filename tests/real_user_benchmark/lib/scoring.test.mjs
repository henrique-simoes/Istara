import assert from "node:assert/strict";
import test from "node:test";

import {
  acceptanceGateStatus,
  benchmarkExitCode,
  benchmarkWorkloadForProfile,
  liveAcceptanceBlockers,
  profileRunsSurface,
  scoreRun,
} from "./scoring.mjs";

test("acceptance profiles select disjoint workload surfaces", () => {
  assert.equal(profileRunsSurface("provider", "corpus"), true);
  assert.equal(profileRunsSurface("provider", "coding"), true);
  assert.equal(profileRunsSurface("provider", "chat"), false);
  assert.equal(profileRunsSurface("provider", "petals"), false);
  assert.equal(profileRunsSurface("petals", "petals"), true);
  assert.equal(profileRunsSurface("petals", "corpus"), false);
  assert.equal(profileRunsSurface("petals", "coding"), false);
  assert.equal(profileRunsSurface("combined", "commonWorkflow"), true);
});

test("workload matrix returns an independent immutable-shaped snapshot", () => {
  const provider = benchmarkWorkloadForProfile("provider");
  provider.coding = false;
  assert.equal(benchmarkWorkloadForProfile("provider").coding, true);
  assert.deepEqual(Object.keys(benchmarkWorkloadForProfile("petals")).sort(), [
    "chat", "coding", "commonWorkflow", "corpus", "findings", "integrations",
    "marathon", "petals", "provider", "selfImprovement", "tasks", "ui",
  ].sort());
});

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
      multiModelResearchSpineValidation: true,
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
      multiModelResearchSpineValidation: true,
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
      multiModelResearchSpineValidation: true,
    },
  });

  assert.equal(scorecard.coding_validation_verified, true);
  assert.equal(scorecard.research_spine_traceability_verified, true);
  assert.equal(scorecard.research_spine_structure_present, true);
  assert.equal(scorecard.research_spine_validation_verified, true);
  assert.equal(scorecard.research_spine_donor_routes_verified, true);
});

test("scorecard cannot treat structural traceability or a weak donor contract as accepted Research Spine validation", () => {
  const scorecard = scoreRun({
    mode: "probe",
    featureResults: {
      distinctDonorEndpoints: true,
      researchSpineTraceability: true,
      codingValidation: false,
      multiModelResearchSpineValidation: false,
    },
    sandbox: {
      relayExpectedCount: 1,
      relayStartedCount: 0,
      modelServerExpectedCount: 0,
      modelServerStartedCount: 0,
    },
  });

  assert.equal(scorecard.distinct_donor_endpoints_verified, true);
  assert.equal(scorecard.donor_endpoint_contract_verified, true);
  assert.equal(scorecard.research_spine_structure_present, true);
  assert.equal(scorecard.research_spine_traceability_verified, true);
  assert.equal(scorecard.research_spine_validation_verified, false);
  assert.equal(scorecard.research_spine_donor_routes_verified, false);
});

test("scorecard accepted Research Spine validation requires all three provider signals", () => {
  const scorecard = scoreRun({
    mode: "probe",
    acceptanceProfile: "provider",
    codingValidationEnabled: true,
    featureResults: {
      codingValidation: true,
      multiModelResearchSpineValidation: false,
      researchSpineTraceability: false,
    },
  });

  assert.equal(scorecard.research_spine_validation_verified, false);
  assert.equal(scorecard.acceptance_gates.provider.verified, false);
});

test("provider acceptance profile verifies coding without requiring Petals donation", () => {
  const gates = acceptanceGateStatus({
    profile: "provider",
    codingValidationEnabled: true,
    requireComputeDonation: false,
    featureResults: {
      codingValidation: true,
      multiModelResearchSpineValidation: true,
      researchSpineTraceability: true,
      computeDonation: false,
    },
  });

  assert.equal(gates.profile, "provider");
  assert.deepEqual(gates.provider, { selected: true, status: "verified", verified: true });
  assert.deepEqual(gates.petals, { selected: false, status: "not_selected", verified: false });
  assert.deepEqual(gates.combined, { selected: false, status: "not_selected", verified: false });
});

test("provider acceptance blocks inconsistent coding-only evidence", () => {
  const gates = acceptanceGateStatus({
    profile: "provider",
    codingValidationEnabled: true,
    requireComputeDonation: false,
    featureResults: {
      codingValidation: true,
      multiModelResearchSpineValidation: false,
      researchSpineTraceability: false,
    },
  });

  assert.deepEqual(gates.provider, { selected: true, status: "blocked", verified: false });
});

test("Petals acceptance profile verifies donation without claiming provider validity", () => {
  const gates = acceptanceGateStatus({
    profile: "petals",
    codingValidationEnabled: false,
    requireComputeDonation: true,
    featureResults: { codingValidation: false, computeDonation: true },
  });

  assert.equal(gates.profile, "petals");
  assert.deepEqual(gates.provider, { selected: false, status: "not_selected", verified: false });
  assert.deepEqual(gates.petals, { selected: true, status: "verified", verified: true });
  assert.deepEqual(gates.combined, { selected: false, status: "not_selected", verified: false });
});

test("combined acceptance profile requires both provider and Petals evidence", () => {
  const scorecard = scoreRun({
    mode: "probe",
    acceptanceProfile: "combined",
    codingValidationEnabled: true,
    requireComputeDonation: true,
    featureResults: {
      codingValidation: true,
      multiModelResearchSpineValidation: true,
      researchSpineTraceability: true,
      computeDonation: false,
    },
  });

  assert.equal(scorecard.acceptance_profile, "combined");
  assert.equal(scorecard.acceptance_gates.provider.status, "verified");
  assert.equal(scorecard.acceptance_gates.petals.status, "blocked");
  assert.deepEqual(scorecard.acceptance_gates.combined, {
    selected: true,
    status: "blocked",
    verified: false,
  });
});

test("selected provider profile fails closed when coding validation is disabled", () => {
  assert.deepEqual(liveAcceptanceBlockers({
    acceptanceProfile: "provider",
    codingValidationEnabled: false,
    requireComputeDonation: false,
    featureResults: {},
  }), [
    "Selected provider Research Spine gate was disabled; acceptance cannot pass.",
  ]);
});

test("selected provider profile fails closed when multi-model validation is missing", () => {
  assert.deepEqual(liveAcceptanceBlockers({
    acceptanceProfile: "provider",
    codingValidationEnabled: true,
    requireComputeDonation: false,
    featureResults: {
      codingValidation: true,
      multiModelResearchSpineValidation: false,
      researchSpineTraceability: true,
    },
  }), [
    "Requested independent multi-model Research Spine validation did not complete.",
  ]);
});

test("provider acceptance does not fail on intentionally unselected chat or task surfaces", () => {
  assert.deepEqual(liveAcceptanceBlockers({
    acceptanceProfile: "provider",
    maxChatTurns: 0,
    chatTurnCount: 0,
    maxTasks: 0,
    completedTasks: 0,
    codingValidationEnabled: true,
    requireComputeDonation: false,
    featureResults: {
      codingValidation: true,
      multiModelResearchSpineValidation: true,
      researchSpineTraceability: true,
    },
  }), []);
});

test("selected Petals profile fails closed when donation validation is disabled", () => {
  assert.deepEqual(liveAcceptanceBlockers({
    acceptanceProfile: "petals",
    codingValidationEnabled: false,
    requireComputeDonation: false,
    featureResults: {},
  }), [
    "Selected Petals donation interoperability gate was disabled; acceptance cannot pass.",
  ]);
});

test("combined profile fails closed when either selected gate is disabled", () => {
  assert.deepEqual(liveAcceptanceBlockers({
    acceptanceProfile: "combined",
    codingValidationEnabled: false,
    requireComputeDonation: false,
    featureResults: {},
  }), [
    "Selected provider Research Spine gate was disabled; acceptance cannot pass.",
    "Selected Petals donation interoperability gate was disabled; acceptance cannot pass.",
  ]);
});
