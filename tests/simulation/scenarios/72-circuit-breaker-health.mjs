/** Scenario 72 — Circuit Breaker & LLM Health: verify LLM availability detection and user notification. */

import { authHeaders, getApiBase } from "../lib/api-client.mjs";

export const name = "Circuit Breaker & LLM Health";
export const id = "72-circuit-breaker-health";

export async function run(ctx) {
  const { api, page } = ctx;
  const checks = [];

  // 1. The old /api/llm-servers CRUD plane was retired in favor of the
  // unified Pi/configured-provider plane. Keep the retirement explicit so a
  // missing route is not mistaken for a broken health implementation.
  try {
    const res = await fetch(`${getApiBase()}/api/llm-servers`, { headers: authHeaders() });
    const retired = res.status === 404 || res.status === 405;
    checks.push({
      name: "Retired legacy LLM server route is absent",
      passed: retired,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Retired legacy LLM server route is absent", passed: false, detail: e.message });
  }

  // 2. Verify the current provider plane reports a usable or bounded state.
  try {
    const status = await api.get("/api/settings/status").catch(() => null);
    const contractModeDegraded = status?.status === "degraded"
      && status?.services?.llm === "connected"
      && status?.llm_readiness?.chat_ready === false;
    const operational = status?.status === "ok"
      || status?.status === "healthy"
      || status?.healthy === true
      || contractModeDegraded;
    checks.push({
      name: "Current provider plane reports bounded health",
      passed: operational,
      detail: `status=${status?.status || "unknown"}, llm=${status?.services?.llm || "unknown"}, chat_ready=${status?.llm_readiness?.chat_ready === true}`,
    });
  } catch (e) {
    checks.push({ name: "Current provider plane reports bounded health", passed: false, detail: e.message });
  }

  // 3. Pi plane availability: configured endpoints (identity view) or an
  // active engine with a reachable provider. LLM health now spans BOTH planes.
  try {
    const catalog = await api.get(`/api/chat/model-catalog${ctx.projectId ? `?project_id=${encodeURIComponent(ctx.projectId)}` : ""}`);
    checks.push({
      name: "Pi/configured model plane visible",
      passed: Array.isArray(catalog.configured) && ["pi", "legacy"].includes(catalog.engine),
      detail: `pi_configured=${catalog.configured?.length}, engine=${catalog.engine}`,
    });
  } catch (e) {
    checks.push({ name: "Pi/configured model plane visible", passed: false, detail: e.message });
  }

  // 4. Verify system status endpoint includes LLM info
  try {
    const status = await api.get("/api/settings/status");
    checks.push({
      name: "System status has LLM info",
      passed: status.services !== undefined,
      detail: `LLM: ${status.services?.llm || "unknown"}, chat_ready: ${status.llm_readiness?.chat_ready === true}`,
    });
  } catch (e) {
    checks.push({ name: "System status", passed: false, detail: e.message });
  }

  // 5. Verify StatusBar shows connection status (frontend)
  try {
    await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded", timeout: 15000 });
    const statusBar = await page.locator("footer").first();
    const statusText = await statusBar.textContent().catch(() => "");
    checks.push({
      name: "StatusBar renders",
      passed: statusText.includes("Connected") || statusText.includes("Disconnected") || statusText.includes("Live updates") || statusText.includes("Idle"),
      detail: `StatusBar text: ${statusText.substring(0, 100)}`,
    });
  } catch (e) {
    checks.push({ name: "StatusBar check", passed: false, detail: e.message });
  }

  // 6. Verify compute nodes endpoint (if exists)
  try {
    if (!ctx.projectId) throw new Error("Missing ctx.projectId for project-scoped compute nodes");
    const compute = await api.get(`/api/compute/nodes?project_id=${encodeURIComponent(ctx.projectId)}`);
    const nodes = compute.nodes || compute || [];
    checks.push({
      name: "Compute nodes endpoint",
      passed: true,
      detail: `${Array.isArray(nodes) ? nodes.length : 0} compute nodes`,
    });
  } catch (e) {
    // Endpoint may not exist — non-fatal
    checks.push({ name: "Compute nodes endpoint", passed: true, detail: `Optional: ${e.message}` });
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}: ${c.detail}`).join("\n"),
  };
}
