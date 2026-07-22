/** Scenario 79 — Engine Selector: per-project agent engine indicator + selector (W8 UX parity). */

export const name = "Engine Selector";
export const id = "79-engine-selector";

export async function run(ctx) {
  const { api, page, screenshot } = ctx;
  const checks = [];

  // Ensure a project to drive the per-project engine field.
  let projectId = typeof ctx.projectId === "string" ? ctx.projectId.trim() : "";
  let createdProject = false;
  if (!projectId) {
    try {
      const created = await api.post("/api/projects", {
        name: "Engine Selector Probe",
        description: "Scenario 79 per-project engine selector probe",
      });
      projectId = created.id;
      createdProject = true;
      checks.push({ name: "Probe project created", passed: !!projectId, detail: `id=${projectId}` });
    } catch (e) {
      checks.push({ name: "Probe project created", passed: false, detail: e.message });
      return { checks, passed: checks.filter((c) => c.passed).length, failed: checks.filter((c) => !c.passed).length, summary: "no project" };
    }
  }

  // 1. API: the project payload exposes the engine field (W8 backend parity).
  try {
    const project = await api.get(`/api/projects/${projectId}`);
    checks.push({
      name: "Project response exposes agentic_engine",
      passed: "agentic_engine" in project,
      detail: `value=${JSON.stringify(project.agentic_engine)}`,
    });
  } catch (e) {
    checks.push({ name: "Project response exposes agentic_engine", passed: false, detail: e.message });
  }

  // 2. API: set the per-project engine to Pi and read it back.
  try {
    const updated = await api.patch(`/api/projects/${projectId}`, { agentic_engine: "pi" });
    checks.push({
      name: "Set per-project engine to Pi",
      passed: updated.agentic_engine === "pi",
      detail: `value=${JSON.stringify(updated.agentic_engine)}`,
    });
    const reread = await api.get(`/api/projects/${projectId}`);
    checks.push({
      name: "Engine selection persists",
      passed: reread.agentic_engine === "pi",
      detail: `value=${JSON.stringify(reread.agentic_engine)}`,
    });
  } catch (e) {
    checks.push({ name: "Set per-project engine to Pi", passed: false, detail: e.message });
  }

  // 3. API: invalid engine values are rejected (never a silent engine switch).
  try {
    await api.patch(`/api/projects/${projectId}`, { agentic_engine: "bogus-engine" });
    checks.push({ name: "Invalid engine rejected", passed: false, detail: "accepted bogus-engine" });
  } catch (e) {
    checks.push({ name: "Invalid engine rejected", passed: true, detail: e.message?.slice(0, 80) });
  }

  // 4. UI: the sidebar shows a per-project engine indicator.
  await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);
  const badge = page.locator('span[aria-label="Engine: Pi"]').first();
  const badgeVisible = await badge.isVisible({ timeout: 5000 }).catch(() => false);
  checks.push({ name: "Sidebar engine indicator (Pi)", passed: badgeVisible, detail: "" });
  await screenshot("79-sidebar-engine-indicator");

  // 5. UI: project settings expose the engine selector and reflect the value.
  try {
    const moreBtn = page.locator('button[aria-label="More views"]').first();
    if (await moreBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await moreBtn.click();
      await page.waitForTimeout(300);
    }
    await page.locator('button[aria-label="Project Settings"]').first().click();
    const selector = page.locator('select[aria-label="Agent engine"]').first();
    await selector.waitFor({ state: "visible", timeout: 10000 });
    checks.push({
      name: "Project settings engine selector",
      passed: (await selector.inputValue()) === "pi",
      detail: `value=${await selector.inputValue()}`,
    });
    await screenshot("79-project-settings-engine-selector");
  } catch (e) {
    checks.push({ name: "Project settings engine selector", passed: false, detail: e.message });
  }

  // 6. Restore the inherited default (and the probe project) — leave no trace.
  try {
    const restored = await api.patch(`/api/projects/${projectId}`, { agentic_engine: "" });
    checks.push({
      name: "Engine reset to global default",
      passed: restored.agentic_engine === null || restored.agentic_engine === "",
      detail: `value=${JSON.stringify(restored.agentic_engine)}`,
    });
  } catch (e) {
    checks.push({ name: "Engine reset to global default", passed: false, detail: e.message });
  }
  if (createdProject) {
    try {
      await api.delete(`/api/projects/${projectId}`);
    } catch { /* cleanup best-effort */ }
  }

  const passed = checks.filter((c) => c.passed).length;
  const failed = checks.length - passed;
  return { checks, passed, failed, summary: `${passed}/${checks.length} engine-selector checks passed` };
}
