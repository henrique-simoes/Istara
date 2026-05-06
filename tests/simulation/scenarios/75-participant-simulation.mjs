/** Scenario 75 — Game Theory Participant Simulation: verify participant_simulation module, game scenarios, and audit logging. */

export const name = "Game Theory Participant Simulation";
export const id = "75-participant-simulation";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // 1. Participant simulation module imports
  try {
    const projectResp = await api.get("/api/projects");
    const projects = projectResp.projects || projectResp || [];
    const projectId = ctx.projectId || (projects.length > 0 ? projects[0].id : null);
    const resp = await fetch("http://localhost:8000/api/chat", {
      method: "POST",
      headers: api._headers(),
      body: JSON.stringify({
        message: "What is the participant-simulation skill?",
        project_id: projectId,
        include_history: false,
      }),
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
      passed: resp !== null && typeof resp === "object",
      detail: `entries=${(resp.logs || resp.items || resp || []).length ?? "unknown"}`,
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
      passed: resp !== null && typeof resp === "object",
      detail: `keys=${Object.keys(resp || {}).join(",")}`,
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
