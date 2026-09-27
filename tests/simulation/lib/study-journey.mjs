/**
 * Helpers for scenario 89 (a research study through messaging channels): the synthetic participant
 * script, a waiting visibility check, and a small RFC 4180 CSV reader for the export.
 */

import { navigateTo, selectProject } from "./embedding-settings.mjs";

export const PROJECT_NAME = "[SIM-89] Study journey";
export const STUDY_NAME = "[SIM-89] Export habits";
export const EXPORT_BUTTON = 'button:has-text("Export CSV")';

/** Messages each synthetic participant sends (sender, channel, texts). */
export const PARTICIPANT_SCRIPT = [
  ["p1", "telegram", ["hi", "yes", "yes", "We email PDFs around", "Big exports time out", "No, that's all"]],
  ["p2", "slack", ["hello", "no", "actually exports are slow"]],
  ["p3", "whatsapp", ["hi", "yes", "no"]],
  ["p4", "slack", ["hi", "yes", "yes", "Shared drive", "STOP", "one more thing"]],
  ["p5", "whatsapp", ["hey", "sure", "Yes", "Screenshots in chat", "Finding the latest version", "Nothing else"]],
  ["p6", "telegram", ["hi there", "yes"]],
];

/** Texts that are never research answers: greetings, consent and screener replies, post-STOP. */
export const NOT_ANSWERS = ["hi", "hello", "yes", "no", "STOP", "sure", "hey", "one more thing", "actually exports are slow"];

/** Playwright's isVisible() does not wait; this does. */
export async function shows(locator, timeout = 8000) {
  return locator.waitFor({ state: "visible", timeout }).then(() => true).catch(() => false);
}

export function parseCsv(text) {
  const lines = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { field += '"'; i += 1; }
      else if (ch === '"') quoted = false;
      else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") { row.push(field); field = ""; }
    else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i += 1;
      row.push(field); field = "";
      if (row.some((c) => c !== "")) lines.push(row);
      row = [];
    } else field += ch;
  }
  if (field || row.length) { row.push(field); lines.push(row); }
  const [header, ...body] = lines;
  return (body || []).map((cells) => Object.fromEntries((header || []).map((h, i) => [h, cells[i] ?? ""])));
}


/** SETUP (API-behind-browser): a project and three channels started against the simulator. */
export async function setup(ctx, checks, state) {
  const label = "[API-behind-browser] SETUP: project and three running channels (protocol simulator)";
  try {
    const project = await ctx.api.post("/api/projects", { name: PROJECT_NAME, description: "Scenario 89 study journey (synthetic data)" });
    state.projectId = project.id;
    const q = `?project_id=${encodeURIComponent(project.id)}`;
    const configs = {
      telegram: { bot_token: "123456789:SIM89_TELEGRAM", base_url: `${state.simulatorUrl}/bot`, secret_token: "sim89-tg-secret" },
      slack: { bot_token: "xoxb-sim89", signing_secret: "sim89-slack-secret", base_url: `${state.simulatorUrl}/` },
      whatsapp: { phone_number_id: "sim89_phone", access_token: "sim89_wa_token", verify_token: "sim89_verify", app_secret: "sim89_app_secret", graph_api_base: state.simulatorUrl },
    };
    const started = [];
    for (const [platform, config] of Object.entries(configs)) {
      const channel = await ctx.api.post("/api/channels", { platform, name: `[SIM-89] ${platform}`, config, project_id: project.id });
      state.channels[platform] = channel.id;
      const res = await ctx.api.post(`/api/channels/${channel.id}/start${q}`, {});
      started.push(`${platform}=${res.status}`);
    }
    const ok = started.every((s) => s.endsWith("started") || s.endsWith("already_running"));
    checks.push({ name: label, passed: ok, detail: started.join(" ") });
  } catch (e) {
    checks.push({ name: label, passed: false, detail: e.message });
  }
}

export async function openDeployments(page) {
  await navigateTo(page, "Integrations", "integrations");
  const tab = page.locator("main button", { hasText: "Deployments" }).first();
  await tab.waitFor({ state: "visible", timeout: 15000 });
  await tab.click();
  await page.waitForTimeout(800);
}

export async function say(ctx, state, platform, sender, text) {
  const q = `?project_id=${encodeURIComponent(state.projectId)}`;
  const res = await ctx.api.post(`/api/channels/${state.channels[platform]}/simulate-inbound${q}`, {
    text,
    sender_id: sender,
    sender_name: `Synthetic ${sender}`,
  });
  return res.reply || "";
}

export async function driveRole(page, role) {
  try {
    await selectProject(page, PROJECT_NAME);
    await navigateTo(page, "Integrations", "integrations");
    await page.locator("main button", { hasText: "Deployments" }).first().click({ timeout: 15000 });
    await page.waitForTimeout(800);
    const newButton = page.locator("main button", { hasText: "New Deployment" }).first();
    const canCreate = await newButton.isEnabled().catch(() => false);
    const study = page.locator("main button", { hasText: STUDY_NAME }).first();
    const seesStudy = await shows(study, 10000);
    if (seesStudy) await study.click();
    // Wait for the dashboard itself before judging whether Export is offered.
    const dashboard = seesStudy && (await shows(page.locator("main h2", { hasText: STUDY_NAME }).first(), 10000));
    await page.waitForTimeout(500);
    const exportShown = await page.locator(EXPORT_BUTTON).first().isVisible().catch(() => false);
    if (role === "viewer") {
      return { ok: dashboard && !canCreate && !exportShown, detail: `dashboard=${dashboard} canCreate=${canCreate} export=${exportShown}` };
    }
    return { ok: dashboard && canCreate && exportShown, detail: `dashboard=${dashboard} canCreate=${canCreate} export=${exportShown}` };
  } catch (e) {
    return { ok: false, detail: e.message };
  }
}

/** CLEANUP (API-behind-browser). */
export async function cleanup(ctx, checks, state) {
  if (!state.projectId) return;
  const q = `?project_id=${encodeURIComponent(state.projectId)}`;
  try {
    if (state.deploymentId) await ctx.api.delete(`/api/deployments/${state.deploymentId}${q}`).catch(() => {});
    for (const channelId of Object.values(state.channels)) {
      await ctx.api.post(`/api/channels/${channelId}/stop${q}`, {}).catch(() => {});
      await ctx.api.delete(`/api/channels/${channelId}${q}`).catch(() => {});
    }
    await ctx.api.delete(`/api/projects/${state.projectId}`);
    checks.push({ name: "[API-behind-browser] CLEANUP: study, channels and project removed", passed: true, detail: state.projectId });
  } catch (e) {
    checks.push({ name: "[API-behind-browser] CLEANUP: study, channels and project removed", passed: false, detail: e.message });
  }
}
