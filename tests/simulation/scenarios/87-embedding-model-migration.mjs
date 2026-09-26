/**
 * Scenario 87 — Switch the install's embedding model (Settings > Embedding model), 2026-09-26.
 *
 * Nothing could change an existing install's embedding model: the persisted embedding profile wins
 * over settings, and every vector store fails closed when the active identity differs. An
 * administrator now moves the install to another model: Istara checks the model first (nothing
 * changes when it cannot embed), activates a new profile version and re-embeds every project's
 * stored chunks, so semantic search keeps working in the new vector space. This scenario drives it
 * the way an administrator does:
 *
 *   1. Settings shows the active model, its prompts and the profile version;
 *   2. loading and error states render, and Retry recovers;
 *   3. a model the provider does not serve ("qa-missing-embedder": the QA stub answers 404 like
 *      Ollama for a model it has not pulled) is refused with a plain message and nothing changes;
 *   4. switching to "embeddinggemma" (confirm dialog, focus on its action) re-indexes with visible
 *      progress; Settings then shows the new model and a newer profile version, the Memory Health
 *      tab names it, and a Memory search still finds the scenario's own document;
 *   5. the matrix: keyboard Tab reaches the model field with visible focus, 375px reflow, light and
 *      dark themes with axe-core WCAG 2.1 AA; researchers and viewers never see the control; a
 *      stranger is held at login.
 *
 * Setup (a fresh project with one synthetic transcript), the cross-check of the active profile and
 * cleanup (moving back to the original model, deleting the project) are API-behind-browser, and
 * labelled so. Credential-free lane: the stub's vectors do not depend on the model, so the check is
 * that the switch is governed and search survives it, not retrieval quality (that is DEC-15's M1).
 */

import { getApiBase, authHeaders } from "../lib/api-client.mjs";
import { reflow375Check, keyboardFocusCheck } from "../lib/matrix-checks.mjs";
import { createVariantLedger } from "../lib/variant-obligations.mjs";
import { ensureRoleAccounts, driveRoleCell } from "../lib/role-variants.mjs";

export const name = "Embedding model switch (Settings)";
export const id = "87-embedding-model-migration";

const PROJECT_NAME = "[SIM-87] Embedding switch";
const SECTION = '[data-testid="embedding-model-section"]';
const ACTIVE = '[data-testid="embedding-active-model"]';
const INPUT = "#embedding-model-input";
const MARKER = "Scenario87 marker ZEBRA";
const TARGET = "embeddinggemma";
const PROFILE = "/api/settings/embedding-profile";

async function navigateTo(page, label, viewId) {
  const nav = page.locator(`nav[aria-label="Views"] button[aria-label="${label}"]`).first();
  if (await nav.isVisible({ timeout: 3000 }).catch(() => false)) {
    await nav.click();
  } else {
    await page.evaluate((detail) => window.dispatchEvent(new CustomEvent("istara:navigate", { detail })), viewId);
  }
}

async function openSettings(page) {
  await navigateTo(page, "Settings", "settings");
  return page.locator(SECTION).first().waitFor({ state: "visible", timeout: 20000 }).then(() => true).catch(() => false);
}

async function remountSettings(page) {
  await navigateTo(page, "Memory", "memory");
  await page.waitForTimeout(400);
  await navigateTo(page, "Settings", "settings");
}

async function activeModel(page, timeout = 15000) {
  const cell = page.locator(ACTIVE).first();
  const shown = await cell.waitFor({ state: "visible", timeout }).then(() => true).catch(() => false);
  return shown ? (await cell.innerText()).trim() : "";
}

async function selectProject(page, projectName) {
  const button = page.locator('[aria-label="Projects list"] button', { hasText: projectName }).first();
  await button.waitFor({ state: "visible", timeout: 15000 });
  await button.click();
  await page.waitForTimeout(800);
}

async function axeScan(page) {
  try {
    const { default: AxeBuilder } = await import("@axe-core/playwright");
    const result = await new AxeBuilder({ page }).include(SECTION).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    const blocking = result.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    return {
      passed: blocking.length === 0,
      detail: blocking.length
        ? blocking.map((v) => `${v.id}(${v.nodes.length}): ${v.nodes.slice(0, 6).map((n) => n.target.join(" ")).join(" | ")}`).join("; ")
        : `0 serious/critical; ${result.violations.length} minor/moderate`,
    };
  } catch (e) {
    return { passed: false, detail: `axe unavailable: ${e.message}` };
  }
}

/** Type a model, submit, and confirm in the dialog (by keyboard: focus lands on its action). */
async function requestSwitch(page, model) {
  const input = page.locator(INPUT).first();
  await input.fill(model);
  await input.press("Enter");
  const dialog = page.getByRole("alertdialog").first();
  const shown = await dialog.waitFor({ state: "visible", timeout: 5000 }).then(() => true).catch(() => false);
  const focused = shown ? await page.evaluate(() => document.activeElement?.textContent?.trim() || "") : "";
  if (shown) await page.keyboard.press("Enter");
  return { shown, focused };
}

async function waitForMigration(ctx, timeoutMs = 120000) {
  const deadline = Date.now() + timeoutMs;
  let status = null;
  while (Date.now() < deadline) {
    status = await ctx.api.get(PROFILE).catch(() => null);
    if (status && status.migration?.state !== "running") return status;
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  return status;
}

export async function run(ctx) {
  const checks = [];
  const ledger = createVariantLedger(id, [
    { variantId: "role=admin", expectation: "admin sees the model, is refused a missing model, switches with progress, and search survives" },
    { variantId: "role=researcher", expectation: "researcher opens Settings and does not see the embedding-model control" },
    { variantId: "role=viewer", expectation: "viewer opens Settings and does not see the embedding-model control" },
    { variantId: "role=stranger", expectation: "unauthenticated stranger is held at the login screen" },
  ]);

  const adminOutcome = await driveAdminCell(ctx, checks);

  const provisioning = await ensureRoleAccounts(ctx);
  for (const role of ["researcher", "viewer"]) {
    await driveRoleCell(ctx, {
      ledger,
      role,
      provisioning,
      shotName: `87-role-${role}`,
      drive: async (rolePage) => driveRoleSettingsCell(rolePage),
    });
  }
  await driveRoleCell(ctx, { ledger, role: "stranger", provisioning, shotName: "87-role-stranger" });

  ledger.record({
    variantId: "role=admin",
    result: adminOutcome.ok ? "pass" : "fail",
    detail: adminOutcome.detail,
    artifacts: ["screenshots/87-settings-before.png", "screenshots/87-settings-after.png", "screenshots/87-settings-375px.png", "screenshots/87-settings-dark.png"],
  });
  checks.push(...ledger.finalize());

  const passed = checks.filter((c) => c.passed).length;
  return { checks, passed, failed: checks.length - passed };
}

async function driveAdminCell(ctx, checks) {
  const start = checks.length;
  const original = await ctx.api.get(PROFILE).catch(() => null);
  const projectId = await setup(ctx, checks);
  try {
    await ctx.page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
    if (projectId) await selectProject(ctx.page, PROJECT_NAME);
    const steps = [checkShown, checkLoadingAndError, checkRefused, checkSwitch, checkSearchSurvives, checkKeyboard, checkNarrow, checkThemes];
    for (const step of steps) await step(ctx, checks, { original, projectId });
  } catch (e) {
    checks.push({ name: "Admin journey completed without an exception", passed: false, detail: e.message });
  } finally {
    await cleanup(ctx, checks, { original, projectId });
  }
  const failed = checks.slice(start).filter((c) => !c.passed).length;
  return { ok: failed === 0, detail: failed === 0 ? "admin embedding-switch journey clean" : `${failed} admin-cell check(s) failed` };
}

/** SETUP (API-behind-browser): a fresh project with one synthetic transcript. */
async function setup(ctx, checks) {
  const name = "[API-behind-browser] SETUP: a fresh project with one synthetic transcript";
  try {
    const created = await ctx.api.post("/api/projects", { name: PROJECT_NAME, description: "Scenario 87 embedding switch (synthetic data)" });
    const form = new FormData();
    const text = `# Scenario87 interview\n\nInterviewer: Where do receipts go?\n\nP1: ${MARKER}. The receipt is in my apron pocket, then the van.\n`;
    form.append("file", new Blob([text], { type: "text/plain" }), "s87-receipts.txt");
    const res = await fetch(`${getApiBase()}/api/files/upload/${created.id}`, { method: "POST", headers: authHeaders(), body: form });
    checks.push({ name, passed: !!created.id && res.ok, detail: `id=${created.id} upload=${res.status}` });
    return created.id || null;
  } catch (e) {
    checks.push({ name, passed: false, detail: e.message });
    return null;
  }
}

/** 1. Settings shows the active model, its prompts and the profile version. */
async function checkShown(ctx, checks, { original }) {
  const { page } = ctx;
  const visible = await openSettings(page);
  const model = await activeModel(page);
  const text = visible ? await page.locator(SECTION).first().innerText() : "";
  await ctx.screenshot("87-settings-before");
  checks.push({
    name: "Settings shows the active embedding model, its prompts and profile version",
    passed: visible && !!model && model === original?.active?.model_id && /Profile version/.test(text) && /Prompts/.test(text),
    detail: `model=${model} api=${original?.active?.model_id} v=${original?.active?.version}`,
  });
}

/** 2. Loading and error states; Retry recovers. */
async function checkLoadingAndError(ctx, checks) {
  const { page } = ctx;
  const glob = `**${PROFILE}`;
  await page.route(glob, async (route) => {
    if (route.request().method() !== "GET") return route.continue();
    await new Promise((resolve) => setTimeout(resolve, 2500));
    await route.continue();
  });
  await remountSettings(page);
  const loading = await page.getByText("Loading the embedding model", { exact: false }).first()
    .waitFor({ state: "visible", timeout: 3000 }).then(() => true).catch(() => false);
  const loaded = !!(await activeModel(page));
  await page.unroute(glob);
  checks.push({ name: "Loading state renders, then the model replaces it", passed: loading && loaded, detail: `loading=${loading} loaded=${loaded}` });

  await page.route(glob, (route) =>
    route.request().method() === "GET"
      ? route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "Scenario87 injected failure" }) })
      : route.continue(), { times: 1 });
  await remountSettings(page);
  const retry = page.locator(SECTION).getByRole("button", { name: "Retry" }).first();
  const error = await retry.waitFor({ state: "visible", timeout: 10000 }).then(() => true).catch(() => false);
  if (error) await retry.click();
  const recovered = !!(await activeModel(page));
  await page.unroute(glob).catch(() => {});
  checks.push({ name: "Error state offers Retry, and Retry recovers", passed: error && recovered, detail: `error=${error} recovered=${recovered}` });
}

/** 3. A model the provider does not serve is refused; nothing changes. */
async function checkRefused(ctx, checks, { original }) {
  const { page } = ctx;
  const { shown, focused } = await requestSwitch(page, "qa-missing-embedder");
  const message = page.locator('[data-testid="embedding-migration-error"]').first();
  const refused = await message.waitFor({ state: "visible", timeout: 20000 }).then(() => true).catch(() => false);
  const text = refused ? await message.innerText() : "";
  const after = await ctx.api.get(PROFILE).catch(() => null);
  checks.push({
    name: "Confirm dialog opens with focus on its action",
    passed: shown && /Re-embed now/.test(focused),
    detail: `dialog=${shown} focused=${focused}`,
  });
  checks.push({
    name: "A model the provider does not serve is refused and nothing changes",
    passed: refused && /could not embed, so nothing changed/.test(text) && after?.active?.version === original?.active?.version,
    detail: `${text.slice(0, 140)} | version ${original?.active?.version} -> ${after?.active?.version}`,
  });
}

/** 4. Switch to the target: progress, then the new model and a newer profile version. */
async function checkSwitch(ctx, checks, { original }) {
  const { page } = ctx;
  await requestSwitch(page, TARGET);
  const status = page.locator('[data-testid="embedding-migration-status"]').first();
  const progressed = await status.getByText(/Re-indexing with|Now using/).first()
    .waitFor({ state: "visible", timeout: 20000 }).then(() => true).catch(() => false);
  const finished = await waitForMigration(ctx);
  const done = await status.getByText(`Now using ${TARGET}`, { exact: false }).first()
    .waitFor({ state: "visible", timeout: 30000 }).then(() => true).catch(() => false);
  const model = await activeModel(page);
  await ctx.screenshot("87-settings-after");
  checks.push({
    name: "Switching re-indexes with visible progress and ends on the new model",
    passed: progressed && done && model === TARGET && finished?.migration?.state === "done",
    detail: `progress=${progressed} done=${done} model=${model} state=${finished?.migration?.state} tables=${finished?.migration?.stores_done} rows=${finished?.migration?.rows_reembedded}`,
  });
  checks.push({
    name: "[API-behind-browser] the active profile is a newer version with the model card's prompts",
    passed: finished?.active?.model_id === TARGET && finished?.active?.version > (original?.active?.version || 0) && finished?.active?.prompt_scheme === "embeddinggemma",
    detail: `v${original?.active?.version} -> v${finished?.active?.version} scheme=${finished?.active?.prompt_scheme}`,
  });
}

/** 4b. The Health tab names the new model and search still finds the scenario's document. */
async function checkSearchSurvives(ctx, checks, { projectId }) {
  const { page } = ctx;
  if (!projectId) {
    checks.push({ name: "Search after the switch", passed: false, detail: "no scenario project" });
    return;
  }
  await navigateTo(page, "Memory", "memory");
  await page.locator('button[aria-label="Switch to Health tab"]').first().click({ timeout: 15000 }).catch(() => {});
  const health = await page.getByText(TARGET, { exact: true }).first()
    .waitFor({ state: "visible", timeout: 15000 }).then(() => true).catch(() => false);
  checks.push({ name: "Memory Health names the new embedding model", passed: health, detail: `shown=${health}` });

  await page.locator('button[aria-label="Switch to Knowledge Base tab"]').first().click().catch(() => {});
  const box = page.locator('input[aria-label="Search knowledge base"]');
  await box.waitFor({ state: "visible", timeout: 15000 });
  await box.fill("apron pocket receipts van");
  const response = page.waitForResponse((r) => r.url().includes(`/api/memory/${encodeURIComponent(projectId)}/search`), { timeout: 20000 }).catch(() => null);
  await page.locator('button[aria-label="Run search"]').click();
  const res = await response;
  const region = page.locator('[role="region"][aria-label="Search results"]');
  await region.waitFor({ state: "visible", timeout: 20000 }).catch(() => {});
  const text = (await region.isVisible().catch(() => false)) ? await region.innerText() : "";
  checks.push({
    name: "After the switch a Memory search finds the scenario's document",
    passed: !!res && res.ok() && text.includes(MARKER),
    detail: `status=${res ? res.status() : "none"} found=${text.includes(MARKER)}`,
  });
}

/** 5a. Keyboard: Tab reaches the model field with visible focus. */
async function checkKeyboard(ctx, checks) {
  const { page } = ctx;
  await openSettings(page);
  await page.locator("body").click({ position: { x: 5, y: 5 } }).catch(() => {});
  await keyboardFocusCheck(page, checks, { name: "Embedding model field", targetSelector: INPUT, maxTabs: 200 });
}

/** 5b. 375px: the section, its field and its button are on screen; no sideways scroll. */
async function checkNarrow(ctx, checks) {
  const { page } = ctx;
  await reflow375Check(page, checks, {
    name: "Settings embedding model",
    onNarrow: async () => {
      await openSettings(page);
      const section = page.locator(SECTION).first();
      await section.scrollIntoViewIfNeeded().catch(() => {});
      const width = page.viewportSize()?.width || 375;
      const inside = async (selector) => {
        const box = await page.locator(selector).first().boundingBox().catch(() => null);
        return !!box && box.x >= 0 && box.x + box.width <= width + 1;
      };
      const ok = (await inside(INPUT)) && (await inside(`${SECTION} button[type="submit"]`));
      checks.push({ name: "375px: the model field and its button are fully on screen", passed: ok, detail: `viewport=${width}` });
      await ctx.screenshot("87-settings-375px");
    },
  });
}

/** 5c. Light and dark themes, axe in both. */
async function checkThemes(ctx, checks) {
  const { page } = ctx;
  await openSettings(page);
  checks.push({ name: "axe-core WCAG 2.1 AA (light): no serious or critical violation in the section", ...(await axeScan(page)) });
  const toDark = page.locator('button[aria-label="Switch to dark mode"]').first();
  const wasLight = await toDark.isVisible({ timeout: 3000 }).catch(() => false);
  if (wasLight) await toDark.click();
  await page.waitForTimeout(600);
  const isDark = await page.evaluate(() => document.documentElement.classList.contains("dark"));
  const bg = await page.locator(SECTION).first().evaluate((el) => getComputedStyle(el).backgroundColor).catch(() => "");
  await ctx.screenshot("87-settings-dark");
  checks.push({ name: "Dark theme renders the section", passed: isDark && !/rgb\(255, 255, 255\)/.test(bg), detail: `html.dark=${isDark} bg=${bg}` });
  checks.push({ name: "axe-core WCAG 2.1 AA (dark): no serious or critical violation in the section", ...(await axeScan(page)) });
  if (wasLight) await page.locator('button[aria-label="Switch to light mode"]').first().click().catch(() => {});
}

/** CLEANUP (API-behind-browser): back to the original model, then delete the scenario project. */
async function cleanup(ctx, checks, { original, projectId }) {
  const { page } = ctx;
  await page.setViewportSize({ width: 1280, height: 800 }).catch(() => {});
  const originalModel = original?.active?.model_id;
  const current = await ctx.api.get(PROFILE).catch(() => null);
  if (originalModel && current?.active?.model_id !== originalModel) {
    const back = await fetch(`${getApiBase()}${PROFILE}`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ model_id: originalModel, prompt_scheme: original.active.prompt_scheme }),
    }).catch((e) => ({ ok: false, status: e.message }));
    const settled = await waitForMigration(ctx);
    checks.push({
      name: "[API-behind-browser] CLEANUP: move back to the original embedding model",
      passed: !!back.ok && settled?.active?.model_id === originalModel && settled?.migration?.state === "done",
      detail: `status=${back.status} model=${settled?.active?.model_id}`,
    });
  }
  try {
    const shared = await ctx.api.get(`/api/projects/${ctx.projectId}`);
    await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
    await selectProject(page, shared.name);
  } catch {}
  if (projectId) {
    const res = await fetch(`${getApiBase()}/api/projects/${projectId}`, { method: "DELETE", headers: authHeaders() }).catch((e) => ({ ok: false, status: e.message }));
    checks.push({ name: "[API-behind-browser] CLEANUP: delete the scenario's synthetic project", passed: !!res.ok, detail: `status=${res.status}` });
  }
}

/** Researcher/viewer: Settings opens, and the embedding-model control is not there. */
async function driveRoleSettingsCell(rolePage) {
  try {
    await navigateTo(rolePage, "Settings", "settings");
    await rolePage.locator("main").first().waitFor({ state: "visible", timeout: 15000 });
    await rolePage.waitForTimeout(1500);
    const count = await rolePage.locator(SECTION).count();
    return { ok: count === 0, detail: count === 0 ? "control absent for the role" : "embedding-model control rendered for a non-admin" };
  } catch (e) {
    return { ok: false, detail: e.message };
  }
}
