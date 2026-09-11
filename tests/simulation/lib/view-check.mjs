/**
 * Shared real-browser view entry for simulation scenarios (Phase 2).
 *
 * Attempts a genuine navigation-tab click first; falls back to the
 * `istara:navigate` DOM event when the tab is not visible (e.g. collapsed
 * under "More views"). Records which path was taken so verdicts stay honest
 * about how "real" each browser act was. Marker strings should come from the
 * 24-view sweep set, which is the proven-resolving reference.
 *
 * Failures are recorded as failed checks, never thrown — the caller's API
 * trajectory below must always still run.
 */

export async function browserViewCheck(
  ctx,
  checks,
  { viewId, navLabel, markers = [], selectors = [], screenshot = null } = {},
) {
  const pass = (name, detail) => {
    checks.push({ name, passed: true, detail });
  };
  try {
    const page = ctx.page;
    await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1000);
    // Onboarding tour overlay swallows nav clicks: mark it complete, reload,
    // and dismiss any residual popover before touching navigation.
    await page
      .evaluate(() => {
        try {
          localStorage.setItem("istara_tour_completed", "true");
          localStorage.setItem("istara_tour_completed_admin", "true");
        } catch {}
      })
      .catch(() => {});
    await page.reload({ waitUntil: "domcontentloaded" }).catch(() => {});
    await page.waitForTimeout(1000);
    await page
      .locator("button[aria-label='Skip tour']")
      .first()
      .click({ timeout: 3000 })
      .catch(() => {});
    await page.waitForTimeout(500);
    const tab = page.locator(`button[aria-label="${navLabel}"]`).first();
    let via = "event-fallback";
    if (await tab.isVisible({ timeout: 5000 }).catch(() => false)) {
      await tab.click();
      await page.waitForTimeout(1000);
      via = "nav-click";
    } else {
      await page.evaluate(
        (view) => window.dispatchEvent(new CustomEvent("istara:navigate", { detail: view })),
        viewId,
      );
      await page.waitForTimeout(1000);
    }
    pass(`Browser: ${viewId} view opened`, via);
    for (const marker of markers) {
      // Views fetch data after mount; poll briefly instead of single-shot.
      // Case-insensitive: CSS text-transform (e.g. uppercase section heads)
      // changes innerText casing but not meaning (matches sweep semantics).
      let seen = false;
      for (let attempt = 0; attempt < 5 && !seen; attempt += 1) {
        if (attempt > 0) await page.waitForTimeout(2000);
        seen = await page
          .evaluate(
            (text) => document.body.innerText.toLowerCase().includes(text.toLowerCase()),
            marker,
          )
          .catch(() => false);
      }
      checks.push({ name: `Browser: ${viewId} shows "${marker}"`, passed: seen, detail: via });
    }
    for (const selector of selectors) {
      // Locator visibility (for inputs keyed by placeholder/aria, whose text
      // never appears in innerText). Same polling as markers.
      let seen = false;
      for (let attempt = 0; attempt < 5 && !seen; attempt += 1) {
        if (attempt > 0) await page.waitForTimeout(2000);
        seen = await page.locator(selector).first().isVisible().catch(() => false);
      }
      checks.push({ name: `Browser: ${viewId} shows "${selector}"`, passed: seen, detail: via });
    }
    if (screenshot && typeof ctx.screenshot === "function") {
      await ctx.screenshot(screenshot);
    }
  } catch (error) {
    checks.push({ name: `Browser: ${viewId} entry`, passed: false, detail: error.message });
  }
  return checks;
}
