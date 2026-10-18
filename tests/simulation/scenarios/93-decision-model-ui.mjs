/** Scenario 93 — Decision-model UI walk (CF-SPEC-1): every screen the decision-model work added,
 * driven in the browser as a user would.
 *
 *  1. Onboarding: the "How outputs are checked" step and its decision-model explainer.
 *  2. Settings → Decision models: explainer, add a local model through the form, the live
 *     connection check on a configured decider, two-step remove.
 *  3. Project Settings → Assurance: switch the mode, consent for a hosted decider, save, trust
 *     status; the previous policy is restored afterwards.
 *  4. Ensemble Health: the evaluator-health panel.
 *
 * Live parts (the connection check, consent, trust) need ISTARA_SIM_DECIDER_ENDPOINTS; without it
 * they are skipped and named in the summary. The review-queue decider note appears only for a
 * trusted scope, so it is not walked here. */

import { navigateTo } from "../lib/embedding-settings.mjs";

export const name = "Decision Model UI Walk";
export const id = "93-decision-model-ui";

const LOCAL_ID = "sim-ui-decider";
const ONBOARDING_PROJECT = "[SIM-ONB] Decision model onboarding";

const visible = (locator, timeout = 15000) =>
  locator.waitFor({ state: "visible", timeout }).then(() => true).catch(() => false);

function check(checks, name, passed, detail = "") {
  checks.push({ name, passed: Boolean(passed), detail });
}

async function onboarding(ctx, checks) {
  const browser = ctx.page.context().browser();
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 }, colorScheme: "light" });
  context.setDefaultTimeout(15000);
  await context.addInitScript(() => {
    try {
      localStorage.setItem(
        "istara_tour_state",
        JSON.stringify({ active: true, isOnboarding: true, step: 0, hasExistingProjects: false })
      );
    } catch {}
  });
  const page = await context.newPage();
  try {
    await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
    await page.locator("#login-username").fill(process.env.ADMIN_USERNAME || "admin");
    await page.locator("#login-password").fill(process.env.ADMIN_PASSWORD || "");
    await page.getByRole("button", { name: "Sign In", exact: true }).click();
    check(checks, "Onboarding: wizard opens after sign-in", await visible(page.getByText("Welcome to Istara").first(), 20000));
    await page.getByRole("button", { name: /Get Started/ }).click();
    await page.getByRole("button", { name: /Continue/ }).first().click();
    await page.getByPlaceholder("e.g., Onboarding Redesign Study").fill(ONBOARDING_PROJECT);
    await page.getByRole("button", { name: /Create Project/ }).click();
    await page.getByRole("button", { name: /Continue/ }).first().click();
    await page.getByRole("button", { name: /Skip for Now/ }).click();
    await page.getByRole("button", { name: /Continue/ }).first().click();
    const step = page.getByRole("heading", { name: "How outputs are checked" });
    check(checks, "Onboarding: assurance step shown last", await visible(step));
    const modes = ["LLM judges only", "Decision models only", "Both, side by side", "No automated review"];
    const shown = [];
    for (const mode of modes) if (await visible(page.getByText(mode, { exact: false }).first(), 3000)) shown.push(mode);
    check(checks, "Onboarding: the four assurance modes are explained", shown.length === modes.length, shown.join(", "));
    await page.getByText("What is a decision model?", { exact: true }).click();
    check(
      checks,
      "Onboarding: explainer says triage, never authority, and nothing is enabled",
      (await visible(page.getByText("Triage, never authority", { exact: false }).first(), 5000)) &&
        (await visible(page.getByText("None is turned on", { exact: false }).first(), 5000))
    );
    await page.screenshot({ path: `${ctx.runDir}/screenshots/93-onboarding-assurance.png` }).catch(() => null);
    await page.getByRole("button", { name: /Skip & Explore|Start Researching/ }).click();
  } catch (e) {
    check(checks, "Onboarding: walk completed", false, e.message.split("\n")[0]);
  } finally {
    await context.close().catch(() => null);
    const projects = await ctx.api.get("/api/projects").catch(() => []);
    for (const project of projects || []) {
      if (project.name === ONBOARDING_PROJECT) await ctx.api.delete(`/api/projects/${project.id}`).catch(() => null);
    }
  }
}

async function settings(ctx, checks, decider) {
  const { page } = ctx;
  try {
    await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
    await page.locator('nav[aria-label="Views"]').first().waitFor({ state: "visible", timeout: 20000 });
    await navigateTo(page, "Settings", "settings");
    const section = page.locator("#tour-target-decision-models");
    await section.waitFor({ state: "visible", timeout: 20000 });
    await section.scrollIntoViewIfNeeded();
    check(checks, "Settings: decision-model explainer", await visible(section.getByText("What is a decision model?", { exact: true })));

    if (decider) {
      const row = section.locator("li", { hasText: decider }).first();
      await row.getByRole("button", { name: /Check connection/ }).click();
      const status = row.getByRole("status");
      const ok = await visible(status.filter({ hasText: "Connected" }), 30000);
      check(checks, `Settings: live connection check on ${decider}`, ok, ok ? await status.innerText() : "no 'Connected' status");
    }

    await section.getByRole("button", { name: /Add Local/ }).click();
    const form = section.locator("form");
    await form.getByLabel("Name").fill(LOCAL_ID);
    await form.getByLabel("Model version").fill("sim-ui-1.0.0");
    await form.getByRole("button", { name: "Add decision model" }).click();
    const added = section.locator("li", { hasText: LOCAL_ID }).first();
    check(checks, "Settings: model added through the form", await visible(added));
    await page.screenshot({ path: `${ctx.runDir}/screenshots/93-settings-decision-models.png` }).catch(() => null);
    await added.getByRole("button", { name: `Remove ${LOCAL_ID}` }).click();
    await added.getByRole("button", { name: "Remove and delete key" }).click();
    check(checks, "Settings: two-step remove", await added.waitFor({ state: "detached", timeout: 15000 }).then(() => true).catch(() => false));
  } catch (e) {
    check(checks, "Settings: walk completed", false, e.message.split("\n")[0]);
    await ctx.api.delete(`/api/settings/decision-models/${LOCAL_ID}`).catch(() => null);
  }
}

async function assurance(ctx, checks, decider) {
  const { page, api } = ctx;
  const url = `/api/projects/${ctx.projectId}/decision-models`;
  const previous = await api.get(url).catch(() => null);
  try {
    const moreBtn = page.locator('button[aria-label="More views"]').first();
    if (await moreBtn.isVisible().catch(() => false)) await moreBtn.click();
    await page.locator('button[aria-label="Project Settings"]').first().click();
    const panel = page.locator("#tour-target-project-assurance");
    await panel.waitFor({ state: "visible", timeout: 20000 });
    await panel.scrollIntoViewIfNeeded();
    await panel.getByText("Decision models only", { exact: true }).click();
    if (decider) {
      const consent = panel.getByLabel(new RegExp(`Allow this project to send research excerpts to ${decider}`));
      if (!(await consent.isChecked())) await consent.check();
      const use = panel.getByLabel(new RegExp(`^Use ${decider}`));
      if (!(await use.isChecked())) await use.check();
      check(checks, `Assurance: ${decider} needs and has the project's cloud consent`, (await consent.isChecked()) && (await use.isChecked()));
    }
    await panel.getByRole("button", { name: "Save assurance settings" }).click();
    check(checks, "Assurance: saved from the UI", await visible(panel.getByText("Saved.", { exact: true })));
    const stored = await api.get(url);
    check(checks, "Assurance: stored mode matches the UI", stored.mode === "decision_models", `mode=${stored.mode}`);
    if (decider) {
      const trust = panel.getByText(/Calibrating|Shadow|Trusted/).first();
      check(checks, "Assurance: trust status shown", await visible(trust, 10000), (await trust.innerText().catch(() => "")) || "none");
    }
    await page.screenshot({ path: `${ctx.runDir}/screenshots/93-project-assurance.png` }).catch(() => null);
  } catch (e) {
    check(checks, "Assurance: walk completed", false, e.message.split("\n")[0]);
  } finally {
    if (previous) {
      const { mode, llm_method, llm_judges, decider_endpoint_ids, hosted_egress_endpoint_ids } = previous;
      await api.put(url, { mode, llm_method, llm_judges, decider_endpoint_ids, hosted_egress_endpoint_ids }).catch(() => null);
    }
  }
}

async function health(ctx, checks, decider) {
  const { page } = ctx;
  try {
    await navigateTo(page, "Ensemble Health", "ensemble");
    const panel = page.locator('section[aria-labelledby="decision-model-health-title"]');
    check(checks, "Ensemble Health: evaluator-health panel", await visible(panel, 20000));
    if (decider) check(checks, `Ensemble Health: ${decider} listed`, await visible(panel.getByText(decider, { exact: true })));
  } catch (e) {
    check(checks, "Ensemble Health: walk completed", false, e.message.split("\n")[0]);
  }
}

export async function run(ctx) {
  const checks = [];
  const decider = String(process.env.ISTARA_SIM_DECIDER_ENDPOINTS || "").split(",")[0].trim();
  await onboarding(ctx, checks);
  await settings(ctx, checks, decider);
  await assurance(ctx, checks, decider);
  await health(ctx, checks, decider);
  const passed = checks.filter((c) => c.passed).length;
  return {
    checks,
    passed,
    failed: checks.length - passed,
    summary:
      `${passed}/${checks.length} decision-model UI checks` +
      (decider ? "" : "; live parts skipped (no ISTARA_SIM_DECIDER_ENDPOINTS)") +
      "; review-queue note not walked (shown only for a trusted scope)",
  };
}
