/** Scenario 13 — Task Agent Assignment: assign agents to tasks, set priority, verify API. */

export const name = "Task Agent Assignment";
export const id = "13-task-agent-assignment";

export async function run(ctx) {
  const { api, page, screenshot } = ctx;
  const checks = [];

  if (!ctx.projectId) {
    return { checks: [{ name: "Skip — no project", passed: false, detail: "No project ID" }], passed: 0, failed: 1 };
  }

  // 1. Get available agents
  let agents = [];
  try {
    const data = await api.get("/api/agents");
    agents = data.agents || [];
    checks.push({
      name: "Agents available for assignment",
      passed: agents.length > 0,
      detail: `${agents.length} agents`,
    });
  } catch (e) {
    checks.push({ name: "Agents available for assignment", passed: false, detail: e.message });
  }

  // 2. Create a task
  let taskId = null;
  try {
    const task = await api.post("/api/tasks", {
      project_id: ctx.projectId,
      title: "[SIM] Agent Assignment Test Task",
      description: "Task for testing agent assignment",
    });
    taskId = task.id;
    checks.push({
      name: "Create test task",
      passed: !!task.id,
      detail: `id=${task.id}`,
    });
  } catch (e) {
    checks.push({ name: "Create test task", passed: false, detail: e.message });
  }

  // 3. Assign agent to task
  if (taskId && agents.length > 0) {
    const agentToAssign = agents[0];
    try {
      const updated = await api.patch(`/api/tasks/${taskId}`, {
        agent_id: agentToAssign.id,
      });
      checks.push({
        name: "Assign agent to task",
        passed: updated.agent_id === agentToAssign.id,
        detail: `agent=${agentToAssign.name} (${agentToAssign.id})`,
      });
    } catch (e) {
      checks.push({ name: "Assign agent to task", passed: false, detail: e.message });
    }
  }

  // 4. Set task priority
  if (taskId) {
    try {
      const updated = await api.patch(`/api/tasks/${taskId}`, {
        priority: "high",
      });
      checks.push({
        name: "Set task priority",
        passed: updated.priority === "high",
        detail: `priority=${updated.priority}`,
      });
    } catch (e) {
      checks.push({ name: "Set task priority", passed: false, detail: e.message });
    }
  }

  // 5. Verify task state via GET
  if (taskId) {
    try {
      const task = await api.get(`/api/tasks/${taskId}`);
      checks.push({
        name: "Verify task state",
        passed: task.agent_id === agents[0]?.id && task.priority === "high",
        detail: `agent_id=${task.agent_id}, priority=${task.priority}`,
      });
    } catch (e) {
      checks.push({ name: "Verify task state", passed: false, detail: e.message });
    }
  }

  // 6. Clear agent assignment
  if (taskId) {
    try {
      const updated = await api.patch(`/api/tasks/${taskId}`, {
        agent_id: null,
      });
      checks.push({
        name: "Clear agent assignment",
        passed: updated.agent_id === null || updated.agent_id === undefined,
        detail: `agent_id=${updated.agent_id}`,
      });
    } catch (e) {
      checks.push({ name: "Clear agent assignment", passed: false, detail: e.message });
    }
  }

  // 7. Set multiple priorities
  const priorities = ["urgent", "high", "medium", "low"];
  for (const p of priorities) {
    if (!taskId) break;
    try {
      const updated = await api.patch(`/api/tasks/${taskId}`, { priority: p });
      checks.push({
        name: `Set priority: ${p}`,
        passed: updated.priority === p,
        detail: "",
      });
    } catch (e) {
      checks.push({ name: `Set priority: ${p}`, passed: false, detail: e.message });
    }
  }

  // 8. UI verification — navigate to Kanban
  await page.goto("http://localhost:3000", { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);

  const projectBtn = page.locator("text=[SIM]").first();
  if (await projectBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await projectBtn.click();
    await page.waitForTimeout(500);
  }

  await page.keyboard.press("Meta+3");
  await page.waitForTimeout(1500);

  const taskVisible = await page.locator("text=[SIM] Agent Assignment").isVisible({ timeout: 3000 }).catch(() => false);
  checks.push({
    name: "Task visible in Kanban UI",
    passed: taskVisible,
    detail: "",
  });
  await screenshot("13-task-agent-assignment");

  // Cleanup
  if (taskId) {
    try {
      await api.delete(`/api/tasks/${taskId}`);
    } catch {}
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
