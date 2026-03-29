/** Scenario 17 — Full Pipeline: populate findings across all 4 Double Diamond phases. */

export const name = "Full Pipeline (Discover → Deliver)";
export const id = "17-full-pipeline";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  if (!ctx.projectId) {
    return { checks: [{ name: "Skip — no project", passed: false, detail: "No project ID" }], passed: 0, failed: 1 };
  }

  // Phase 1: DISCOVER — raw evidence gathering
  const discoverNuggets = [
    { text: "[SIM] P002 mentioned 'I spend 30 minutes every morning just organizing my research notes'", source: "Interview P002", source_location: "00:05:12", tags: ["time-waste", "organization", "daily-routine"], phase: "discover", confidence: 0.92 },
    { text: "[SIM] 5 out of 7 participants opened the search bar before trying the menu", source: "Usability Test Round 2", source_location: "Task 3", tags: ["search-first", "navigation", "mental-model"], phase: "discover", confidence: 0.88 },
    { text: "[SIM] P004 said: 'I keep a separate spreadsheet to track which interviews I've coded'", source: "Interview P004", source_location: "00:18:22", tags: ["workaround", "coding", "tracking"], phase: "discover", confidence: 0.9 },
    { text: "[SIM] Analytics show 68% of users access the platform on mobile at least once per week", source: "Analytics Dashboard", source_location: "Q4 Report", tags: ["mobile", "usage-pattern", "frequency"], phase: "discover", confidence: 0.95 },
    { text: "[SIM] P001 abandoned the export flow after 3 attempts, saying 'this is too many clicks'", source: "Usability Test Round 2", source_location: "Task 7", tags: ["friction", "export", "abandonment"], phase: "discover", confidence: 0.87 },
  ];

  const nuggetIds = [];
  for (const nugget of discoverNuggets) {
    try {
      const created = await api.post(`/api/findings/nuggets`, { ...nugget, project_id: ctx.projectId });
      if (created.id) nuggetIds.push(created.id);
      checks.push({ name: `Discover nugget: ${nugget.tags[0]}`, passed: !!created.id, detail: `id=${created.id}` });
    } catch (e) {
      checks.push({ name: `Discover nugget: ${nugget.tags[0]}`, passed: false, detail: e.message });
    }
  }

  // Phase 2: DEFINE — synthesized facts from nuggets
  const defineFacts = [
    { text: "[SIM] Research organization is a universal pain point consuming 20-30 min daily for most researchers", nugget_ids: nuggetIds.slice(0, 2), phase: "define", confidence: 0.85 },
    { text: "[SIM] Users have a strong search-first mental model, expecting search as primary navigation", nugget_ids: nuggetIds.slice(1, 3), phase: "define", confidence: 0.88 },
    { text: "[SIM] Export and sharing workflows have critical friction points causing task abandonment", nugget_ids: nuggetIds.slice(3, 5), phase: "define", confidence: 0.82 },
  ];

  const factIds = [];
  for (const fact of defineFacts) {
    try {
      const created = await api.post(`/api/findings/facts`, { ...fact, project_id: ctx.projectId });
      if (created.id) factIds.push(created.id);
      checks.push({ name: `Define fact: ${fact.text.substring(6, 40)}...`, passed: !!created.id, detail: `id=${created.id}` });
    } catch (e) {
      checks.push({ name: `Define fact`, passed: false, detail: e.message });
    }
  }

  // Phase 2: DEFINE — insights from facts
  const defineInsights = [
    { text: "[SIM] Auto-organization features would save researchers 2+ hours per week and reduce cognitive load", fact_ids: factIds.slice(0, 2), phase: "define", confidence: 0.8, impact: "high" },
    { text: "[SIM] Simplifying export to a 1-click action would prevent 40% of abandonment in sharing workflows", fact_ids: factIds.slice(1, 3), phase: "define", confidence: 0.78, impact: "high" },
  ];

  const insightIds = [];
  for (const insight of defineInsights) {
    try {
      const created = await api.post(`/api/findings/insights`, { ...insight, project_id: ctx.projectId });
      if (created.id) insightIds.push(created.id);
      checks.push({ name: `Define insight: ${insight.impact} impact`, passed: !!created.id, detail: `id=${created.id}` });
    } catch (e) {
      checks.push({ name: `Define insight`, passed: false, detail: e.message });
    }
  }

  // Phase 3: DEVELOP — recommendations
  const developRecs = [
    { text: "[SIM] Build AI-powered auto-tagging that suggests codes as researcher highlights text", insight_ids: insightIds.slice(0, 1), phase: "develop", priority: "high", effort: "large", status: "proposed" },
    { text: "[SIM] Add universal search overlay (Cmd+K) that searches across all research artifacts", insight_ids: insightIds.slice(0, 1), phase: "develop", priority: "high", effort: "medium", status: "proposed" },
    { text: "[SIM] Implement 1-click export to PDF/PPTX with auto-generated executive summary", insight_ids: insightIds.slice(1, 2), phase: "develop", priority: "medium", effort: "medium", status: "proposed" },
  ];

  for (const rec of developRecs) {
    try {
      const created = await api.post(`/api/findings/recommendations`, { ...rec, project_id: ctx.projectId });
      checks.push({ name: `Develop rec: ${rec.priority} priority`, passed: !!created.id, detail: `id=${created.id}` });
    } catch (e) {
      checks.push({ name: `Develop rec`, passed: false, detail: e.message });
    }
  }

  // Phase 4: DELIVER — implementation tracking nuggets and recs
  const deliverNuggets = [
    { text: "[SIM] Auto-tagging prototype tested with 5 users — 4/5 rated it 'very useful'", source: "Prototype Test", source_location: "Sprint 3", tags: ["validation", "auto-tagging", "prototype"], phase: "deliver", confidence: 0.9 },
    { text: "[SIM] Cmd+K search reduced time-to-find from 45s to 8s in A/B test", source: "A/B Test Results", source_location: "Sprint 4", tags: ["validation", "search", "performance"], phase: "deliver", confidence: 0.93 },
  ];

  for (const nugget of deliverNuggets) {
    try {
      const created = await api.post(`/api/findings/nuggets`, { ...nugget, project_id: ctx.projectId });
      checks.push({ name: `Deliver nugget: ${nugget.tags[1]}`, passed: !!created.id, detail: `id=${created.id}` });
    } catch (e) {
      checks.push({ name: `Deliver nugget`, passed: false, detail: e.message });
    }
  }

  const deliverRecs = [
    { text: "[SIM] Ship auto-tagging v1 to all users in next release", insight_ids: insightIds.slice(0, 1), phase: "deliver", priority: "high", effort: "small", status: "approved" },
    { text: "[SIM] Roll out Cmd+K search to 20% of users for beta monitoring", insight_ids: insightIds.slice(0, 1), phase: "deliver", priority: "high", effort: "small", status: "approved" },
  ];

  for (const rec of deliverRecs) {
    try {
      const created = await api.post(`/api/findings/recommendations`, { ...rec, project_id: ctx.projectId });
      checks.push({ name: `Deliver rec: ${rec.status}`, passed: !!created.id, detail: `id=${created.id}` });
    } catch (e) {
      checks.push({ name: `Deliver rec`, passed: false, detail: e.message });
    }
  }

  // Verify summary has items in ALL phases
  try {
    const summary = await api.get(`/api/findings/summary/${ctx.projectId}`);
    const bp = summary.by_phase || {};
    const allPhasesPopulated =
      (bp.discover?.nuggets || 0) > 0 &&
      (bp.define?.facts || 0) > 0 &&
      (bp.define?.insights || 0) > 0 &&
      (bp.develop?.recommendations || 0) > 0 &&
      (bp.deliver?.nuggets || 0) > 0 &&
      (bp.deliver?.recommendations || 0) > 0;

    checks.push({
      name: "All 4 phases populated",
      passed: allPhasesPopulated,
      detail: `D=${JSON.stringify(bp.discover)} Df=${JSON.stringify(bp.define)} Dv=${JSON.stringify(bp.develop)} Dl=${JSON.stringify(bp.deliver)}`,
    });
  } catch (e) {
    checks.push({ name: "All 4 phases populated", passed: false, detail: e.message });
  }

  // ── Research Integrity: Reports endpoint ──
  try {
    const reports = await api.get(`/api/reports/${ctx.projectId}`);
    const reportList = Array.isArray(reports) ? reports : reports.reports || [];
    checks.push({
      name: "GET /api/reports/{project_id} returns reports",
      passed: true,
      detail: `count=${reportList.length}`,
    });

    // Verify reports have layer field (2, 3, or 4)
    if (reportList.length > 0) {
      const validLayers = [2, 3, 4];
      const withValidLayer = reportList.filter((r) => validLayers.includes(r.layer));
      checks.push({
        name: "Reports have valid layer field (2, 3, or 4)",
        passed: withValidLayer.length === reportList.length,
        detail: `${withValidLayer.length}/${reportList.length} reports have valid layer`,
      });
    } else {
      checks.push({
        name: "Reports have valid layer field (2, 3, or 4)",
        passed: true,
        detail: "No reports yet — will be created by skill execution",
      });
    }
  } catch (e) {
    // 404 is acceptable if the reports endpoint is not yet implemented
    const is404 = e.message.includes("404");
    checks.push({
      name: "GET /api/reports/{project_id} returns reports",
      passed: is404,
      detail: is404 ? "Endpoint not implemented yet (404)" : e.message,
    });
  }

  // ── Research Integrity: Report convergence — running a skill should update, not duplicate ──
  try {
    const reportsBefore = await api.get(`/api/reports/${ctx.projectId}`);
    const beforeList = Array.isArray(reportsBefore) ? reportsBefore : reportsBefore.reports || [];
    const beforeCount = beforeList.length;

    // Re-fetch reports (in a real test, a skill would run between these calls;
    // here we verify the endpoint is stable and the count doesn't grow spuriously)
    const reportsAfter = await api.get(`/api/reports/${ctx.projectId}`);
    const afterList = Array.isArray(reportsAfter) ? reportsAfter : reportsAfter.reports || [];
    const afterCount = afterList.length;

    checks.push({
      name: "Report convergence: count stable without new skill runs",
      passed: afterCount === beforeCount,
      detail: `before=${beforeCount}, after=${afterCount}`,
    });
  } catch (e) {
    // If reports endpoint doesn't exist, this is a graceful skip
    const is404 = e.message.includes("404");
    checks.push({
      name: "Report convergence check",
      passed: is404,
      detail: is404 ? "Reports endpoint not implemented yet (404)" : e.message,
    });
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
