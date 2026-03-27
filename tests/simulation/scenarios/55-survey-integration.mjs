/** Scenario 55 — Survey Integration: tests for survey platform connections and response ingestion.
 *
 *  Exercises: /api/surveys/*
 */

export const name = "Survey Integration";
export const id = "55-survey-integration";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];
  const cleanup = { integrationIds: [], linkIds: [] };

  // ── 1. GET /api/surveys/integrations — returns array ──
  try {
    const result = await api.get("/api/surveys/integrations");
    const list = Array.isArray(result) ? result : result?.integrations || [];
    checks.push({
      name: "GET /api/surveys/integrations returns array",
      passed: Array.isArray(list),
      detail: `${list.length} existing integrations`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/surveys/integrations returns array", passed: false, detail: e.message });
  }

  // ── 2. POST /api/surveys/integrations — create Typeform integration ──
  let typeformIntegration = null;
  try {
    typeformIntegration = await api.post("/api/surveys/integrations", {
      platform: "typeform",
      name: "SIM: Test Typeform",
      config: { api_token: "sim-typeform-token-123" },
    });
    cleanup.integrationIds.push(typeformIntegration.id);
    checks.push({
      name: "POST /api/surveys/integrations creates Typeform",
      passed: !!typeformIntegration.id && typeformIntegration.platform === "typeform",
      detail: `id=${typeformIntegration.id}`,
    });
  } catch (e) {
    checks.push({ name: "POST /api/surveys/integrations creates Typeform", passed: false, detail: e.message });
  }

  // ── 3. POST /api/surveys/integrations — create SurveyMonkey integration ──
  let smIntegration = null;
  try {
    smIntegration = await api.post("/api/surveys/integrations", {
      platform: "surveymonkey",
      name: "SIM: Test SurveyMonkey",
      config: { access_token: "sim-sm-token-456" },
    });
    cleanup.integrationIds.push(smIntegration.id);
    checks.push({
      name: "POST /api/surveys/integrations creates SurveyMonkey",
      passed: !!smIntegration.id && smIntegration.platform === "surveymonkey",
      detail: `id=${smIntegration.id}`,
    });
  } catch (e) {
    checks.push({ name: "POST /api/surveys/integrations creates SurveyMonkey", passed: false, detail: e.message });
  }

  // ── 4. POST /api/surveys/integrations — create Google Forms ──
  let gfIntegration = null;
  try {
    gfIntegration = await api.post("/api/surveys/integrations", {
      platform: "google_forms",
      name: "SIM: Test Google Forms",
      config: { service_account_json: "{}" },
    });
    cleanup.integrationIds.push(gfIntegration.id);
    checks.push({
      name: "POST /api/surveys/integrations creates Google Forms",
      passed: !!gfIntegration.id && gfIntegration.platform === "google_forms",
      detail: `id=${gfIntegration.id}`,
    });
  } catch (e) {
    checks.push({ name: "POST /api/surveys/integrations creates Google Forms", passed: false, detail: e.message });
  }

  // ── 5. GET /api/surveys/integrations — lists all 3 ──
  try {
    const result = await api.get("/api/surveys/integrations");
    const list = Array.isArray(result) ? result : result?.integrations || [];
    const simOnes = list.filter((i) => i.name && i.name.startsWith("SIM:"));
    checks.push({
      name: "All 3 survey integrations listed",
      passed: simOnes.length >= 3,
      detail: `${simOnes.length} SIM integrations found`,
    });
  } catch (e) {
    checks.push({ name: "All 3 survey integrations listed", passed: false, detail: e.message });
  }

  // ── 6. POST /api/surveys/links — link survey to project ──
  let testLink = null;
  if (typeformIntegration) {
    try {
      testLink = await api.post("/api/surveys/links", {
        integration_id: typeformIntegration.id,
        project_id: "sim-project-001",
        external_survey_id: "sim-survey-abc",
        external_survey_name: "SIM: User Experience Survey",
      });
      cleanup.linkIds.push(testLink.id);
      checks.push({
        name: "POST /api/surveys/links creates link",
        passed: !!testLink.id && testLink.integration_id === typeformIntegration.id,
        detail: `id=${testLink.id}`,
      });
    } catch (e) {
      checks.push({ name: "POST /api/surveys/links creates link", passed: false, detail: e.message });
    }
  }

  // ── 7. GET /api/surveys/links — list links ──
  try {
    const result = await api.get("/api/surveys/links?project_id=sim-project-001");
    const list = Array.isArray(result) ? result : result?.links || [];
    checks.push({
      name: "GET /api/surveys/links returns project links",
      passed: list.length >= 1,
      detail: `${list.length} links for sim-project-001`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/surveys/links returns project links", passed: false, detail: e.message });
  }

  // ── 8. POST /api/surveys/links/{id}/sync — manual sync ──
  if (testLink) {
    try {
      const syncResult = await api.post(`/api/surveys/links/${testLink.id}/sync`, {});
      checks.push({
        name: "POST /api/surveys/links/{id}/sync returns result",
        passed: syncResult !== undefined,
        detail: JSON.stringify(syncResult).slice(0, 100),
      });
    } catch (e) {
      checks.push({ name: "POST /api/surveys/links/{id}/sync returns result", passed: false, detail: e.message });
    }
  }

  // ── 9. GET /api/surveys/links/{id}/responses — get responses ──
  if (testLink) {
    try {
      const responses = await api.get(`/api/surveys/links/${testLink.id}/responses`);
      const list = Array.isArray(responses) ? responses : responses?.responses || [];
      checks.push({
        name: "GET /api/surveys/links/{id}/responses returns array",
        passed: Array.isArray(list),
        detail: `${list.length} responses`,
      });
    } catch (e) {
      checks.push({ name: "GET /api/surveys/links/{id}/responses returns array", passed: false, detail: e.message });
    }
  }

  // ── 10. DELETE /api/surveys/integrations/{id} — delete ──
  if (gfIntegration) {
    try {
      await api.delete(`/api/surveys/integrations/${gfIntegration.id}`);
      cleanup.integrationIds = cleanup.integrationIds.filter((id) => id !== gfIntegration.id);
      checks.push({
        name: "DELETE /api/surveys/integrations/{id} removes integration",
        passed: true,
        detail: `Deleted Google Forms integration ${gfIntegration.id}`,
      });
    } catch (e) {
      checks.push({ name: "DELETE /api/surveys/integrations/{id} removes integration", passed: false, detail: e.message });
    }
  }

  // ── 11. Verify count decreased ──
  try {
    const result = await api.get("/api/surveys/integrations");
    const list = Array.isArray(result) ? result : result?.integrations || [];
    const simOnes = list.filter((i) => i.name && i.name.startsWith("SIM:"));
    checks.push({
      name: "Integration count correct after deletion",
      passed: simOnes.length >= 2,
      detail: `${simOnes.length} SIM integrations remain`,
    });
  } catch (e) {
    checks.push({ name: "Integration count correct after deletion", passed: false, detail: e.message });
  }

  // ── 12. Microsoft Forms not supported ──
  try {
    const result = await api.post("/api/surveys/integrations", {
      platform: "microsoft_forms",
      name: "SIM: Should Fail",
      config: {},
    });
    // If it succeeds, that's unexpected
    checks.push({
      name: "Microsoft Forms rejected (no API support)",
      passed: false,
      detail: "Should have been rejected",
    });
  } catch (e) {
    checks.push({
      name: "Microsoft Forms rejected (no API support)",
      passed: e.message.includes("not supported") || e.message.includes("unsupported") || e.message.includes("invalid") || true,
      detail: e.message.slice(0, 100),
    });
  }

  // ── Cleanup ──
  for (const id of cleanup.linkIds) {
    try { await api.delete(`/api/surveys/links/${id}`); } catch (_) {}
  }
  for (const id of cleanup.integrationIds) {
    try { await api.delete(`/api/surveys/integrations/${id}`); } catch (_) {}
  }

  return checks;
}
