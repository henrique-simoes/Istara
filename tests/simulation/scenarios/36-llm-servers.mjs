/** Scenario 36 — Model Management & Provenance (pi model management owns provider
 * configuration for BOTH agentic cores; the legacy LLM Servers surface is retired —
 * CF-SPEC-1 Phase 6). Pins: catalog truth, active-engine reporting, identity-only
 * configured view, and per-plane visibility. */

export const name = "Model Management & Provenance";
export const id = "36-llm-servers";

import { authHeaders, getApiBase } from "../lib/api-client.mjs";

export async function run(ctx) {
  const { api, screenshot } = ctx;
  const checks = [];
  let projectId = typeof ctx.projectId === "string" ? ctx.projectId.trim() : "";

  // 1. Retired surface stays retired: the management API answers 404/405.
  try {
    const res = await fetch(`${getApiBase()}/api/llm-servers`, { headers: authHeaders() });
    checks.push({
      name: "Retired LLM Servers API is gone",
      passed: res.status === 404 || res.status === 405,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Retired LLM Servers API is gone", passed: false, detail: e.message });
  }

  // 2. Catalog endpoint: providers + total models + active engine.
  try {
    const catalog = await api.get(
      `/api/chat/model-catalog${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ""}`
    );
    checks.push({
      name: "Model catalog serves providers",
      passed: Array.isArray(catalog.providers) && catalog.total_models > 0,
      detail: `providers=${catalog.providers?.length}, total_models=${catalog.total_models}`,
    });
    checks.push({
      name: "Catalog reports active agentic core",
      passed: catalog.engine === "pi" || catalog.engine === "legacy",
      detail: `engine=${JSON.stringify(catalog.engine)}`,
    });
    checks.push({
      name: "Configured endpoints are identity-only",
      passed:
        Array.isArray(catalog.configured) &&
        catalog.configured.every((entry) =>
          ["api_key", "base_url", "host", "secret", "token"].every(
            (key) => !Object.prototype.hasOwnProperty.call(entry || {}, key)
          )
        ),
      detail: `configured=${catalog.configured?.length}, fields=${JSON.stringify(
        Object.keys(catalog.configured?.[0] || {})
      )}`,
    });
  } catch (e) {
    checks.push({ name: "Model catalog", passed: false, detail: e.message });
  }

  // 3. Legacy model inventory still visible for routing truth (donations/local).
  try {
    const catalog = await api.get(
      `/api/chat/model-catalog${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ""}`
    );
    checks.push({
      name: "Legacy/donated model inventory present",
      passed: Array.isArray(catalog.legacy_models),
      detail: `legacy_models=${catalog.legacy_models?.length}`,
    });
  } catch (e) {
    checks.push({ name: "Legacy model inventory", passed: false, detail: e.message });
  }

  await screenshot("36-model-management-provenance");

  const passed = checks.filter((c) => c.passed).length;
  const failed = checks.length - passed;
  return { checks, passed, failed };
}
