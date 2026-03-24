/** Scenario 37 — Ensemble Health View: verify frontend views render. */

export const name = "Ensemble Health View";
export const id = "37-ensemble-health-view";

export async function run(ctx) {
  const { page, screenshot } = ctx;
  const checks = [];

  // 1. Navigate to compute pool view
  try {
    // Click "More" to expand secondary nav, then click "Compute Pool"
    const moreBtn = page.locator('button[aria-label="More views"]');
    if (await moreBtn.isVisible()) {
      await moreBtn.click();
      await page.waitForTimeout(300);
    }

    const computeBtn = page.locator('button:has-text("Compute Pool")');
    if (await computeBtn.isVisible()) {
      await computeBtn.click();
      await page.waitForTimeout(500);
    }

    const heading = page.locator('h2:has-text("Compute Pool")');
    const visible = await heading.isVisible().catch(() => false);
    checks.push({
      name: "Compute Pool view renders",
      passed: visible,
      detail: visible ? "Heading found" : "Heading not visible",
    });
  } catch (e) {
    checks.push({ name: "Compute Pool view renders", passed: false, detail: e.message });
  }

  // 2. Navigate to ensemble health view
  try {
    const ensembleBtn = page.locator('button:has-text("Ensemble Health")');
    if (await ensembleBtn.isVisible()) {
      await ensembleBtn.click();
      await page.waitForTimeout(500);
    }

    const heading = page.locator('h2:has-text("Ensemble Health")');
    const visible = await heading.isVisible().catch(() => false);
    checks.push({
      name: "Ensemble Health view renders",
      passed: visible,
      detail: visible ? "Heading found" : "Heading not visible",
    });
  } catch (e) {
    checks.push({ name: "Ensemble Health view renders", passed: false, detail: e.message });
  }

  // 3. Confidence thresholds section visible
  try {
    const thresholds = page.locator('text=Confidence Thresholds');
    const visible = await thresholds.isVisible().catch(() => false);
    checks.push({
      name: "Confidence thresholds shown",
      passed: visible,
      detail: visible ? "Section found" : "Section not visible",
    });
  } catch (e) {
    checks.push({ name: "Confidence thresholds shown", passed: false, detail: e.message });
  }

  // 4. Validation methods listed
  try {
    const selfMoa = page.locator('text=Self-MoA');
    const visible = await selfMoa.isVisible().catch(() => false);
    checks.push({
      name: "Validation methods listed",
      passed: visible,
      detail: visible ? "Self-MoA found" : "Not found",
    });
  } catch (e) {
    checks.push({ name: "Validation methods listed", passed: false, detail: e.message });
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
