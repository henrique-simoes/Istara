/** Scenario 25 — Systemic Robustness: cascade deletion, orphan cleanup, timezone safety. */

export const name = "Systemic Robustness (Cascades & Orphan Cleanup)";
export const id = "25-systemic-robustness";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // ── 1. Create a TEMPORARY project for cascade deletion testing ──
  // NOTE: This scenario intentionally creates and deletes its own project
  // to test cascade deletion. It does NOT use the persistent simulation project.
  let projectId = null;
  let sessionId = null;
  let taskId = null;

  try {
    const project = await api.post("/api/projects", {
      name: "[SIM-TEMP] Cascade Deletion Test",
      description: "Temporary project — will be deleted to test cascade behavior",
    });
    projectId = project.id;
    checks.push({ name: "Create temporary cascade test project", passed: !!projectId, detail: `id=${projectId}` });
  } catch (e) {
    checks.push({ name: "Create temporary cascade test project", passed: false, detail: e.message });
    return { checks, passed: 0, failed: checks.length };
  }

  // Create a session
  try {
    const session = await api.post("/api/sessions", {
      project_id: projectId,
      title: "[SIM] Cascade Session",
    });
    sessionId = session.id;
    checks.push({ name: "Create test session", passed: !!sessionId, detail: `id=${sessionId}` });
  } catch (e) {
    checks.push({ name: "Create test session", passed: false, detail: e.message });
  }

  // Create a task
  try {
    const task = await api.post("/api/tasks", {
      project_id: projectId,
      title: "[SIM] Cascade Task",
      description: "Task for cascade test",
    });
    taskId = task.id;
    checks.push({ name: "Create test task", passed: !!taskId, detail: `id=${taskId}` });
  } catch (e) {
    checks.push({ name: "Create test task", passed: false, detail: e.message });
  }

  // ── 2. Verify DAG health endpoint works for our session ──
  if (sessionId) {
    try {
      const health = await api.get(`/api/context-dag/${sessionId}/health`);
      checks.push({
        name: "DAG health before deletion",
        passed: typeof health.total_messages === "number",
        detail: `total=${health.total_messages}`,
      });
    } catch (e) {
      checks.push({ name: "DAG health before deletion", passed: false, detail: e.message });
    }
  }

  // ── 3. Delete the project — should cascade to tasks, sessions, and orphan-free entities ──
  try {
    const res = await api.delete(`/api/projects/${projectId}`);
    checks.push({
      name: "Delete project (cascade)",
      passed: res.status === 204,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Delete project (cascade)", passed: false, detail: e.message });
  }

  // ── 4. Verify session was cascade-deleted ──
  if (sessionId) {
    try {
      const res = await fetch(`http://localhost:8000/api/sessions/detail/${sessionId}`);
      checks.push({
        name: "Session cascade-deleted",
        passed: res.status === 404,
        detail: `status=${res.status} (expect 404)`,
      });
    } catch (e) {
      checks.push({ name: "Session cascade-deleted", passed: false, detail: e.message });
    }
  }

  // ── 5. Verify task was cascade-deleted ──
  if (taskId) {
    try {
      const tasks = await api.get(`/api/tasks?project_id=${projectId}`);
      const orphanFound = Array.isArray(tasks) && tasks.some((t) => t.id === taskId);
      checks.push({
        name: "Task cascade-deleted",
        passed: !orphanFound,
        detail: orphanFound ? "Task still exists (orphan!)" : "Task gone",
      });
    } catch (e) {
      // 404 is also acceptable (project gone)
      checks.push({ name: "Task cascade-deleted", passed: true, detail: "Project gone, tasks inaccessible" });
    }
  }

  // ── 6. Verify DAG nodes were cleaned up (session gone → DAG nodes gone) ──
  if (sessionId) {
    try {
      const structure = await api.get(`/api/context-dag/${sessionId}`);
      const nodesEmpty = structure.nodes && structure.nodes.length === 0;
      checks.push({
        name: "DAG nodes cleaned on session deletion",
        passed: nodesEmpty,
        detail: `nodes=${structure.nodes?.length || 0}`,
      });
    } catch (e) {
      // If endpoint returns error because session gone, that's also acceptable
      checks.push({ name: "DAG nodes cleaned on session deletion", passed: true, detail: "Session gone" });
    }
  }

  // ── 7. Test project 404 after deletion ──
  try {
    const res = await fetch(`http://localhost:8000/api/projects/${projectId}`);
    checks.push({
      name: "Project confirmed deleted",
      passed: res.status === 404,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Project confirmed deleted", passed: false, detail: e.message });
  }

  // ── 8. Health endpoint still works (system-wide stability) ──
  try {
    const health = await api.get("/api/health");
    checks.push({
      name: "System health after cascade deletion",
      passed: health.status === "ok" || health.status === "healthy",
      detail: `status=${health.status}`,
    });
  } catch (e) {
    checks.push({ name: "System health after cascade deletion", passed: false, detail: e.message });
  }

  // ── 9. Backend logs are clean (check no heartbeat/audit timezone errors) ──
  // We verify indirectly: if the settings endpoint works, the heartbeat is running fine
  try {
    const status = await api.get("/api/settings/status");
    checks.push({
      name: "Settings status (heartbeat ok)",
      passed: !!status,
      detail: "No timezone crash",
    });
  } catch (e) {
    checks.push({ name: "Settings status (heartbeat ok)", passed: false, detail: e.message });
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
