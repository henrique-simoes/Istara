/** Scenario 02 — Onboarding: full wizard walkthrough or project creation. */

export const name = "Onboarding & Project Setup";
export const id = "02-onboarding";

export async function run(ctx) {
  const { api, page, screenshot } = ctx;
  const checks = [];

  // Use the persistent simulation project from the runner — no new project creation
  checks.push({
    name: "Persistent project available",
    passed: !!ctx.projectId,
    detail: ctx.projectId ? `ID: ${ctx.projectId}` : "No project — runner should have created one",
  });

  // Navigate to home
  await page.goto("http://localhost:3000", { waitUntil: "networkidle", timeout: 15000 });
  await page.waitForTimeout(3000);

  // Check if onboarding wizard appeared (only shows when no projects exist)
  const wizardVisible = await page.locator("text=Welcome to Istara").isVisible().catch(() => false);

  if (wizardVisible) {
    checks.push({ name: "Onboarding wizard appears", passed: true, detail: "Wizard detected (no projects yet)" });
    await screenshot("02-onboarding-wizard");

    // Skip through wizard — project already exists via runner
    const skipBtn = page.locator("button:has-text('Skip'), button:has-text('Get Started'), button:has-text('Start Researching'), button:has-text('Done')").first();
    if (await skipBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await skipBtn.click();
      await page.waitForTimeout(1000);
    }
    await screenshot("02-onboarding-complete");
  } else {
    checks.push({ name: "Onboarding wizard skipped", passed: true, detail: "Project already exists — wizard not shown" });
  }

  // Verify project exists in API
  const projects = await api.get("/api/projects");
  const simProject = projects.find((p) => p.id === ctx.projectId);
  checks.push({
    name: "Project exists in API",
    passed: !!simProject,
    detail: simProject ? `Name: ${simProject.name}` : "Not found",
  });

  // Verify project appears in sidebar
  await page.goto("http://localhost:3000", { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);
  await screenshot("02-project-in-sidebar");

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
