/** Scenario 18 — Task Verification: test self-verification gate on task completion. */

export const name = "Task Self-Verification";
export const id = "18-task-verification";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  if (!ctx.projectId) {
    return { checks: [{ name: "Skip — no project", passed: false, detail: "No project ID" }], passed: 0, failed: 1 };
  }

  // 1. Create a task with empty notes — verify endpoint should flag it
  let taskId = null;
  try {
    const task = await api.post("/api/tasks", {
      project_id: ctx.projectId,
      title: "[SIM] Test verification — empty notes",
      description: "Task for testing self-verification",
      skill_name: "user-interviews",
    });
    taskId = task.id;
    checks.push({ name: "Create test task", passed: !!taskId, detail: `id=${taskId}` });
  } catch (e) {
    checks.push({ name: "Create test task", passed: false, detail: e.message });
  }

  // 2. Move to in_review with no notes
  if (taskId) {
    try {
      await api.post(`/api/tasks/${taskId}/move?status=in_review`);
      checks.push({ name: "Move to in_review", passed: true, detail: "" });
    } catch (e) {
      checks.push({ name: "Move to in_review", passed: false, detail: e.message });
    }
  }

  // 3. Call verify — should fail (empty notes)
  if (taskId) {
    try {
      const result = await api.post(`/api/tasks/${taskId}/verify`);
      checks.push({
        name: "Verify rejects empty notes",
        passed: result.verified === false,
        detail: `verified=${result.verified}, issues=${(result.issues || []).join("; ")}`,
      });
    } catch (e) {
      checks.push({ name: "Verify rejects empty notes", passed: false, detail: e.message });
    }
  }

  // 4. Add error notes and verify — should still fail
  if (taskId) {
    try {
      await api.patch(`/api/tasks/${taskId}`, {
        agent_notes: "Error: No files provided for analysis.",
        progress: 1.0,
      });
      const result = await api.post(`/api/tasks/${taskId}/verify`);
      checks.push({
        name: "Verify rejects error notes",
        passed: result.verified === false,
        detail: `verified=${result.verified}, issues=${(result.issues || []).join("; ")}`,
      });
    } catch (e) {
      checks.push({ name: "Verify rejects error notes", passed: false, detail: e.message });
    }
  }

  // 5. Add valid notes and verify — should pass and move to done
  if (taskId) {
    try {
      await api.patch(`/api/tasks/${taskId}`, {
        agent_notes: "[SIM] Analysis complete. Found 5 key themes: onboarding friction, search preference, mobile usage, export complexity, and organization overhead. Extracted 12 nuggets, 3 facts, and 2 insights.",
        progress: 1.0,
      });
      const result = await api.post(`/api/tasks/${taskId}/verify`);
      checks.push({
        name: "Verify accepts valid notes",
        passed: result.verified === true,
        detail: `verified=${result.verified}, status=${result.status}`,
      });
      checks.push({
        name: "Task moved to done after verify",
        passed: result.status === "done",
        detail: `status=${result.status}`,
      });
    } catch (e) {
      checks.push({ name: "Verify accepts valid notes", passed: false, detail: e.message });
    }
  }

  // 6. Create a task with incomplete progress — verify should flag it
  let task2Id = null;
  try {
    const task = await api.post("/api/tasks", {
      project_id: ctx.projectId,
      title: "[SIM] Test verification — incomplete progress",
      description: "Task for testing progress check",
    });
    task2Id = task.id;
    await api.post(`/api/tasks/${task2Id}/move?status=in_review`);
    await api.patch(`/api/tasks/${task2Id}`, {
      agent_notes: "Partial analysis done. Identified 2 themes so far but need more data.",
      progress: 0.5,
    });
    const result = await api.post(`/api/tasks/${task2Id}/verify`);
    checks.push({
      name: "Verify rejects incomplete progress",
      passed: result.verified === false,
      detail: `verified=${result.verified}, progress=0.5`,
    });
  } catch (e) {
    checks.push({ name: "Verify rejects incomplete progress", passed: false, detail: e.message });
  }

  // Cleanup
  for (const id of [taskId, task2Id]) {
    if (id) {
      try { await api.delete(`/api/tasks/${id}`); } catch {}
    }
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
