import assert from "node:assert/strict";
import test from "node:test";

import {
  SIMULATION_PROJECT_NAME,
  isProjectPaused,
  projectScopedPath,
  requireActiveProjectId,
  selectCanonicalSimulationProject,
} from "./project-selection.mjs";

test("selectCanonicalSimulationProject selects the known simulation project among many admin projects", () => {
  const projects = [
    { id: "real-first-project", name: "Executive Research Archive" },
    { id: "old-sim-one", name: "[SIM-21] Previous Harness Run" },
    { id: "canonical", name: SIMULATION_PROJECT_NAME },
    { id: "old-sim-two", name: "[SIM] Legacy Smoke Project" },
    { id: "real-last-project", name: "Customer Interviews" },
  ];

  const selected = selectCanonicalSimulationProject(projects);

  assert.equal(selected.canonical.id, "canonical");
  assert.deepEqual(
    selected.staleProjects.map((project) => project.id).sort(),
    ["old-sim-one", "old-sim-two"],
  );
  assert.ok(!selected.staleProjects.some((project) => project.id === "real-first-project"));
});

test("selectCanonicalSimulationProject does not reuse paused simulation projects", () => {
  const selected = selectCanonicalSimulationProject([
    { id: "paused-canonical", name: SIMULATION_PROJECT_NAME, is_paused: true },
    { id: "paused-legacy", name: "[SIM] Legacy Smoke Project", status: "paused" },
    { id: "active-legacy", name: "[SIM-21] Previous Harness Run", is_paused: false },
    { id: "real-project", name: "Customer Interviews", is_paused: false },
  ]);

  assert.equal(selected.canonical, null);
  assert.deepEqual(selected.activeSimProjects.map((project) => project.id), ["active-legacy"]);
  assert.deepEqual(
    selected.pausedSimProjects.map((project) => project.id).sort(),
    ["paused-canonical", "paused-legacy"],
  );
  assert.deepEqual(selected.staleProjects.map((project) => project.id), ["active-legacy"]);
});

test("selectCanonicalSimulationProject does not fall back to the first project", () => {
  const selected = selectCanonicalSimulationProject([
    { id: "admin-first-project", name: "Admin Project 001" },
    { id: "research", name: "Research Repository" },
  ]);

  assert.equal(selected.canonical, null);
  assert.deepEqual(selected.simProjects, []);
  assert.deepEqual(selected.staleProjects, []);
});

test("isProjectPaused recognizes current paused-project shapes", () => {
  assert.equal(isProjectPaused({ is_paused: true }), true);
  assert.equal(isProjectPaused({ paused: true }), true);
  assert.equal(isProjectPaused({ status: "paused" }), true);
  assert.equal(isProjectPaused({ status: "active" }), false);
});

test("requireActiveProjectId rejects empty project ids and trims real ids", () => {
  assert.equal(requireActiveProjectId("  project-123  "), "project-123");
  assert.throws(() => requireActiveProjectId(""), /explicit active project_id/);
  assert.throws(() => requireActiveProjectId(null), /explicit active project_id/);
});

test("projectScopedPath preserves existing query params while adding project_id", () => {
  assert.equal(
    projectScopedPath("/api/tasks?status=open", "project 123"),
    "/api/tasks?status=open&project_id=project+123",
  );
});
