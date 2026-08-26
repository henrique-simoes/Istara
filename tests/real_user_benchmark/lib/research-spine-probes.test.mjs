import assert from "node:assert/strict";
import test from "node:test";

import {
  exerciseResearchSpineValidation,
  selectSubstantiveEvidenceUnits,
} from "./research-spine-probes.mjs";

function makeLogger() {
  const issues = [];
  const actions = [];
  return {
    issues,
    actions,
    action(step, payload) {
      actions.push({ step, payload });
    },
    issue(issue) {
      issues.push(issue);
    },
    writeJson(_name, payload) {
      this.payload = payload;
    },
  };
}

function makeSubstantiveUnits(count = 4) {
  return Array.from({ length: count }, (_unused, index) => ({
    id: `eu-${index + 1}`,
    source_id: `source-${(index % 2) + 1}`,
    source_location: `interview-${(index % 2) + 1}.md`,
    unit_index: index + 20,
    source_text: `Participant source-grounded observation ${index + 1}. ${"This exact raw span describes a concrete workflow contradiction. ".repeat(3)}`,
  }));
}

function makeReconciledApplications(runId, count = 12) {
  return Array.from({ length: count }, (_unused, index) => ({
    id: `${runId}-application-${index + 1}`,
    coding_run_id: runId,
    promotion_status: "accepted",
    reconciliation_status: "accepted",
    review_status: "approved",
  }));
}

function makeReconciliationDecisions(runId, count = 12) {
  return Array.from({ length: count }, (_unused, index) => ({
    id: `${runId}-decision-${index + 1}`,
    coding_run_id: runId,
    code_application_id: `${runId}-application-${index + 1}`,
    decision_type: "accepted",
  }));
}

test("coding proof samples distributed substantive spans instead of document headers", () => {
  const units = [
    { id: "title", source_text: "# CareNav Renewal interview source 03" },
    { id: "product", source_text: "CareNav Renewal" },
    {
      id: "protocol",
      source_text: "Moderator probes for concrete examples. This protocol exists to preserve the Research Spine and human review guardrails.",
    },
    ...[1, 2, 3, 4, 5].map((index) => ({
      id: `body-${index}`,
      source_text: `P03 describes source-grounded workflow contradiction ${index}. ${"Evidence must remain linked to the exact participant span. ".repeat(3)}`,
    })),
  ];

  assert.deepEqual(
    selectSubstantiveEvidenceUnits(units, 3).map((unit) => unit.id),
    ["body-1", "body-3", "body-5"],
  );
});

test("coding proof prefers distinct source documents when the corpus provides them", () => {
  const units = [
    ...Array.from({ length: 9 }, (_unused, index) => ["source-a", 0, index + 1]),
    ["source-b", 1, 1],
    ["source-c", 2, 1],
  ].map(([sourceId, sourceIndex, unitIndex]) => ({
      id: `${sourceId}-${unitIndex}`,
      source_id: sourceId,
      source_location: `interview-${sourceIndex + 1}.md`,
      unit_index: unitIndex,
      source_text: `Participant evidence from ${sourceId}, span ${unitIndex}. ${"This raw source span describes a concrete workflow contradiction. ".repeat(3)}`,
    }));

  const selected = selectSubstantiveEvidenceUnits(units, 3);

  assert.equal(new Set(selected.map((unit) => unit.source_id)).size, 3);
});

test("coding proof blocks when three source identities are not available", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  let postCalled = false;
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/summary")) return { coding_run_count: 0, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      postCalled = true;
      return {};
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-a",
    logger,
    featureResults,
    blockers,
    codingValidationEnabled: true,
    codingValidationLimit: 4,
    expectedDistinctCoders: 3,
    expectedDistinctSources: 3,
  });

  assert.equal(postCalled, false);
  assert.equal(featureResults.codingValidation, false);
  assert.equal(blockers.length, 1);
  assert.match(blockers[0], /0?2\/3 distinct source identities/);
  assert.equal(logger.issues[0].title, "Research Spine source diversity was not proven");
});

test("three-donor benchmark blocks when coding falls back to single-coder assurance", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/code-applications/")) return makeReconciledApplications("run-1");
      if (path.includes("/reconciliation-decisions")) return makeReconciliationDecisions("run-1");
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [{ id: "run-1" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-1",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 4,
        reliability_method: "single_coder_lower_assurance",
        distinct_model_count: 1,
        rater_count: 1,
        fallback_reason: "Only one coder/model is available.",
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-a",
    logger,
    featureResults,
    blockers,
    codingValidationEnabled: true,
    codingValidationLimit: 4,
    expectedDistinctCoders: 3,
  });

  assert.equal(featureResults.codingValidation, false);
  assert.equal(featureResults.multiModelResearchSpineValidation, false);
  assert.equal(blockers.length, 1);
  assert.match(blockers[0], /1\/3 distinct model coders/);
  assert.equal(logger.issues[0].severity, "high");
});

test("three-donor benchmark accepts full multi-model coding evidence", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/code-applications/")) return makeReconciledApplications("run-1");
      if (path.includes("/reconciliation-decisions")) return makeReconciliationDecisions("run-1");
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [{ id: "run-1" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-1",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        kappa: 0.81,
        alpha: 0.79,
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-a",
    logger,
    featureResults,
    blockers,
    codingValidationEnabled: true,
    codingValidationLimit: 4,
    expectedDistinctCoders: 3,
  });

  assert.equal(featureResults.codingValidation, true);
  assert.equal(featureResults.multiModelResearchSpineValidation, true);
  assert.deepEqual(blockers, []);
});

test("accepted reliability is still blocked when code applications lack reconciliation decisions", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/code-applications/")) {
        return makeReconciledApplications("run-unreconciled").map((row) => ({
          ...row,
          reconciliation_status: "unreconciled",
          review_status: "pending",
        }));
      }
      if (path.includes("/reconciliation-decisions")) return [];
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-unreconciled",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        kappa: 0.81,
        alpha: 0.79,
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-a",
    logger,
    featureResults,
    blockers,
    codingValidationEnabled: true,
    codingValidationLimit: 4,
    expectedDistinctCoders: 3,
  });

  assert.equal(featureResults.codingValidation, false);
  assert.equal(featureResults.multiModelResearchSpineValidation, false);
  assert.equal(blockers.length, 1);
  assert.match(blockers[0], /reconciliation decisions/i);
  assert.equal(logger.issues[0].title, "Research Spine reconciliation was not proven");
});

test("three-donor benchmark rejects a named reliability method without numeric kappa and alpha", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/code-applications/")) return makeReconciledApplications("run-1");
      if (path.includes("/reconciliation-decisions")) return makeReconciliationDecisions("run-1");
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [{ id: "run-1" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-1",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        kappa: 0.81,
        alpha: null,
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-a",
    logger,
    featureResults,
    blockers,
    codingValidationEnabled: true,
    codingValidationLimit: 4,
    expectedDistinctCoders: 3,
  });

  assert.equal(featureResults.codingValidation, false);
  assert.equal(featureResults.multiModelResearchSpineValidation, false);
  assert.equal(blockers.length, 1);
  assert.match(blockers[0], /numeric Fleiss kappa and Krippendorff alpha/);
});

test("three-donor benchmark rejects accepted status when kappa is below its threshold", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/code-applications/")) return makeReconciledApplications("run-low-kappa");
      if (path.includes("/reconciliation-decisions")) return makeReconciliationDecisions("run-low-kappa");
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [{ id: "run-low-kappa" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-low-kappa",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        threshold: 0.6,
        kappa: 0.4,
        alpha: 0.79,
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-a",
    logger,
    featureResults,
    blockers,
    codingValidationEnabled: true,
    codingValidationLimit: 4,
    expectedDistinctCoders: 3,
  });

  assert.equal(featureResults.codingValidation, false);
  assert.equal(featureResults.multiModelResearchSpineValidation, false);
  assert.equal(blockers.length, 1);
  assert.match(blockers[0], /numeric Fleiss kappa and Krippendorff alpha/i);
  assert.equal(logger.issues[0].evidence.kappa_meets_threshold, false);
});

test("three-donor benchmark requires three served donor routes, not only three model aliases", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/code-applications/")) return makeReconciledApplications("run-1");
      if (path.includes("/reconciliation-decisions")) return makeReconciliationDecisions("run-1");
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [{ id: "run-1" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-1",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        kappa: 0.81,
        alpha: 0.79,
        route_evidence: [
          { node_id: "host-donor", outcome: "served" },
          { node_id: "colima-donor-a", outcome: "served" },
          { node_id: "host-donor", outcome: "served", model: "host-second-alias" },
        ],
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-a",
    logger,
    featureResults,
    blockers,
    codingValidationEnabled: true,
    codingValidationLimit: 4,
    expectedDistinctCoders: 3,
    expectedDistinctDonorRoutes: 3,
  });

  assert.equal(featureResults.codingValidation, false);
  assert.equal(featureResults.multiModelResearchSpineValidation, false);
  assert.equal(blockers.length, 1);
  assert.match(blockers[0], /2\/3 required distinct served donor routes/);
  assert.equal(logger.issues[0].severity, "high");
});

test("three-donor benchmark accepts model coders only when all donor routes served", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/code-applications/")) return makeReconciledApplications("run-1");
      if (path.includes("/reconciliation-decisions")) return makeReconciliationDecisions("run-1");
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [{ id: "run-1" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-1",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        kappa: 0.81,
        alpha: 0.79,
        route_evidence: [
          { node_id: "host-donor", outcome: "served" },
          { node_id: "colima-donor-a", outcome: "served" },
          { node_id: "colima-donor-b", outcome: "served" },
        ],
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-a",
    logger,
    featureResults,
    blockers,
    codingValidationEnabled: true,
    codingValidationLimit: 4,
    expectedDistinctCoders: 3,
    expectedDistinctDonorRoutes: 3,
  });

  assert.equal(featureResults.codingValidation, true);
  assert.equal(featureResults.multiModelResearchSpineValidation, true);
  assert.deepEqual(blockers, []);
});

test("coding proof uses project source units while preserving approved task context", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  let codingPayload = null;
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/code-applications/")) return makeReconciledApplications("run-1");
      if (path.includes("/reconciliation-decisions")) return makeReconciliationDecisions("run-1");
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [{ id: "run-1" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post(_path, payload) {
      codingPayload = payload;
      return {
        id: "run-1",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        kappa: 0.81,
        alpha: 0.79,
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-a",
    taskWorkflow: { approvedTasks: [{ id: "task-approved-1" }] },
    logger,
    featureResults,
    blockers,
    codingValidationEnabled: true,
    codingValidationLimit: 4,
    expectedDistinctCoders: 3,
  });

  assert.equal(codingPayload.task_id, null);
  assert.deepEqual(codingPayload.evidence_unit_ids, ["eu-1", "eu-2", "eu-3", "eu-4"]);
  assert.equal(logger.payload.coding_selection.strategy, "deterministic_substantive_source_diverse");
  assert.equal(logger.payload.coding_selection.selected_unit_count, 4);
  assert.equal(logger.payload.coding_selection.selected_source_count, 2);
  assert.equal(logger.payload.approved_task_id, "task-approved-1");
  assert.equal(logger.actions.find((entry) => entry.step === "research_spine.coding_run").payload.coded_scope, "project_source_evidence_units");
  assert.equal(featureResults.codingValidation, true);
});

test("required multi-donor coding failure becomes a blocker", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/summary")) return { coding_run_count: 0, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      throw new Error("This operation was aborted");
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-a",
    logger,
    featureResults,
    blockers,
    codingValidationEnabled: true,
    codingValidationLimit: 4,
    expectedDistinctCoders: 3,
  });

  assert.equal(featureResults.codingValidation, false);
  assert.equal(blockers.length, 1);
  assert.match(blockers[0], /did not complete/);
  assert.equal(logger.issues[0].title, "Research Spine coding validation did not complete");
});

test("long coding request transport failure can recover completed server-side run", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const completedRun = {
    id: "run-1",
    status: "completed",
    promotion_status: "accepted",
    code_application_count: 12,
    reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
    distinct_model_count: 3,
    rater_count: 3,
    kappa: 0.81,
    alpha: 0.79,
    route_evidence: [
      { node_id: "host-donor", outcome: "served" },
      { node_id: "colima-donor-a", outcome: "served" },
      { node_id: "colima-donor-b", outcome: "served" },
    ],
  };
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/code-applications/")) return makeReconciledApplications(completedRun.id);
      if (path.includes("/reconciliation-decisions")) return makeReconciliationDecisions(completedRun.id);
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [completedRun];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      throw new Error("fetch failed");
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-a",
    logger,
    featureResults,
    blockers,
    codingValidationEnabled: true,
    codingValidationLimit: 4,
    expectedDistinctCoders: 3,
    expectedDistinctDonorRoutes: 3,
  });

  assert.equal(featureResults.codingValidation, true);
  assert.equal(featureResults.multiModelResearchSpineValidation, true);
  assert.deepEqual(blockers, []);
  assert.equal(logger.payload.coding_run.id, "run-1");
  assert.ok(logger.actions.find((entry) => entry.step === "research_spine.coding_run_recovered"));
});

test("a blocked current coding run never counts as Research Spine validation", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const blockedRun = {
    id: "run-blocked",
    status: "blocked",
    promotion_status: "blocked",
    reliability_method: "no_coders",
    distinct_model_count: 0,
    rater_count: 0,
    code_application_count: 0,
  };
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/summary")) return { coding_run_count: 8, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [blockedRun];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return blockedRun;
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-a",
    logger,
    featureResults,
    blockers,
    codingValidationEnabled: true,
    codingValidationLimit: 4,
  });

  assert.equal(featureResults.codingValidation, false);
  assert.equal(blockers.length, 1);
  assert.match(blockers[0], /blocked current coding run/i);
});

test("low-agreement coding remains blocked until human reconciliation accepts it", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/summary")) {
        return {
          coding_run_count: 1,
          evidence_unit_count: 4,
          accepted_code_application_count: 0,
          reconciliation_decision_count: 0,
        };
      }
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-low-agreement",
        status: "completed",
        promotion_status: "needs_reconciliation",
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        kappa: 0.2,
        alpha: 0.4,
        code_application_count: 12,
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-a",
    logger,
    featureResults,
    blockers,
    codingValidationEnabled: true,
    codingValidationLimit: 4,
    expectedDistinctCoders: 3,
  });

  assert.equal(featureResults.codingValidation, false);
  assert.match(blockers[0], /needs_reconciliation.*not accepted/i);
});

test("three model calls do not pass without the Fleiss and Krippendorff method", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-wrong-method",
        status: "completed",
        promotion_status: "accepted",
        reliability_method: "call_count_only",
        distinct_model_count: 3,
        rater_count: 3,
        code_application_count: 12,
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-a",
    logger,
    featureResults,
    blockers,
    codingValidationEnabled: true,
    codingValidationLimit: 4,
    expectedDistinctCoders: 3,
  });

  assert.equal(featureResults.codingValidation, false);
  assert.equal(blockers.length, 1);
  assert.match(blockers[0], /Fleiss.*Krippendorff/i);
});

test("enabled coding validation defaults to the three-model Research Spine contract", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-single",
        status: "completed",
        promotion_status: "needs_human_review",
        reliability_method: "single_coder_lower_assurance",
        distinct_model_count: 1,
        rater_count: 1,
        code_application_count: 4,
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-a",
    logger,
    featureResults,
    blockers,
    codingValidationEnabled: true,
    codingValidationLimit: 4,
  });

  assert.equal(featureResults.codingValidation, false);
  assert.match(blockers[0], /needs_human_review.*not accepted/i);
  assert.equal(logger.issues[0].evidence.expected_distinct_coders, 3);
});
