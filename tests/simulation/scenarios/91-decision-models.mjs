/** Scenario 91 — Decision models (CF-SPEC-1 Phase 7): admin configuration, the project assurance
 * policy and its cloud-egress rule, and the Settings / Project Settings surfaces.
 *
 * Credential-free by default: it configures a loopback endpoint that is never called, so no data
 * leaves the QA stack. The hosted-endpoint branch is exercised only through the refusal path.
 * With ISTARA_SIM_DECIDER_ENDPOINTS set (a live stack with real deciders), it also checks those
 * endpoints are configured with a key and runs one connection check per endpoint: one constant
 * probe question, no research data. The project's previous policy is always restored. */

import { getApiBase } from "../lib/api-client.mjs";
import { navigateTo } from "../lib/embedding-settings.mjs";

export const name = "Decision Models";
export const id = "91-decision-models";

const ENDPOINT_ID = "sim-local-decider";

function result(checks, summary) {
  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary,
  };
}

// The shared client reports only the status code; a refusal check needs the server's reason code.
async function refusal(api, method, path, body) {
  const response = await fetch(`${getApiBase()}${path}`, {
    method,
    headers: api._headers(),
    body: JSON.stringify(body),
  });
  if (response.ok) return "accepted";
  const payload = await response.json().catch(() => ({}));
  return `${response.status} ${typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail)}`;
}

async function shows(locator, timeout = 10000) {
  return locator.waitFor({ state: "visible", timeout }).then(() => true).catch(() => false);
}

export async function run(ctx) {
  const { api, page, screenshot } = ctx;
  const checks = [];

  let projectId = typeof ctx.projectId === "string" ? ctx.projectId.trim() : "";
  if (!projectId) {
    try {
      projectId = (await api.post("/api/projects", { name: "Decision Models Probe" })).id;
    } catch (e) {
      checks.push({ name: "Probe project created", passed: false, detail: e.message });
      return result(checks, "no project");
    }
  }

  const policyUrl = `/api/projects/${projectId}/decision-models`;
  let previous = null;
  try {
    previous = await api.get(policyUrl);
  } catch (e) {
    checks.push({ name: "Project policy readable", passed: false, detail: e.message });
  }

  // 0. Live stack: the configured deciders answer a constant probe (one metered call each).
  const liveDeciders = String(process.env.ISTARA_SIM_DECIDER_ENDPOINTS || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  for (const endpointId of liveDeciders) {
    try {
      const listing = await api.get("/api/settings/decision-models");
      const endpoint = (listing.endpoints || []).find((item) => item.endpoint_id === endpointId);
      checks.push({
        name: `Live decider ${endpointId} configured with a key`,
        passed: Boolean(endpoint) && endpoint.credential_status !== "missing",
        detail: endpoint ? `${endpoint.locality}, model=${endpoint.model}, alias=${endpoint.model_is_alias}` : "not configured",
      });
      const probe = await api.post(`/api/settings/decision-models/${endpointId}/check`, {});
      checks.push({
        name: `Live decider ${endpointId} answers the connection check`,
        passed: probe.ok === true,
        detail: probe.ok ? `served_model=${probe.served_model}` : `reason=${probe.reason}`,
      });
    } catch (e) {
      checks.push({ name: `Live decider ${endpointId} answers the connection check`, passed: false, detail: e.message });
    }
  }

  // 1. API: listing is secret-free and offers both presets.
  try {
    const listing = await api.get("/api/settings/decision-models");
    const presets = (listing.presets || []).map((p) => p.preset_id);
    checks.push({
      name: "Decision-model presets offered (hosted Jev + local server)",
      passed: presets.includes("typesafe-jev") && presets.includes("local-systemone"),
      detail: presets.join(","),
    });
  } catch (e) {
    checks.push({ name: "Decision-model presets offered (hosted Jev + local server)", passed: false, detail: e.message });
  }

  // 2. API: add a local endpoint (no key, never called here).
  await api.delete(`/api/settings/decision-models/${ENDPOINT_ID}`).catch(() => null);
  try {
    const added = await api.post("/api/settings/decision-models", {
      endpoint_id: ENDPOINT_ID,
      base_url: "http://127.0.0.1:9",
      model: "sim-decider-1.0.0",
    });
    checks.push({
      name: "Local decision model added without a key",
      passed: added?.endpoint?.locality === "local" && added?.endpoint?.credential_status === "not_needed",
      detail: JSON.stringify(added?.endpoint || {}),
    });
  } catch (e) {
    checks.push({ name: "Local decision model added without a key", passed: false, detail: e.message });
  }

  // 3. API: a hosted endpoint without a key is refused before anything is stored.
  const hosted = await refusal(api, "POST", "/api/settings/decision-models", {
    endpoint_id: "sim-hosted-without-key",
    base_url: "https://api.typesafe.ai",
    model: "jev-1.14.0",
  });
  checks.push({
    name: "Hosted decision model without a key is refused",
    passed: /decider_api_key_required/.test(hosted),
    detail: hosted.slice(0, 120),
  });

  // 4. API: the project policy accepts the local decider and reports it.
  try {
    const saved = await api.put(policyUrl, {
      mode: "both",
      llm_method: "auto",
      llm_judges: 3,
      decider_endpoint_ids: [ENDPOINT_ID],
      hosted_egress_endpoint_ids: [],
    });
    checks.push({
      name: "Project assurance mode 'both' saved with a local decider",
      passed: saved.mode === "both" && saved.decider_endpoint_ids.includes(ENDPOINT_ID),
      detail: `mode=${saved.mode}`,
    });
  } catch (e) {
    checks.push({ name: "Project assurance mode 'both' saved with a local decider", passed: false, detail: e.message });
  }
  const noDecider = await refusal(api, "PUT", policyUrl, {
    mode: "decision_models",
    llm_method: "auto",
    llm_judges: 3,
    decider_endpoint_ids: [],
    hosted_egress_endpoint_ids: [],
  });
  checks.push({
    name: "Decision-model mode without a decider is refused",
    passed: /mode_needs_a_decider/.test(noDecider),
    detail: noDecider.slice(0, 120),
  });

  // 5. UI: Settings shows the Decision models section with its explainer.
  try {
    await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1200);
    await navigateTo(page, "Settings", "settings");
    const heading = page.locator("#decision-models-title").first();
    await heading.waitFor({ state: "visible", timeout: 15000 });
    await heading.scrollIntoViewIfNeeded().catch(() => null);
    const explainer = page.getByText("What is a decision model?", { exact: true }).first();
    checks.push({
      name: "Settings: Decision models section with explainer",
      passed: await shows(explainer),
      detail: "",
    });
    const listed = page.getByText(ENDPOINT_ID, { exact: true }).first();
    checks.push({
      name: "Settings: configured local decision model listed",
      passed: await shows(listed, 15000),
      detail: "",
    });
    await screenshot("91-settings-decision-models");
  } catch (e) {
    checks.push({ name: "Settings: Decision models section with explainer", passed: false, detail: e.message });
  }

  // 6. UI: Project Settings shows the assurance mode radio group with the saved mode.
  try {
    const moreBtn = page.locator('button[aria-label="More views"]').first();
    if (await moreBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await moreBtn.click();
      await page.waitForTimeout(300);
    }
    await page.locator('button[aria-label="Project Settings"]').first().click();
    const both = page.locator('#tour-target-project-assurance input[type="radio"][value="both"]').first();
    await page.locator("#tour-target-project-assurance").first().waitFor({ state: "visible", timeout: 15000 });
    checks.push({
      name: "Project Settings: assurance mode reflects the saved choice",
      passed: await both.isChecked().catch(() => false),
      detail: "",
    });
    await screenshot("91-project-assurance");
  } catch (e) {
    checks.push({ name: "Project Settings: assurance mode reflects the saved choice", passed: false, detail: e.message });
  }

  // Leave the project and the stack as they were (a live run keeps its deciders on).
  const restore = previous
    ? {
        mode: previous.mode,
        llm_method: previous.llm_method,
        llm_judges: previous.llm_judges,
        decider_endpoint_ids: previous.decider_endpoint_ids,
        hosted_egress_endpoint_ids: previous.hosted_egress_endpoint_ids,
      }
    : { mode: "auto", llm_method: "auto", llm_judges: 3, decider_endpoint_ids: [], hosted_egress_endpoint_ids: [] };
  await api.put(policyUrl, restore).catch(() => null);
  await api.delete(`/api/settings/decision-models/${ENDPOINT_ID}`).catch(() => null);

  return result(checks, `${checks.filter((c) => c.passed).length}/${checks.length} decision-model checks`);
}
