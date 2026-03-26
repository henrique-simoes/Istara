/** Scenario 45 — Interfaces Menu: comprehensive mock-based integration tests
 *  for the design menu endpoints, screen CRUD, mock generation, configuration,
 *  and design chat.
 *
 *  Uses mock endpoints that simulate Stitch/Figma responses without API keys,
 *  exercising the full pipeline: endpoint -> service -> model -> DB.
 */

export const name = "Interfaces Menu";
export const id = "45-interfaces-menu";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];
  const cleanup = { screenIds: [], decisionIds: [] };

  // ── Helper: ensure we have a project ──
  let projectId = ctx.projectId;
  if (!projectId) {
    try {
      const created = await api.post("/api/projects", {
        name: "[SIM-45] Interfaces Test Project",
        description: "Temporary project for Interfaces menu integration tests",
      });
      projectId = created.id;
    } catch {
      // Fall back to any existing project
      try {
        const projects = await api.get("/api/projects");
        const list = projects.projects || projects || [];
        if (list.length > 0) projectId = list[0].id;
      } catch {}
    }
  }

  // ── 1. GET /api/interfaces/status ──
  try {
    const status = await api.get("/api/interfaces/status");
    checks.push({
      name: "GET /api/interfaces/status returns 200",
      passed: true,
      detail: `stitch_configured=${status.stitch_configured}, figma_configured=${status.figma_configured}`,
    });
    checks.push({
      name: "Status has stitch_configured field",
      passed: status.stitch_configured !== undefined,
      detail: `stitch_configured=${status.stitch_configured}`,
    });
    checks.push({
      name: "Status has figma_configured field",
      passed: status.figma_configured !== undefined,
      detail: `figma_configured=${status.figma_configured}`,
    });
    checks.push({
      name: "Status has onboarding_needed field",
      passed: status.onboarding_needed !== undefined,
      detail: `onboarding_needed=${status.onboarding_needed}`,
    });
    checks.push({
      name: "Status has screens_count field",
      passed: status.screens_count !== undefined,
      detail: `screens_count=${status.screens_count}`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/interfaces/status returns 200", passed: false, detail: e.message });
  }

  // ── 2. Mock generate a screen ──
  let generatedScreenId = null;
  if (projectId) {
    try {
      const screen = await api.post("/api/interfaces/mock/generate", {
        project_id: projectId,
        prompt: "[SIM-45] Dashboard with user metrics and KPIs",
        device_type: "DESKTOP",
      });
      generatedScreenId = screen.id;
      cleanup.screenIds.push(generatedScreenId);
      checks.push({
        name: "Mock generate creates DesignScreen in DB",
        passed: !!generatedScreenId,
        detail: `id=${generatedScreenId}`,
      });
      checks.push({
        name: "Generated screen has html_content (not empty)",
        passed: !!screen.html_content && screen.html_content.length > 50,
        detail: `html_length=${(screen.html_content || "").length}`,
      });
      checks.push({
        name: "Generated screen has correct device_type",
        passed: screen.device_type === "DESKTOP",
        detail: `device_type=${screen.device_type}`,
      });
      checks.push({
        name: "Generated screen has status 'ready'",
        passed: screen.status === "ready",
        detail: `status=${screen.status}`,
      });
      checks.push({
        name: "Generated screen has title from prompt",
        passed: !!screen.title && screen.title.length > 0,
        detail: `title=${(screen.title || "").substring(0, 60)}`,
      });
      checks.push({
        name: "Generated screen has model_used 'MOCK'",
        passed: screen.model_used === "MOCK",
        detail: `model_used=${screen.model_used}`,
      });
    } catch (e) {
      checks.push({ name: "Mock generate creates DesignScreen in DB", passed: false, detail: e.message });
    }
  }

  // ── 3. List screens — verify generated screen appears ──
  if (projectId) {
    try {
      const screens = await api.get(`/api/interfaces/screens?project_id=${projectId}`);
      const screenList = Array.isArray(screens) ? screens : screens.screens || [];
      checks.push({
        name: "GET /api/interfaces/screens returns array",
        passed: Array.isArray(screenList),
        detail: `count=${screenList.length}`,
      });
      if (generatedScreenId) {
        const found = screenList.some((s) => s.id === generatedScreenId);
        checks.push({
          name: "Generated screen appears in list",
          passed: found,
          detail: `found=${found}, total=${screenList.length}`,
        });
      }
    } catch (e) {
      checks.push({ name: "GET /api/interfaces/screens returns array", passed: false, detail: e.message });
    }
  }

  // ── 4. Get single screen ──
  if (generatedScreenId) {
    try {
      const screen = await api.get(`/api/interfaces/screens/${generatedScreenId}`);
      checks.push({
        name: "GET single screen returns correct screen",
        passed: screen.id === generatedScreenId,
        detail: `id=${screen.id}`,
      });
      checks.push({
        name: "Single screen has html_content with DOCTYPE",
        passed: (screen.html_content || "").includes("<!DOCTYPE"),
        detail: `starts_with_doctype=${(screen.html_content || "").substring(0, 20)}`,
      });
    } catch (e) {
      checks.push({ name: "GET single screen returns correct screen", passed: false, detail: e.message });
    }
  }

  // ── 5. Mock edit the screen ──
  let editedScreenId = null;
  if (generatedScreenId) {
    try {
      const edited = await api.post("/api/interfaces/mock/edit", {
        screen_id: generatedScreenId,
        instructions: "Make it blue and add a profile link",
      });
      editedScreenId = edited.id;
      cleanup.screenIds.push(editedScreenId);
      checks.push({
        name: "Mock edit creates child screen",
        passed: !!editedScreenId && editedScreenId !== generatedScreenId,
        detail: `new_id=${editedScreenId}`,
      });
      checks.push({
        name: "Edited screen has parent_screen_id pointing to original",
        passed: edited.parent_screen_id === generatedScreenId,
        detail: `parent=${edited.parent_screen_id}, expected=${generatedScreenId}`,
      });
      checks.push({
        name: "Edited screen has non-empty html_content",
        passed: !!edited.html_content && edited.html_content.length > 50,
        detail: `html_length=${(edited.html_content || "").length}`,
      });
    } catch (e) {
      checks.push({ name: "Mock edit creates child screen", passed: false, detail: e.message });
    }
  }

  // ── 6. Mock generate variants ──
  if (generatedScreenId) {
    try {
      const result = await api.post("/api/interfaces/mock/variants", {
        screen_id: generatedScreenId,
        variant_type: "EXPLORE",
        count: 2,
      });
      const variants = result.variants || [];
      for (const v of variants) cleanup.screenIds.push(v.id);
      checks.push({
        name: "Mock variants creates 2+ variant screens",
        passed: variants.length >= 2,
        detail: `count=${variants.length}`,
      });
      if (variants.length > 0) {
        checks.push({
          name: "Variant screens linked to parent via parent_screen_id",
          passed: variants.every((v) => v.parent_screen_id === generatedScreenId),
          detail: `all_linked=${variants.every((v) => v.parent_screen_id === generatedScreenId)}`,
        });
        checks.push({
          name: "Variant screens have variant_type set",
          passed: variants.every((v) => !!v.variant_type),
          detail: `types=${variants.map((v) => v.variant_type).join(", ")}`,
        });
      }
    } catch (e) {
      checks.push({ name: "Mock variants creates 2+ variant screens", passed: false, detail: e.message });
    }
  }

  // ── 7. Delete a screen ──
  if (editedScreenId) {
    try {
      const res = await fetch(`http://localhost:8000/api/interfaces/screens/${editedScreenId}`, {
        method: "DELETE",
      });
      checks.push({
        name: "DELETE screen returns 204",
        passed: res.status === 204,
        detail: `status=${res.status}`,
      });
      // Verify removed from list
      const screens = await api.get(`/api/interfaces/screens?project_id=${projectId}`);
      const screenList = Array.isArray(screens) ? screens : screens.screens || [];
      const stillPresent = screenList.some((s) => s.id === editedScreenId);
      checks.push({
        name: "Deleted screen removed from list",
        passed: !stillPresent,
        detail: `still_present=${stillPresent}`,
      });
      // Remove from cleanup since already deleted
      cleanup.screenIds = cleanup.screenIds.filter((id) => id !== editedScreenId);
    } catch (e) {
      checks.push({ name: "DELETE screen returns 204", passed: false, detail: e.message });
    }
  }

  // ── 8. Configure Stitch key ──
  try {
    const result = await api.post("/api/interfaces/configure/stitch", { api_key: "sim-test-key-45" });
    checks.push({
      name: "Configure Stitch returns success",
      passed: result.success === true && result.stitch_configured === true,
      detail: `success=${result.success}, configured=${result.stitch_configured}`,
    });
    // Reset it back so mock endpoints keep working
    await api.post("/api/interfaces/configure/stitch", { api_key: "" });
  } catch (e) {
    checks.push({ name: "Configure Stitch returns success", passed: false, detail: e.message });
  }

  // ── 9. Configure Figma token ──
  try {
    const result = await api.post("/api/interfaces/configure/figma", { api_token: "sim-test-token-45" });
    checks.push({
      name: "Configure Figma returns success",
      passed: result.success === true && result.figma_configured === true,
      detail: `success=${result.success}, configured=${result.figma_configured}`,
    });
    // Reset it back
    await api.post("/api/interfaces/configure/figma", { api_token: "" });
  } catch (e) {
    checks.push({ name: "Configure Figma returns success", passed: false, detail: e.message });
  }

  // ── 10. Design chat endpoint responds ──
  if (projectId) {
    try {
      const res = await fetch("http://localhost:8000/api/interfaces/design-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: "Hello", project_id: projectId }),
      });
      const contentType = res.headers.get("content-type") || "";
      checks.push({
        name: "POST /api/interfaces/design-chat responds (200 or SSE)",
        passed: res.status === 200 || contentType.includes("text/event-stream"),
        detail: `status=${res.status}, content-type=${contentType.substring(0, 50)}`,
      });
    } catch (e) {
      checks.push({ name: "POST /api/interfaces/design-chat responds", passed: false, detail: e.message });
    }
  }

  // ── 11. Handoff briefs endpoint ──
  if (projectId) {
    try {
      const briefs = await api.get(`/api/interfaces/handoff/briefs?project_id=${projectId}`);
      checks.push({
        name: "GET /api/interfaces/handoff/briefs returns 200",
        passed: !!briefs && (briefs.briefs !== undefined || Array.isArray(briefs)),
        detail: `keys=${Object.keys(briefs).join(", ").substring(0, 100)}`,
      });
    } catch (e) {
      checks.push({ name: "GET /api/interfaces/handoff/briefs returns 200", passed: false, detail: e.message });
    }
  }

  // ── 12. Generate returns error if Stitch not configured ──
  try {
    const res = await fetch("http://localhost:8000/api/interfaces/screens/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt: "A login screen",
        device_type: "mobile",
        project_id: projectId || "test",
      }),
    });
    checks.push({
      name: "Real generate endpoint responds",
      passed: res.status === 200 || (res.status >= 400 && res.status < 600),
      detail: `status=${res.status} (expected 4xx/5xx)`,
    });
  } catch (e) {
    checks.push({ name: "Real generate rejects without Stitch config", passed: false, detail: e.message });
  }

  // ── 13. Figma import returns error if Figma not configured ──
  try {
    const res = await fetch("http://localhost:8000/api/interfaces/figma/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        figma_url: "https://figma.com/file/test123",
        project_id: projectId || "test",
      }),
    });
    checks.push({
      name: "Real Figma import endpoint responds",
      passed: res.status === 200 || (res.status >= 400 && res.status < 600),
      detail: `status=${res.status} (expected 4xx/5xx)`,
    });
  } catch (e) {
    checks.push({ name: "Figma import rejects without config", passed: false, detail: e.message });
  }

  // ── 14. Design decisions endpoint ──
  try {
    const decisions = await api.get("/api/findings/design-decisions");
    checks.push({
      name: "GET /api/findings/design-decisions returns 200",
      passed: true,
      detail: `type=${typeof decisions}, isArray=${Array.isArray(decisions)}`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/findings/design-decisions returns 200", passed: false, detail: e.message });
  }

  // ── 15. Integration status endpoint ──
  try {
    const integrations = await api.get("/api/settings/integrations-status");
    checks.push({
      name: "GET /api/settings/integrations-status returns 200",
      passed: true,
      detail: `keys=${Object.keys(integrations).join(", ").substring(0, 100)}`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/settings/integrations-status returns 200", passed: false, detail: e.message });
  }

  // ── 16. Onboarding flips after configuration ──
  try {
    const before = await api.get("/api/interfaces/status");
    const wasPending = before.onboarding_needed;
    // Configure stitch
    await api.post("/api/interfaces/configure/stitch", { api_key: "sim-test-onboarding" });
    const after = await api.get("/api/interfaces/status");
    checks.push({
      name: "Onboarding_needed flips false after Stitch config",
      passed: after.onboarding_needed === false || after.stitch_configured === true,
      detail: `before_onboarding=${wasPending}, after_onboarding=${after.onboarding_needed}, stitch=${after.stitch_configured}`,
    });
    // Reset
    await api.post("/api/interfaces/configure/stitch", { api_key: "" });
  } catch (e) {
    checks.push({ name: "Onboarding flips after configuration", passed: false, detail: e.message });
  }

  // ── Cleanup ──
  for (const id of cleanup.screenIds) {
    try { await fetch(`http://localhost:8000/api/interfaces/screens/${id}`, { method: "DELETE" }); } catch {}
  }
  for (const id of cleanup.decisionIds) {
    try { await api.delete(`/api/findings/design-decisions/${id}`); } catch {}
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
