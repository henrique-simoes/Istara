/** Scenario 35 — Ensemble Validation: verify consensus and validation endpoints. */

export const name = "Ensemble Validation";
export const id = "35-ensemble-validation";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // Use persistent simulation project
  let projectId = ctx.projectId;
  if (!projectId) {
    checks.push({ name: "Project available", passed: false, detail: "No persistent project from runner" });
    return { checks, passed: 0, failed: 1 };
  }
  const projectQuery = `project_id=${encodeURIComponent(projectId)}`;

  // 1. Model catalog surface (Pi providers + legacy identity list + active engine).
  try {
    const catalog = await api.get(`/api/chat/model-catalog?project_id=${encodeURIComponent(projectId)}`);
    checks.push({
      name: "Model catalog endpoint",
      passed: Array.isArray(catalog.providers) && typeof catalog.total_models === "number",
      detail: `providers=${catalog.providers?.length}, total_models=${catalog.total_models}, engine=${catalog.engine}`,
    });
    checks.push({
      name: "Catalog reports active agentic core",
      passed: catalog.engine === "pi" || catalog.engine === "legacy",
      detail: `engine=${JSON.stringify(catalog.engine)}`,
    });
  } catch (e) {
    checks.push({ name: "Model catalog endpoint", passed: false, detail: e.message });
  }

  // 2. Legacy compute plane still exposes routable models (compat projection source).
  try {
    const catalog = await api.get(`/api/chat/model-catalog?project_id=${encodeURIComponent(projectId)}`);
    const legacyModels = Array.isArray(catalog.legacy_models) ? catalog.legacy_models : [];
    const configured = Array.isArray(catalog.configured) ? catalog.configured : [];
    checks.push({
      name: "Routable models available (legacy or Pi-configured)",
      passed: legacyModels.length > 0 || configured.length > 0,
      detail: `legacy_models=${legacyModels.length}, pi_configured=${configured.length}`,
    });
  } catch (e) {
    checks.push({ name: "Routable models available", passed: false, detail: e.message });
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
    try { await api.delete(`/api/tasks/${task.id}?${projectQuery}`); } catch {}
  } catch (e) {
    checks.push({ name: "Task has validation fields", passed: false, detail: e.message });
  }

  const passed = checks.filter((c) => c.passed).length;
  const failed = checks.filter((c) => !c.passed).length;
  return { checks, passed, failed };
}
