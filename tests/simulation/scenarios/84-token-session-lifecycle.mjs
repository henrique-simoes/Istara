/** Scenario 84 — Token session lifecycle: the changed auth/token custody path.
 *
 *  Remediation (testing-to-main-remediation-20260909, blocker B5 / plan W1.4):
 *  proves the tokenStore custody contract in real browsers across the required
 *  role/variant cells instead of a single admin-only boolean:
 *    - stranger: a fresh unauthenticated context is held at the login screen;
 *    - admin: real form login → memory-only token (NO `istara_token` in
 *      localStorage; the legacy key is a read-only fallback), HttpOnly session
 *      cookie, session persists across reload via cookie transport, and the
 *      real Settings → Session Manager "Sign Out" control ends the session;
 *    - researcher / viewer: synthetic accounts (labeled SETUP via the admin
 *      provisioning API — the admin UI has no create-user form) form-login in
 *      isolated contexts and the same custody contract is asserted.
 *
 *  Every cell is recorded in the machine-checkable obligation ledger; a missing,
 *  failed, or invalidly-unavailable required cell fails the scenario (B5).
 */

import { createVariantLedger } from "../lib/variant-obligations.mjs";
import { ensureRoleAccounts, driveRoleCell } from "../lib/role-variants.mjs";

export const name = "Token Session Lifecycle";
export const id = "84-token-session-lifecycle";

export async function run(ctx) {
  const checks = [];
  const ledger = createVariantLedger(id, [
    { variantId: "role=stranger", expectation: "fresh unauthenticated visitor is held at the login screen" },
    { variantId: "role=admin", expectation: "admin custody: form login, memory-only token, HttpOnly cookie, reload persistence, real UI sign-out" },
    { variantId: "role=researcher", expectation: "researcher custody: form login and memory-only token/HttpOnly cookie" },
    { variantId: "role=viewer", expectation: "viewer custody: form login and memory-only token/HttpOnly cookie" },
  ]);

  // ── Admin cell: the full custody journey (its fresh pre-login phase is the
  // stranger cell — the exact experience an unauthenticated visitor gets). ──
  const adminOutcome = await driveAdminCustodyJourney(ctx, checks, ledger);

  // ── Researcher / viewer cells: isolated contexts, real form logins. ──
  const provisioning = await ensureRoleAccounts(ctx);
  await driveRoleCell(ctx, {
    ledger,
    role: "researcher",
    provisioning,
    shotName: "84-role-researcher",
    drive: async (rolePage) => driveRoleCustodyCell(rolePage),
  });
  await driveRoleCell(ctx, {
    ledger,
    role: "viewer",
    provisioning,
    shotName: "84-role-viewer",
    drive: async (rolePage) => driveRoleCustodyCell(rolePage),
  });

  ledger.record({
    variantId: "role=admin",
    result: adminOutcome.ok ? "pass" : "fail",
    detail: adminOutcome.detail,
    artifacts: ["screenshots/84-fresh-login-screen.png", "screenshots/84-session-manager.png", "screenshots/84-after-signout.png"],
  });
  checks.push(...ledger.finalize());

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
  };
}

async function driveAdminCustodyJourney(ctx, checks, ledger) {
  const username = process.env.ADMIN_USERNAME || "admin";
  const password = process.env.ADMIN_PASSWORD || "";

  const browser = ctx.page.context().browser();
  const freshContext = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    colorScheme: "dark",
  });
  freshContext.setDefaultTimeout(15000);
  const page = await freshContext.newPage();

  const shot = async (name) => {
    try {
      await page.screenshot({ path: `${ctx.runDir}/screenshots/${name}.png` });
    } catch {}
  };

  try {
    // Stranger cell (recorded from this fresh context BEFORE any login): the
    // unauthenticated visitor lands on the login screen with no shell.
    await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1500);
    const logo = await page
      .locator('[aria-label="Istara logo"]')
      .first()
      .isVisible({ timeout: 10000 })
      .catch(() => false);
    const shellHiddenPreLogin = !(await page.locator('nav[aria-label="Views"]').isVisible().catch(() => false));
    checks.push({
      name: "Browser: fresh visitor lands on login screen",
      passed: logo && shellHiddenPreLogin,
      detail: logo ? "Istara logo visible" : "logo not visible",
    });
    await shot("84-fresh-login-screen");

    if (logo && password) {
      // 2. Real form login with the synthetic QA admin credentials.
      await page.locator("#login-username").fill(username);
      await page.locator("#login-password").fill(password);
      await shot("84-credentials-filled");
      await page.locator('form button[type="submit"]').first().click();
      await page.waitForTimeout(2500);

      const shell = await page
        .locator('nav[aria-label="Views"]')
        .first()
        .isVisible({ timeout: 15000 })
        .catch(() => false);
      checks.push({
        name: "Browser: form login reaches the authenticated shell",
        passed: shell,
        detail: shell ? "Views nav visible" : "Views nav never appeared",
      });

      // 3. Custody contract: memory-only token, HttpOnly cookie.
      const custody = await page.evaluate(() => ({
        legacyToken: window.localStorage.getItem("istara_token"),
        cookieExposesSession: /istara_session/.test(document.cookie || ""),
      }));
      checks.push({
        name: "Browser: fresh login writes no localStorage token (memory-only custody)",
        passed: custody.legacyToken === null,
        detail: `istara_token=${custody.legacyToken === null ? "absent" : "present"}`,
      });
      checks.push({
        name: "Browser: session cookie is not JS-readable (HttpOnly)",
        passed: !custody.cookieExposesSession,
        detail: custody.cookieExposesSession ? "istara_session leaked to document.cookie" : "no session cookie in document.cookie",
      });
      await shot("84-authenticated-shell");

      // 4. Reload: session survives via cookie transport, not localStorage.
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.waitForTimeout(2000);
      const shellAfterReload = await page
        .locator('nav[aria-label="Views"]')
        .first()
        .isVisible({ timeout: 15000 })
        .catch(() => false);
      const tokenAfterReload = await page.evaluate(() => window.localStorage.getItem("istara_token"));
      checks.push({
        name: "Browser: session persists across reload without a localStorage token",
        passed: shellAfterReload && tokenAfterReload === null,
        detail: `shell=${shellAfterReload} istara_token=${tokenAfterReload === null ? "absent" : "present"}`,
      });

      // 5. Real UI logout: Settings → Session Manager → Sign Out.
      await page.keyboard.press("Escape").catch(() => {});
      const settingsTab = page.locator('button[aria-label="Settings"], nav[aria-label="Views"] button:has-text("Settings")').first();
      const settingsVisible = await settingsTab.isVisible({ timeout: 5000 }).catch(() => false);
      if (settingsVisible) {
        await settingsTab.click();
        await page.waitForTimeout(1500);
      } else {
        await page.evaluate(() =>
          window.dispatchEvent(new CustomEvent("istara:navigate", { detail: "settings" })),
        );
        await page.waitForTimeout(1500);
      }
      const signOut = page.locator('button[aria-label="Sign out this device"]').first();
      const signOutVisible = await signOut.isVisible({ timeout: 10000 }).catch(() => false);
      if (signOutVisible) {
        await shot("84-session-manager");
        await signOut.click();
        await page.waitForTimeout(2500);
        const backToLogin = await page
          .locator('[aria-label="Istara logo"]')
          .first()
          .isVisible({ timeout: 15000 })
          .catch(() => false);
        const residue = await page.evaluate(() => window.localStorage.getItem("istara_token"));
        checks.push({
          name: "Browser: Sign Out ends the session at the UI",
          passed: backToLogin,
          detail: backToLogin ? "login screen restored" : "login screen did not return",
        });
        checks.push({
          name: "Browser: logout clears token residue from storage",
          passed: residue === null,
          detail: `istara_token=${residue === null ? "absent" : "present after logout"}`,
        });
        await shot("84-after-signout");
      } else {
        checks.push({
          name: "Browser: Session Manager Sign Out control",
          passed: false,
          detail: "Sign out this device control not visible in Settings",
        });
      }
    } else if (!password) {
      checks.push({
        name: "QA admin credentials available for the journey",
        passed: false,
        detail: "ADMIN_PASSWORD env not set — journey cannot sign in honestly; not skipped silently",
      });
    }
  } catch (error) {
    checks.push({ name: "Token session lifecycle journey", passed: false, detail: error.message });
  } finally {
    await freshContext.close().catch(() => {});
  }

  // The stranger cell rides the same evidence: it held at the login screen.
  const strangerHeld = checks
    .filter((c) => c.name === "Browser: fresh visitor lands on login screen")
    .every((c) => c.passed);
  ledger.record({
    variantId: "role=stranger",
    result: strangerHeld ? "pass" : "fail",
    detail: `unauthenticated fresh context held at the login screen (held=${strangerHeld})`,
    artifacts: ["screenshots/84-fresh-login-screen.png"],
  });

  const custodyChecks = checks.filter((c) => c.name !== "Browser: fresh visitor lands on login screen");
  const custodyFailed = custodyChecks.filter((c) => !c.passed).length;
  if (!password) {
    return { ok: false, detail: "ADMIN_PASSWORD unavailable — admin custody journey could not sign in honestly" };
  }
  return {
    ok: custodyFailed === 0,
    detail: custodyFailed === 0
      ? "admin custody journey clean (form login, memory-only token, HttpOnly cookie, reload persistence, real sign-out)"
      : `${custodyFailed} admin custody check(s) failed`,
  };
}

/** Researcher/viewer custody: real form login + the same custody contract. */
async function driveRoleCustodyCell(rolePage) {
  const shell = await rolePage
    .locator('nav[aria-label="Views"]')
    .first()
    .isVisible({ timeout: 20000 })
    .catch(() => false);
  if (!shell) {
    return { ok: false, detail: "form login never reached the authenticated shell" };
  }
  const custody = await rolePage.evaluate(() => ({
    legacyToken: window.localStorage.getItem("istara_token"),
    cookieExposesSession: /istara_session/.test(document.cookie || ""),
  }));
  const custodyHeld = custody.legacyToken === null && !custody.cookieExposesSession;
  return {
    ok: custodyHeld,
    detail: custodyHeld
      ? "role custody holds: memory-only token, no JS-readable session cookie"
      : `role custody violated: istara_token=${custody.legacyToken === null ? "absent" : "present"} cookieLeak=${custody.cookieExposesSession}`,
  };
}
