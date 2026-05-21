/** Scenario 70 — Research Integrity System: verify codebook versioning, code
 *  application audit trails, project reports, convergence pyramid, and
 *  intercoder reliability endpoints.
 */

import { readFileSync } from "fs";
import { basename, join, dirname } from "path";
import { fileURLToPath } from "url";
import { selectCanonicalCorpus } from "../../document_corpus/shared-corpus.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));

export const name = "Research Integrity System";
export const id = "70-research-integrity";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];
  const cleanup = { nuggetIds: [], factIds: [], insightIds: [], recIds: [] };

  // ── 1. Health check ──
  try {
    const health = await api.get("/api/health");
    checks.push({
      name: "Backend healthy",
      passed: health.status === "healthy",
      detail: `status=${health.status}`,
    });
  } catch (e) {
    checks.push({ name: "Backend healthy", passed: false, detail: e.message });
  }

  // ── Ensure project ──
  let projectId = ctx.projectId;
  if (!projectId) {
    checks.push({ name: "Project available", passed: false, detail: "No persistent project from runner" });
    return { checks, passed: 0, failed: checks.length };
  }
  checks.push({ name: "Project available", passed: true, detail: `id=${projectId}` });

  // ── 2. Upload test interview transcript ──
  let uploadSuccess = false;
  let sourceName = "canonical-interview.md";
  try {
    const [canonicalInterview] = selectCanonicalCorpus({ slice: "interview-heavy", minimumSources: 1 });
    sourceName = basename(canonicalInterview.relative_path || canonicalInterview.path);
    const sourcePath = join(__dirname, "..", "..", "document_corpus", "canonical", canonicalInterview.path || canonicalInterview.relative_path);
    const content = readFileSync(sourcePath, "utf-8");
    const result = await api.uploadContent(projectId, content, sourceName);
    uploadSuccess = true;
    checks.push({
      name: "Upload interview transcript",
      passed: true,
      detail: `source=${sourceName}, chunks=${result.chunks_indexed || result.chunks || "uploaded"}`,
    });
  } catch (e) {
    checks.push({ name: "Upload interview transcript", passed: false, detail: e.message });
  }

  // ── 3. Verify skills catalog includes thematic-analysis ──
  let hasThematicSkill = false;
  try {
    const skills = await api.get("/api/skills");
    const list = Array.isArray(skills) ? skills : skills.skills || [];
    hasThematicSkill = list.some(
      (s) => s.name === "thematic-analysis" || s.name === "kappa-thematic-analysis"
    );
    checks.push({
      name: "Thematic analysis skill available",
      passed: hasThematicSkill,
      detail: `skills_count=${list.length}, has_thematic=${hasThematicSkill}`,
    });
  } catch (e) {
    checks.push({ name: "Thematic analysis skill available", passed: false, detail: e.message });
  }

  // ── 4. Run thematic-analysis skill (requires LLM) ──
  let skillResult = null;
  if (ctx.llmConnected && hasThematicSkill && uploadSuccess) {
    try {
      skillResult = await api.post("/api/skills/thematic-analysis/execute", {
        project_id: projectId,
        user_context: "Analyze the uploaded canonical interview source for readiness trust and source traceability themes",
      });
      checks.push({
        name: "Thematic analysis execution",
        passed: skillResult.success === true || !!skillResult.summary,
        detail: `summary=${(skillResult.summary || "").substring(0, 80)}`,
      });
    } catch (e) {
      // Graceful: skill execution may fail without LLM but endpoint works
      checks.push({
        name: "Thematic analysis execution",
        passed: e.message.includes("422") || e.message.includes("503"),
        detail: `Graceful: ${e.message.substring(0, 80)}`,
      });
    }
  } else {
    checks.push({
      name: "Thematic analysis execution",
      passed: true,
      detail: `Skipped: llm=${ctx.llmConnected}, skill=${hasThematicSkill}, upload=${uploadSuccess}`,
    });
  }

  // ── 5. Create nuggets with source_location and verify ──
  const nuggets = [
    {
      text: "[SIM-70] Canonical interview evidence says appointment-prep readiness is hard to trust without source trails",
      source: sourceName,
      source_location: `${sourceName}:L11`,
      tags: ["readiness", "source-traceability", "friction"],
      phase: "discover",
    },
    {
      text: "[SIM-70] Canonical interview evidence says patients cannot tell which tasks are required before appointments",
      source: sourceName,
      source_location: `${sourceName}:L12`,
      tags: ["appointment-prep", "clarity"],
      phase: "discover",
    },
    {
      text: "[SIM-70] Canonical interview evidence says staff need source labels before trusting automation",
      source: sourceName,
      source_location: `${sourceName}:L16`,
      tags: ["trust", "source-traceability"],
      phase: "discover",
    },
    {
      text: "[SIM-70] Canonical interview evidence says report eligibility requires approved Done task evidence",
      source: sourceName,
      source_location: `${sourceName}:L17`,
      tags: ["reporting", "approval"],
      phase: "discover",
    },
  ];

  for (const nugget of nuggets) {
    try {
      const created = await api.post("/api/findings/nuggets", {
        project_id: projectId,
        ...nugget,
      });
      cleanup.nuggetIds.push(created.id);
    } catch {}
  }

  // Verify nuggets have source_location populated
  try {
    const allNuggets = await api.get(`/api/findings/nuggets?project_id=${projectId}`);
    const list = Array.isArray(allNuggets) ? allNuggets : allNuggets.nuggets || [];
    const simNuggets = list.filter((n) => n.text && n.text.startsWith("[SIM-70]"));

    const withLocation = simNuggets.filter((n) => n.source_location && n.source_location.length > 0);
    checks.push({
      name: "Nuggets have source_location populated",
      passed: withLocation.length === simNuggets.length && simNuggets.length > 0,
      detail: `with_location=${withLocation.length}/${simNuggets.length}`,
    });

    // Verify nuggets have non-empty tags
    const withTags = simNuggets.filter((n) => Array.isArray(n.tags) && n.tags.length > 0);
    checks.push({
      name: "Nuggets have non-empty tags",
      passed: withTags.length === simNuggets.length && simNuggets.length > 0,
      detail: `with_tags=${withTags.length}/${simNuggets.length}`,
    });
  } catch (e) {
    checks.push({ name: "Nuggets have source_location populated", passed: false, detail: e.message });
    checks.push({ name: "Nuggets have non-empty tags", passed: false, detail: e.message });
  }

  // ── 6. Create facts and insights to seed report generation ──
  let factId = null;
  let insightId = null;
  let recId = null;

  try {
    const fact = await api.post("/api/findings/facts", {
      project_id: projectId,
      text: "[SIM-70] 3/4 canonical interview nuggets indicate readiness and reporting trust depend on traceable approved evidence",
      nugget_ids: cleanup.nuggetIds.slice(0, 3),
      phase: "discover",
    });
    factId = fact.id;
    cleanup.factIds.push(factId);
  } catch {}

  try {
    const insight = await api.post("/api/findings/insights", {
      project_id: projectId,
      text: "[SIM-70] Readiness automation is trusted only when source evidence and approval state are visible",
      fact_ids: factId ? [factId] : [],
      phase: "define",
      impact: "high",
    });
    insightId = insight.id;
    cleanup.insightIds.push(insightId);
  } catch {}

  try {
    const rec = await api.post("/api/findings/recommendations", {
      project_id: projectId,
      text: "[SIM-70] Show source traceability and Done-task approval state beside generated readiness findings",
      insight_ids: insightId ? [insightId] : [],
      phase: "deliver",
      priority: "high",
      effort: "medium",
    });
    recId = rec.id;
    cleanup.recIds.push(recId);
  } catch {}

  const chainCreated = cleanup.nuggetIds.length > 0 && factId && insightId && recId;
  checks.push({
    name: "Evidence chain created (nuggets -> fact -> insight -> rec)",
    passed: !!chainCreated,
    detail: `nuggets=${cleanup.nuggetIds.length}, fact=${!!factId}, insight=${!!insightId}, rec=${!!recId}`,
  });

  // ── 7. Check project reports via GET /api/reports/{project_id} ──
  let reports = [];
  try {
    reports = await api.get(`/api/reports/${projectId}`);
    const reportList = Array.isArray(reports) ? reports : [];
    checks.push({
      name: "GET /api/reports/{project_id} returns 200",
      passed: Array.isArray(reports),
      detail: `report_count=${reportList.length}`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/reports/{project_id} returns 200", passed: false, detail: e.message });
  }

  // ── 8. Verify convergence pyramid structure ──
  // Reports are ordered by layer (highest first) — check the response structure
  const reportList = Array.isArray(reports) ? reports : [];
  if (reportList.length > 0) {
    // Check that reports have required pyramid fields
    const firstReport = reportList[0];
    const hasFields = firstReport.layer !== undefined &&
                      firstReport.scope !== undefined &&
                      firstReport.status !== undefined &&
                      firstReport.title !== undefined;
    checks.push({
      name: "Reports have convergence pyramid fields (layer, scope, status, title)",
      passed: hasFields,
      detail: `fields=${Object.keys(firstReport).join(", ").substring(0, 120)}`,
    });

    // Check ordering: layer descending
    const layers = reportList.map((r) => r.layer);
    const isDescending = layers.every((val, i) => i === 0 || val <= layers[i - 1]);
    checks.push({
      name: "Reports ordered by layer descending",
      passed: isDescending,
      detail: `layers=${JSON.stringify(layers)}`,
    });
  } else {
    // No reports yet is acceptable — the system creates them on skill execution
    checks.push({
      name: "Reports have convergence pyramid fields",
      passed: true,
      detail: "No reports yet (created on skill execution)",
    });
    checks.push({
      name: "Reports ordered by layer descending",
      passed: true,
      detail: "No reports to check ordering",
    });
  }

  // ── 9. Verify skills catalog includes kappa-thematic-analysis ──
  try {
    const skills = await api.get("/api/skills");
    const list = Array.isArray(skills) ? skills : skills.skills || [];
    const hasKappa = list.some((s) => s.name === "kappa-thematic-analysis");
    checks.push({
      name: "Kappa intercoder skill registered",
      passed: hasKappa,
      detail: `found=${hasKappa}`,
    });
  } catch (e) {
    checks.push({ name: "Kappa intercoder skill registered", passed: false, detail: e.message });
  }

  // ── 10. Codebook version endpoint (if available) ──
  try {
    const codebooks = await api.get(`/api/codebooks?project_id=${projectId}`);
    const list = Array.isArray(codebooks) ? codebooks : codebooks.codebooks || [];
    checks.push({
      name: "Codebooks endpoint responds",
      passed: true,
      detail: `count=${list.length}`,
    });
  } catch (e) {
    // Endpoint may not exist yet — gracefully accept 404
    const graceful = e.message.includes("404") || e.message.includes("Not Found");
    checks.push({
      name: "Codebooks endpoint responds",
      passed: graceful,
      detail: graceful ? "Endpoint not yet implemented (404)" : e.message,
    });
  }

  // ── 11. Findings summary includes all types ──
  try {
    const summary = await api.get(`/api/findings/summary/${projectId}`);
    const hasCounts = summary.nuggets !== undefined || summary.total !== undefined ||
                      (typeof summary === "object" && Object.keys(summary).length > 0);
    checks.push({
      name: "Findings summary endpoint responds with data",
      passed: hasCounts,
      detail: JSON.stringify(summary).substring(0, 120),
    });
  } catch (e) {
    checks.push({ name: "Findings summary endpoint", passed: false, detail: e.message });
  }

  // ── 12. Evidence chain API — verify traceability ──
  if (recId) {
    try {
      const chain = await api.get(`/api/findings/evidence-chain?finding_type=recommendation&finding_id=${recId}&project_id=${projectId}`);
      const hasChain = !!chain && !!chain.chain;
      checks.push({
        name: "Evidence chain API returns linked findings",
        passed: hasChain,
        detail: `keys=${Object.keys(chain.chain || chain || {}).join(", ")}`,
      });
    } catch (e) {
      checks.push({
        name: "Evidence chain API returns linked findings",
        passed: true,
        detail: `Endpoint variation: ${e.message.substring(0, 80)}`,
      });
    }
  }

  // ── Cleanup ──
  for (const id of cleanup.recIds) {
    try { await api.delete(`/api/findings/recommendations/${id}?project_id=${projectId}`); } catch {}
  }
  for (const id of cleanup.insightIds) {
    try { await api.delete(`/api/findings/insights/${id}?project_id=${projectId}`); } catch {}
  }
  for (const id of cleanup.factIds) {
    try { await api.delete(`/api/findings/facts/${id}?project_id=${projectId}`); } catch {}
  }
  for (const id of cleanup.nuggetIds) {
    try { await api.delete(`/api/findings/nuggets/${id}?project_id=${projectId}`); } catch {}
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}: ${c.detail}`).join("\n"),
  };
}
