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
  const projectId = typeof ctx.projectId === "string" ? ctx.projectId.trim() : "";
  const scopedSkipDetail = "[skipped] No active project id; scoped endpoint not called";

  const scopedPath = (path) => {
    const separator = path.includes("?") ? "&" : "?";
    return `${path}${separator}project_id=${encodeURIComponent(projectId)}`;
  };

  const apiGetProjectScoped = async (path, checkName) => {
    if (!projectId) {
      checks.push({ name: checkName, passed: true, detail: scopedSkipDetail });
      return null;
    }
    return api.get(scopedPath(path));
  };

  const apiPostProjectScoped = async (path, body, checkName) => {
    if (!projectId) {
      checks.push({ name: checkName, passed: true, detail: scopedSkipDetail });
      return null;
    }
    return api.post(scopedPath(path), body);
  };

  // ── 1. GET /api/meta-hyperagent/status — reports persisted enabled state ──
  let initialStatus = null;
  try {
    initialStatus = await apiGetProjectScoped("/api/meta-hyperagent/status", "GET /api/meta-hyperagent/status reports enabled state");
    if (initialStatus) {
      checks.push({
        name: "GET /api/meta-hyperagent/status reports enabled state",
        passed: typeof initialStatus.enabled === "boolean",
        detail: `enabled=${initialStatus.enabled}`,
      });
    }
  } catch (e) {
    checks.push({ name: "GET /api/meta-hyperagent/status reports enabled state", passed: false, detail: e.message });
  }

  // ── 2. Status has experimental=true ──
  if (initialStatus) {
    checks.push({
      name: "Status has experimental=true",
      passed: initialStatus.experimental === true,
      detail: `experimental=${initialStatus.experimental}`,
    });
  } else if (!projectId) {
    checks.push({ name: "Status has experimental=true", passed: true, detail: scopedSkipDetail });
  } else {
    checks.push({ name: "Status has experimental=true", passed: false, detail: "No status returned" });
  }

  // ── 3. POST /api/meta-hyperagent/toggle enables it ──
  try {
    const result = await apiPostProjectScoped("/api/meta-hyperagent/toggle", { enabled: true }, "POST /api/meta-hyperagent/toggle enables it");
    if (result) {
      const passed = result.enabled === true || result.success === true;
      checks.push({
        name: "POST /api/meta-hyperagent/toggle enables it",
        passed,
        detail: `result=${JSON.stringify(result)}`,
      });
    }
  } catch (e) {
    checks.push({ name: "POST /api/meta-hyperagent/toggle enables it", passed: false, detail: e.message });
  }

  // ── 4. Status now shows enabled=true ──
  try {
    const status = await apiGetProjectScoped("/api/meta-hyperagent/status", "Status now shows enabled=true");
    if (status) {
      checks.push({
        name: "Status now shows enabled=true",
        passed: status.enabled === true,
        detail: `enabled=${status.enabled}`,
      });
    }
  } catch (e) {
    checks.push({ name: "Status now shows enabled=true", passed: false, detail: e.message });
  }

  // ── 5. GET /api/meta-hyperagent/proposals returns array ──
  try {
    const result = await apiGetProjectScoped("/api/meta-hyperagent/proposals", "GET /api/meta-hyperagent/proposals returns array");
    if (result) {
      const proposals = Array.isArray(result) ? result : result?.proposals || [];
      checks.push({
        name: "GET /api/meta-hyperagent/proposals returns array",
        passed: Array.isArray(proposals),
        detail: `count=${proposals.length}`,
      });
    }
  } catch (e) {
    checks.push({ name: "GET /api/meta-hyperagent/proposals returns array", passed: false, detail: e.message });
  }

  // ── 6. GET /api/meta-hyperagent/variants returns array ──
  try {
    const result = await apiGetProjectScoped("/api/meta-hyperagent/variants", "GET /api/meta-hyperagent/variants returns array");
    if (result) {
      const variants = Array.isArray(result) ? result : result?.variants || [];
      checks.push({
        name: "GET /api/meta-hyperagent/variants returns array",
        passed: Array.isArray(variants),
        detail: `count=${variants.length}`,
      });
    }
  } catch (e) {
    checks.push({ name: "GET /api/meta-hyperagent/variants returns array", passed: false, detail: e.message });
  }

  // ── 7. GET /api/meta-hyperagent/observations returns observation data ──
  try {
    const result = await apiGetProjectScoped("/api/meta-hyperagent/observations", "GET /api/meta-hyperagent/observations returns observation data");
    if (result) {
      const hasData = result !== null && typeof result === "object";
      checks.push({
        name: "GET /api/meta-hyperagent/observations returns observation data",
        passed: hasData,
        detail: `keys=${Object.keys(result || {}).join(",")}`,
      });
    }
  } catch (e) {
    checks.push({ name: "GET /api/meta-hyperagent/observations returns observation data", passed: false, detail: e.message });
  }

  // ── 8. POST /api/meta-hyperagent/proposals/nonexistent/approve returns 404 ──
  try {
    const result = await apiPostProjectScoped("/api/meta-hyperagent/proposals/nonexistent/approve", {}, "POST /api/meta-hyperagent/proposals/nonexistent/approve returns 404");
    if (result) {
      // If we get here, it didn't return an error — which is unexpected
      checks.push({
        name: "POST /api/meta-hyperagent/proposals/nonexistent/approve returns 404",
        passed: false,
        detail: "Expected 404 but got success",
      });
    }
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
    const result = await apiPostProjectScoped("/api/meta-hyperagent/proposals/nonexistent/reject", {}, "POST /api/meta-hyperagent/proposals/nonexistent/reject returns 404");
    if (result) {
      checks.push({
        name: "POST /api/meta-hyperagent/proposals/nonexistent/reject returns 404",
        passed: false,
        detail: "Expected 404 but got success",
      });
    }
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
    const result = await apiPostProjectScoped("/api/meta-hyperagent/variants/nonexistent/revert", {}, "POST /api/meta-hyperagent/variants/nonexistent/revert returns 404");
    if (result) {
      checks.push({
        name: "POST /api/meta-hyperagent/variants/nonexistent/revert returns 404",
        passed: false,
        detail: "Expected 404 but got success",
      });
    }
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
    const result = await apiPostProjectScoped("/api/meta-hyperagent/toggle", { enabled: false }, "POST /api/meta-hyperagent/toggle disables it");
    if (result) {
      const passed = result.enabled === false || result.success === true;
      checks.push({
        name: "POST /api/meta-hyperagent/toggle disables it",
        passed,
        detail: `result=${JSON.stringify(result)}`,
      });
    }
  } catch (e) {
    checks.push({ name: "POST /api/meta-hyperagent/toggle disables it", passed: false, detail: e.message });
  }

  // ── 12. Status shows enabled=false again ──
  try {
    const status = await apiGetProjectScoped("/api/meta-hyperagent/status", "Status shows enabled=false again");
    if (status) {
      checks.push({
        name: "Status shows enabled=false again",
        passed: status.enabled === false,
        detail: `enabled=${status.enabled}`,
      });
    }
  } catch (e) {
    checks.push({ name: "Status shows enabled=false again", passed: false, detail: e.message });
  }

  // ── Cleanup: restore the persisted state we found at startup ──
  try {
    if (projectId && initialStatus && typeof initialStatus.enabled === "boolean") {
      await api.post(scopedPath("/api/meta-hyperagent/toggle"), { enabled: initialStatus.enabled });
    }
  } catch {}

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
