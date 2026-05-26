import assert from "node:assert/strict";
import test from "node:test";

import { exerciseResearchSpineValidation } from "./research-spine-probes.mjs";

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

test("three-donor benchmark blocks when coding falls back to single-coder assurance", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return [{ id: "eu-1" }];
      if (path.includes("/coding-runs")) return [{ id: "run-1" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-1",
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
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return [{ id: "eu-1" }];
      if (path.includes("/coding-runs")) return [{ id: "run-1" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-1",
        reliability_method: "fleiss_kappa",
        distinct_model_count: 3,
        rater_count: 3,
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

test("three-donor benchmark requires three served donor routes, not only three model aliases", async () => {
  const logger = makeLogger();
  const blockers = [];
  const featureResults = {};
  const api = {
    async get(path) {
      if (path === "/api/research-validity/contract") {
        return { contract: {}, qualitative_coding_protocol: {} };
      }
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return [{ id: "eu-1" }];
      if (path.includes("/coding-runs")) return [{ id: "run-1" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-1",
        reliability_method: "fleiss_kappa",
        distinct_model_count: 3,
        rater_count: 3,
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
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return [{ id: "eu-1" }];
      if (path.includes("/coding-runs")) return [{ id: "run-1" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post() {
      return {
        id: "run-1",
        reliability_method: "fleiss_kappa",
        distinct_model_count: 3,
        rater_count: 3,
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
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return [{ id: "eu-1" }];
      if (path.includes("/coding-runs")) return [{ id: "run-1" }];
      if (path.includes("/traceability")) return { edges: [] };
      if (path.includes("/telemetry-audit")) return { status: "ok" };
      return {};
    },
    async post(_path, payload) {
      codingPayload = payload;
      return {
        id: "run-1",
        reliability_method: "fleiss_kappa",
        distinct_model_count: 3,
        rater_count: 3,
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
      if (path.includes("/evidence-units")) return [{ id: "eu-1" }];
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
    reliability_method: "fleiss_kappa",
    distinct_model_count: 3,
    rater_count: 3,
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
      if (path.includes("/summary")) return { coding_run_count: 1, evidence_unit_count: 4 };
      if (path.includes("/evidence-units")) return [{ id: "eu-1" }];
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
