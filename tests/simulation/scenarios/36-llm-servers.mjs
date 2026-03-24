/** Scenario 36 — LLM Servers: verify external server CRUD and health checks. */

export const name = "LLM Servers";
export const id = "36-llm-servers";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];
  let serverId;

  // 1. List servers (initially may have none persisted)
  try {
    const list = await api.get("/api/llm-servers");
    checks.push({
      name: "List LLM servers",
      passed: Array.isArray(list.servers),
      detail: `count=${list.servers?.length}`,
    });
  } catch (e) {
    checks.push({ name: "List LLM servers", passed: false, detail: e.message });
  }

  // 2. Add a test server (non-existent host — should add but be unhealthy)
  try {
    const added = await api.post("/api/llm-servers", {
      name: "Test Server",
      provider_type: "openai_compat",
      host: "http://192.0.2.1:9999",  // RFC 5737 test address — guaranteed unreachable
      priority: 100,
    });
    serverId = added.id;
    checks.push({
      name: "Add LLM server",
      passed: !!added.id && added.name === "Test Server",
      detail: `id=${added.id}, healthy=${added.is_healthy}`,
    });
  } catch (e) {
    checks.push({ name: "Add LLM server", passed: false, detail: e.message });
  }

  // 3. Health check on added server (should be unhealthy)
  if (serverId) {
    try {
      const health = await api.post(`/api/llm-servers/${serverId}/health-check`, {});
      checks.push({
        name: "Health check (unreachable server)",
        passed: health.healthy === false,
        detail: `healthy=${health.healthy}`,
      });
    } catch (e) {
      checks.push({ name: "Health check", passed: false, detail: e.message });
    }
  }

  // 4. Delete the test server
  if (serverId) {
    try {
      const deleted = await api.delete(`/api/llm-servers/${serverId}`);
      checks.push({
        name: "Delete LLM server",
        passed: true,
        detail: "Server deleted",
      });
    } catch (e) {
      checks.push({ name: "Delete LLM server", passed: false, detail: e.message });
    }
  }

  // 5. Verify deletion
  try {
    const list = await api.get("/api/llm-servers");
    const found = list.servers?.find((s) => s.id === serverId);
    checks.push({
      name: "Server removed from list",
      passed: !found,
      detail: `found=${!!found}`,
    });
  } catch (e) {
    checks.push({ name: "Server removed from list", passed: false, detail: e.message });
  }

  const passed = checks.filter((c) => c.passed).length;
  const failed = checks.filter((c) => !c.passed).length;
  return { checks, passed, failed };
}
