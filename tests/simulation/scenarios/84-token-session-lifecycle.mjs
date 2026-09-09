/** Scenario 84 — Token session lifecycle: the changed auth/token custody path.
 *
 *  W5 browser-spine-acceptance: proves the tokenStore custody contract in a
 *  real browser with a FRESH context (no runner token injection, so the
 *  journey is exactly what an end user experiences):
 *    1. Login screen renders; synthetic QA admin signs in via the real form.
 *    2. Custody: a fresh login writes NO `istara_token` into localStorage
 *       (memory-only token; the legacy key is a read-only fallback) and the
 *       session cookie is not JS-readable (HttpOnly).
 *    3. Reload: the session persists via cookie transport (not localStorage).
 *    4. Settings → Session Manager "Sign Out": the real UI control ends the
 *       session — login screen returns and no token residue remains.
 *
 *  Roles: the QA ui lane boots one deterministic first-admin and keeps
 *  TEAM_MODE off, so admin is the only role this journey can honestly drive;
 *  researcher/viewer/stranger journeys stay explicitly not_runnable in the
 *  lane's not-runnable ledger rather than faked here.
 */

export const name = "Token Session Lifecycle";
export const id = "84-token-session-lifecycle";

export async function run(ctx) {
  const checks = [];
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
    // 1. Fresh visitor sees the login screen.
    await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1500);
    const logo = await page
      .locator('[aria-label="Istara logo"]')
      .first()
      .isVisible({ timeout: 10000 })
      .catch(() => false);
    checks.push({
      name: "Browser: fresh visitor lands on login screen",
      passed: logo,
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

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
  };
}
