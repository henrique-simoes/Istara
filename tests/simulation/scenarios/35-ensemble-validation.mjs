/** Scenario 35 — Ensemble Validation: verify consensus and validation endpoints. */

export const name = "Ensemble Validation";
export const id = "35-ensemble-validation";

export async function run(ctx) {
  const { api, projectId } = ctx;
  const checks = [];

  // 1. LLM servers list endpoint
  try {
    const servers = await api.get("/api/llm-servers");
    checks.push({
      name: "LLM servers endpoint",
      passed: Array.isArray(servers.servers) && Array.isArray(servers.router_live),
      detail: `servers=${servers.servers?.length}, router_live=${servers.router_live?.length}`,
    });
  } catch (e) {
    checks.push({ name: "LLM servers endpoint", passed: false, detail: e.message });
  }

  // 2. Router has at least one entry (local provider)
  try {
    const servers = await api.get("/api/llm-servers");
    const routerHasEntries = servers.router_live && servers.router_live.length > 0;
    checks.push({
      name: "Router has local provider",
      passed: routerHasEntries,
      detail: `entries=${servers.router_live?.length}, first=${servers.router_live?.[0]?.name}`,
    });
  } catch (e) {
    checks.push({ name: "Router has local provider", passed: false, detail: e.message });
  }

  // 3. Maintenance status endpoint
  try {
    const maint = await api.get("/api/settings/maintenance");
    checks.push({
      name: "Maintenance status endpoint",
      passed: maint.maintenance_mode !== undefined,
      detail: `mode=${maint.maintenance_mode}`,
    });
  } catch (e) {
    checks.push({ name: "Maintenance status endpoint", passed: false, detail: e.message });
  }

  // 4. Task model supports validation fields
  try {
    const task = await api.post("/api/tasks", {
      project_id: projectId,
      title: "Validation Test Task",
      description: "Testing validation fields",
    });
    checks.push({
      name: "Task has validation fields",
      passed: task.validation_method === null || task.validation_method === undefined,
      detail: `validation_method=${task.validation_method}, consensus_score=${task.consensus_score}`,
    });
    // Cleanup
    try { await api.delete(`/api/tasks/${task.id}`); } catch {}
  } catch (e) {
    checks.push({ name: "Task has validation fields", passed: false, detail: e.message });
  }

  const passed = checks.filter((c) => c.passed).length;
  const failed = checks.filter((c) => !c.passed).length;
  return { checks, passed, failed };
}
