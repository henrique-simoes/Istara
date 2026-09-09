/** Scenario 82 — Quality Dashboard: metrics & quality views journey.
 *
 *  W5 browser-spine-acceptance: proves the changed metrics/quality surfaces
 *  in a real browser — Quality Dashboard view entry, its rendered sections
 *  (loading→data, empty-safe on a fresh project, error-free), the dark/light
 *  theme matrix, 375px reflow, and keyboard Tab + visible focus.
 *
 *  Companion to 81-project-settings (which owns the Research Spine
 *  evidence-chain markers inside Project Settings → Research Metrics).
 */

import { browserViewCheck } from "../lib/view-check.mjs";
import { reflow375Check, keyboardFocusCheck } from "../lib/matrix-checks.mjs";

export const name = "Quality Dashboard";
export const id = "82-quality-dashboard";

export async function run(ctx) {
  const { page } = ctx;
  const checks = [];

  // Browser entry: real navigation-tab click (event fallback allowed),
  // then assert the quality view's rendered sections.
  await browserViewCheck(ctx, checks, {
    viewId: "quality",
    navLabel: "Quality Dashboard",
    markers: ["Quality Dashboard", "Methodology Rigor", "Model Performance Leaderboard"],
    screenshot: "82-quality-dashboard-view",
  });

  // Error state: a healthy view must not render its error surface.
  try {
    const hasError = await page
      .evaluate(() => /failed to load|something went wrong|error loading/i.test(document.body.innerText))
      .catch(() => true);
    checks.push({
      name: "Browser: quality view shows no error surface",
      passed: !hasError,
      detail: hasError ? "error text visible in view" : "no error text rendered",
    });
  } catch (error) {
    checks.push({ name: "Browser: quality view shows no error surface", passed: false, detail: error.message });
  }

  // Theme matrix: toggle dark → light and assert the html class flips.
  try {
    const before = await page.evaluate(() => document.documentElement.classList.contains("dark"));
    const darkToggle = page
      .locator('button[aria-label*="dark"], button[aria-label*="theme"], button[aria-label*="mode"]')
      .first();
    const toggled = await darkToggle.isVisible({ timeout: 3000 }).catch(() => false);
    if (toggled) {
      await darkToggle.click({ timeout: 3000 });
      await page.waitForTimeout(600);
      const after = await page.evaluate(() => document.documentElement.classList.contains("dark"));
      checks.push({
        name: "Browser: dark/light theme toggles",
        passed: before !== after,
        detail: `dark before=${before} after=${after}`,
      });
      await ctx.screenshot("82-quality-light-theme");
      await darkToggle.click({ timeout: 3000 });
      await page.waitForTimeout(400);
    } else {
      checks.push({
        name: "Browser: dark/light theme toggles",
        passed: false,
        detail: "theme toggle button not visible",
      });
    }
  } catch (error) {
    checks.push({ name: "Browser: dark/light theme toggles", passed: false, detail: error.message });
  }

  // 375px reflow of the quality view.
  await reflow375Check(page, checks, {
    name: "Quality Dashboard",
    onNarrow: () => ctx.screenshot("82-quality-375px"),
  });

  // Keyboard: Tab navigation reaches the Quality Dashboard nav control
  // with a visible focus indicator.
  await keyboardFocusCheck(page, checks, {
    name: "Quality Dashboard nav",
    targetSelector: 'button[aria-label="Quality Dashboard"], nav[aria-label="Views"] button',
    maxTabs: 40,
  });

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
  };
}
