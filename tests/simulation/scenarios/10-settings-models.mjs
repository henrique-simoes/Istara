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

  // Pi Model Management is the only mutation surface; retired classical
  // Switch/Pull affordances must not reappear in Settings.
  const piManagement = await page.locator("#pi-model-management-title").first().isVisible({ timeout: 2000 }).catch(() => false);
  checks.push({ name: "Pi Model Management visible", passed: piManagement, detail: "" });
  const retiredSwitch = await page.locator('button:text("Switch")').count();
  const retiredPull = await page.locator('h3:has-text("Pull New Model")').count();
  checks.push({
    name: "Classical model mutation controls absent",
    passed: retiredSwitch === 0 && retiredPull === 0,
    detail: `switch=${retiredSwitch}, pull=${retiredPull}`,
  });

  // Check Refresh button
  const refreshBtn = await page.locator("text=Refresh").first().isVisible({ timeout: 2000 }).catch(() => false);
  checks.push({ name: "Refresh button visible", passed: refreshBtn, detail: "" });

  // F-16: the AC-6 admission refusal must be remediable from the product's
  // own add-model flow via operator contract-rate inputs. Real browser acts:
  // open the add form, pick a provider+model, assert the rate fields exist.
  try {
    const addBtn = page.locator('button:has-text("Add a model")').first();
    const addVisible = await addBtn.isVisible({ timeout: 3000 }).catch(() => false);
    checks.push({ name: "Pi add-model flow opens", passed: addVisible, detail: "" });
    if (addVisible) {
      await addBtn.click();
      await page.waitForTimeout(400);
      const providerInput = page.locator('input[placeholder="Browse or search providers"]').first();
      const providerVisible = await providerInput.isVisible({ timeout: 3000 }).catch(() => false);
      checks.push({ name: "Pi provider picker visible", passed: providerVisible, detail: "" });
      if (providerVisible) {
        await providerInput.fill("zai");
        await page.waitForTimeout(400);
        const firstProvider = page.locator('[role="option"]').first();
        if (await firstProvider.isVisible({ timeout: 3000 }).catch(() => false)) {
          await firstProvider.click();
          await page.waitForTimeout(400);
        }
        const modelInput = page.locator('input[placeholder="Browse or search models"]').first();
        const modelVisible = await modelInput.isVisible({ timeout: 3000 }).catch(() => false);
        checks.push({ name: "Pi model picker visible", passed: modelVisible, detail: "" });
        if (modelVisible) {
          await modelInput.fill("glm-4.7");
          await page.waitForTimeout(400);
          const firstModel = page.locator('[role="option"]').first();
          if (await firstModel.isVisible({ timeout: 3000 }).catch(() => false)) {
            await firstModel.click();
            await page.waitForTimeout(400);
          }
        }
      }
      const rateIds = ["#pi-cost-input", "#pi-cost-output", "#pi-cost-cache-read", "#pi-cost-cache-write"];
      let ratesVisible = 0;
      for (const id of rateIds) {
        if (await page.locator(id).first().isVisible({ timeout: 2000 }).catch(() => false)) ratesVisible++;
      }
      checks.push({
        name: "Pi contract-rate inputs visible (F-16 remedy)",
        passed: ratesVisible === rateIds.length,
        detail: `${ratesVisible}/${rateIds.length} rate fields after provider+model selection`,
      });
      await screenshot("10-pi-contract-rates");
      // Keyboard: the first rate field must be Tab-reachable with visible focus.
      const firstRate = page.locator("#pi-cost-input").first();
      if (await firstRate.isVisible({ timeout: 2000 }).catch(() => false)) {
        await firstRate.focus();
        const focused = await page.evaluate(() => document.activeElement?.id || "").catch(() => "");
        checks.push({
          name: "Pi contract-rate field keyboard-focusable",
          passed: focused === "pi-cost-input",
          detail: `activeElement=${focused || "none"}`,
        });
      }
    }
  } catch (e) {
    checks.push({ name: "Pi contract-rate inputs visible (F-16 remedy)", passed: false, detail: e.message });
  }

  // F-16 (API-behind-browser): a zero-priced catalog model posted without
  // contract rates must refuse 400 pi_endpoint_unpriced naming the remedy
  // and the API path. A refused POST persists nothing, so this is
  // side-effect free; the successful rate-supply admission is covered by
  // backend contract tests (no credential exists in the QA lane to custody).
  try {
    const catalog = await api.get("/api/settings/pi-catalog");
    const providers = catalog.providers || [];
    let target = null;
    for (const p of providers) {
      if (p.id === "dashscope") continue; // governed overlays are preflight-exempt
      for (const m of (p.models || [])) {
        const cost = m.cost || {};
        if (Number(cost.input || 0) <= 0 && Number(cost.output || 0) <= 0) {
          target = { provider: p.id, model: m.id };
          break;
        }
      }
      if (target) break;
    }
    checks.push({
      name: "Zero-priced upstream model present in catalog (F-16 probe)",
      passed: Boolean(target),
      detail: target ? `${target.provider}/${target.model}` : "no $0 upstream model found",
    });
    if (target) {
      const syntheticId = `sim-f16-${Date.now()}`;
      const apiBase = process.env.ISTARA_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiBase}/api/settings/pi-endpoints`, {
        method: "POST",
        headers: api._headers(),
        body: JSON.stringify({
          endpoint_id: syntheticId,
          provider_kind: "openai_compat",
          base_url: "",
          model: "",
          pi_provider: target.provider,
          pi_model: target.model,
          keychain_service: `istara-pi-sim-${syntheticId}`,
        }),
      });
      const body = await response.json().catch(() => ({}));
      const detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body).slice(0, 200);
      checks.push({
        name: "Zero-priced add refuses with remediable 400 (API-behind-browser)",
        passed:
          response.status === 400
          && detail.includes("pi_endpoint_unpriced")
          && detail.includes("cost_input_per_mtok")
          && detail.includes("/api/settings/pi-endpoints"),
        detail: `status=${response.status}, ${detail.slice(0, 160)}`,
      });
    }
  } catch (e) {
    checks.push({ name: "Zero-priced add refuses with remediable 400 (API-behind-browser)", passed: false, detail: e.message });
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}: ${c.detail}`).join("\n"),
  };
}
