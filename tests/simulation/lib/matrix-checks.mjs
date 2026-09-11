/**
 * Shared UI-matrix checks for simulation scenarios (W5 browser-spine-acceptance).
 *
 * Covers two Full UI Testing Suite Contract obligations that individual views
 * must re-prove per surface: 375px reflow (no horizontal page overflow) and
 * keyboard Tab navigation with a visible focus indicator. Failures are
 * recorded as failed checks, never thrown — the caller's remaining checks
 * must always still run.
 */

/** Emulate a 375px viewport, measure horizontal overflow, restore desktop. */
export async function reflow375Check(page, checks, { name, onNarrow = null } = {}) {
  try {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.waitForTimeout(600);
    const metrics = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    const overflowPx = metrics.scrollWidth - metrics.clientWidth;
    checks.push({
      name: `${name}: 375px reflow (no horizontal overflow)`,
      passed: overflowPx <= 5,
      detail: `scrollWidth=${metrics.scrollWidth} clientWidth=${metrics.clientWidth} overflow=${overflowPx}px`,
    });
    if (typeof onNarrow === "function") await onNarrow();
  } catch (error) {
    checks.push({ name: `${name}: 375px reflow`, passed: false, detail: error.message });
  } finally {
    await page.setViewportSize({ width: 1280, height: 800 }).catch(() => {});
    await page.waitForTimeout(300);
  }
}

/**
 * Tab through the page until the active element matches `targetSelector`
 * (scoped to the current view markup), then assert a visible focus indicator
 * (outline, box-shadow, or a Tailwind focus ring class).
 *
 * `targetText` optionally pins the match to a control bearing that text —
 * for rows with several controls matching one selector (e.g. the chat
 * composer's agent picker + model picker, scenario 83), so Tab stops on a
 * sibling do not satisfy the check.
 */
export async function keyboardFocusCheck(page, checks, { name, targetSelector, targetText = null, maxTabs = 80 } = {}) {
  try {
    await page.keyboard.press("Escape").catch(() => {});
    let reached = false;
    let focusVisible = false;
    for (let i = 0; i < maxTabs && !reached; i += 1) {
      await page.keyboard.press("Tab");
      await page.waitForTimeout(60);
      reached = await page.evaluate(
        ({ sel, text }) => {
          const el = document.activeElement;
          if (!el || !el.matches(sel)) return false;
          if (typeof text === "string" && text.length > 0) {
            return (el.innerText || el.textContent || "").includes(text);
          }
          return !!el.closest(sel);
        },
        { sel: targetSelector, text: targetText },
      );
    }
    if (reached) {
      focusVisible = await page.evaluate(() => {
        const el = document.activeElement;
        if (!el) return false;
        const s = window.getComputedStyle(el);
        const outline = s.outlineStyle !== "none" && parseFloat(s.outlineWidth || "0") > 0;
        const shadow = !!s.boxShadow && s.boxShadow !== "none";
        const ringClass = [...(el.classList || [])].some((c) => /(^|:)focus/.test(c) || c.includes("ring"));
        return outline || shadow || ringClass;
      });
    }
    checks.push({
      name: `${name}: keyboard Tab reaches control with visible focus`,
      passed: reached && focusVisible,
      detail: reached
        ? `focusVisible=${focusVisible} activeElement=${await page.evaluate(() => document.activeElement?.tagName)}`
        : `target not reached within ${maxTabs} Tabs`,
    });
  } catch (error) {
    checks.push({ name: `${name}: keyboard focus`, passed: false, detail: error.message });
  }
}
