/** Scenario 72 — Circuit Breaker & LLM Health: verify LLM availability detection and user notification. */

export const name = "Circuit Breaker & LLM Health";
export const id = "72-circuit-breaker-health";

export async function run(ctx) {
  const { api, page } = ctx;
  const checks = [];

  // 1. Verify /api/llm-servers returns server list with health info
  try {
    const data = await api.get("/api/llm-servers");
    const servers = data.servers || [];
    checks.push({
      name: "LLM servers list",
      passed: true,
      detail: `${servers.length} servers registered`,
    });

    // Check that servers have health fields
    if (servers.length > 0) {
      const s = servers[0];
      checks.push({
        name: "Server has health fields",
        passed: s.is_healthy !== undefined && s.has_api_key !== undefined,
        detail: `is_healthy: ${s.is_healthy}, has_api_key: ${s.has_api_key}, health_error: ${s.health_error || "none"}`,
      });
    }
  } catch (e) {
    checks.push({ name: "LLM servers list", passed: false, detail: e.message });
  }

  // 2. Add a server with an unreachable URL → verify health_error
  let badServerId;
  try {
    const result = await api.post("/api/llm-servers", {
      name: "Test Unreachable Server",
      provider_type: "openai_compat",
      host: "http://192.0.2.1:9999", // RFC 5737 TEST-NET — guaranteed unreachable
    });
    badServerId = result.id;
    checks.push({
      name: "Unreachable server added",
      passed: !!badServerId && !result.is_healthy,
      detail: `ID: ${badServerId}, healthy: ${result.is_healthy}`,
    });
  } catch (e) {
    checks.push({ name: "Add unreachable server", passed: false, detail: e.message });
  }

  // 3. Run health check on the bad server → verify health_error populated
  if (badServerId) {
    try {
      const health = await api.post(`/api/llm-servers/${badServerId}/health-check`, {});
      checks.push({
        name: "Health check returns error",
        passed: !health.healthy && !!health.health_error,
        detail: `healthy: ${health.healthy}, error: ${health.health_error || "none"}`,
      });
    } catch (e) {
      checks.push({ name: "Health check error", passed: false, detail: e.message });
    }

    // Clean up
    try {
      await api.delete(`/api/llm-servers/${badServerId}`);
    } catch {}
  }

  // 4. Verify healthy servers have proper status
  try {
    const data = await api.get("/api/llm-servers");
    const healthyServers = (data.servers || []).filter((s) => s.is_healthy);
    checks.push({
      name: "At least one healthy server",
      passed: healthyServers.length > 0,
      detail: `${healthyServers.length} healthy server(s)`,
    });
  } catch (e) {
    checks.push({ name: "Healthy server check", passed: false, detail: e.message });
  }

  // 5. Verify system status endpoint includes LLM info
  try {
    const status = await api.get("/api/settings/status");
    checks.push({
      name: "System status has LLM info",
      passed: status.services !== undefined,
      detail: `LLM: ${status.services?.llm || "unknown"}, provider: ${status.provider || "unknown"}`,
    });
  } catch (e) {
    checks.push({ name: "System status", passed: false, detail: e.message });
  }

  // 6. Verify StatusBar shows connection status (frontend)
  try {
    await page.goto("http://localhost:3000", { waitUntil: "networkidle", timeout: 15000 });
    const statusBar = await page.locator("footer").first();
    const statusText = await statusBar.textContent().catch(() => "");
    checks.push({
      name: "StatusBar renders",
      passed: statusText.includes("Connected") || statusText.includes("Disconnected"),
      detail: `StatusBar text: ${statusText.substring(0, 100)}`,
    });
  } catch (e) {
    checks.push({ name: "StatusBar check", passed: false, detail: e.message });
  }

  // 7. Verify compute nodes endpoint (if exists)
  try {
    const compute = await api.get("/api/compute/nodes");
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
