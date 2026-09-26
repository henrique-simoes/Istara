/**
 * Shared UI-matrix checks for simulation scenarios (W5 browser-spine-acceptance).
 *
 * Covers two Full UI Testing Suite Contract obligations that individual views
 * must re-prove per surface: 375px reflow (no horizontal page overflow, nothing in the view cut
 * off) and
 * keyboard Tab navigation with a visible focus indicator. Failures are
 * recorded as failed checks, never thrown — the caller's remaining checks
 * must always still run.
 */

/**
 * Elements inside `main` that are cut off past the viewport's right edge, reported where the
 * overflow starts (the element sticks out while its parent does not). The page itself never
 * scrolls sideways when an ancestor clips, so document scrollWidth alone missed a Settings column
 * 527 px wide at 375 px (2026-09-26). Content inside its own horizontal scroller is reachable and
 * excluded, as are hidden elements and anything that starts past the edge (an off-canvas drawer).
 */
export async function clippedInMain(page) {
  return page.evaluate(clippedElements);
}

/** Runs in the page: the cut-off elements inside `main`, one line each. */
function clippedElements() {
  const main = document.querySelector("main");
  if (!main) return [];
  const vw = window.innerWidth;
  const all = [...main.querySelectorAll("*")];
  // Starts on screen, ends past the edge, while its parent ends on screen.
  const sticksOut = (el) => {
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.left < vw && r.right > vw + 1 && el.parentElement.getBoundingClientRect().right <= vw + 1;
  };
  const scrollers = all.filter((a) => ["auto", "scroll"].includes(getComputedStyle(a).overflowX) && a.scrollWidth > a.clientWidth);
  const insideScroller = (el) => scrollers.some((s) => s !== el && s.contains(el));
  const label = (el) => (el.getAttribute("aria-label") || el.textContent || "").trim().slice(0, 40);
  return all
    .filter((el) => sticksOut(el) && el.checkVisibility({ visibilityProperty: true }) && !insideScroller(el))
    .map((el) => `${el.tagName.toLowerCase()} right=${Math.round(el.getBoundingClientRect().right)} "${label(el)}"`);
}

/**
 * Put the app in `theme` ("light" | "dark") through its own toggle and return whether the page is
 * dark. Istara stores an explicit choice, so emulating the colour scheme alone does not switch a
 * page whose theme an earlier scenario chose.
 */
export async function setTheme(page, theme) {
  const label = theme === "dark" ? "Switch to dark mode" : "Switch to light mode";
  const toggle = page.locator(`button[aria-label="${label}"]`).first();
  if (await toggle.isVisible({ timeout: 3000 }).catch(() => false)) await toggle.click();
  await page.waitForTimeout(400);
  return page.evaluate(() => document.documentElement.classList.contains("dark"));
}

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
    const clipped = await clippedInMain(page);
    checks.push({
      name: `${name}: 375px nothing in the view is cut off`,
      passed: clipped.length === 0,
      detail: clipped.length ? `${clipped.length} cut off: ${clipped.slice(0, 3).join("; ")}` : "none cut off",
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
