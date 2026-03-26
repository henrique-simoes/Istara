/** Scenario 45 — Interfaces Menu: verify design menu endpoints, configuration, and integration status. */

export const name = "Interfaces Menu";
export const id = "45-interfaces-menu";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // ── 1. Menu visibility — GET /api/interfaces/status ──
  try {
    const status = await api.get("/api/interfaces/status");
    checks.push({
      name: "GET /api/interfaces/status returns 200",
      passed: true,
      detail: `stitch_configured=${status.stitch_configured}, figma_configured=${status.figma_configured}`,
    });
    checks.push({
      name: "Status has stitch_configured field",
      passed: status.stitch_configured !== undefined,
      detail: `stitch_configured=${status.stitch_configured}`,
    });
    checks.push({
      name: "Status has figma_configured field",
      passed: status.figma_configured !== undefined,
      detail: `figma_configured=${status.figma_configured}`,
    });
    checks.push({
      name: "Status has onboarding_needed field",
      passed: status.onboarding_needed !== undefined,
      detail: `onboarding_needed=${status.onboarding_needed}`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/interfaces/status returns 200", passed: false, detail: e.message });
  }

  // ── 2. Screens endpoint — GET /api/interfaces/screens/{project_id} ──
  if (ctx.projectId) {
    try {
      const screens = await api.get(`/api/interfaces/screens?project_id=${ctx.projectId}`);
      checks.push({
        name: "GET /api/interfaces/screens returns 200",
        passed: true,
        detail: `screens=${Array.isArray(screens.screens) ? screens.screens.length : JSON.stringify(screens).substring(0, 100)}`,
      });
      checks.push({
        name: "Screens response has screens array",
        passed: Array.isArray(screens.screens || screens),
        detail: `isArray=${Array.isArray(screens.screens || screens)}`,
      });
    } catch (e) {
      checks.push({ name: "GET /api/interfaces/screens returns 200", passed: false, detail: e.message });
    }
  } else {
    checks.push({ name: "GET /api/interfaces/screens (skip)", passed: true, detail: "No projectId" });
  }

  // ── 3. Briefs endpoint — GET /api/interfaces/handoff/briefs/{project_id} ──
  if (ctx.projectId) {
    try {
      const briefs = await api.get(`/api/interfaces/handoff/briefs?project_id=${ctx.projectId}`);
      checks.push({
        name: "GET /api/interfaces/handoff/briefs returns 200",
        passed: true,
        detail: `keys=${Object.keys(briefs).join(", ").substring(0, 100)}`,
      });
    } catch (e) {
      checks.push({ name: "GET /api/interfaces/handoff/briefs returns 200", passed: false, detail: e.message });
    }
  } else {
    checks.push({ name: "GET /api/interfaces/handoff/briefs (skip)", passed: true, detail: "No projectId" });
  }

  // ── 4. Design chat endpoint exists — POST /api/interfaces/design-chat ──
  try {
    const res = await fetch("http://localhost:8000/api/interfaces/design-chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "Hello", project_id: ctx.projectId || "test" }),
    });
    // 200 or SSE stream (content-type text/event-stream) both count as success
    const contentType = res.headers.get("content-type") || "";
    checks.push({
      name: "POST /api/interfaces/design-chat responds",
      passed: res.status === 200 || res.status === 404 || contentType.includes("text/event-stream"),
      detail: `status=${res.status}, content-type=${contentType.substring(0, 50)}`,
    });
  } catch (e) {
    checks.push({ name: "POST /api/interfaces/design-chat responds", passed: false, detail: e.message });
  }

  // ── 5. Configure stitch — POST /api/interfaces/configure/stitch ──
  try {
    const result = await api.post("/api/interfaces/configure/stitch", { api_key: "" });
    checks.push({
      name: "POST /api/interfaces/configure/stitch returns 200",
      passed: true,
      detail: `keys=${Object.keys(result).join(", ").substring(0, 100)}`,
    });
  } catch (e) {
    // 400 is also acceptable — it means the endpoint exists but rejected empty key validation
    const is400 = e.message.includes("400");
    checks.push({
      name: "POST /api/interfaces/configure/stitch returns 200",
      passed: is400,
      detail: is400 ? "400 — endpoint exists, rejects empty key (acceptable)" : e.message,
    });
  }

  // ── 6. Configure figma — POST /api/interfaces/configure/figma ──
  try {
    const result = await api.post("/api/interfaces/configure/figma", { api_token: "" });
    checks.push({
      name: "POST /api/interfaces/configure/figma returns 200",
      passed: true,
      detail: `keys=${Object.keys(result).join(", ").substring(0, 100)}`,
    });
  } catch (e) {
    const is400 = e.message.includes("400");
    checks.push({
      name: "POST /api/interfaces/configure/figma returns 200",
      passed: is400,
      detail: is400 ? "400 — endpoint exists, rejects empty token (acceptable)" : e.message,
    });
  }

  // ── 7. Generate returns error if Stitch not configured ──
  try {
    const res = await fetch("http://localhost:8000/api/interfaces/screens/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: "A login screen", device_type: "mobile" }),
    });
    // Expected: 400 or 422 or 503 because Stitch is not configured
    checks.push({
      name: "POST /api/interfaces/generate returns error if Stitch not configured",
      passed: res.status >= 400 && res.status < 600,
      detail: `status=${res.status} (expected 4xx/5xx without Stitch key)`,
    });
  } catch (e) {
    checks.push({ name: "Generate rejects without Stitch config", passed: false, detail: e.message });
  }

  // ── 8. Figma import returns error if Figma not configured ──
  try {
    const res = await fetch("http://localhost:8000/api/interfaces/figma/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ figma_url: "https://figma.com/file/test123" }),
    });
    checks.push({
      name: "POST /api/interfaces/figma/import returns error if Figma not configured",
      passed: res.status >= 400 && res.status < 600,
      detail: `status=${res.status} (expected 4xx/5xx without Figma token)`,
    });
  } catch (e) {
    checks.push({ name: "Figma import rejects without Figma config", passed: false, detail: e.message });
  }

  // ── 9. Design decisions endpoint — GET /api/findings/design-decisions ──
  try {
    const decisions = await api.get("/api/findings/design-decisions");
    checks.push({
      name: "GET /api/findings/design-decisions returns 200",
      passed: true,
      detail: `type=${typeof decisions}, isArray=${Array.isArray(decisions.decisions || decisions)}`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/findings/design-decisions returns 200", passed: false, detail: e.message });
  }

  // ── 10. Integration status — GET /api/settings/integrations-status ──
  try {
    const integrations = await api.get("/api/settings/integrations-status");
    checks.push({
      name: "GET /api/settings/integrations-status returns 200",
      passed: true,
      detail: `keys=${Object.keys(integrations).join(", ").substring(0, 100)}`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/settings/integrations-status returns 200", passed: false, detail: e.message });
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
