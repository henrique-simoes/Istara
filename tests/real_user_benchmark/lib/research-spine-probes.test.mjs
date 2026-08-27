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

function makeReconciledApplications(runId, count = 12, expectedUnits = makeSubstantiveUnits()) {
  return Array.from({ length: count }, (_unused, index) => ({
    // Mirror the production API: each persisted application carries a quote
    // from, and the exact location of, its selected raw evidence unit.
    ...(() => {
      const unit = expectedUnits[index % expectedUnits.length];
      return {
        source_text: unit.source_text,
        source_location: unit.source_location,
        start_offset: unit.start_offset ?? null,
        end_offset: unit.end_offset ?? null,
        code_id: "workflow-contradiction",
        confidence: 0.9,
        reasoning: "The source describes a concrete workflow contradiction that fits this code.",
      };
    })(),
    id: `${runId}-application-${index + 1}`,
    coding_run_id: runId,
    coder_id: `coder-${Math.floor(index / 4) + 1}`,
    evidence_unit_id: `eu-${(index % 4) + 1}`,
    model_name: `model-${String.fromCharCode(97 + Math.floor(index / 4))}`,
    route_evidence: {
      node_id: `donor-${String.fromCharCode(97 + Math.floor(index / 4))}`,
      model: `model-${String.fromCharCode(97 + Math.floor(index / 4))}`,
      endpoint_id: `endpoint-${String.fromCharCode(97 + Math.floor(index / 4))}`,
      outcome: "served",
    },
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

function makeServedModelRoutes() {
  return [
    { node_id: "donor-a", model: "model-a", outcome: "served" },
    { node_id: "donor-b", model: "model-b", outcome: "served" },
    { node_id: "donor-c", model: "model-c", outcome: "served" },
  ];
}

function makeTraceability(runId, expectedUnits = makeSubstantiveUnits()) {
  const applications = makeReconciledApplications(runId, 12, expectedUnits);
  return {
    contract: {
      graph_role: "synthesis_and_traceability",
      promotion_rule: "graph_traceability_cannot_bypass_coding_reliability_reconciliation_or_done_gates",
    },
    coding_runs: [{ id: runId }],
    code_applications: applications,
    reconciliation_decisions: makeReconciliationDecisions(runId),
    evidence_graph_edges: applications.map((application) => ({
      coding_run_id: runId,
      source_type: "evidence_unit",
      source_id: application.evidence_unit_id,
      relation: "coded_as",
      target_type: "code_application",
      target_id: application.id,
    })),
  };
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

test("coding proof does not invent a three-document gate for one source with multiple spans", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  let postPayload = null;
  const units = makeSubstantiveUnits(4).map((unit) => ({
    ...unit,
    source_id: "one-interview",
    source_location: "interview-one.md",
  }));
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/evidence-units")) return units;
      if (path.includes("/code-applications/")) {
        return makeReconciledApplications("run-one-source", 12, units);
      }
      if (path.includes("/reconciliation-decisions")) return makeReconciliationDecisions("run-one-source", 12);
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/coding-runs")) return [{ id: "run-one-source" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post(_path, payload) {
      postPayload = payload;
      return {
        id: "run-one-source",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        kappa: 0.81,
        alpha: 0.79,
        route_evidence: makeServedModelRoutes(),
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-one-source",
    logger,
    featureResults,
    blockers,
    codingValidationEnabled: true,
    codingValidationLimit: 4,
    expectedDistinctCoders: 3,
    expectedDistinctSources: 0,
  });

  assert.equal(postPayload?.evidence_unit_ids?.length, 4);
  assert.equal(featureResults.codingValidation, true);
  assert.deepEqual(blockers, []);
});

test("accepted coding cannot pass when the Research Spine contract is unavailable", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") return {};
      if (path.includes("/code-applications/")) return makeReconciledApplications("run-no-contract", 12);
      if (path.includes("/reconciliation-decisions")) return makeReconciliationDecisions("run-no-contract", 12);
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [{ id: "run-no-contract" }];
      if (path.includes("/traceability")) return { contract: {}, summary: {} };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-no-contract",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        kappa: 0.81,
        alpha: 0.79,
        route_evidence: makeServedModelRoutes(),
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-no-contract",
    logger,
    featureResults,
    blockers,
    codingValidationEnabled: true,
    codingValidationLimit: 4,
    expectedDistinctCoders: 3,
  });

  assert.equal(featureResults.codingValidation, false);
  assert.equal(featureResults.ensembleCodingValidation, false);
  assert.equal(featureResults.multiModelResearchSpineValidation, false);
  assert.equal(blockers.length, 1);
  assert.match(blockers[0], /contract/i);
});

test("empty traceability and telemetry payloads do not count as Research Spine evidence", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/summary")) return {};
      if (path.includes("/evidence-units")) return [];
      if (path.includes("/coding-runs")) return [];
      if (path.includes("/traceability")) return {};
      if (path.includes("/telemetry-audit")) return {};
      return {};
    },
    async post() {
      throw new Error("coding should not run");
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-empty-evidence",
    logger,
    featureResults,
    blockers,
    codingValidationEnabled: false,
    codingValidationLimit: 0,
  });

  assert.equal(featureResults.researchSpineTraceability, false);
  assert.equal(featureResults.ragTraceabilityEvidence, false);
  assert.equal(featureResults.telemetryEvidence, false);
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
  assert.match(blockers[0], /1\/3 backend-reported model coders/);
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
      if (path.includes("/summary")) return {
        report_gate: "accepted_reconciled_evidence_from_approved_done_tasks_only",
        coding_run_count: 1,
        evidence_unit_count: 4,
      };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [{ id: "run-1" }];
      if (path.includes("/traceability")) return makeTraceability("run-1");
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
        route_evidence: makeServedModelRoutes(),
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
  assert.equal(featureResults.researchSpineTraceability, true);
  assert.equal(featureResults.ragTraceabilityEvidence, true);
  assert.deepEqual(blockers, []);
});

test("traceability rejects duplicate current-run application identities", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const traceability = makeTraceability("run-duplicate");
  traceability.code_applications[traceability.code_applications.length - 1]
    = { ...traceability.code_applications[0] };
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/code-applications/")) return makeReconciledApplications("run-duplicate");
      if (path.includes("/reconciliation-decisions")) return makeReconciliationDecisions("run-duplicate");
      if (path.includes("/summary")) return {
        report_gate: "accepted_reconciled_evidence_from_approved_done_tasks_only",
        coding_run_count: 1,
        evidence_unit_count: 4,
      };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [{ id: "run-duplicate" }];
      if (path.includes("/traceability")) return traceability;
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-duplicate",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        kappa: 0.81,
        alpha: 0.79,
        route_evidence: makeServedModelRoutes(),
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-duplicate-traceability",
    logger,
    featureResults,
    blockers,
    codingValidationEnabled: true,
    codingValidationLimit: 4,
    expectedDistinctCoders: 3,
  });

  assert.equal(featureResults.codingValidation, true);
  assert.equal(featureResults.researchSpineTraceability, false);
  assert.equal(logger.payload.traceability_coding_run.application_evidence_ok, false);
  assert.equal(logger.payload.traceability_coding_run.unique_application_count, 11);
  assert.equal(logger.issues.at(-1).title, "Research Spine traceability was not bound to the current coding run");
});

test("traceability rejects a current-run application without a coded evidence edge", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const traceability = makeTraceability("run-missing-edge");
  traceability.evidence_graph_edges = traceability.evidence_graph_edges.slice(1);
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/code-applications/")) return makeReconciledApplications("run-missing-edge");
      if (path.includes("/reconciliation-decisions")) return makeReconciliationDecisions("run-missing-edge");
      if (path.includes("/summary")) return {
        report_gate: "accepted_reconciled_evidence_from_approved_done_tasks_only",
        coding_run_count: 1,
        evidence_unit_count: 4,
      };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [{ id: "run-missing-edge" }];
      if (path.includes("/traceability")) return traceability;
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-missing-edge",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        kappa: 0.81,
        alpha: 0.79,
        route_evidence: makeServedModelRoutes(),
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-missing-edge",
    logger,
    featureResults,
    blockers,
    codingValidationEnabled: true,
    codingValidationLimit: 4,
    expectedDistinctCoders: 3,
  });

  assert.equal(featureResults.codingValidation, true);
  assert.equal(featureResults.researchSpineTraceability, false);
  assert.equal(logger.payload.traceability_coding_run.edge_evidence_ok, false);
  assert.equal(logger.payload.traceability_coding_run.coded_application_edge_count, 11);
  assert.equal(logger.payload.traceability_coding_run.missing_application_edge_ids.length, 1);
  assert.equal(logger.issues.at(-1).title, "Research Spine traceability was not bound to the current coding run");
});

test("three-donor benchmark rejects project traceability that omits the current coding run", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/code-applications/")) return makeReconciledApplications("run-unbound");
      if (path.includes("/reconciliation-decisions")) return makeReconciliationDecisions("run-unbound");
      if (path.includes("/summary")) return {
        report_gate: "accepted_reconciled_evidence_from_approved_done_tasks_only",
        coding_run_count: 1,
        evidence_unit_count: 4,
      };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [{ id: "run-unbound" }];
      if (path.includes("/traceability")) return {
        contract: {
          graph_role: "synthesis_and_traceability",
          promotion_rule: "graph_traceability_cannot_bypass_coding_reliability_reconciliation_or_done_gates",
        },
        coding_runs: [],
        code_applications: [],
        reconciliation_decisions: [],
        evidence_graph_edges: [],
      };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-unbound",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        kappa: 0.81,
        alpha: 0.79,
        route_evidence: makeServedModelRoutes(),
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-unbound-traceability",
    logger,
    featureResults,
    blockers,
    codingValidationEnabled: true,
    codingValidationLimit: 4,
    expectedDistinctCoders: 3,
  });

  assert.equal(featureResults.codingValidation, true);
  assert.equal(featureResults.multiModelResearchSpineValidation, true);
  assert.equal(featureResults.researchSpineTraceability, false);
  assert.equal(featureResults.ragTraceabilityEvidence, false);
  assert.equal(blockers.length, 0);
  assert.equal(
    logger.issues.at(-1).title,
    "Research Spine traceability was not bound to the current coding run",
  );
  assert.equal(logger.payload.traceability_coding_run.run_id, "run-unbound");
  assert.equal(logger.payload.traceability_coding_run.run_listed, false);
});

test("three-donor benchmark rejects code applications returned from another coding run", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      // The endpoint is queried with the requested run id, but this fixture
      // simulates an adapter that ignores that filter and returns a complete,
      // otherwise-valid response for a different run.
      if (path.includes("/code-applications/")) return makeReconciledApplications("foreign-run");
      if (path.includes("/reconciliation-decisions")) return makeReconciliationDecisions("foreign-run");
      if (path.includes("/summary")) return { coding_run_count: 2, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [{ id: "run-cross-run" }, { id: "foreign-run" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-cross-run",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        kappa: 0.81,
        alpha: 0.79,
        route_evidence: makeServedModelRoutes(),
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-cross-run",
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
  assert.match(blockers[0], /complete coder-by-evidence-unit coverage/i);
  assert.equal(logger.issues[0].evidence.application_coverage.invalid_rows.length, 12);
  assert.equal(logger.issues[0].evidence.application_coverage.invalid_rows[0].coding_run_id, "foreign-run");
  assert.equal(logger.issues[0].evidence.application_coverage.invalid_rows[0].expected_coding_run_id, "run-cross-run");
});

test("three-donor benchmark rejects reconciliation decisions returned from another coding run", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const rows = makeReconciledApplications("run-decision-cross");
  const foreignDecisions = makeReconciliationDecisions("foreign-run").map((decision, index) => ({
    ...decision,
    code_application_id: rows[index].id,
  }));
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/code-applications/")) return rows;
      // IDs intentionally point at the requested rows while the run identity
      // is foreign; linking by application ID alone must not pass.
      if (path.includes("/reconciliation-decisions")) return foreignDecisions;
      if (path.includes("/summary")) return { coding_run_count: 2, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [{ id: "run-decision-cross" }, { id: "foreign-run" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-decision-cross",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        kappa: 0.81,
        alpha: 0.79,
        route_evidence: makeServedModelRoutes(),
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-decision-cross",
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
  assert.match(blockers[0], /reconciliation decisions belong to another coding run/i);
  assert.equal(logger.issues[0].evidence.invalid_decision_count, 12);
  assert.equal(logger.issues[0].evidence.all_applications_have_decisions, false);
});

test("three-donor benchmark rejects duplicate code-application identities", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const rows = makeReconciledApplications("run-duplicate-app");
  rows[11] = { ...rows[11], id: rows[0].id };
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/code-applications/")) return rows;
      if (path.includes("/reconciliation-decisions")) return makeReconciliationDecisions("run-duplicate-app");
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [{ id: "run-duplicate-app" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-duplicate-app",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        kappa: 0.81,
        alpha: 0.79,
        route_evidence: makeServedModelRoutes(),
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-duplicate-app",
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
  assert.match(blockers[0], /complete coder-by-evidence-unit coverage/i);
  assert.deepEqual(logger.issues[0].evidence.application_coverage.duplicate_application_ids, [
    "run-duplicate-app-application-1",
  ]);
  assert.equal(logger.issues[0].evidence.application_coverage.invalid_rows.at(-1).duplicate_count, 2);
});

test("three-donor benchmark rejects coder rows that omit a served model identity", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const rows = makeReconciledApplications("run-model-coverage").map((row, index) => (
    index >= 8
      ? {
          ...row,
          model_name: "model-a",
          route_evidence: { ...row.route_evidence, model: "model-a" },
        }
      : row
  ));
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/code-applications/")) return rows;
      if (path.includes("/reconciliation-decisions")) return makeReconciliationDecisions("run-model-coverage");
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [{ id: "run-model-coverage" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-model-coverage",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        kappa: 0.81,
        alpha: 0.79,
        route_evidence: makeServedModelRoutes(),
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-model-coverage",
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
  assert.match(blockers[0], /complete coder-by-evidence-unit coverage/i);
  assert.deepEqual(logger.issues[0].evidence.application_coverage.missing_served_model_identities, ["model-c"]);
  assert.deepEqual(logger.issues[0].evidence.application_coverage.observed_model_identities, ["model-a", "model-b"]);
});

test("three-donor benchmark rejects fabricated or re-located source spans", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const rows = makeReconciledApplications("run-source-binding");
  rows[0] = {
    ...rows[0],
    source_text: "A paraphrase that never appears in the selected raw evidence unit.",
    source_location: "wrong-document.md:999",
  };
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/code-applications/")) return rows;
      if (path.includes("/reconciliation-decisions")) return makeReconciliationDecisions("run-source-binding");
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [{ id: "run-source-binding" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-source-binding",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        kappa: 0.81,
        alpha: 0.79,
        route_evidence: makeServedModelRoutes(),
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-source-binding",
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
  assert.match(blockers[0], /complete coder-by-evidence-unit coverage/i);
  assert.deepEqual(
    logger.issues[0].evidence.application_coverage.source_span_mismatches.map((item) => item.evidence_unit_id),
    ["eu-1"],
  );
  assert.deepEqual(
    logger.issues[0].evidence.application_coverage.source_location_mismatches.map((item) => item.evidence_unit_id),
    ["eu-1"],
  );
});

test("three-donor benchmark rejects applications without substantive open-code payload", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const units = makeSubstantiveUnits().map((unit, index) => ({
    ...unit,
    start_offset: index * 100,
    end_offset: index * 100 + unit.source_text.length,
  }));
  const rows = makeReconciledApplications("run-code-payload-gap", 12, units);
  rows[0] = {
    ...rows[0],
    code_id: "",
    reasoning: "",
    confidence: null,
  };
  rows[1] = { ...rows[1], start_offset: 999 };
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/code-applications/")) return rows;
      if (path.includes("/reconciliation-decisions")) return makeReconciliationDecisions("run-code-payload-gap");
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return units;
      if (path.includes("/coding-runs")) return [{ id: "run-code-payload-gap" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-code-payload-gap",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        kappa: 0.81,
        alpha: 0.79,
        route_evidence: makeServedModelRoutes(),
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-code-payload-gap",
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
  assert.match(blockers[0], /substantive open-code payload/i);
  assert.deepEqual(logger.issues[0].evidence.application_coverage.missing_code_payloads, [
    {
      id: "run-code-payload-gap-application-1",
      evidence_unit_id: "eu-1",
      has_code_id: false,
      has_reasoning: false,
    },
  ]);
  assert.deepEqual(logger.issues[0].evidence.application_coverage.invalid_confidence_rows, [
    {
      id: "run-code-payload-gap-application-1",
      evidence_unit_id: "eu-1",
      confidence: null,
    },
  ]);
  assert.deepEqual(logger.issues[0].evidence.application_coverage.source_offset_mismatches, [
    {
      id: "run-code-payload-gap-application-2",
      evidence_unit_id: "eu-2",
      expected_start_offset: 100,
      observed_start_offset: 999,
      expected_end_offset: 100 + units[1].source_text.length,
      observed_end_offset: 100 + units[1].source_text.length,
    },
  ]);
  assert.equal(logger.issues[0].evidence.application_coverage.invalid_rows[0].confidence_valid, false);
});

test("three-model coding blocks when an application omits a coder-unit span or provenance", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const incompleteRows = makeReconciledApplications("run-coverage-gap");
  incompleteRows[3] = {
    ...incompleteRows[3],
    evidence_unit_id: "eu-1",
    source_text: "",
    route_evidence: {},
  };
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/code-applications/")) return incompleteRows;
      if (path.includes("/reconciliation-decisions")) return makeReconciliationDecisions("run-coverage-gap", 12);
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [{ id: "run-coverage-gap" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-coverage-gap",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        kappa: 0.81,
        alpha: 0.79,
        route_evidence: makeServedModelRoutes(),
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-coverage-gap",
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
  assert.match(blockers[0], /complete coder-by-evidence-unit coverage/i);
  assert.equal(logger.issues[0].evidence.application_coverage.invalid_rows.length, 1);
  assert.deepEqual(logger.issues[0].evidence.application_coverage.missing_pairs, [
    { coder_id: "coder-1", evidence_unit_id: "eu-4" },
  ]);
});

test("three-model coding cannot trust a backend count without three served route identities", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/code-applications/")) return makeReconciledApplications("run-route-model-gap");
      if (path.includes("/reconciliation-decisions")) return makeReconciliationDecisions("run-route-model-gap");
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [{ id: "run-route-model-gap" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-route-model-gap",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        kappa: 0.81,
        alpha: 0.79,
        route_evidence: [
          { node_id: "donor-a", model: "model-a", outcome: "served" },
          { node_id: "donor-b", model: "model-b", outcome: "served" },
        ],
      };
    },
  };

  await exerciseResearchSpineValidation({
    api,
    projectId: "project-route-model-gap",
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
  assert.match(blockers[0], /only 2\/3 distinct served model identities/);
  assert.deepEqual(logger.issues[0].evidence.served_model_identities, ["model-a", "model-b"]);
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
        route_evidence: makeServedModelRoutes(),
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
  assert.equal(featureResults.ensembleCodingValidation, true);
  assert.equal(featureResults.multiModelResearchSpineValidation, false);
  assert.equal(blockers.length, 1);
  assert.match(blockers[0], /reconciliation decisions/i);
  assert.equal(logger.issues[0].title, "Research Spine reconciliation was not proven");
});

test("opt-in synthetic reconciliation proves receipts without changing the human gate", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  let syntheticPayload = null;
  let syntheticOptions = null;
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/code-applications/")) {
        return makeReconciledApplications("run-synthetic").map((row) => ({
          ...row,
          reconciliation_status: "unreconciled",
          review_status: "pending",
          promotion_status: "blocked",
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
    async post(path, payload, options) {
      if (path.includes("/synthetic-reconciliation")) {
        syntheticPayload = payload;
        syntheticOptions = options;
        return {
          source: "benchmark_synthetic",
          accepted_reportable: false,
          human_review_required: true,
          decisions: payload.decisions.map((decision) => ({
            ...decision,
            source: "benchmark_synthetic",
          })),
        };
      }
      return {
        id: "run-synthetic",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        kappa: 0.81,
        alpha: 0.79,
        route_evidence: makeServedModelRoutes(),
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
    syntheticReconciliationEnabled: true,
  });

  assert.equal(featureResults.syntheticReconciliationValidation, true);
  assert.equal(featureResults.ensembleCodingValidation, true);
  assert.equal(featureResults.multiModelResearchSpineValidation, false);
  assert.equal(syntheticPayload.coding_run_id, "run-synthetic");
  assert.equal(syntheticPayload.decisions.length, 12);
  assert.equal(syntheticOptions.headers["x-istara-synthetic-reconciliation"], "benchmark-v1");
  assert.ok(logger.actions.find((entry) => entry.step === "research_spine.ensemble_coding"));
  assert.deepEqual(blockers, [
    "Research Spine reliability passed, but 0/12 code applications have accepted reconciliation decisions (0 linked decisions for 12 applications).",
  ]);
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
        route_evidence: makeServedModelRoutes(),
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
        route_evidence: makeServedModelRoutes(),
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

test("three-donor benchmark rejects impossible out-of-range reliability metrics", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/code-applications/")) return makeReconciledApplications("run-invalid-metrics");
      if (path.includes("/reconciliation-decisions")) return makeReconciliationDecisions("run-invalid-metrics");
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [{ id: "run-invalid-metrics" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-invalid-metrics",
        status: "completed",
        promotion_status: "accepted",
        code_application_count: 12,
        reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
        distinct_model_count: 3,
        rater_count: 3,
        threshold: 0.6,
        // These values must never certify an accepted run, even if a malformed
        // adapter or fixture reports them as finite numeric values.
        kappa: 9,
        alpha: 2,
        route_evidence: makeServedModelRoutes(),
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
  assert.match(blockers[0], /out-of-range reliability metrics/i);
  assert.equal(logger.issues[0].evidence.kappa_in_range, false);
  assert.equal(logger.issues[0].evidence.alpha_in_range, false);
  assert.equal(logger.issues[0].evidence.reliability_metric_bounds_ok, false);
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
          { node_id: "host-donor", model: "model-a", outcome: "served" },
          { node_id: "colima-donor-a", model: "model-b", outcome: "served" },
          { node_id: "host-donor", model: "model-c", outcome: "served" },
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
          { node_id: "host-donor", model: "model-a", outcome: "served" },
          { node_id: "colima-donor-a", model: "model-b", outcome: "served" },
          { node_id: "colima-donor-b", model: "model-c", outcome: "served" },
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
        route_evidence: makeServedModelRoutes(),
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
    started_at: new Date().toISOString(),
    promotion_status: "accepted",
    code_application_count: 12,
    reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
    distinct_model_count: 3,
    rater_count: 3,
    kappa: 0.81,
    alpha: 0.79,
    route_evidence: [
      { node_id: "host-donor", model: "model-a", outcome: "served" },
      { node_id: "colima-donor-a", model: "model-b", outcome: "served" },
      { node_id: "colima-donor-b", model: "model-c", outcome: "served" },
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

test("timed-out coding validation rejects a stale completed run", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const staleRun = {
    id: "run-stale",
    status: "completed",
    started_at: new Date(Date.now() - 3600000).toISOString(),
    promotion_status: "accepted",
    code_application_count: 12,
    reliability_method: "fleiss_kappa_with_krippendorff_alpha_companion",
    distinct_model_count: 3,
    rater_count: 3,
    kappa: 0.81,
    alpha: 0.79,
    route_evidence: makeServedModelRoutes(),
  };
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return makeSubstantiveUnits();
      if (path.includes("/coding-runs")) return [staleRun];
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

  assert.equal(featureResults.codingValidation, false);
  assert.equal(featureResults.multiModelResearchSpineValidation, false);
  assert.equal(blockers.length, 1);
  assert.match(blockers[0], /did not complete/i);
  assert.ok(logger.actions.find((entry) => entry.step === "research_spine.coding_run_recovery.stale"));
  assert.equal(logger.actions.some((entry) => entry.step === "research_spine.coding_run_recovered"), false);
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
        route_evidence: makeServedModelRoutes(),
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
        route_evidence: makeServedModelRoutes(),
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
