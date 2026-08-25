/** Scenario 26 — Pi model authority and session persistence. */

export const name = "Pi Model Authority & Session Persistence";
export const id = "26-model-session-persistence";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];
  const fixedTestModel = ctx.fixedTestModel || process.env.ISTARA_FIXED_LLM_TEST_MODEL || null;

  // ── 1. Compatibility inventory remains readable without write authority ──
  let initialModel = null;
  let provider = null;
  let models = [];
  let piCatalog = [];
  try {
    const inventory = await api.get("/api/settings/models");
    provider = inventory.provider;
    initialModel = inventory.active_model;
    models = inventory.models || [];
    piCatalog = inventory.pi_catalog || [];
    checks.push({
      name: "Compatibility model inventory is readable",
      passed: Array.isArray(models) && Array.isArray(piCatalog),
      detail: `provider=${provider}, active=${initialModel}, classical=${models.length}, pi=${piCatalog.length}`,
    });
  } catch (e) {
    checks.push({ name: "Compatibility model inventory is readable", passed: false, detail: e.message });
  }

  // ── 2. Pi Model Management projects at least one admitted endpoint ──
  try {
    const managed = await api.get("/api/settings/pi-endpoints");
    const endpoints = managed.endpoints || [];
    checks.push({
      name: "Pi Model Management endpoint inventory available",
      passed: Array.isArray(endpoints) && typeof managed.retirement_note === "string",
      detail: `configured=${endpoints.length}, retirement_note=${Boolean(managed.retirement_note)}`,
    });
  } catch (e) {
    checks.push({ name: "Pi Model Management endpoint inventory available", passed: false, detail: e.message });
  }

  // ── 3. Classical model/provider writes fail closed with a Pi successor ──
  const targetModel = fixedTestModel || piCatalog[0]?.model || models[0]?.name || "authority-probe";
  for (const [label, path] of [
    ["Classical model write retired", `/api/settings/model?model_name=${encodeURIComponent(targetModel)}`],
    ["Classical provider write retired", "/api/settings/provider?provider=ollama"],
  ]) {
    try {
      const response = await fetch(`http://localhost:8000${path}`, {
        method: "POST",
        headers: api._headers(),
      });
      const body = await response.json();
      checks.push({
        name: label,
        passed:
          response.status === 410
          && body.error === "pi_model_management_required"
          && body.replacement === "/api/settings/pi-endpoints",
        detail: `status=${response.status}, replacement=${body.replacement}`,
      });
    } catch (e) {
      checks.push({ name: label, passed: false, detail: e.message });
    }
  }

  // ── 7. Inference presets endpoint works ──
  try {
    const presets = await api.get("/api/inference-presets");
    const keys = Object.keys(presets.presets || {});
    const hasRequired = ["lightweight", "medium", "high", "custom"].every((k) => keys.includes(k));
    checks.push({
      name: "Inference presets available",
      passed: hasRequired,
      detail: `keys=${keys.join(",")}`,
    });
  } catch (e) {
    checks.push({ name: "Inference presets available", passed: false, detail: e.message });
  }

  // ── 8. Session CRUD with persistence ──
  let projectId = typeof ctx.projectId === "string" ? ctx.projectId.trim() : "";
  const createdProjectForCleanup = false;
  let sessionId = null;
  const projectQuery = projectId ? `project_id=${encodeURIComponent(projectId)}` : "";

  if (!projectId) {
    checks.push({
      name: "Project available for session tests",
      passed: false,
      detail: "No persistent project from runner",
    });
  } else {
    checks.push({ name: "Project available for session tests", passed: true, detail: `id=${projectId}` });
  }

  if (projectId) {
    // Create session
    try {
      const session = await api.post("/api/sessions", {
        project_id: projectId,
        title: "[SIM] Persistent Session",
        inference_preset: "high",
      });
      sessionId = session.id;
      checks.push({
        name: "Create session with preset",
        passed: !!sessionId && session.inference_preset === "high",
        detail: `id=${sessionId}, preset=${session.inference_preset}`,
      });
    } catch (e) {
      checks.push({ name: "Create session with preset", passed: false, detail: e.message });
    }

    // List sessions — session should persist
    try {
      const result = await api.get(`/api/sessions/${projectId}`);
      const sessions = result.sessions || [];
      const found = sessions.find((s) => s.id === sessionId);
      checks.push({
        name: "Session persisted in list",
        passed: !!found,
        detail: `found=${!!found}, total=${sessions.length}`,
      });
    } catch (e) {
      checks.push({ name: "Session persisted in list", passed: false, detail: e.message });
    }

    // Update session with model override
    if (sessionId && initialModel) {
      try {
        const updated = await api.patch(`/api/sessions/${sessionId}?${projectQuery}`, {
          model_override: initialModel,
          inference_preset: "custom",
          custom_temperature: 0.5,
          custom_max_tokens: 2048,
        });
        checks.push({
          name: "Update session model override",
          passed: updated.model_override === initialModel && updated.inference_preset === "custom",
          detail: `model=${updated.model_override}, preset=${updated.inference_preset}`,
        });
      } catch (e) {
        checks.push({ name: "Update session model override", passed: false, detail: e.message });
      }
    }

    // Star session
    if (sessionId) {
      try {
        const star = await api.post(`/api/sessions/${sessionId}/star?${projectQuery}`, {});
        checks.push({
          name: "Star session toggle",
          passed: star.starred === true,
          detail: `starred=${star.starred}`,
        });
      } catch (e) {
        checks.push({ name: "Star session toggle", passed: false, detail: e.message });
      }
    }

    // Ensure-default creates a session if none exist after deletion
    try {
      const defaultSession = await api.get(`/api/sessions/${projectId}/ensure-default`);
      checks.push({
        name: "Ensure default session",
        passed: !!defaultSession.id,
        detail: `id=${defaultSession.id}`,
      });
    } catch (e) {
      checks.push({ name: "Ensure default session", passed: false, detail: e.message });
    }

    // Delete session
    if (sessionId) {
      try {
        const res = await api.delete(`/api/sessions/${sessionId}?${projectQuery}`);
        checks.push({
          name: "Delete session",
          passed: res.status === 204,
          detail: `status=${res.status}`,
        });
      } catch (e) {
        checks.push({ name: "Delete session", passed: false, detail: e.message });
      }

      // Verify session actually gone
      try {
        const res = await fetch(`http://localhost:8000/api/sessions/detail/${sessionId}?${projectQuery}`, { headers: api._headers() });
        checks.push({
          name: "Session deletion confirmed (404)",
          passed: res.status === 404,
          detail: `status=${res.status}`,
        });
      } catch (e) {
        checks.push({ name: "Session deletion confirmed (404)", passed: false, detail: e.message });
      }
    }

    // Clean up only the temporary project created by this scenario. The shared
    // simulation project must survive for later scenarios in a full run.
    if (createdProjectForCleanup) {
      try {
        await api.delete(`/api/projects/${projectId}`);
      } catch {
        // Ignore cleanup errors
      }
    }
  }

  // ── 9. Read-only compatibility inventory remains stable ──
  try {
    const inventory = await api.get("/api/settings/models");
    checks.push({
      name: "Compatibility inventory unchanged by retired writes",
      passed: inventory.provider === provider && inventory.active_model === initialModel,
      detail: `provider=${inventory.provider}, active=${inventory.active_model}`,
    });
  } catch (e) {
    checks.push({ name: "Compatibility inventory unchanged by retired writes", passed: false, detail: e.message });
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
