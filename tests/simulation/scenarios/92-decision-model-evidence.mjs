/** Scenario 92 — Decision-model evidence (CF-SPEC-1): after the run's coding and validation, did
 * the project's live deciders record verdicts, with provenance and trust status, and does Ensemble
 * Health show them?
 *
 * Live only: it needs ISTARA_SIM_DECIDER_ENDPOINTS (run.mjs turns those deciders on for the
 * simulation project before the first scenario). Without it the scenario reports that it has
 * nothing to check instead of passing. Read-only: it makes no decider call itself. */

import { navigateTo } from "../lib/embedding-settings.mjs";

export const name = "Decision Model Evidence";
export const id = "92-decision-model-evidence";

function result(checks, summary) {
  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary,
  };
}

export async function run(ctx) {
  const { api, page, screenshot } = ctx;
  const checks = [];
  const deciders = String(process.env.ISTARA_SIM_DECIDER_ENDPOINTS || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  const projectId = typeof ctx.projectId === "string" ? ctx.projectId.trim() : "";
  if (!deciders.length || !projectId) {
    checks.push({
      name: "Live deciders configured for this run",
      passed: false,
      detail: "not_runnable: set ISTARA_SIM_DECIDER_ENDPOINTS on a stack with a real decider",
    });
    return result(checks, "not runnable without live deciders");
  }

  // 1. The project's policy still names the deciders (scenario 91 restores it).
  try {
    const policy = await api.get(`/api/projects/${projectId}/decision-models`);
    checks.push({
      name: "Simulation project uses the live deciders",
      passed: deciders.every((id) => policy.decider_endpoint_ids.includes(id)),
      detail: `mode=${policy.mode} deciders=${policy.decider_endpoint_ids.join(",")}`,
    });
  } catch (e) {
    checks.push({ name: "Simulation project uses the live deciders", passed: false, detail: e.message });
  }

  // 2. Verdicts were recorded, with the served model and a trust status.
  let health = null;
  try {
    health = await api.get(`/api/metrics/${projectId}/decision-models`);
  } catch (e) {
    checks.push({ name: "Decision-model health readable", passed: false, detail: e.message });
  }
  if (health) {
    for (const endpointId of deciders) {
      const scopes = (health.scopes || []).filter((scope) => scope.endpoint_id === endpointId);
      const verdicts = scopes.reduce((sum, scope) => sum + (scope.verdicts || 0), 0);
      checks.push({
        name: `Decider ${endpointId} recorded verdicts during the run`,
        passed: verdicts > 0,
        detail: `${scopes.length} scope(s), ${verdicts} verdict(s): ${scopes
          .map((scope) => `${scope.question_set} served=${scope.served_model} trusted=${scope.trusted}`)
          .join("; ") || "none"}`,
      });
      checks.push({
        name: `Decider ${endpointId} records the model that actually answered`,
        passed: scopes.length > 0 && scopes.every((scope) => Boolean(scope.served_model)),
        detail: scopes.map((scope) => scope.served_model).join(",") || "no scopes",
      });
      checks.push({
        name: `Decider ${endpointId} is not trusted before human labels exist`,
        passed: scopes.every((scope) => scope.trusted === false || (scope.labelled || 0) >= 50),
        detail: scopes.map((scope) => `labelled=${scope.labelled} reasons=${(scope.reasons || []).join("|")}`).join("; "),
      });
    }
  }

  // 3. UI: Ensemble Health shows the evaluator-health panel (API-behind-browser: read only).
  try {
    await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1200);
    await navigateTo(page, "Ensemble Health", "ensemble");
    const panel = page.locator("#decision-model-health-title").first();
    await panel.waitFor({ state: "visible", timeout: 20000 });
    await panel.scrollIntoViewIfNeeded().catch(() => null);
    const row = page.getByText(deciders[0], { exact: true }).first();
    checks.push({
      name: "Ensemble Health shows the decider's scope",
      passed: await row.waitFor({ state: "visible", timeout: 20000 }).then(() => true).catch(() => false),
      detail: "",
    });
    await screenshot("92-ensemble-health-decision-models");
  } catch (e) {
    checks.push({ name: "Ensemble Health shows the decider's scope", passed: false, detail: e.message });
  }

  return result(checks, `${checks.filter((c) => c.passed).length}/${checks.length} decision-model evidence checks`);
}
