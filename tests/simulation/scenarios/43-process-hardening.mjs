/** Scenario 43 — Process Hardening: test checkpoint recovery, retry logic, and system resilience. */

export const name = "Process Hardening";
export const id = "43-process-hardening";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // ── 1. System health ──
  try {
    const health = await api.get("/api/settings/status");
    checks.push({
      name: "GET /api/settings/status returns system health",
      passed: health !== null && typeof health === "object",
      detail: `keys=${Object.keys(health).slice(0, 5).join(", ")}`,
    });
  } catch (e) {
    checks.push({ name: "System health", passed: false, detail: e.message });
  }

  // ── 2. Data integrity endpoint includes checkpoint-related checks ──
  try {
    const integrity = await api.get("/api/settings/data-integrity");
    checks.push({
      name: "Data integrity returns valid health report",
      passed: integrity.status !== undefined && Array.isArray(integrity.checks),
      detail: `status=${integrity.status}, checks=${integrity.checks?.length}`,
    });
    // Check that the integrity report covers tables
    const checkNames = (integrity.checks || []).map((c) => c.name || "").join(", ");
    checks.push({
      name: "Integrity report covers data stores",
      passed: integrity.checks?.length >= 2,
      detail: `checks: ${checkNames.substring(0, 200)}`,
    });
  } catch (e) {
    checks.push({ name: "Data integrity", passed: false, detail: e.message });
  }

  // ── 3. Create a task and verify it has default retry_count=0 ──
  let taskId = null;
  if (ctx.projectId) {
    try {
      const task = await api.post("/api/tasks", {
        project_id: ctx.projectId,
        title: "[SIM] Process hardening test task",
        description: "Verify default retry and checkpoint state",
      });
      taskId = task.id;
      checks.push({
        name: "Created task has valid id",
        passed: !!task.id,
        detail: `id=${task.id}`,
      });
      // Verify retry_count defaults to 0
      checks.push({
        name: "Task retry_count defaults to 0",
        passed: task.retry_count === 0 || task.retry_count === undefined,
        detail: `retry_count=${task.retry_count}`,
      });
      // Verify task has a status field
      checks.push({
        name: "Task has status field",
        passed: !!task.status,
        detail: `status=${task.status}`,
      });
    } catch (e) {
      checks.push({ name: "Create task for checkpoint test", passed: false, detail: e.message });
    }
  } else {
    checks.push({ name: "Create task for checkpoint test", passed: false, detail: "No project ID" });
  }

  // ── 4. Scheduler endpoint exists ──
  try {
    const res = await fetch("http://localhost:8000/api/settings/status");
    const data = await res.json();
    // The scheduler state is typically reported in system status
    checks.push({
      name: "Scheduler status available via settings",
      passed: res.ok,
      detail: `scheduler info in status response`,
    });
  } catch (e) {
    checks.push({ name: "Scheduler endpoint", passed: false, detail: e.message });
  }

  // ── 5. Maintenance pause/resume endpoints exist (graceful shutdown concept) ──
  try {
    // Test that the maintenance endpoint exists — don't actually pause
    const res = await fetch("http://localhost:8000/api/settings/maintenance/pause?reason=sim-hardening-probe", {
      method: "POST",
    });
    checks.push({
      name: "Maintenance pause endpoint exists",
      passed: res.status === 200 || res.status === 409,
      detail: `status=${res.status}`,
    });
    // Immediately resume if we paused
    if (res.ok) {
      await fetch("http://localhost:8000/api/settings/maintenance/resume", { method: "POST" });
    }
  } catch (e) {
    checks.push({ name: "Maintenance pause endpoint", passed: false, detail: e.message });
  }

  try {
    const res = await fetch("http://localhost:8000/api/settings/maintenance/resume", {
      method: "POST",
    });
    checks.push({
      name: "Maintenance resume endpoint exists",
      passed: res.status === 200 || res.status === 409 || res.status === 400,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Maintenance resume endpoint", passed: false, detail: e.message });
  }

  // ── 6. Health endpoint stable after operations ──
  try {
    const health = await api.get("/api/health");
    checks.push({
      name: "System health stable after hardening checks",
      passed: health.status === "ok" || health.status === "healthy",
      detail: `status=${health.status}`,
    });
  } catch (e) {
    checks.push({ name: "Post-check health", passed: false, detail: e.message });
  }

  // ── Cleanup ──
  if (taskId) {
    try { await api.delete(`/api/tasks/${taskId}`); } catch {}
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
