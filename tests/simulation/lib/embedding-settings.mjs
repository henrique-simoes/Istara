/**
 * Page helpers for scenario 87 (Settings > Embedding model): navigation, reading the active model,
 * the confirm-dialog switch, waiting for a migration, and an axe scan scoped to the section.
 */

export const SECTION = '[data-testid="embedding-model-section"]';
export const ACTIVE = '[data-testid="embedding-active-model"]';
export const INPUT = "#embedding-model-input";
export const MARKER = "Scenario87 marker ZEBRA";
export const TARGET = "embeddinggemma";
export const PROFILE = "/api/settings/embedding-profile";

export async function navigateTo(page, label, viewId) {
  const nav = page.locator(`nav[aria-label="Views"] button[aria-label="${label}"]`).first();
  if (await nav.isVisible({ timeout: 3000 }).catch(() => false)) {
    await nav.click();
  } else {
    await page.evaluate((detail) => window.dispatchEvent(new CustomEvent("istara:navigate", { detail })), viewId);
  }
}

export async function openSettings(page) {
  await navigateTo(page, "Settings", "settings");
  return page.locator(SECTION).first().waitFor({ state: "visible", timeout: 20000 }).then(() => true).catch(() => false);
}

export async function remountSettings(page) {
  await navigateTo(page, "Memory", "memory");
  await page.waitForTimeout(400);
  await navigateTo(page, "Settings", "settings");
}

export async function activeModel(page, timeout = 15000) {
  const cell = page.locator(ACTIVE).first();
  const shown = await cell.waitFor({ state: "visible", timeout }).then(() => true).catch(() => false);
  return shown ? (await cell.innerText()).trim() : "";
}

export async function selectProject(page, projectName) {
  const button = page.locator('[aria-label="Projects list"] button', { hasText: projectName }).first();
  await button.waitFor({ state: "visible", timeout: 15000 });
  await button.click();
  await page.waitForTimeout(800);
}

export async function axeScan(page) {
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
export async function requestSwitch(page, model) {
  const input = page.locator(INPUT).first();
  await input.fill(model);
  await input.press("Enter");
  const dialog = page.getByRole("alertdialog").first();
  const shown = await dialog.waitFor({ state: "visible", timeout: 5000 }).then(() => true).catch(() => false);
  const focused = shown ? await page.evaluate(() => document.activeElement?.textContent?.trim() || "") : "";
  if (shown) await page.keyboard.press("Enter");
  return { shown, focused };
}

export async function waitForMigration(ctx, timeoutMs = 120000) {
  const deadline = Date.now() + timeoutMs;
  let status = null;
  while (Date.now() < deadline) {
    status = await ctx.api.get(PROFILE).catch(() => null);
    if (status && status.migration?.state !== "running") return status;
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  return status;
}

/** Researcher/viewer: Settings opens, and the embedding-model control is not there. */
export async function driveRoleSettingsCell(rolePage) {
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
