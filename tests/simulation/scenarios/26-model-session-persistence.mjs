/** Scenario 26 — Model & Session Persistence: model switching, .env persistence, session survival. */

export const name = "Model & Session Persistence";
export const id = "26-model-session-persistence";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];
  const fixedTestModel = ctx.fixedTestModel || process.env.ISTARA_FIXED_LLM_TEST_MODEL || null;

  // ── 1. Admin model inventory reports correct provider and model ──
  let initialModel = null;
  let provider = null;
  let models = [];
  try {
    const inventory = await api.get("/api/settings/models");
    provider = inventory.provider;
    initialModel = inventory.active_model;
    models = inventory.models || [];
    checks.push({
      name: "Model inventory reports active model",
      passed: !!initialModel && initialModel !== "default",
      detail: `provider=${provider}, model=${initialModel}`,
    });
  } catch (e) {
    checks.push({ name: "Model inventory reports active model", passed: false, detail: e.message });
  }

  // ── 2. Model list returns available models ──
  try {
    const mdl = models.length > 0 ? { models, status: "online" } : await api.get("/api/settings/models");
    models = mdl.models || [];
    checks.push({
      name: "Model list available",
      passed: models.length > 0,
      detail: `count=${models.length}, status=${mdl.status}`,
    });
  } catch (e) {
    checks.push({ name: "Model list available", passed: false, detail: e.message });
  }

  // ── 3. Active model is in model list (not "default" placeholder) ──
  if (initialModel && models.length > 0) {
    const modelNames = models.map((m) => m.name || m.id);
    const modelInList = modelNames.some((n) => n === initialModel || n.includes(initialModel));
    const fixedModelPinned = fixedTestModel && initialModel === fixedTestModel;
    checks.push({
      name: "Active model exists in model list",
      passed: modelInList || fixedModelPinned,
      detail: modelInList
        ? `${initialModel} found`
        : fixedModelPinned
          ? `${initialModel} pinned by fixed test profile`
          : `${initialModel} NOT in [${modelNames.join(", ")}]`,
    });
  }

  // ── 4. Switch model via API ──
  let switchedModel = null;
  if (models.length > 0) {
    const targetModel = fixedTestModel || models[0].name || models[0].id;
    try {
      const result = await api.post(`/api/settings/model?model_name=${encodeURIComponent(targetModel)}`, {});
      switchedModel = result.model;
      checks.push({
        name: fixedTestModel ? "Re-apply fixed test model via API" : "Switch model via API",
        passed:
          result.status === "switched"
          && result.persisted === true
          && (!fixedTestModel || result.model === fixedTestModel),
        detail: `model=${result.model}, persisted=${result.persisted}`,
      });
    } catch (e) {
      checks.push({ name: "Switch model via API", passed: false, detail: e.message });
    }
  }

  // ── 5. Verify model switch reflected in status ──
  if (switchedModel) {
    try {
      const inventory = await api.get("/api/settings/models");
      checks.push({
        name: "Model switch reflected in inventory",
        passed: inventory.active_model === switchedModel,
        detail: `expected=${switchedModel}, got=${inventory.active_model}`,
      });
    } catch (e) {
      checks.push({ name: "Model switch reflected in inventory", passed: false, detail: e.message });
    }
  }

  // ── 6. Restore original model ──
  if (initialModel && switchedModel && initialModel !== switchedModel) {
    try {
      await api.post(`/api/settings/model?model_name=${encodeURIComponent(initialModel)}`, {});
      checks.push({ name: "Restore original model", passed: true, detail: `restored=${initialModel}` });
    } catch (e) {
      checks.push({ name: "Restore original model", passed: false, detail: e.message });
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

  // ── 9. Provider inventory is consistent ──
  try {
    const inventory = await api.get("/api/settings/models");
    checks.push({
      name: "Provider consistent after operations",
      passed: inventory.provider === provider,
      detail: `expected=${provider}, got=${inventory.provider}`,
    });
  } catch (e) {
    checks.push({ name: "Provider consistent after operations", passed: false, detail: e.message });
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
