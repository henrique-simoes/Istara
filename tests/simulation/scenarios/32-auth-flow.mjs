/** Scenario 32 — Auth Flow: verify team mode auth endpoints. */

export const name = "Auth Flow";
export const id = "32-auth-flow";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // 1. Team status endpoint
  try {
    const status = await api.get("/api/auth/team-status");
    checks.push({
      name: "Team status endpoint",
      passed: status.team_mode !== undefined,
      detail: `team_mode=${status.team_mode}`,
    });
  } catch (e) {
    checks.push({ name: "Team status endpoint", passed: false, detail: e.message });
  }

  // 2. Login endpoint reachable (exempt from JWT middleware)
  //    Send a raw fetch without JWT to confirm the middleware lets it through.
  //    We expect either 200 (valid credentials) or 401 with "Invalid username"
  //    (handler rejection), NOT 401 with "Authentication required" (middleware).
  try {
    const res = await fetch("http://localhost:8000/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: "test", password: "test" }),
    });
    const body = await res.json().catch(() => ({}));
    const reachedHandler = res.status === 200 ||
      res.status === 429 ||
      (body.detail && body.detail.includes("Invalid username or password"));
    checks.push({
      name: "Local mode login",
      passed: reachedHandler,
      detail: `status=${res.status} detail=${body.detail || body.user?.username || "ok"}`,
    });
  } catch (e) {
    checks.push({ name: "Local mode login", passed: false, detail: e.message });
  }

  // 3. Auth/me endpoint
  try {
    const me = await api.get("/api/auth/me");
    checks.push({
      name: "Auth me endpoint",
      passed: !!me,
      detail: JSON.stringify(me).substring(0, 100),
    });
  } catch (e) {
    checks.push({ name: "Auth me endpoint", passed: false, detail: e.message });
  }

  // 4. Preferences update
  try {
    const prefs = await api.put("/api/auth/preferences", { preferences: { theme: "dark" } });
    checks.push({
      name: "Preferences update",
      passed: prefs.status === "ok",
      detail: JSON.stringify(prefs),
    });
  } catch (e) {
    checks.push({ name: "Preferences update", passed: false, detail: e.message });
  }

  const passed = checks.filter((c) => c.passed).length;
  const failed = checks.filter((c) => !c.passed).length;
  return { checks, passed, failed };
}
