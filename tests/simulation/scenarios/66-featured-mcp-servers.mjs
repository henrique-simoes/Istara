/** Scenario 66 — Featured MCP Servers: tests for the pre-configured MCP server catalog.
 *
 *  Exercises: /api/mcp/featured/*
 */

export const name = "Featured MCP Servers";
export const id = "66-featured-mcp-servers";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // ── 1. GET /api/mcp/featured — returns array of featured servers ──
  let featured = [];
  try {
    featured = await api.get("/api/mcp/featured");
    checks.push({
      name: "GET /api/mcp/featured returns array",
      passed: Array.isArray(featured) && featured.length >= 1,
      detail: `${featured.length} featured servers`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/mcp/featured returns array", passed: false, detail: e.message });
  }

  // ── 2. MCP Brasil is in the list ──
  const brasil = featured.find((s) => s.id === "mcp-brasil");
  checks.push({
    name: "MCP Brasil is listed as featured",
    passed: !!brasil,
    detail: brasil ? `name=${brasil.name}, tools=${brasil.tool_count}` : "NOT FOUND",
  });

  // ── 3. MCP Brasil has 213 tools ──
  if (brasil) {
    checks.push({
      name: "MCP Brasil reports 213 tools",
      passed: brasil.tool_count === 213,
      detail: `tool_count=${brasil.tool_count}`,
    });
  }

  // ── 4. GET /api/mcp/featured/mcp-brasil — single server detail ──
  try {
    const detail = await api.get("/api/mcp/featured/mcp-brasil");
    checks.push({
      name: "GET /api/mcp/featured/mcp-brasil returns full detail",
      passed: detail.id === "mcp-brasil" && detail.features && detail.features.length > 0,
      detail: `features=${detail.features?.length}, categories=${detail.categories?.length}`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/mcp/featured/mcp-brasil returns detail", passed: false, detail: e.message });
  }

  // ── 5. Featured server has required fields ──
  if (brasil) {
    const requiredFields = ["id", "name", "description", "package", "repository", "license", "tool_count", "categories", "features"];
    const hasAll = requiredFields.every((f) => brasil[f] !== undefined);
    checks.push({
      name: "Featured server has all required fields",
      passed: hasAll,
      detail: `Checked: ${requiredFields.join(", ")}`,
    });
  }

  // ── 6. Features list includes key APIs ──
  if (brasil && brasil.features) {
    const featureNames = brasil.features.map((f) => f.name);
    const hasKey = featureNames.some((n) => n.includes("Banco Central") || n.includes("BCB"));
    checks.push({
      name: "Features include Banco Central",
      passed: hasKey,
      detail: `Features: ${featureNames.slice(0, 5).join(", ")}...`,
    });
  }

  // ── 7. UX research applications present ──
  if (brasil) {
    checks.push({
      name: "UX research applications listed",
      passed: brasil.ux_research_applications && brasil.ux_research_applications.length >= 3,
      detail: `${brasil.ux_research_applications?.length || 0} applications`,
    });
  }

  // ── 8. Environment variables documented ──
  if (brasil) {
    checks.push({
      name: "Environment variables documented",
      passed: brasil.env_vars && brasil.env_vars.length >= 2,
      detail: `${brasil.env_vars?.length || 0} env vars: ${(brasil.env_vars || []).map((v) => v.name).join(", ")}`,
    });
  }

  // ── 9. Unknown featured server returns 404 ──
  try {
    await api.get("/api/mcp/featured/nonexistent-server");
    checks.push({ name: "Unknown featured server returns 404", passed: false, detail: "Should have thrown" });
  } catch (e) {
    checks.push({
      name: "Unknown featured server returns 404",
      passed: e.message.includes("404") || e.message.includes("not found"),
      detail: e.message.slice(0, 80),
    });
  }

  // ── 10. Connect endpoint exists (will fail without actual server running) ──
  try {
    await api.post("/api/mcp/featured/mcp-brasil/connect", { env_vars: {} });
    checks.push({
      name: "Connect endpoint responds",
      passed: true,
      detail: "Connection initiated (server may not be running)",
    });
  } catch (e) {
    checks.push({
      name: "Connect endpoint responds (graceful error if server not running)",
      passed: !e.message.includes("500"),
      detail: e.message.slice(0, 100),
    });
  }

  return checks;
}
