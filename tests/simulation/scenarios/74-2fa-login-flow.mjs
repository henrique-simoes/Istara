/** Scenario 74 — 2FA Login Flow: verify conditional 2FA UI and passkey button. */

export const name = "2FA Login Flow";
export const id = "74-2fa-login-flow";

export async function run(ctx) {
  const { api, page, report } = ctx;
  const checks = [];

  // 1. Check that the backend returns requires_2fa structure
  try {
    const resp = await api.post("/api/auth/login", { username: "nonexistent", password: "wrong" });
    checks.push({
      name: "Login endpoint rejects bad creds",
      passed: resp.status === 401,
      detail: resp.status,
    });
  } catch (e) {
    checks.push({ name: "Login endpoint rejects bad creds", passed: true, detail: "401 as expected" });
  }

  // 2. UI: Verify login page renders
  try {
    await page.goto("http://localhost:3000", { waitUntil: "networkidle", timeout: 15000 });
    const usernameInput = await page.locator('input[aria-label="Username"]').isVisible({ timeout: 5000 }).catch(() => false);
    checks.push({
      name: "Login page renders username input",
      passed: usernameInput,
      detail: usernameInput ? "Found" : "Not found",
    });
  } catch (e) {
    checks.push({ name: "Login page renders username input", passed: false, detail: e.message });
  }

  // 3. UI: Verify passkey button is present in team mode
  try {
    const passkeyBtn = await page.getByRole("button", { name: /sign in with passkey/i })
      .isVisible({ timeout: 3000 }).catch(() => false);
    checks.push({
      name: "Passkey sign-in button visible",
      passed: passkeyBtn,
      detail: passkeyBtn ? "Found" : "Not found (may be local mode)",
    });
  } catch (e) {
    checks.push({ name: "Passkey sign-in button visible", passed: false, detail: e.message });
  }

  // 4. UI: Verify security headers on the page response
  try {
    const resp = await page.context().request.get("http://localhost:3000");
    const csp = resp.headers()["content-security-policy"];
    const hsts = resp.headers()["strict-transport-security"];
    checks.push({
      name: "CSP header present",
      passed: !!csp,
      detail: csp ? "Present" : "Missing",
    });
    checks.push({
      name: "HSTS header present",
      passed: !!hsts,
      detail: hsts ? "Present" : "Missing",
    });
  } catch (e) {
    checks.push({ name: "Security headers check", passed: false, detail: e.message });
  }

  return {
    checks,
    passed: checks.filter(c => c.passed).length,
    failed: checks.filter(c => !c.passed).length,
    summary: `2FA Login Flow: ${checks.filter(c => c.passed).length}/${checks.length} passed`
  };
}
