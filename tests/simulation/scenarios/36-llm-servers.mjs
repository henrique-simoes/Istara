/** Scenario 36 — LLM Servers compat plane & Pi projection: the legacy management
 * surface persists as a read/CRUD compat plane whose rows project into the Pi
 * model catalog (W8 UX parity). This scenario pins BOTH sides of that contract. */

export const name = "LLM Servers Compat & Pi Projection";
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

  // 6. Pi projection invariant: a compat-plane server appears in the Pi model
  // catalog's configured (identity-only) view while it exists, and is gone
  // after deletion. No API key material may ever appear in the catalog.
  try {
    const added = await api.post("/api/llm-servers", {
      name: "Pi Projection Probe",
      provider_type: "openai_compat",
      host: "http://192.0.2.1:9998", // RFC 5737 TEST-NET — unreachable by design
      priority: 100,
    });
    const probeId = added.id;
    let catalog = await api.get("/api/chat/model-catalog?project_id=");
    const configuredDuring = JSON.stringify(catalog.configured || []);
    checks.push({
      name: "Compat row projects into Pi catalog (while present)",
      passed: configuredDuring.includes("Pi Projection Probe"),
      detail: `configured_entries=${catalog.configured?.length}`,
    });
    const leaksSecrets = configuredDuring.toLowerCase().includes('"api_key"') ||
      /sk-[a-z0-9]{16,}/i.test(configuredDuring);
    checks.push({
      name: "Pi catalog exposes identity only (no secrets)",
      passed: !leaksSecrets,
      detail: leaksSecrets ? "secret-like material found in configured view" : "identity fields only",
    });
    if (probeId) {
      try { await api.delete(`/api/llm-servers/${probeId}`); } catch {}
    }
    catalog = await api.get("/api/chat/model-catalog?project_id=");
    const configuredAfter = JSON.stringify(catalog.configured || []);
    checks.push({
      name: "Projection removed after compat delete",
      passed: !configuredAfter.includes("Pi Projection Probe"),
      detail: `configured_entries=${catalog.configured?.length}`,
    });
  } catch (e) {
    checks.push({ name: "Pi projection invariant", passed: false, detail: e.message });
  }

  // 7. Active agentic core is reported by the catalog.
  try {
    const catalog = await api.get("/api/chat/model-catalog");
    checks.push({
      name: "Catalog reports active engine",
      passed: catalog.engine === "pi" || catalog.engine === "legacy",
      detail: `engine=${JSON.stringify(catalog.engine)}`,
    });
  } catch (e) {
    checks.push({ name: "Catalog reports active engine", passed: false, detail: e.message });
  }

  const passed = checks.filter((c) => c.passed).length;
  const failed = checks.filter((c) => !c.passed).length;
  return { checks, passed, failed };
}
