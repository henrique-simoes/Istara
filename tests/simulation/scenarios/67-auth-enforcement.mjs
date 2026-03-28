/** Scenario 67 — Authentication Enforcement: verify JWT is required on all
 *  protected endpoints and that security headers are present. */

export const name = "Authentication Enforcement";
export const id = "67-auth-enforcement";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // First, we need to login to get a JWT for authenticated tests
  let jwt = null;
  try {
    // The test runner needs to authenticate first
    const loginRes = await fetch("http://localhost:8000/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: "admin", password: "admin" }),
    });
    if (loginRes.ok) {
      const data = await loginRes.json();
      jwt = data.token || data.access_token;
    }
  } catch {}

  // 1. Health endpoint accessible without JWT
  try {
    const res = await fetch("http://localhost:8000/api/health");
    checks.push({
      name: "Health endpoint accessible without JWT",
      passed: res.status === 200,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Health endpoint without JWT", passed: false, detail: e.message });
  }

  // 2. Projects endpoint returns 401 without JWT
  try {
    const res = await fetch("http://localhost:8000/api/projects");
    checks.push({
      name: "Projects returns 401 without JWT",
      passed: res.status === 401,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Projects without JWT", passed: false, detail: e.message });
  }

  // 3. Findings returns 401 without JWT
  try {
    const res = await fetch("http://localhost:8000/api/findings/nuggets?project_id=test");
    checks.push({
      name: "Findings returns 401 without JWT",
      passed: res.status === 401,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Findings without JWT", passed: false, detail: e.message });
  }

  // 4. Backup download returns 401 without JWT
  try {
    const res = await fetch("http://localhost:8000/api/backups");
    checks.push({
      name: "Backups returns 401 without JWT",
      passed: res.status === 401,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Backups without JWT", passed: false, detail: e.message });
  }

  // 5. Settings returns 401 without JWT
  try {
    const res = await fetch("http://localhost:8000/api/settings/hardware");
    checks.push({
      name: "Settings/hardware returns 401 without JWT",
      passed: res.status === 401,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Settings without JWT", passed: false, detail: e.message });
  }

  // 6. MCP returns 401 without JWT
  try {
    const res = await fetch("http://localhost:8000/api/mcp/server/status");
    checks.push({
      name: "MCP status returns 401 without JWT",
      passed: res.status === 401,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "MCP without JWT", passed: false, detail: e.message });
  }

  // 7. Login endpoint accessible (exempt)
  try {
    const res = await fetch("http://localhost:8000/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: "nonexistent", password: "wrong" }),
    });
    checks.push({
      name: "Login endpoint accessible without JWT",
      passed: res.status !== 401, // Should be 400 or 422, not 401
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Login endpoint accessible", passed: false, detail: e.message });
  }

  // 8. Channels returns 401 without JWT
  try {
    const res = await fetch("http://localhost:8000/api/channels");
    checks.push({
      name: "Channels returns 401 without JWT",
      passed: res.status === 401,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Channels without JWT", passed: false, detail: e.message });
  }

  // 9. Agents returns 401 without JWT
  try {
    const res = await fetch("http://localhost:8000/api/agents");
    checks.push({
      name: "Agents returns 401 without JWT",
      passed: res.status === 401,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Agents without JWT", passed: false, detail: e.message });
  }

  // 10. Autoresearch returns 401 without JWT
  try {
    const res = await fetch("http://localhost:8000/api/autoresearch/status");
    checks.push({
      name: "Autoresearch returns 401 without JWT",
      passed: res.status === 401,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Autoresearch without JWT", passed: false, detail: e.message });
  }

  // 11. Laws returns 401 without JWT
  try {
    const res = await fetch("http://localhost:8000/api/laws");
    checks.push({
      name: "Laws of UX returns 401 without JWT",
      passed: res.status === 401,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Laws without JWT", passed: false, detail: e.message });
  }

  // 12. Skills returns 401 without JWT
  try {
    const res = await fetch("http://localhost:8000/api/skills");
    checks.push({
      name: "Skills returns 401 without JWT",
      passed: res.status === 401,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Skills without JWT", passed: false, detail: e.message });
  }

  // 13. Security headers present
  try {
    const res = await fetch("http://localhost:8000/api/health");
    checks.push({
      name: "X-Content-Type-Options header present",
      passed: res.headers.get("x-content-type-options") === "nosniff",
      detail: `value=${res.headers.get("x-content-type-options")}`,
    });
    checks.push({
      name: "X-Frame-Options header present",
      passed: res.headers.get("x-frame-options") === "DENY",
      detail: `value=${res.headers.get("x-frame-options")}`,
    });
  } catch (e) {
    checks.push({ name: "Security headers", passed: false, detail: e.message });
  }

  // 14. Webhook endpoints accessible (exempt)
  try {
    const res = await fetch("http://localhost:8000/webhooks/whatsapp/test-instance", { method: "GET" });
    checks.push({
      name: "Webhook endpoints accessible without JWT (exempt)",
      passed: res.status !== 401,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Webhook accessibility", passed: false, detail: e.message });
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
  };
}
