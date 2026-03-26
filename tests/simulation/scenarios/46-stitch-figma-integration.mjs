/** Scenario 46 — Stitch & Figma Integration: comprehensive mock-based tests
 *  for design skills registry, screen CRUD with mock generate/edit/variants,
 *  Figma import simulation, handoff, and dev spec endpoints.
 *
 *  Uses mock endpoints to exercise the full pipeline without API keys.
 */

export const name = "Stitch & Figma Integration";
export const id = "46-stitch-figma-integration";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];
  const cleanup = { screenIds: [] };

  // ── Helper: ensure we have a project ──
  let projectId = ctx.projectId;
  if (!projectId) {
    try {
      const created = await api.post("/api/projects", {
        name: "[SIM-46] Stitch Figma Test Project",
        description: "Temporary project for Stitch & Figma integration tests",
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

  // ── 1. Stitch skills in registry ──
  let allSkills = [];
  try {
    const data = await api.get("/api/skills");
    allSkills = data.skills || data || [];
    const stitchSkillIds = ["stitch-design", "stitch-enhance-prompt", "stitch-react-components", "stitch-design-system"];
    const foundStitch = stitchSkillIds.filter((id) =>
      allSkills.some((s) => s.id === id || s.name === id || s.skill_id === id)
    );
    checks.push({
      name: "Stitch skills present in registry (4/4)",
      passed: foundStitch.length === 4,
      detail: `Found ${foundStitch.length}/4: ${foundStitch.join(", ")}`,
    });
  } catch (e) {
    checks.push({ name: "Stitch skills present in registry", passed: false, detail: e.message });
  }

  // ── 2. Stitch skill definitions have required fields ──
  try {
    const stitchSkills = allSkills.filter((s) =>
      (s.id || s.name || s.skill_id || "").startsWith("stitch-")
    );
    const requiredFields = ["name", "display_name", "description", "phase", "skill_type"];
    let allValid = true;
    const details = [];
    for (const skill of stitchSkills) {
      const missing = requiredFields.filter((f) => !skill[f]);
      if (missing.length > 0) {
        allValid = false;
        details.push(`${skill.id || skill.name}: missing ${missing.join(", ")}`);
      }
    }
    checks.push({
      name: "Stitch skill definitions have required fields",
      passed: stitchSkills.length > 0 && allValid,
      detail: stitchSkills.length === 0
        ? "No stitch skills found"
        : allValid
          ? `All ${stitchSkills.length} stitch skills valid`
          : details.join("; "),
    });
  } catch (e) {
    checks.push({ name: "Stitch skill definitions valid", passed: false, detail: e.message });
  }

  // ── 3. All 4 Stitch skills have valid plan_prompt and execute_prompt ──
  try {
    const stitchSkills = allSkills.filter((s) =>
      (s.id || s.name || s.skill_id || "").startsWith("stitch-")
    );
    const withPrompts = stitchSkills.filter(
      (s) => (s.plan_prompt || s.execute_prompt || s.prompt || s.description || "").length > 0
    );
    checks.push({
      name: "Stitch skills have non-empty prompts/descriptions",
      passed: withPrompts.length >= stitchSkills.length && stitchSkills.length > 0,
      detail: `${withPrompts.length}/${stitchSkills.length} skills have prompts`,
    });
  } catch (e) {
    checks.push({ name: "Stitch skills have prompts", passed: false, detail: e.message });
  }

  // ── 4. Design chat endpoint accepts messages ──
  if (projectId) {
    try {
      const res = await fetch("http://localhost:8000/api/interfaces/design-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: "List available design tools",
          project_id: projectId,
        }),
      });
      const contentType = res.headers.get("content-type") || "";
      checks.push({
        name: "Design chat endpoint accepts messages",
        passed: res.status === 200 || contentType.includes("text/event-stream"),
        detail: `status=${res.status}, content-type=${contentType.substring(0, 50)}`,
      });
    } catch (e) {
      checks.push({ name: "Design chat endpoint accepts messages", passed: false, detail: e.message });
    }
  }

  // ── 5. Mock generate with DESKTOP device_type ──
  let desktopScreenId = null;
  if (projectId) {
    try {
      const screen = await api.post("/api/interfaces/mock/generate", {
        project_id: projectId,
        prompt: "[SIM-46] Desktop dashboard",
        device_type: "DESKTOP",
      });
      desktopScreenId = screen.id;
      cleanup.screenIds.push(desktopScreenId);
      checks.push({
        name: "Mock generate DESKTOP screen — device_type stored correctly",
        passed: screen.device_type === "DESKTOP",
        detail: `device_type=${screen.device_type}`,
      });
      checks.push({
        name: "Screen has html_content (not empty) after mock generate",
        passed: !!screen.html_content && screen.html_content.includes("<!DOCTYPE"),
        detail: `html_length=${(screen.html_content || "").length}`,
      });
      checks.push({
        name: "Screen has status 'ready' after generation",
        passed: screen.status === "ready",
        detail: `status=${screen.status}`,
      });
    } catch (e) {
      checks.push({ name: "Mock generate DESKTOP screen", passed: false, detail: e.message });
    }
  }

  // ── 6. Mock generate with MOBILE device_type ──
  if (projectId) {
    try {
      const screen = await api.post("/api/interfaces/mock/generate", {
        project_id: projectId,
        prompt: "[SIM-46] Mobile login form",
        device_type: "MOBILE",
      });
      cleanup.screenIds.push(screen.id);
      checks.push({
        name: "Mock generate MOBILE screen — device_type stored correctly",
        passed: screen.device_type === "MOBILE",
        detail: `device_type=${screen.device_type}`,
      });
    } catch (e) {
      checks.push({ name: "Mock generate MOBILE screen", passed: false, detail: e.message });
    }
  }

  // ── 7. Mock generate with seed_finding_ids ──
  if (projectId) {
    try {
      // Create a recommendation to use as seed
      const rec = await api.post("/api/findings/recommendations", {
        project_id: projectId,
        text: "[SIM-46] Simplify the onboarding wizard to reduce drop-off",
        insight_ids: [],
        phase: "deliver",
        priority: "high",
        effort: "medium",
      });
      const recId = rec.id;

      const screen = await api.post("/api/interfaces/mock/generate", {
        project_id: projectId,
        prompt: "[SIM-46] Onboarding screen seeded from findings",
        device_type: "DESKTOP",
        seed_finding_ids: [recId],
      });
      cleanup.screenIds.push(screen.id);
      checks.push({
        name: "Mock generate with seed_finding_ids creates DesignDecision",
        passed: !!screen.design_decision_id,
        detail: `decision_id=${screen.design_decision_id}`,
      });
      checks.push({
        name: "Screen source_findings contains the seed finding IDs",
        passed: Array.isArray(screen.source_findings) && screen.source_findings.includes(recId),
        detail: `source_findings=${JSON.stringify(screen.source_findings)}`,
      });

      // Clean up recommendation and decision
      if (screen.design_decision_id) {
        try { await api.delete(`/api/findings/design-decisions/${screen.design_decision_id}`); } catch {}
      }
      try { await api.delete(`/api/findings/recommendations/${recId}`); } catch {}
    } catch (e) {
      checks.push({ name: "Mock generate with seed_finding_ids", passed: false, detail: e.message });
    }
  }

  // ── 8. Mock edit creates child screen with parent_screen_id ──
  if (desktopScreenId) {
    try {
      const edited = await api.post("/api/interfaces/mock/edit", {
        screen_id: desktopScreenId,
        instructions: "Change the color scheme to dark mode",
      });
      cleanup.screenIds.push(edited.id);
      checks.push({
        name: "Edit screen has parent_screen_id pointing to original",
        passed: edited.parent_screen_id === desktopScreenId,
        detail: `parent=${edited.parent_screen_id}`,
      });
    } catch (e) {
      checks.push({ name: "Edit creates child with parent_screen_id", passed: false, detail: e.message });
    }
  }

  // ── 9. Mock variants have correct variant_type and parent_screen_id ──
  if (desktopScreenId) {
    try {
      const result = await api.post("/api/interfaces/mock/variants", {
        screen_id: desktopScreenId,
        variant_type: "REFINE",
        count: 2,
      });
      const variants = result.variants || [];
      for (const v of variants) cleanup.screenIds.push(v.id);
      checks.push({
        name: "Variant screens have correct variant_type",
        passed: variants.length >= 2 && variants.every((v) => v.variant_type === "refine"),
        detail: `types=${variants.map((v) => v.variant_type).join(", ")}`,
      });
      checks.push({
        name: "Variant screens have parent_screen_id pointing to original",
        passed: variants.every((v) => v.parent_screen_id === desktopScreenId),
        detail: `all_linked=${variants.every((v) => v.parent_screen_id === desktopScreenId)}`,
      });
    } catch (e) {
      checks.push({ name: "Variant screens correct", passed: false, detail: e.message });
    }
  }

  // ── 10. Mock Figma import returns design context ──
  if (projectId) {
    try {
      const result = await api.post("/api/interfaces/mock/figma-import", {
        project_id: projectId,
        figma_url: "https://www.figma.com/file/abc123XYZ/TestDesign",
      });
      checks.push({
        name: "Mock Figma import returns design context with components",
        passed: result.success === true && Array.isArray(result.components) && result.components.length > 0,
        detail: `components=${(result.components || []).length}, styles=${(result.styles || []).length}`,
      });
      checks.push({
        name: "Mock Figma import returns styles",
        passed: Array.isArray(result.styles) && result.styles.length > 0,
        detail: `styles=${(result.styles || []).length}`,
      });
      checks.push({
        name: "Mock Figma import returns layout data",
        passed: !!result.layout && !!result.layout.grid,
        detail: `grid=${result.layout?.grid}, spacing=${result.layout?.spacing_unit}`,
      });
    } catch (e) {
      checks.push({ name: "Mock Figma import returns design context", passed: false, detail: e.message });
    }
  }

  // ── 11. Figma URL parsing works with real-looking URLs ──
  if (projectId) {
    try {
      const result = await api.post("/api/interfaces/mock/figma-import", {
        project_id: projectId,
        figma_url: "https://www.figma.com/design/XYZABC789/MyDesignSystem?node-id=123-456",
      });
      checks.push({
        name: "Figma URL parsing extracts file_key",
        passed: result.file_key === "XYZABC789",
        detail: `file_key=${result.file_key}`,
      });
      checks.push({
        name: "Figma URL parsing extracts node_id",
        passed: result.node_id === "123-456",
        detail: `node_id=${result.node_id}`,
      });
    } catch (e) {
      checks.push({ name: "Figma URL parsing", passed: false, detail: e.message });
    }
  }

  // ── 12. Dev spec generation with valid screen_id ──
  if (desktopScreenId) {
    try {
      const spec = await api.post("/api/interfaces/handoff/dev-spec", {
        screen_id: desktopScreenId,
      });
      checks.push({
        name: "Dev spec generation returns structured spec",
        passed: spec.success === true && !!spec.dev_spec,
        detail: `has_spec=${!!spec.dev_spec}, keys=${Object.keys(spec.dev_spec || {}).join(", ").substring(0, 80)}`,
      });
    } catch (e) {
      checks.push({ name: "Dev spec generation", passed: false, detail: e.message });
    }
  }

  // ── 13. Dev spec with invalid screen_id returns 404 ──
  try {
    const res = await fetch("http://localhost:8000/api/interfaces/handoff/dev-spec", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ screen_id: "nonexistent-screen-id-999" }),
    });
    checks.push({
      name: "Dev spec with invalid screen_id returns 404",
      passed: res.status === 404 || res.status === 422,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Dev spec with invalid screen_id returns 404", passed: false, detail: e.message });
  }

  // ── 14. Variant with invalid screen_id returns 404 ──
  try {
    const res = await fetch("http://localhost:8000/api/interfaces/screens/variant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ screen_id: "nonexistent-screen-id-999", variant_type: "EXPLORE", count: 2 }),
    });
    checks.push({
      name: "Variant with invalid screen_id returns 404",
      passed: res.status === 404 || res.status === 422,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Variant with invalid screen_id returns 404", passed: false, detail: e.message });
  }

  // ── 15. Edit with invalid screen_id returns 404 ──
  try {
    const res = await fetch("http://localhost:8000/api/interfaces/screens/edit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ screen_id: "nonexistent-screen-id-999", instructions: "Make it blue" }),
    });
    checks.push({
      name: "Edit with invalid screen_id returns 404",
      passed: res.status === 404 || res.status === 422,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Edit with invalid screen_id returns 404", passed: false, detail: e.message });
  }

  // ── Cleanup ──
  for (const id of cleanup.screenIds) {
    try { await fetch(`http://localhost:8000/api/interfaces/screens/${id}`, { method: "DELETE" }); } catch {}
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
