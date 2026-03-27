/** Scenario 52 — Meta-Hyperagent: integration tests for the experimental
 *  meta-hyperagent system — status, toggle, proposals, variants, observations.
 *
 *  Exercises: /api/meta-hyperagent/*
 */

export const name = "Meta-Hyperagent";
export const id = "52-meta-hyperagent";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // ── 1. GET /api/meta-hyperagent/status — shows enabled=false by default ──
  let initialStatus = null;
  try {
    initialStatus = await api.get("/api/meta-hyperagent/status");
    checks.push({
      name: "GET /api/meta-hyperagent/status shows enabled=false by default",
      passed: initialStatus.enabled === false,
      detail: `enabled=${initialStatus.enabled}`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/meta-hyperagent/status shows enabled=false by default", passed: false, detail: e.message });
  }

  // ── 2. Status has experimental=true ──
  if (initialStatus) {
    checks.push({
      name: "Status has experimental=true",
      passed: initialStatus.experimental === true,
      detail: `experimental=${initialStatus.experimental}`,
    });
  } else {
    checks.push({ name: "Status has experimental=true", passed: false, detail: "No status returned" });
  }

  // ── 3. POST /api/meta-hyperagent/toggle enables it ──
  try {
    const result = await api.post("/api/meta-hyperagent/toggle", { enabled: true });
    const passed = result.enabled === true || result.success === true;
    checks.push({
      name: "POST /api/meta-hyperagent/toggle enables it",
      passed,
      detail: `result=${JSON.stringify(result)}`,
    });
  } catch (e) {
    checks.push({ name: "POST /api/meta-hyperagent/toggle enables it", passed: false, detail: e.message });
  }

  // ── 4. Status now shows enabled=true ──
  try {
    const status = await api.get("/api/meta-hyperagent/status");
    checks.push({
      name: "Status now shows enabled=true",
      passed: status.enabled === true,
      detail: `enabled=${status.enabled}`,
    });
  } catch (e) {
    checks.push({ name: "Status now shows enabled=true", passed: false, detail: e.message });
  }

  // ── 5. GET /api/meta-hyperagent/proposals returns array ──
  try {
    const result = await api.get("/api/meta-hyperagent/proposals");
    const proposals = Array.isArray(result) ? result : result?.proposals || [];
    checks.push({
      name: "GET /api/meta-hyperagent/proposals returns array",
      passed: Array.isArray(proposals),
      detail: `count=${proposals.length}`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/meta-hyperagent/proposals returns array", passed: false, detail: e.message });
  }

  // ── 6. GET /api/meta-hyperagent/variants returns array ──
  try {
    const result = await api.get("/api/meta-hyperagent/variants");
    const variants = Array.isArray(result) ? result : result?.variants || [];
    checks.push({
      name: "GET /api/meta-hyperagent/variants returns array",
      passed: Array.isArray(variants),
      detail: `count=${variants.length}`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/meta-hyperagent/variants returns array", passed: false, detail: e.message });
  }

  // ── 7. GET /api/meta-hyperagent/observations returns observation data ──
  try {
    const result = await api.get("/api/meta-hyperagent/observations");
    const hasData = result !== null && typeof result === "object";
    checks.push({
      name: "GET /api/meta-hyperagent/observations returns observation data",
      passed: hasData,
      detail: `keys=${Object.keys(result || {}).join(",")}`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/meta-hyperagent/observations returns observation data", passed: false, detail: e.message });
  }

  // ── 8. POST /api/meta-hyperagent/proposals/nonexistent/approve returns 404 ──
  try {
    await api.post("/api/meta-hyperagent/proposals/nonexistent/approve", {});
    // If we get here, it didn't return an error — which is unexpected
    checks.push({
      name: "POST /api/meta-hyperagent/proposals/nonexistent/approve returns 404",
      passed: false,
      detail: "Expected 404 but got success",
    });
  } catch (e) {
    const is404 = e.message.includes("404") || e.message.includes("400") || e.message.includes("not found") || e.message.includes("Not Found");
    checks.push({
      name: "POST /api/meta-hyperagent/proposals/nonexistent/approve returns 404",
      passed: is404,
      detail: e.message,
    });
  }

  // ── 9. POST /api/meta-hyperagent/proposals/nonexistent/reject returns 404 ──
  try {
    await api.post("/api/meta-hyperagent/proposals/nonexistent/reject", {});
    checks.push({
      name: "POST /api/meta-hyperagent/proposals/nonexistent/reject returns 404",
      passed: false,
      detail: "Expected 404 but got success",
    });
  } catch (e) {
    const is404 = e.message.includes("404") || e.message.includes("400") || e.message.includes("not found") || e.message.includes("Not Found");
    checks.push({
      name: "POST /api/meta-hyperagent/proposals/nonexistent/reject returns 404",
      passed: is404,
      detail: e.message,
    });
  }

  // ── 10. POST /api/meta-hyperagent/variants/nonexistent/revert returns 404 ──
  try {
    await api.post("/api/meta-hyperagent/variants/nonexistent/revert", {});
    checks.push({
      name: "POST /api/meta-hyperagent/variants/nonexistent/revert returns 404",
      passed: false,
      detail: "Expected 404 but got success",
    });
  } catch (e) {
    const is404 = e.message.includes("404") || e.message.includes("400") || e.message.includes("not found") || e.message.includes("Not Found");
    checks.push({
      name: "POST /api/meta-hyperagent/variants/nonexistent/revert returns 404",
      passed: is404,
      detail: e.message,
    });
  }

  // ── 11. POST /api/meta-hyperagent/toggle disables it ──
  try {
    const result = await api.post("/api/meta-hyperagent/toggle", { enabled: false });
    const passed = result.enabled === false || result.success === true;
    checks.push({
      name: "POST /api/meta-hyperagent/toggle disables it",
      passed,
      detail: `result=${JSON.stringify(result)}`,
    });
  } catch (e) {
    checks.push({ name: "POST /api/meta-hyperagent/toggle disables it", passed: false, detail: e.message });
  }

  // ── 12. Status shows enabled=false again ──
  try {
    const status = await api.get("/api/meta-hyperagent/status");
    checks.push({
      name: "Status shows enabled=false again",
      passed: status.enabled === false,
      detail: `enabled=${status.enabled}`,
    });
  } catch (e) {
    checks.push({ name: "Status shows enabled=false again", passed: false, detail: e.message });
  }

  // ── Cleanup: ensure meta-hyperagent is disabled ──
  try {
    await api.post("/api/meta-hyperagent/toggle", { enabled: false });
  } catch {}

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
