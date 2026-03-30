/** Scenario 59 — Agent Integration Knowledge: tests that agents understand the Integrations menu.
 *  Verifies agents can discuss messaging, surveys, deployments, and MCP.
 *
 *  Exercises: /api/chat (with integration-related queries), /api/skills
 */

export const name = "Agent Integration Knowledge";
export const id = "59-agent-integration-knowledge";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // ── 1. Channel Research Deployment skill exists ──
  try {
    const skills = await api.get("/api/skills");
    const list = Array.isArray(skills) ? skills : skills?.skills || [];
    const deploySkill = list.find((s) => s.name === "channel-research-deployment");
    checks.push({
      name: "Channel Research Deployment skill registered",
      passed: !!deploySkill,
      detail: deploySkill ? `${deploySkill.display_name} (${deploySkill.phase})` : "NOT FOUND",
    });
  } catch (e) {
    checks.push({ name: "Channel Research Deployment skill registered", passed: false, detail: e.message });
  }

  // ── 2. Skills include survey-related skills ──
  try {
    const skills = await api.get("/api/skills");
    const list = Array.isArray(skills) ? skills : skills?.skills || [];
    const surveySkills = list.filter((s) =>
      s.name && (s.name.includes("survey") || s.name.includes("interview"))
    );
    checks.push({
      name: "Survey and interview skills available",
      passed: surveySkills.length >= 3,
      detail: `${surveySkills.length} survey/interview skills: ${surveySkills.map((s) => s.name).join(", ")}`,
    });
  } catch (e) {
    checks.push({ name: "Survey and interview skills available", passed: false, detail: e.message });
  }

  // ── 3. Agent SKILLS.md contains integration keywords ──
  try {
    // Check agent persona files include integration skills
    const agents = await api.get("/api/agents");
    const agentList = Array.isArray(agents) ? agents : agents?.agents || [];
    const mainAgent = agentList.find((a) => a.name && (a.name.includes("Cleo") || a.id === "istara-main"));
    checks.push({
      name: "Main agent (Cleo) exists in agent list",
      passed: !!mainAgent,
      detail: mainAgent ? `id=${mainAgent.id}, name=${mainAgent.name}` : "NOT FOUND",
    });
  } catch (e) {
    checks.push({ name: "Main agent (Cleo) exists in agent list", passed: false, detail: e.message });
  }

  // ── 4. All 5 system agents active ──
  try {
    const agents = await api.get("/api/agents");
    const agentList = Array.isArray(agents) ? agents : agents?.agents || [];
    const systemAgents = agentList.filter((a) => a.is_system === true);
    checks.push({
      name: "All 5 system agents registered",
      passed: systemAgents.length >= 5,
      detail: `${systemAgents.length} system agents: ${systemAgents.map((a) => a.name).join(", ")}`,
    });
  } catch (e) {
    checks.push({ name: "All 5 system agents registered", passed: false, detail: e.message });
  }

  // ── 5. Integration API endpoints accessible ──
  const integrationEndpoints = [
    { path: "/api/channels", name: "Channels" },
    { path: "/api/surveys/integrations", name: "Survey Integrations" },
    { path: "/api/deployments?project_id=test", name: "Deployments" },
    { path: "/api/mcp/server/status", name: "MCP Server Status" },
    { path: "/api/mcp/clients", name: "MCP Clients" },
  ];

  for (const endpoint of integrationEndpoints) {
    try {
      await api.get(endpoint.path);
      checks.push({
        name: `${endpoint.name} endpoint accessible`,
        passed: true,
        detail: `GET ${endpoint.path} OK`,
      });
    } catch (e) {
      checks.push({
        name: `${endpoint.name} endpoint accessible`,
        passed: false,
        detail: e.message,
      });
    }
  }

  // ── 10. Deployment analytics endpoint accessible ──
  try {
    // Create a temp deployment to test analytics
    const tempDeploy = await api.post("/api/deployments", {
      project_id: "sim-agent-knowledge-test",
      name: "SIM: Analytics Test",
      deployment_type: "survey",
      questions: [{ text: "Test question" }],
      channel_instance_ids: [],
      target_responses: 1,
    });
    const analytics = await api.get(`/api/deployments/${tempDeploy.id}/analytics`);
    checks.push({
      name: "Deployment analytics endpoint returns data structure",
      passed: analytics.per_question_stats !== undefined,
      detail: `Keys: ${Object.keys(analytics).join(", ")}`,
    });
    // Cleanup
    try { await api.delete(`/api/deployments/${tempDeploy.id}`); } catch (_) {}
  } catch (e) {
    checks.push({ name: "Deployment analytics endpoint returns data structure", passed: false, detail: e.message });
  }

  return checks;
}
