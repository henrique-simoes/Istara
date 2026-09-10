/** Scenario 82 — Quality Dashboard: metrics & quality views journey.
 *
 *  Remediation (testing-to-main-remediation-20260909, plan W1.3 + B5): the old
 *  journey proved only theme/reflow/focus and its error oracle matched strings
 *  the view never renders. The journey now exercises the dashboard's real
 *  states:
 *    - loading → rendered sections (the loading panel is replaced by content);
 *    - non-empty data surface (Methodology Rigor + Model Performance
 *      Leaderboard) on a fresh project WITHOUT a false-data claim (the
 *      fresh-project empty-safe cells show "No runs" / "N/A");
 *    - error/empty distinguishable: the view's real error strings are asserted
 *      absent on a healthy lane, and the scoped error box is the oracle.
 *
 *  Auth-adjacent (plan W1.5): machine-checkable cells for admin, researcher,
 *  viewer, and stranger via the shared obligation ledger.
 *
 *  Companion to 81-project-settings (which owns the Research Spine
 *  evidence-chain markers inside Project Settings → Research Metrics).
 */

import { browserViewCheck } from "../lib/view-check.mjs";
import { reflow375Check, keyboardFocusCheck } from "../lib/matrix-checks.mjs";
import { createVariantLedger } from "../lib/variant-obligations.mjs";
import { ensureRoleAccounts, driveRoleCell } from "../lib/role-variants.mjs";

export const name = "Quality Dashboard";
export const id = "82-quality-dashboard";

// The view's REAL error strings (QualityView.tsx) — the old /failed to load|/
// regex never matched them, so a rendered error box could hide from the oracle.
const QUALITY_ERROR_TEXTS = [
  "Could not load quality metrics",
  "Model intelligence temporarily unavailable",
];

export async function run(ctx) {
  const { page } = ctx;
  const checks = [];
  const ledger = createVariantLedger(id, [
    { variantId: "role=admin", expectation: "admin drives the dashboard state branches (loading→data, empty-safe, no error)" },
    { variantId: "role=researcher", expectation: "researcher opens the quality dashboard (read-only role)" },
    { variantId: "role=viewer", expectation: "viewer opens the quality dashboard (read-only role)" },
    { variantId: "role=stranger", expectation: "unauthenticated stranger is held at the login screen" },
  ]);

  // ── Admin cell: full dashboard journey in the runner-authenticated session ──
  const adminOutcome = await driveAdminCell(ctx, checks);

  // ── Researcher / viewer / stranger cells in isolated contexts ──
  const provisioning = await ensureRoleAccounts(ctx);
  await driveRoleCell(ctx, {
    ledger,
    role: "researcher",
    provisioning,
    shotName: "82-role-researcher",
    drive: async (rolePage) => driveAuthenticatedDashboardCell(rolePage),
  });
  await driveRoleCell(ctx, {
    ledger,
    role: "viewer",
    provisioning,
    shotName: "82-role-viewer",
    drive: async (rolePage) => driveAuthenticatedDashboardCell(rolePage),
  });
  await driveRoleCell(ctx, { ledger, role: "stranger", provisioning, shotName: "82-role-stranger" });

  ledger.record({
    variantId: "role=admin",
    result: adminOutcome.ok ? "pass" : "fail",
    detail: adminOutcome.detail,
    artifacts: ["screenshots/82-quality-dashboard-view.png", "screenshots/82-quality-375px.png"],
  });
  checks.push(...ledger.finalize());

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
  };
}

/** Admin journey: state branches of the quality dashboard in a real browser. */
async function driveAdminCell(ctx, checks) {
  const { page } = ctx;

  // Browser entry: real navigation-tab click (event fallback allowed),
  // then assert the quality view's rendered sections.
  await browserViewCheck(ctx, checks, {
    viewId: "quality",
    navLabel: "Quality Dashboard",
    markers: ["Quality Dashboard", "Methodology Rigor", "Model Performance Leaderboard"],
    screenshot: "82-quality-dashboard-view",
  });

  // Loading → data: the view mounts with a loading panel and replaces it with
  // the rendered sections; a perpetually loading dashboard fails here.
  try {
    const loadingGone = await page
      .locator("text=Loading quality metrics...")
      .first()
      .waitFor({ state: "hidden", timeout: 15000 })
      .then(() => true)
      .catch(() => false);
    const sectionsRendered =
      (await page.locator("text=Methodology Rigor").first().isVisible().catch(() => false)) &&
      (await page.locator("text=Model Performance Leaderboard").first().isVisible().catch(() => false));
    checks.push({
      name: "Browser: quality view resolves loading → rendered sections",
      passed: loadingGone && sectionsRendered,
      detail: `loadingPanelGone=${loadingGone} sectionsRendered=${sectionsRendered}`,
    });
  } catch (error) {
    checks.push({ name: "Browser: quality view resolves loading → rendered sections", passed: false, detail: error.message });
  }

  // Error state: the view's actual error strings must be absent on a healthy
  // lane (scoped to the real error-box vocabulary, not a generic regex).
  try {
    let errorText = null;
    for (const text of QUALITY_ERROR_TEXTS) {
      if (await page.locator(`text=${text}`).first().isVisible().catch(() => false)) {
        errorText = text;
        break;
      }
    }
    checks.push({
      name: "Browser: quality view shows no error surface (real error strings)",
      passed: !errorText,
      detail: errorText ? `error box rendered: "${errorText}"` : "no view error string rendered",
    });
  } catch (error) {
    checks.push({ name: "Browser: quality view shows no error surface", passed: false, detail: error.message });
  }

  // Empty-safe on a fresh project: with no validation runs yet, the method
  // cards must show their honest empty cells ("No runs" / "N/A") instead of
  // fabricated data.
  try {
    const noRuns = await page.locator("text=No runs").first().isVisible({ timeout: 10000 }).catch(() => false);
    const notAvailable = await page.locator("text=N/A").first().isVisible({ timeout: 3000 }).catch(() => false);
    checks.push({
      name: "Browser: fresh-project empty-safe cells are explicit (No runs / N/A)",
      passed: noRuns || notAvailable,
      detail: `noRunsCell=${noRuns} naCell=${notAvailable} — a fresh QA project has no validation runs yet`,
    });
  } catch (error) {
    checks.push({ name: "Browser: fresh-project empty-safe cells are explicit (No runs / N/A)", passed: false, detail: error.message });
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

  const failed = checks.filter((c) => !c.passed).length;
  return { ok: failed === 0, detail: failed === 0 ? "admin dashboard journey clean" : `${failed} admin-cell check(s) failed` };
}

/** Researcher/viewer cells: dashboard renders for the read-only role. */
async function driveAuthenticatedDashboardCell(rolePage) {
  const qualityTab = rolePage.locator('button[aria-label="Quality Dashboard"]').first();
  const tabVisible = await qualityTab.isVisible({ timeout: 8000 }).catch(() => false);
  if (tabVisible) {
    await qualityTab.click();
  } else {
    await rolePage
      .evaluate(() => window.dispatchEvent(new CustomEvent("istara:navigate", { detail: "quality" })))
      .catch(() => {});
  }
  await rolePage.waitForTimeout(1500);

  const heading = await rolePage
    .locator("text=Quality Dashboard")
    .first()
    .isVisible({ timeout: 10000 })
    .catch(() => false);
  const sections =
    (await rolePage.locator("text=Methodology Rigor").first().isVisible().catch(() => false)) ||
    (await rolePage.locator("text=Loading quality metrics...").first().isVisible().catch(() => false));
  return {
    ok: heading && sections,
    detail:
      heading && sections
        ? "quality dashboard renders for the authenticated role (read-path authorization holds)"
        : `dashboard not reachable for the role: heading=${heading} sections=${sections}`,
  };
}
