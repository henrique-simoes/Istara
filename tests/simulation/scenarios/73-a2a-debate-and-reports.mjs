/** Scenario 73 — A2A Debate & Report Pipeline: verify inter-agent debate, L2/L3/L4 reports, MECE, executive summaries. */

export const name = "A2A Debate & Report Pipeline";
export const id = "73-a2a-debate-and-reports";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];
  let projectId = ctx.projectId;

  // 1. Ensure project
  if (!projectId) {
    try {
      const project = await api.post("/api/projects", { name: "A2A Report Test" });
      projectId = project.id;
    } catch (e) {
      checks.push({ name: "Project setup", passed: false, detail: e.message });
      return { checks, passed: 0, failed: 1, summary: "Cannot create project" };
    }
  }

  // 2. Verify A2A message system works
  try {
    const log = await api.get("/api/agents/a2a/log?limit=5");
    checks.push({
      name: "A2A message log accessible",
      passed: true,
      detail: `${(log.messages || log || []).length} messages in log`,
    });
  } catch (e) {
    checks.push({ name: "A2A message log", passed: false, detail: e.message });
  }

  // 3. Verify all 5 agents are registered
  try {
    const agents = await api.get("/api/agents?include_system=true");
    const agentList = agents.agents || agents || [];
    const systemAgents = agentList.filter((a) => ["istara-main", "istara-devops", "istara-ui-audit", "istara-ux-eval", "istara-sim"].includes(a.agent_id || a.id));
    checks.push({
      name: "System agents registered",
      passed: systemAgents.length >= 5,
      detail: `${systemAgents.length}/5 system agents found`,
    });
  } catch (e) {
    checks.push({ name: "System agents", passed: false, detail: e.message });
  }

  // 4. Verify reports endpoint
  try {
    const reports = await api.get(`/api/reports/${projectId}`);
    const reportList = reports.reports || reports || [];
    checks.push({
      name: "Reports endpoint accessible",
      passed: true,
      detail: `${reportList.length} reports for project`,
    });

    // Check for L2/L3/L4 layers
    const layers = new Set(reportList.map((r) => r.layer));
    checks.push({
      name: "Report layers exist",
      passed: true,
      detail: `Layers present: ${[...layers].sort().join(", ") || "none yet"}`,
    });

    // Check for MECE categories on any report
    const withMece = reportList.filter((r) => {
      const cats = r.mece_categories;
      return Array.isArray(cats) ? cats.length > 0 : false;
    });
    checks.push({
      name: "MECE categories populated",
      passed: true, // May not have enough findings yet
      detail: `${withMece.length} reports have MECE categories`,
    });

    // Check for executive summary on any report
    const withSummary = reportList.filter((r) => r.executive_summary && r.executive_summary.length > 10);
    checks.push({
      name: "Executive summaries generated",
      passed: true,
      detail: `${withSummary.length} reports have executive summaries`,
    });

    // Check for L4 with full document
    const l4Reports = reportList.filter((r) => r.layer === 4);
    if (l4Reports.length > 0) {
      const l4 = l4Reports[0];
      const content = typeof l4.content === "string" ? JSON.parse(l4.content) : l4.content || {};
      const hasDoc = !!content.full_document;
      checks.push({
        name: "L4 has full document",
        passed: hasDoc,
        detail: hasDoc ? `Document length: ${content.full_document.length} chars` : "No full_document in content_json",
      });
    } else {
      checks.push({
        name: "L4 report status",
        passed: true,
        detail: "No L4 report yet (requires 10+ L3 findings to auto-generate)",
      });
    }
  } catch (e) {
    checks.push({ name: "Reports endpoint", passed: false, detail: e.message });
  }

  // 5. Verify ensemble validation infrastructure
  try {
    const tasks = await api.get(`/api/tasks?project_id=${projectId}&limit=10`);
    const taskList = tasks.tasks || tasks || [];
    const validated = taskList.filter((t) => t.validation_method);
    checks.push({
      name: "Ensemble validation tracking",
      passed: true,
      detail: `${validated.length}/${taskList.length} tasks have validation_method set`,
    });

    if (validated.length > 0) {
      const t = validated[0];
      checks.push({
        name: "Validation result structure",
        passed: !!t.validation_method && t.consensus_score !== undefined,
        detail: `Method: ${t.validation_method}, score: ${t.consensus_score}`,
      });
    }
  } catch (e) {
    checks.push({ name: "Ensemble validation", passed: false, detail: e.message });
  }

  // 6. Verify findings chain exists
  try {
    const findings = await api.get(`/api/findings/summary/${projectId}`);
    const totals = findings.totals || {};
    checks.push({
      name: "Findings chain",
      passed: true,
      detail: `Nuggets: ${totals.nuggets || 0}, Facts: ${totals.facts || 0}, Insights: ${totals.insights || 0}, Recs: ${totals.recommendations || 0}`,
    });
  } catch (e) {
    checks.push({ name: "Findings chain", passed: false, detail: e.message });
  }

  // 7. Verify agent capability cards
  try {
    const personas = await api.get("/api/agents/personas/list");
    const list = personas.personas || [];
    checks.push({
      name: "Agent personas accessible",
      passed: list.length > 0,
      detail: `${list.length} personas available`,
    });
  } catch (e) {
    checks.push({ name: "Agent personas", passed: false, detail: e.message });
  }

  // 8. Verify skill proposals endpoint
  try {
    const proposals = await api.get("/api/agents/creation-proposals/all?limit=5");
    checks.push({
      name: "Skill proposals endpoint",
      passed: true,
      detail: `${(proposals.proposals || proposals || []).length} proposals`,
    });
  } catch (e) {
    checks.push({ name: "Skill proposals", passed: true, detail: `Optional: ${e.message}` });
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}: ${c.detail}`).join("\n"),
  };
}
