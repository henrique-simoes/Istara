/** Scenario 33 — Task Locking: verify lock/unlock mechanics. */

export const name = "Task Locking";
export const id = "33-task-locking";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // Use persistent simulation project
  let projectId = ctx.projectId;
  if (!projectId) {
    checks.push({ name: "Project available", passed: false, detail: "No persistent project from runner" });
    return { checks, passed: 0, failed: 1 };
  }

  // 1. Create a test task
  let taskId;
  try {
    const task = await api.post("/api/tasks", {
      project_id: projectId,
      title: "Lock Test Task",
      description: "Testing lock mechanics",
    });
    taskId = task.id;
    checks.push({
      name: "Create test task",
      passed: !!taskId,
      detail: `task_id=${taskId}`,
    });
  } catch (e) {
    checks.push({ name: "Create test task", passed: false, detail: e.message });
    return { checks, passed: 0, failed: 1 };
  }

  // 2. Lock the task
  try {
    const lock = await api.post(`/api/tasks/${taskId}/lock?user_id=test-user`, {});
    checks.push({
      name: "Lock task",
      passed: !!lock.locked_by && lock.locked_by === "test-user",
      detail: `locked_by=${lock.locked_by}`,
    });
  } catch (e) {
    checks.push({ name: "Lock task", passed: false, detail: e.message });
  }

  // 3. Verify lock is visible in task data
  try {
    const task = await api.get(`/api/tasks/${taskId}`);
    checks.push({
      name: "Task shows lock info",
      passed: task.locked_by === "test-user",
      detail: `locked_by=${task.locked_by}, lock_expires_at=${task.lock_expires_at}`,
    });
  } catch (e) {
    checks.push({ name: "Task shows lock info", passed: false, detail: e.message });
  }

  // 4. Try locking from different user (should fail with 409)
  try {
    await api.post(`/api/tasks/${taskId}/lock?user_id=other-user`, {});
    checks.push({ name: "Lock conflict detection", passed: false, detail: "Should have rejected" });
  } catch (e) {
    checks.push({
      name: "Lock conflict detection",
      passed: e.message.includes("locked") || e.message.includes("409"),
      detail: e.message,
    });
  }

  // 5. Unlock the task
  try {
    const unlock = await api.post(`/api/tasks/${taskId}/unlock?user_id=test-user`, {});
    checks.push({
      name: "Unlock task",
      passed: unlock.unlocked === true,
      detail: JSON.stringify(unlock),
    });
  } catch (e) {
    checks.push({ name: "Unlock task", passed: false, detail: e.message });
  }

  // 6. Verify task is unlocked
  try {
    const task = await api.get(`/api/tasks/${taskId}`);
    checks.push({
      name: "Task unlocked successfully",
      passed: task.locked_by === null || task.locked_by === undefined,
      detail: `locked_by=${task.locked_by}`,
    });
  } catch (e) {
    checks.push({ name: "Task unlocked successfully", passed: false, detail: e.message });
  }

  // Cleanup
  try { await api.delete(`/api/tasks/${taskId}`); } catch {}

  const passed = checks.filter((c) => c.passed).length;
  const failed = checks.filter((c) => !c.passed).length;
  return { checks, passed, failed };
}
