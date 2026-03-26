/** Scenario 49 — Loops & Schedule: integration tests for the loop overview
 *  dashboard, agent loop configuration, pause/resume, execution history,
 *  statistics, custom loops, and the cron scheduler CRUD endpoints.
 *
 *  Exercises: /api/loops/*, /api/schedules/*
 */

export const name = "Loops & Schedule";
export const id = "49-loops-schedule";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];
  const cleanup = { scheduleIds: [], customLoopIds: [] };

  // ── Helper: ensure we have a project ──
  let projectId = ctx.projectId;
  if (!projectId) {
    try {
      const created = await api.post("/api/projects", {
        name: "[SIM-49] Loops & Schedule Test Project",
        description: "Temporary project for Loops & Schedule integration tests",
      });
      projectId = created.id;
    } catch {
      try {
        const projects = await api.get("/api/projects");
        const list = projects.projects || projects || [];
        if (list.length > 0) projectId = list[0].id;
      } catch {}
    }
  }

  // ── 1. GET /api/loops/overview — returns overview data ──
  let overviewAgents = [];
  try {
    const overview = await api.get("/api/loops/overview");
    const hasAgents = Array.isArray(overview.agents);
    const hasHealthSummary = overview.health_summary && typeof overview.health_summary === "object";
    checks.push({
      name: "GET /api/loops/overview returns 200 with agents and health_summary",
      passed: hasAgents && hasHealthSummary,
      detail: `agents=${overview.agents?.length}, health_summary_keys=${Object.keys(overview.health_summary || {}).join(",")}`,
    });
    checks.push({
      name: "Overview health_summary has expected status counters",
      passed: overview.health_summary?.total !== undefined && overview.health_summary?.active !== undefined,
      detail: `total=${overview.health_summary?.total}, active=${overview.health_summary?.active}`,
    });
    overviewAgents = overview.agents || [];
  } catch (e) {
    checks.push({ name: "GET /api/loops/overview returns 200 with agents and health_summary", passed: false, detail: e.message });
  }

  // ── 2. GET /api/loops/agents — lists all agents with configs ──
  let agentList = [];
  try {
    const result = await api.get("/api/loops/agents");
    agentList = result.agents || [];
    const isArray = Array.isArray(agentList);
    const hasLoopFields = agentList.length === 0 || (
      agentList[0].agent_id !== undefined || agentList[0].id !== undefined
    );
    checks.push({
      name: "GET /api/loops/agents returns array with loop config fields",
      passed: isArray && hasLoopFields,
      detail: `count=${agentList.length}, sample_keys=${agentList.length > 0 ? Object.keys(agentList[0]).slice(0, 6).join(",") : "empty"}`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/loops/agents returns array with loop config fields", passed: false, detail: e.message });
  }

  // ── 3. GET /api/loops/health — returns health items ──
  try {
    const health = await api.get("/api/loops/health");
    const items = health.health || [];
    const isArray = Array.isArray(items);
    const hasRequiredFields = items.length === 0 || (
      items[0].source_type !== undefined &&
      items[0].source_id !== undefined &&
      items[0].status !== undefined
    );
    checks.push({
      name: "GET /api/loops/health returns array with source_type, source_id, status",
      passed: isArray && hasRequiredFields,
      detail: `count=${items.length}, statuses=${[...new Set(items.map(i => i.status))].join(",")}`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/loops/health returns array with source_type, source_id, status", passed: false, detail: e.message });
  }

  // ── 4. POST /api/schedules — create a test schedule ──
  let testScheduleId = null;
  if (projectId) {
    try {
      const schedule = await api.post("/api/schedules", {
        name: "[SIM-49] Test Schedule",
        cron_expression: "0 9 * * *",
        project_id: projectId,
        skill_name: "analyze-interview",
        description: "Simulation test schedule for scenario 49",
      });
      testScheduleId = schedule.id;
      cleanup.scheduleIds.push(testScheduleId);
      checks.push({
        name: "POST /api/schedules creates schedule with id and next_run",
        passed: !!schedule.id && !!schedule.next_run,
        detail: `id=${schedule.id}, next_run=${schedule.next_run}`,
      });
    } catch (e) {
      checks.push({ name: "POST /api/schedules creates schedule with id and next_run", passed: false, detail: e.message });
    }
  }

  // ── 5. GET /api/schedules — verify test schedule appears ──
  if (testScheduleId) {
    try {
      const schedules = await api.get("/api/schedules");
      const list = Array.isArray(schedules) ? schedules : schedules.schedules || [];
      const found = list.some((s) => s.id === testScheduleId);
      checks.push({
        name: "GET /api/schedules lists test schedule",
        passed: found,
        detail: `found=${found}, total=${list.length}`,
      });
    } catch (e) {
      checks.push({ name: "GET /api/schedules lists test schedule", passed: false, detail: e.message });
    }
  }

  // ── 6. PATCH /api/loops/agents/{id}/config — update interval ──
  // Use the first available agent from the agents list
  let testAgentId = null;
  let originalInterval = null;
  if (agentList.length > 0) {
    testAgentId = agentList[0].agent_id || agentList[0].id;
  }
  if (testAgentId) {
    try {
      // Save original config
      const original = await api.get(`/api/loops/agents/${testAgentId}/config`);
      originalInterval = original.loop_interval_seconds;

      const newInterval = (originalInterval || 60) + 10;
      const updated = await (async (url, body) => { const r = await fetch("http://localhost:8000" + url, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); if (!r.ok) throw new Error("PATCH " + url + ": " + r.status); return r.json(); })(`/api/loops/agents/${testAgentId}/config`, {
        loop_interval_seconds: newInterval,
      });
      checks.push({
        name: "PATCH /api/loops/agents/{id}/config updates interval",
        passed: updated.loop_interval_seconds === newInterval && updated.updated === true,
        detail: `old=${originalInterval}, new=${updated.loop_interval_seconds}`,
      });
    } catch (e) {
      checks.push({ name: "PATCH /api/loops/agents/{id}/config updates interval", passed: false, detail: e.message });
    }
  }

  // ── 7. POST /api/loops/agents/{id}/pause — pause agent ──
  if (testAgentId) {
    try {
      const result = await api.post(`/api/loops/agents/${testAgentId}/pause`, {});
      checks.push({
        name: "POST /api/loops/agents/{id}/pause returns paused status",
        passed: result.status === "paused" && result.agent_id === testAgentId,
        detail: `agent_id=${result.agent_id}, status=${result.status}`,
      });
    } catch (e) {
      checks.push({ name: "POST /api/loops/agents/{id}/pause returns paused status", passed: false, detail: e.message });
    }
  }

  // ── 8. POST /api/loops/agents/{id}/resume — resume agent ──
  if (testAgentId) {
    try {
      const result = await api.post(`/api/loops/agents/${testAgentId}/resume`, {});
      checks.push({
        name: "POST /api/loops/agents/{id}/resume returns resumed status",
        passed: result.status === "resumed" && result.agent_id === testAgentId,
        detail: `agent_id=${result.agent_id}, status=${result.status}`,
      });
    } catch (e) {
      checks.push({ name: "POST /api/loops/agents/{id}/resume returns resumed status", passed: false, detail: e.message });
    }
  }

  // ── 9. GET /api/loops/executions — execution history ──
  try {
    const result = await api.get("/api/loops/executions");
    const hasExecutions = Array.isArray(result.executions);
    const hasPagination = result.total !== undefined && result.page !== undefined;
    checks.push({
      name: "GET /api/loops/executions returns paginated data with executions array",
      passed: hasExecutions && hasPagination,
      detail: `total=${result.total}, page=${result.page}, count=${result.executions?.length}`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/loops/executions returns paginated data with executions array", passed: false, detail: e.message });
  }

  // ── 10. GET /api/loops/executions/stats — statistics ──
  try {
    const stats = await api.get("/api/loops/executions/stats");
    const hasExpectedFields =
      stats.total_agents !== undefined &&
      stats.total_agent_executions !== undefined &&
      stats.total_schedules !== undefined;
    checks.push({
      name: "GET /api/loops/executions/stats returns stats with expected fields",
      passed: hasExpectedFields,
      detail: `total_agents=${stats.total_agents}, total_executions=${stats.total_agent_executions}, total_schedules=${stats.total_schedules}`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/loops/executions/stats returns stats with expected fields", passed: false, detail: e.message });
  }

  // ── 11. POST /api/loops/custom — create custom loop ──
  if (projectId) {
    try {
      const custom = await api.post("/api/loops/custom", {
        name: "[SIM-49] Custom Loop",
        skill_name: "analyze-interview",
        project_id: projectId,
        interval_seconds: 300,
        description: "Custom loop created by simulation scenario 49",
      });
      cleanup.customLoopIds.push(custom.id);
      checks.push({
        name: "POST /api/loops/custom creates task with cron_expression and next_run",
        passed: !!custom.id && !!custom.cron_expression && !!custom.next_run,
        detail: `id=${custom.id}, cron=${custom.cron_expression}, next_run=${custom.next_run}`,
      });
    } catch (e) {
      checks.push({ name: "POST /api/loops/custom creates task with cron_expression and next_run", passed: false, detail: e.message });
    }
  }

  // ── 12. GET /api/loops/agents/{id}/config — get specific agent config ──
  if (testAgentId) {
    try {
      const config = await api.get(`/api/loops/agents/${testAgentId}/config`);
      checks.push({
        name: "GET /api/loops/agents/{id}/config returns config with matching agent_id",
        passed: config.agent_id === testAgentId && config.name !== undefined,
        detail: `agent_id=${config.agent_id}, name=${config.name}, interval=${config.loop_interval_seconds}`,
      });
    } catch (e) {
      checks.push({ name: "GET /api/loops/agents/{id}/config returns config with matching agent_id", passed: false, detail: e.message });
    }
  }

  // ── 13. DELETE schedule — cleanup test schedule ──
  if (testScheduleId) {
    try {
      const res = await fetch(`http://localhost:8000/api/schedules/${testScheduleId}`, {
        method: "DELETE",
      });
      checks.push({
        name: "DELETE /api/schedules/{id} returns 204",
        passed: res.status === 204,
        detail: `status=${res.status}`,
      });
      // Verify it's gone
      try {
        await api.get(`/api/schedules/${testScheduleId}`);
        checks.push({
          name: "Deleted schedule no longer retrievable",
          passed: false,
          detail: "GET succeeded when it should have 404'd",
        });
      } catch {
        checks.push({
          name: "Deleted schedule no longer retrievable",
          passed: true,
          detail: "GET returned expected 404",
        });
      }
      cleanup.scheduleIds = cleanup.scheduleIds.filter((id) => id !== testScheduleId);
    } catch (e) {
      checks.push({ name: "DELETE /api/schedules/{id} returns 204", passed: false, detail: e.message });
    }
  }

  // ── 14. PATCH config — restore original interval ──
  if (testAgentId && originalInterval !== null) {
    try {
      const restored = await (async (url, body) => { const r = await fetch("http://localhost:8000" + url, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); if (!r.ok) throw new Error("PATCH " + url + ": " + r.status); return r.json(); })(`/api/loops/agents/${testAgentId}/config`, {
        loop_interval_seconds: originalInterval,
      });
      checks.push({
        name: "PATCH restore original interval succeeds",
        passed: restored.loop_interval_seconds === originalInterval,
        detail: `restored_interval=${restored.loop_interval_seconds}`,
      });
    } catch (e) {
      checks.push({ name: "PATCH restore original interval succeeds", passed: false, detail: e.message });
    }
  }

  // ── Cleanup ──
  for (const id of cleanup.scheduleIds) {
    try { await fetch(`http://localhost:8000/api/schedules/${id}`, { method: "DELETE" }); } catch {}
  }
  for (const id of cleanup.customLoopIds) {
    try { await fetch(`http://localhost:8000/api/schedules/${id}`, { method: "DELETE" }); } catch {}
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
