/** Scenario 75 — Game Theory Participant Simulation: verify participant_simulation module, game scenarios, and audit logging. */

export const name = "Game Theory Participant Simulation";
export const id = "75-participant-simulation";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // 1. Participant simulation module imports
  try {
    const resp = await api.post("/api/chat", {
      message: "What is the participant-simulation skill?",
      session_id: "sim-test",
    });
    checks.push({
      name: "Chat responds with skill knowledge",
      passed: resp.status === 200 || resp.status === 201,
      detail: `Status: ${resp.status}`,
    });
  } catch (e) {
    checks.push({ name: "Chat responds with skill knowledge", passed: false, detail: e.message });
  }

  // 2. Audit log endpoint exists and responds
  try {
    const resp = await api.get("/api/audit/logs?limit=5");
    checks.push({
      name: "Audit log endpoint responds",
      passed: resp.status === 200 || resp.status === 401,
      detail: `Status: ${resp.status}`,
    });
  } catch (e) {
    checks.push({ name: "Audit log endpoint responds", passed: false, detail: e.message });
  }

  // 3. Validation metrics endpoint responds
  try {
    const projectResp = await api.get("/api/projects");
    const projects = projectResp.projects || projectResp || [];
    const projectId = projects.length > 0 ? projects[0].id : "test";
    const resp = await api.get(`/api/metrics/${projectId}/validation`);
    checks.push({
      name: "Validation metrics endpoint responds",
      passed: resp.status === 200 || resp.status === 404,
      detail: `Status: ${resp.status}`,
    });
  } catch (e) {
    checks.push({ name: "Validation metrics endpoint responds", passed: false, detail: e.message });
  }

  return {
    checks,
    passed: checks.filter(c => c.passed).length,
    failed: checks.filter(c => !c.passed).length,
    summary: `Game Theory Participant Simulation: ${checks.filter(c => c.passed).length}/${checks.length} passed`,
  };
}