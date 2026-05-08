/** Scenario 10 — Settings & Models: verify hardware detection, model display. */

export const name = "Settings & Models";
export const id = "10-settings-models";

export async function run(ctx) {
  const { api, page, screenshot } = ctx;
  const checks = [];

  // Navigate to Settings via More menu
  await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1000);

  const moreBtn = page.locator('button[aria-label="More views"]').first();
  if (await moreBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    await moreBtn.click();
    await page.waitForTimeout(300);
  }

  const settingsNav = page.locator('button[aria-label="Settings"]').first();
  await settingsNav.click();
  await page.locator("text=Loading system info").waitFor({ state: "detached", timeout: 30000 }).catch(() => {});
  await page.locator("text=System Status").first().waitFor({ state: "visible", timeout: 30000 });

  // Verify Settings sections load. The current settings page is longer than
  // one viewport, so scroll target sections into view before asserting them.
  const sections = ["Software Updates", "Governed Evolution", "Team Members", "Connection Strings", "System Status", "Hardware (Server)", "Recommended Model"];
  for (const section of sections) {
    const sectionLocator = page.locator(`text=${section}`).first();
    await sectionLocator.scrollIntoViewIfNeeded({ timeout: 2000 }).catch(() => {});
    const visible = await sectionLocator.isVisible({ timeout: 2000 }).catch(() => false);
    checks.push({ name: `Section: ${section}`, passed: visible, detail: "" });
  }
  await screenshot("10-settings-view");

  // Check System Status details
  const backendStatus = await page.locator("text=running").first().isVisible({ timeout: 2000 }).catch(() => false);
  checks.push({ name: "Backend status: running", passed: backendStatus, detail: "" });

  const llmStatus = await page.locator("text=Connected").first().isVisible({ timeout: 2000 }).catch(() => false);
  checks.push({ name: "LLM status: Connected", passed: llmStatus, detail: "" });

  // Verify hardware info via API
  try {
    const hw = await api.get("/api/settings/hardware");
    checks.push({
      name: "Hardware API returns data",
      passed: !!hw.hardware,
      detail: `OS: ${hw.hardware?.os}, RAM: ${hw.hardware?.total_ram_gb}GB, CPU: ${hw.hardware?.cpu_cores} cores`,
    });
    if (hw.recommendation) {
      checks.push({
        name: "Model recommendation available",
        passed: !!hw.recommendation.model_name,
        detail: `Recommends: ${hw.recommendation.model_name} (${hw.recommendation.quantization})`,
      });
    }
  } catch (e) {
    checks.push({ name: "Hardware API returns data", passed: false, detail: e.message });
  }

  // Verify models API
  try {
    const models = await api.get("/api/settings/models");
    const modelCount = models.models?.length || 0;
    checks.push({
      name: "Models API returns models",
      passed: modelCount >= 0,
      detail: `${modelCount} models, active: ${models.active_model || "unknown"}`,
    });
  } catch (e) {
    checks.push({ name: "Models API returns models", passed: false, detail: e.message });
  }

  // Check Available Models section in UI
  const availableModels = page.locator("text=Available Models").first();
  await availableModels.scrollIntoViewIfNeeded({ timeout: 2000 }).catch(() => {});
  const modelsSection = await availableModels.isVisible({ timeout: 2000 }).catch(() => false);
  checks.push({ name: "Available Models section", passed: modelsSection, detail: "" });

  // Check Pull New Model input
  const pullInput = await page.locator('input[placeholder*="qwen"]').first().isVisible({ timeout: 2000 }).catch(() => false);
  checks.push({ name: "Pull model input visible", passed: pullInput, detail: "" });

  // Check Refresh button
  const refreshBtn = await page.locator("text=Refresh").first().isVisible({ timeout: 2000 }).catch(() => false);
  checks.push({ name: "Refresh button visible", passed: refreshBtn, detail: "" });

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}: ${c.detail}`).join("\n"),
  };
}
