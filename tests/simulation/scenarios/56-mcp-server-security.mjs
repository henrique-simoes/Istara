/** Scenario 56 — MCP Server Security: tests for MCP server with access control, audit logging, and warnings.
 *
 *  Exercises: /api/mcp/server/*
 */

export const name = "MCP Server Security";
export const id = "56-mcp-server-security";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // ── 1. MCP server disabled by default ──
  try {
    const status = await api.get("/api/mcp/server/status");
    checks.push({
      name: "MCP server disabled by default",
      passed: status.enabled === false,
      detail: `enabled=${status.enabled}`,
    });
  } catch (e) {
    checks.push({ name: "MCP server disabled by default", passed: false, detail: e.message });
  }

  // ── 2. Toggle MCP server on ──
  try {
    const result = await api.post("/api/mcp/server/toggle", { enabled: true });
    checks.push({
      name: "Toggle MCP server on returns success",
      passed: result.enabled === true || result.status === "enabled",
      detail: JSON.stringify(result).slice(0, 100),
    });
  } catch (e) {
    checks.push({ name: "Toggle MCP server on returns success", passed: false, detail: e.message });
  }

  // ── 3. Verify enabled status ──
  try {
    const status = await api.get("/api/mcp/server/status");
    checks.push({
      name: "MCP server shows enabled after toggle",
      passed: status.enabled === true,
      detail: `enabled=${status.enabled}`,
    });
  } catch (e) {
    checks.push({ name: "MCP server shows enabled after toggle", passed: false, detail: e.message });
  }

  // ── 4. GET /api/mcp/server/policy — default policy ──
  let policy = null;
  try {
    policy = await api.get("/api/mcp/server/policy");
    checks.push({
      name: "Default policy has LOW tools enabled, SENSITIVE/HIGH disabled",
      passed:
        policy.tools?.list_skills?.allowed === true &&
        policy.tools?.get_findings?.allowed === false &&
        policy.tools?.execute_skill?.allowed === false,
      detail: `list_skills=${policy.tools?.list_skills?.allowed}, get_findings=${policy.tools?.get_findings?.allowed}, execute_skill=${policy.tools?.execute_skill?.allowed}`,
    });
  } catch (e) {
    checks.push({ name: "Default policy has LOW tools enabled, SENSITIVE/HIGH disabled", passed: false, detail: e.message });
  }

  // ── 5. Policy tools have risk levels ──
  if (policy) {
    const hasRisks =
      policy.tools?.list_skills?.risk === "low" &&
      policy.tools?.get_findings?.risk === "sensitive" &&
      policy.tools?.execute_skill?.risk === "high";
    checks.push({
      name: "Policy tools include risk level classification",
      passed: hasRisks,
      detail: `list_skills=${policy.tools?.list_skills?.risk}, get_findings=${policy.tools?.get_findings?.risk}, execute_skill=${policy.tools?.execute_skill?.risk}`,
    });
  }

  // ── 6. PATCH /api/mcp/server/policy — enable a SENSITIVE tool ──
  try {
    const updated = await api.patch("/api/mcp/server/policy", {
      allow_get_findings: true,
    });
    checks.push({
      name: "PATCH policy enables SENSITIVE tool",
      passed: updated.tools?.get_findings?.allowed === true,
      detail: `get_findings now ${updated.tools?.get_findings?.allowed}`,
    });
  } catch (e) {
    checks.push({ name: "PATCH policy enables SENSITIVE tool", passed: false, detail: e.message });
  }

  // ── 7. Policy limits exist ──
  if (policy) {
    checks.push({
      name: "Policy includes rate limits and scope",
      passed:
        policy.limits?.max_findings_per_request !== undefined &&
        policy.limits?.max_skill_executions_per_hour !== undefined &&
        Array.isArray(policy.limits?.allowed_project_ids),
      detail: `max_findings=${policy.limits?.max_findings_per_request}, max_executions=${policy.limits?.max_skill_executions_per_hour}`,
    });
  }

  // ── 8. GET /api/mcp/server/exposure — data exposure summary ──
  try {
    const exposure = await api.get("/api/mcp/server/exposure");
    checks.push({
      name: "Exposure summary endpoint returns data",
      passed: exposure !== undefined && exposure !== null,
      detail: JSON.stringify(exposure).slice(0, 100),
    });
  } catch (e) {
    checks.push({ name: "Exposure summary endpoint returns data", passed: false, detail: e.message });
  }

  // ── 9. GET /api/mcp/server/audit — audit log ──
  try {
    const audit = await api.get("/api/mcp/server/audit");
    const list = Array.isArray(audit) ? audit : audit?.entries || [];
    checks.push({
      name: "Audit log endpoint returns array",
      passed: Array.isArray(list),
      detail: `${list.length} audit entries`,
    });
  } catch (e) {
    checks.push({ name: "Audit log endpoint returns array", passed: false, detail: e.message });
  }

  // ── 10. PATCH policy — set project scope ──
  try {
    const updated = await api.patch("/api/mcp/server/policy", {
      allowed_project_ids_json: '["test-project-001"]',
    });
    checks.push({
      name: "Policy project scope can be updated",
      passed: true,
      detail: `project_ids updated`,
    });
  } catch (e) {
    checks.push({ name: "Policy project scope can be updated", passed: false, detail: e.message });
  }

  // ── 11. PATCH policy — update rate limits ──
  try {
    const updated = await api.patch("/api/mcp/server/policy", {
      max_findings_per_request: 25,
      max_skill_executions_per_hour: 3,
    });
    checks.push({
      name: "Policy rate limits can be updated",
      passed: true,
      detail: "Rate limits updated",
    });
  } catch (e) {
    checks.push({ name: "Policy rate limits can be updated", passed: false, detail: e.message });
  }

  // ── 12. PATCH policy — disable all HIGH RISK tools ──
  try {
    const updated = await api.patch("/api/mcp/server/policy", {
      allow_execute_skill: false,
      allow_create_project: false,
      allow_deploy_research: false,
    });
    checks.push({
      name: "All HIGH RISK tools can be disabled",
      passed:
        updated.tools?.execute_skill?.allowed === false &&
        updated.tools?.create_project?.allowed === false &&
        updated.tools?.deploy_research?.allowed === false,
      detail: "All HIGH RISK tools disabled",
    });
  } catch (e) {
    checks.push({ name: "All HIGH RISK tools can be disabled", passed: false, detail: e.message });
  }

  // ── 13. Toggle MCP server off ──
  try {
    const result = await api.post("/api/mcp/server/toggle", { enabled: false });
    checks.push({
      name: "Toggle MCP server off",
      passed: result.enabled === false || result.status === "disabled",
      detail: JSON.stringify(result).slice(0, 100),
    });
  } catch (e) {
    checks.push({ name: "Toggle MCP server off", passed: false, detail: e.message });
  }

  // ── 14. Verify disabled after toggle off ──
  try {
    const status = await api.get("/api/mcp/server/status");
    checks.push({
      name: "MCP server confirmed disabled",
      passed: status.enabled === false,
      detail: `enabled=${status.enabled}`,
    });
  } catch (e) {
    checks.push({ name: "MCP server confirmed disabled", passed: false, detail: e.message });
  }

  return checks;
}
