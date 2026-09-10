/** Scenario 83 — Chat model controls: the changed chat model-control surface.
 *
 *  Remediation (testing-to-main-remediation-20260909, blocker B4): the old
 *  journey recorded unconditional passes — a search that matched nothing still
 *  "passed" and an empty catalog was labeled "available". Every branch now
 *  asserts the actual post-filter state:
 *    - a known zero-match query yields the explicit no-results state and no
 *      option click is attempted;
 *    - an empty catalog is reported as empty (never "available");
 *    - a selection only counts when an enabled model is actually selected, and
 *      a disabled catalog row is honestly recorded as disabled;
 *    - a catalog load failure is distinguishable from an empty catalog via the
 *      product's accessible error-state seam (`resolveCatalogListState`).
 *
 *  Auth-adjacent (plan W1.5): machine-checkable cells for admin, researcher,
 *  viewer, and stranger via the shared obligation ledger (B5).
 *
 *  The composer is only rendering-checked: the QA lane's provider stub is a
 *  deterministic contract wire, not a model service, so chat generation is
 *  asserted nowhere.
 */

import { browserViewCheck } from "../lib/view-check.mjs";
import { reflow375Check, keyboardFocusCheck } from "../lib/matrix-checks.mjs";
import { createVariantLedger } from "../lib/variant-obligations.mjs";
import { ensureRoleAccounts, driveRoleCell } from "../lib/role-variants.mjs";

export const name = "Chat Model Controls";
export const id = "83-chat-model-controls";

const ZERO_MATCH_QUERY = "zz-no-such-model-qa-8f3";

export async function run(ctx) {
  const { page } = ctx;
  const checks = [];
  const ledger = createVariantLedger(id, [
    { variantId: "role=admin", expectation: "admin drives the picker/filter/selection branches" },
    { variantId: "role=researcher", expectation: "researcher sees the chat workbench and can open the model picker" },
    { variantId: "role=viewer", expectation: "viewer sees the chat workbench and can open the model picker (read-only role)" },
    { variantId: "role=stranger", expectation: "unauthenticated stranger is held at the login screen" },
  ]);

  // ── Admin cell: full picker journey in the runner-authenticated session ──
  const adminOutcome = await driveAdminCell(ctx, checks);

  // ── Researcher / viewer / stranger cells in isolated contexts ──
  const provisioning = await ensureRoleAccounts(ctx);
  await driveRoleCell(ctx, {
    ledger,
    role: "researcher",
    provisioning,
    shotName: "83-role-researcher",
    drive: async (rolePage) => driveAuthenticatedPickerCell(rolePage),
  });
  await driveRoleCell(ctx, {
    ledger,
    role: "viewer",
    provisioning,
    shotName: "83-role-viewer",
    drive: async (rolePage) => driveAuthenticatedPickerCell(rolePage),
  });
  await driveRoleCell(ctx, { ledger, role: "stranger", provisioning, shotName: "83-role-stranger" });

  // Aggregate the admin cell into its ledger row, then enforce the obligation set.
  ledger.record({
    variantId: "role=admin",
    result: adminOutcome.ok ? "pass" : "fail",
    detail: adminOutcome.detail,
    artifacts: ["screenshots/83-model-picker-open.png", "screenshots/83-model-zero-match.png"],
  });
  checks.push(...ledger.finalize());

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
  };
}

/** Admin journey: real browser acts over every picker branch. */
async function driveAdminCell(ctx, checks) {
  const { page } = ctx;
  const detail = [];

  // Browser entry: chat view with its model-control toolbar.
  await browserViewCheck(ctx, checks, {
    viewId: "chat",
    navLabel: "Chat",
    markers: ["Your Research Assistant"],
    selectors: ["[data-chat-workbench]"],
    screenshot: "83-chat-workbench",
  });

  try {
    const trigger = page.locator('[data-chat-workbench] button[aria-haspopup="listbox"]').first();
    await trigger.waitFor({ state: "visible", timeout: 10000 });
    const labelBefore = (await trigger.innerText().catch(() => "")).trim();
    await trigger.click();
    await page.waitForTimeout(500);
    const listbox = page.locator('[role="listbox"][aria-label="Chat models"]');
    const listboxOpen = await listbox.isVisible({ timeout: 5000 }).catch(() => false);
    checks.push({
      name: "Browser: chat model picker opens listbox",
      passed: listboxOpen,
      detail: `trigger="${labelBefore.split("\n")[0] || "n/a"}"`,
    });
    if (!listboxOpen) {
      return { ok: false, detail: "picker listbox never opened" };
    }

    const optionsBefore = await listbox.locator('[role="option"]').count();
    const search = page.locator('input[aria-label="Search chat models"]');

    // 1. Known zero-match query: the explicit no-results state must appear and
    //    no option may be clicked while it is shown.
    await search.fill(ZERO_MATCH_QUERY);
    await page.waitForTimeout(400);
    const zeroMatchOptions = await listbox.locator('[role="option"]').count();
    const zeroMatchState = await listbox
      .locator("text=No models match that search.")
      .isVisible()
      .catch(() => false);
    checks.push({
      name: `Browser: zero-match search "${ZERO_MATCH_QUERY}" shows the explicit no-results state`,
      passed: zeroMatchOptions === 0 && zeroMatchState,
      detail: `options=${zeroMatchOptions} noResultsState=${zeroMatchState} (no click attempted on an empty result set)`,
    });
    await ctx.screenshot("83-model-zero-match");

    // 2. Clearing the query restores the unfiltered catalog exactly.
    await search.fill("");
    await page.waitForTimeout(400);
    const optionsRestored = await listbox.locator('[role="option"]').count();
    checks.push({
      name: "Browser: clearing the search restores the unfiltered catalog",
      passed: optionsRestored === optionsBefore,
      detail: `before=${optionsBefore} restored=${optionsRestored}`,
    });

    // 3. Catalog honesty: selection only when an enabled option exists; a
    //    disabled-only catalog must be reported as disabled, never available;
    //    a truly empty catalog must show the explicit empty state.
    if (optionsBefore === 0) {
      const errorState = await listbox
        .locator("text=Model catalog failed to load")
        .first()
        .isVisible()
        .catch(() => false);
      const emptyState = await listbox
        .locator("text=No models are configured yet")
        .first()
        .isVisible()
        .catch(() => false);
      checks.push({
        name: "Browser: empty catalog is reported as empty or failed (never 'available')",
        passed: emptyState || errorState,
        detail: `options=0 explicitEmptyState=${emptyState} loadFailureState=${errorState} — the two states are distinguishable (resolveCatalogListState seam)`,
      });
      detail.push(errorState ? "catalog load failure surfaced as an error state" : "catalog empty on the QA stub — explicit empty state asserted");
    } else {
      const disabledRows = await listbox.locator('[role="option"][aria-disabled="true"]').count();
      const firstEnabled = listbox.locator('[role="option"]:not([aria-disabled="true"])').first();
      const hasEnabled = await firstEnabled.isVisible().catch(() => false);
      if (hasEnabled) {
        await firstEnabled.click();
        await page.waitForTimeout(500);
        const labelAfter = (await trigger.innerText().catch(() => "")).trim();
        checks.push({
          name: "Browser: selecting an enabled model updates the picker label",
          passed: labelAfter.length > 0 && labelAfter !== labelBefore,
          detail: `before="${labelBefore.split("\n")[0]}" after="${labelAfter.split("\n")[0]}"`,
        });
        detail.push("enabled model selected");
      } else {
        checks.push({
          name: "Browser: disabled-only catalog rows are honestly disabled (no fake availability)",
          passed: disabledRows === optionsBefore && disabledRows > 0,
          detail: `options=${optionsBefore} disabled=${disabledRows} — every row requires configuration, so selection is refused rather than faked`,
        });
        detail.push("catalog present but all rows disabled on the contract stub");
      }
    }
    await ctx.screenshot("83-model-picker-open");

    // 4. Usage dialog: the token/usage control renders and closes.
    await page.keyboard.press("Escape").catch(() => {});
    await page.waitForTimeout(300);
    const usageTrigger = page.locator('[data-chat-workbench] button[aria-haspopup="dialog"]').first();
    await usageTrigger.waitFor({ state: "visible", timeout: 8000 });
    await usageTrigger.click();
    await page.waitForTimeout(400);
    const dialog = page.locator('[role="dialog"][aria-label="Chat usage details"]');
    const open = await dialog.isVisible({ timeout: 5000 }).catch(() => false);
    const heading = open
      ? await dialog.locator("text=This chat's usage").first().isVisible().catch(() => false)
      : false;
    checks.push({
      name: "Browser: chat usage dialog renders",
      passed: open && heading,
      detail: `dialog=${open} heading=${heading}`,
    });
    await ctx.screenshot("83-usage-dialog");
    await page.locator('button[aria-label="Close usage details"]').first().click({ timeout: 3000 }).catch(() => {});
    await page.waitForTimeout(200);

    // 5. Composer renders (rendering only — the contract stub intentionally
    //    fails chat generation closed, so no message is sent in this lane).
    const composer = page
      .locator('[data-chat-workbench] textarea, [data-chat-workbench] [contenteditable="true"]')
      .first();
    const composerVisible = await composer.isVisible({ timeout: 8000 }).catch(() => false);
    checks.push({
      name: "Browser: chat composer renders (no send — contract stub lane)",
      passed: composerVisible,
      detail: composerVisible ? "composer visible; generation not asserted against a wire stub" : "composer not visible",
    });

    // 6. 375px reflow: toolbar and picker trigger survive the narrow viewport.
    await reflow375Check(page, checks, {
      name: "Chat toolbar",
      onNarrow: async () => {
        const narrowTrigger = page.locator('[data-chat-workbench] button[aria-haspopup="listbox"]').first();
        const visible = await narrowTrigger.isVisible({ timeout: 3000 }).catch(() => false);
        checks.push({
          name: "Chat toolbar: model picker usable at 375px",
          passed: visible,
          detail: visible ? "picker trigger visible" : "picker trigger hidden at 375px",
        });
        await ctx.screenshot("83-chat-375px");
      },
    });

    // 7. Keyboard: Tab reaches the model picker trigger with visible focus.
    await keyboardFocusCheck(page, checks, {
      name: "Chat model picker",
      targetSelector: '[data-chat-workbench] button[aria-haspopup="listbox"]',
      maxTabs: 90,
    });

    const failed = checks.filter((c) => !c.passed).length;
    return {
      ok: failed === 0,
      detail: failed === 0 ? `admin picker journey clean (${detail.join("; ")})` : `${failed} admin-cell check(s) failed: ${detail.join("; ")}`,
    };
  } catch (error) {
    checks.push({ name: "Browser: chat model picker", passed: false, detail: error.message });
    return { ok: false, detail: `admin cell error: ${error.message}` };
  }
}

/** Researcher/viewer cells: workbench + picker open (read-path authorization). */
async function driveAuthenticatedPickerCell(rolePage) {
  const workbench = await rolePage
    .locator("[data-chat-workbench]")
    .first()
    .isVisible({ timeout: 15000 })
    .catch(() => false);
  if (!workbench) {
    return { ok: false, detail: "chat workbench not visible for the authenticated role" };
  }
  const trigger = rolePage.locator('[data-chat-workbench] button[aria-haspopup="listbox"]').first();
  const triggerVisible = await trigger.isVisible({ timeout: 8000 }).catch(() => false);
  if (!triggerVisible) {
    return { ok: false, detail: "model picker trigger not visible for the authenticated role" };
  }
  await trigger.click();
  await rolePage.waitForTimeout(400);
  const listbox = rolePage.locator('[role="listbox"][aria-label="Chat models"]');
  const open = await listbox.isVisible({ timeout: 5000 }).catch(() => false);
  await rolePage.keyboard.press("Escape").catch(() => {});
  return {
    ok: open,
    detail: open
      ? "model picker opened for the authenticated role (read-path authorization holds)"
      : "model picker did not open for the authenticated role",
  };
}
