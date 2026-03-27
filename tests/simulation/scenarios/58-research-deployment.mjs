/** Scenario 58 — Research Deployment: tests for deploying interviews/surveys via messaging.
 *
 *  Exercises: /api/deployments/*
 */

export const name = "Research Deployment";
export const id = "58-research-deployment";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];
  const cleanup = { deploymentIds: [], channelIds: [] };

  // ── 1. Create a channel instance for deployment ──
  let channel = null;
  try {
    channel = await api.post("/api/channels", {
      platform: "telegram",
      name: "SIM: Deployment Channel",
      config: { bot_token: "sim-deploy-bot-token" },
    });
    cleanup.channelIds.push(channel.id);
    checks.push({
      name: "Create channel for deployment",
      passed: !!channel.id,
      detail: `channel_id=${channel.id}`,
    });
  } catch (e) {
    checks.push({ name: "Create channel for deployment", passed: false, detail: e.message });
  }

  // ── 2. POST /api/deployments — create interview deployment ──
  let deployment = null;
  try {
    deployment = await api.post("/api/deployments", {
      project_id: "sim-project-001",
      name: "SIM: User Interview Study",
      deployment_type: "interview",
      questions: [
        { text: "How do you currently manage your tasks?" },
        { text: "What frustrates you about your current workflow?" },
        { text: "What would an ideal solution look like?" },
      ],
      channel_instance_ids: channel ? [channel.id] : [],
      config: {
        adaptive: true,
        max_followups: 2,
        research_goals: "Understand task management pain points",
        intro_message: "Hi! We're conducting a brief interview about task management.",
        thank_you_message: "Thank you for your valuable insights!",
      },
      target_responses: 5,
    });
    cleanup.deploymentIds.push(deployment.id);
    checks.push({
      name: "POST /api/deployments creates interview",
      passed: !!deployment.id && deployment.deployment_type === "interview" && deployment.state === "draft",
      detail: `id=${deployment.id}, state=${deployment.state}`,
    });
  } catch (e) {
    checks.push({ name: "POST /api/deployments creates interview", passed: false, detail: e.message });
  }

  // ── 3. GET /api/deployments — list ──
  try {
    const result = await api.get("/api/deployments?project_id=sim-project-001");
    const list = Array.isArray(result) ? result : result?.deployments || [];
    checks.push({
      name: "GET /api/deployments returns project deployments",
      passed: list.length >= 1,
      detail: `${list.length} deployments`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/deployments returns project deployments", passed: false, detail: e.message });
  }

  // ── 4. GET /api/deployments/{id} — detail ──
  if (deployment) {
    try {
      const detail = await api.get(`/api/deployments/${deployment.id}`);
      const hasQuestions = detail.questions && detail.questions.length === 3;
      checks.push({
        name: "GET /api/deployments/{id} returns full detail",
        passed: detail.id === deployment.id && hasQuestions,
        detail: `questions=${detail.questions?.length}, channels=${detail.channel_instance_ids?.length}`,
      });
    } catch (e) {
      checks.push({ name: "GET /api/deployments/{id} returns full detail", passed: false, detail: e.message });
    }
  }

  // ── 5. POST /api/deployments/{id}/activate — activate ──
  if (deployment) {
    try {
      const result = await api.post(`/api/deployments/${deployment.id}/activate`, {});
      checks.push({
        name: "POST /api/deployments/{id}/activate starts deployment",
        passed: result.status === "activated" || result.status === "active",
        detail: `status=${result.status}`,
      });
    } catch (e) {
      checks.push({ name: "POST /api/deployments/{id}/activate starts deployment", passed: false, detail: e.message });
    }
  }

  // ── 6. Verify state changed to active ──
  if (deployment) {
    try {
      const detail = await api.get(`/api/deployments/${deployment.id}`);
      checks.push({
        name: "Deployment state is active after activation",
        passed: detail.state === "active",
        detail: `state=${detail.state}`,
      });
    } catch (e) {
      checks.push({ name: "Deployment state is active after activation", passed: false, detail: e.message });
    }
  }

  // ── 7. POST /api/deployments/{id}/pause — pause ──
  if (deployment) {
    try {
      const result = await api.post(`/api/deployments/${deployment.id}/pause`, {});
      checks.push({
        name: "POST /api/deployments/{id}/pause pauses deployment",
        passed: result.status === "paused",
        detail: `status=${result.status}`,
      });
    } catch (e) {
      checks.push({ name: "POST /api/deployments/{id}/pause pauses deployment", passed: false, detail: e.message });
    }
  }

  // ── 8. POST /api/deployments/{id}/complete — complete ──
  if (deployment) {
    try {
      const result = await api.post(`/api/deployments/${deployment.id}/complete`, {});
      checks.push({
        name: "POST /api/deployments/{id}/complete ends deployment",
        passed: result.status === "completed",
        detail: `status=${result.status}`,
      });
    } catch (e) {
      checks.push({ name: "POST /api/deployments/{id}/complete ends deployment", passed: false, detail: e.message });
    }
  }

  // ── 9. GET /api/deployments/{id}/analytics — analytics data ──
  if (deployment) {
    try {
      const analytics = await api.get(`/api/deployments/${deployment.id}/analytics`);
      checks.push({
        name: "GET /api/deployments/{id}/analytics returns analytics",
        passed: analytics.deployment_id === deployment.id && analytics.per_question_stats !== undefined,
        detail: `response_rate=${analytics.response_rate}%, questions=${analytics.per_question_stats?.length}`,
      });
    } catch (e) {
      checks.push({ name: "GET /api/deployments/{id}/analytics returns analytics", passed: false, detail: e.message });
    }
  }

  // ── 10. GET /api/deployments/{id}/conversations — empty initially ──
  if (deployment) {
    try {
      const convos = await api.get(`/api/deployments/${deployment.id}/conversations`);
      const list = Array.isArray(convos) ? convos : convos?.conversations || [];
      checks.push({
        name: "GET /api/deployments/{id}/conversations returns array",
        passed: Array.isArray(list),
        detail: `${list.length} conversations`,
      });
    } catch (e) {
      checks.push({ name: "GET /api/deployments/{id}/conversations returns array", passed: false, detail: e.message });
    }
  }

  // ── 11. GET /api/deployments/overview — cross-deployment summary ──
  try {
    const overview = await api.get("/api/deployments/overview?project_id=sim-project-001");
    checks.push({
      name: "GET /api/deployments/overview returns summary",
      passed: overview.total_deployments !== undefined || overview.active_deployments !== undefined,
      detail: `total=${overview.total_deployments}, active=${overview.active_deployments?.length}`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/deployments/overview returns summary", passed: false, detail: e.message });
  }

  // ── 12. Create survey deployment ──
  let surveyDeployment = null;
  try {
    surveyDeployment = await api.post("/api/deployments", {
      project_id: "sim-project-001",
      name: "SIM: Quick Survey",
      deployment_type: "survey",
      questions: [
        { text: "Rate your experience (1-5)" },
        { text: "Would you recommend this to a friend?" },
      ],
      channel_instance_ids: channel ? [channel.id] : [],
      target_responses: 10,
    });
    cleanup.deploymentIds.push(surveyDeployment.id);
    checks.push({
      name: "Survey deployment type supported",
      passed: !!surveyDeployment.id && surveyDeployment.deployment_type === "survey",
      detail: `id=${surveyDeployment.id}`,
    });
  } catch (e) {
    checks.push({ name: "Survey deployment type supported", passed: false, detail: e.message });
  }

  // ── 13. Create diary study deployment ──
  let diaryDeployment = null;
  try {
    diaryDeployment = await api.post("/api/deployments", {
      project_id: "sim-project-001",
      name: "SIM: Week-long Diary",
      deployment_type: "diary_study",
      questions: [
        { text: "What tasks did you complete today?" },
        { text: "What was the most challenging moment?" },
      ],
      channel_instance_ids: channel ? [channel.id] : [],
      target_responses: 7,
    });
    cleanup.deploymentIds.push(diaryDeployment.id);
    checks.push({
      name: "Diary study deployment type supported",
      passed: !!diaryDeployment.id && diaryDeployment.deployment_type === "diary_study",
      detail: `id=${diaryDeployment.id}`,
    });
  } catch (e) {
    checks.push({ name: "Diary study deployment type supported", passed: false, detail: e.message });
  }

  // ── 14. All 3 deployment types in project ──
  try {
    const result = await api.get("/api/deployments?project_id=sim-project-001");
    const list = Array.isArray(result) ? result : result?.deployments || [];
    const types = new Set(list.map((d) => d.deployment_type));
    checks.push({
      name: "All 3 deployment types coexist",
      passed: types.has("interview") && types.has("survey") && types.has("diary_study"),
      detail: `Types: ${[...types].join(", ")}`,
    });
  } catch (e) {
    checks.push({ name: "All 3 deployment types coexist", passed: false, detail: e.message });
  }

  // ── 15. Adaptive config persisted ──
  if (deployment) {
    try {
      const detail = await api.get(`/api/deployments/${deployment.id}`);
      const config = detail.config || {};
      checks.push({
        name: "Adaptive config persisted correctly",
        passed: config.adaptive === true && config.max_followups === 2,
        detail: `adaptive=${config.adaptive}, max_followups=${config.max_followups}`,
      });
    } catch (e) {
      checks.push({ name: "Adaptive config persisted correctly", passed: false, detail: e.message });
    }
  }

  // ── Cleanup ──
  for (const id of cleanup.deploymentIds) {
    try { await api.delete(`/api/deployments/${id}`); } catch (_) {}
  }
  for (const id of cleanup.channelIds) {
    try { await api.delete(`/api/channels/${id}`); } catch (_) {}
  }

  return checks;
}
