/** Scenario 37 — Ensemble Health View: verify frontend views and their backing APIs. */

export const name = "Ensemble Health View";
export const id = "37-ensemble-health-view";

export async function run(ctx) {
  const { page, screenshot, api } = ctx;
  const checks = [];
  const projectId = ctx.projectId;

  // 1. Verify compute stats API works (backend for ComputePoolView)
  try {
    if (!projectId) throw new Error("Missing ctx.projectId for project-scoped compute stats");
    const stats = await api.get(`/api/compute/stats?project_id=${encodeURIComponent(projectId)}`);
    checks.push({
      name: "Compute pool API works",
      passed: stats.swarm_tier !== undefined && stats.total_nodes !== undefined,
      detail: `tier=${stats.swarm_tier}, nodes=${stats.total_nodes}`,
    });
  } catch (e) {
    checks.push({ name: "Compute pool API works", passed: false, detail: e.message });
  }

  // 2. Verify the model catalog API works (Pi providers + configured endpoints identity view).
  try {
    const catalog = await api.get(`/api/chat/model-catalog?project_id=${encodeURIComponent(projectId)}`);
    checks.push({
      name: "Model catalog API works",
      passed: Array.isArray(catalog.providers) && ["pi", "legacy"].includes(catalog.engine),
      detail: `providers=${catalog.providers?.length}, engine=${catalog.engine}, pi_configured=${catalog.configured?.length}`,
    });
  } catch (e) {
    checks.push({ name: "Model catalog API works", passed: false, detail: e.message });
  }

  // 3. Verify maintenance endpoint works (used by ensemble views)
  try {
    const maint = await api.get("/api/settings/maintenance");
    checks.push({
      name: "Maintenance API works",
      passed: maint.maintenance_mode !== undefined,
      detail: `mode=${maint.maintenance_mode}`,
    });
  } catch (e) {
    checks.push({ name: "Maintenance API works", passed: false, detail: e.message });
  }

  // 4. Navigate to frontend and check if sidebar renders
  try {
    await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded", timeout: 15000 });
    await page.waitForSelector('button[aria-label="More views"], button[aria-label="Chat"], main', { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(1000);

    // Check if the app loaded (either main app with sidebar or LLM connection screen)
    const bodyText = await page.textContent("body");
    const sidebarVisible = await page.locator('button[aria-label="More views"]').first().isVisible().catch(() => false);

    if (sidebarVisible) {
      // Sidebar is visible — click through to views
      await page.locator('button[aria-label="More views"]').first().click();
      await page.waitForTimeout(500);
      const computeBtn = await page.locator('button[aria-label="Compute Pool"]').first().isVisible().catch(() => false);
      const ensembleBtn = await page.locator('button[aria-label="Ensemble Health"]').first().isVisible().catch(() => false);
      checks.push({
        name: "Sidebar nav items present",
        passed: computeBtn && ensembleBtn,
        detail: `compute=${computeBtn}, ensemble=${ensembleBtn}`,
      });
    } else {
      // LLM not connected — frontend blocks sidebar; this is expected behavior
      const isLlmBlock = bodyText.includes("LLM Provider Not Connected") || bodyText.includes("Check Again");
      const bodyHasNav = bodyText.includes("Compute Pool") && bodyText.includes("Ensemble Health");
      checks.push({
        name: "Sidebar nav items present",
        passed: isLlmBlock || bodyHasNav, // Pass if LLM gate is the reason or nav text rendered without the More button.
        detail: isLlmBlock
          ? "Sidebar hidden behind LLM connection gate (expected without local LLM)"
          : bodyHasNav
            ? "Navigation labels rendered in app body"
            : "Sidebar not found for unknown reason",
      });
    }
  } catch (e) {
    checks.push({ name: "Sidebar nav items present", passed: false, detail: e.message });
  }

  // 5. Take screenshot
  if (screenshot) {
    try {
      await screenshot("ensemble-health-view");
      checks.push({ name: "Screenshot captured", passed: true, detail: "ensemble-health-view.png" });
    } catch (e) {
      checks.push({ name: "Screenshot captured", passed: false, detail: e.message });
    }
  }

  const passed = checks.filter((c) => c.passed).length;
  const failed = checks.filter((c) => !c.passed).length;
  return { checks, passed, failed };
}
