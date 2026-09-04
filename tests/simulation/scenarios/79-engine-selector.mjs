/** Scenario 79 — Engine Selector: per-project agent engine indicator + selector (W8 UX parity),
 * plus bounded behavioral turns proving each agentic core actually routes (CF-SPEC-1 Phase 5). */

import { chat as chatClient, getApiBase } from "../lib/api-client.mjs";

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
    const group = page.locator('[role="radiogroup"][aria-labelledby="agentic-core-project-title"]').first();
    await group.waitFor({ state: "visible", timeout: 10000 });
    const piRadio = page.locator('input[type="radio"][name="agentic-core-choice"][value="pi"]').first();
    checks.push({
      name: "Project settings engine radiogroup",
      passed: await piRadio.isChecked().catch(() => false),
      detail: `pi checked=${await piRadio.isChecked().catch(() => false)}`,
    });
    // W3 deliverable: evidence-backed comparative summary + provisional badge.
    const provisionalBadge = page.getByText("Provisional benchmark", { exact: true }).first();
    checks.push({
      name: "Engine comparative summary present with provisional badge",
      passed: await provisionalBadge.isVisible({ timeout: 3000 }).catch(() => false),
      detail: "",
    });
    // The UI intentionally renders a short, readable filename while the
    // anchor href carries the complete repository-relative provenance path.
    // Assert both surfaces instead of requiring hidden path text to be
    // duplicated into the visible copy.
    const evidenceLink = page.locator('a[href*="/reports/"]').first();
    const evidenceHref = await evidenceLink.getAttribute("href").catch(() => "");
    checks.push({
      name: "Comparative summary cites evidence provenance",
      passed: await evidenceLink.isVisible({ timeout: 3000 }).catch(() => false)
        && /\/comparison-Istara-pi\/reports\//.test(evidenceHref || ""),
      detail: `href=${evidenceHref || "missing"}`,
    });
    await screenshot("79-project-settings-engine-selector");
  } catch (e) {
    checks.push({ name: "Project settings engine selector", passed: false, detail: e.message });
  }

  // 5b. Behavioral: one bounded chat turn per engine, asserting the usage
  // ledger records the selected core. This is the end-to-end routing proof:
  // config surface alone cannot show the loop actually executed per engine.
  if (!ctx.llmConnected || ctx.llmReadiness?.chat_ready === false) {
    checks.push({
      name: "Behavioral per-engine chat turns",
      passed: true,
      detail: !ctx.llmConnected
        ? "Skipped: LLM not connected — routing evidence requires a configured provider"
        : "Skipped: provider is reachable but chat_ready=false — routing evidence requires a live chat model",
    });
  } else {
    for (const engine of ["legacy", "pi"]) {
      try {
        await api.patch(`/api/projects/${projectId}`, { agentic_engine: engine });
        const events = await chatClient.send(projectId, "Reply with exactly: ok", { engine });
        const errored = events.find((event) => event?.type === "error");
        checks.push({
          name: `Chat turn executes on engine=${engine}`,
          passed: !errored && events.length > 0,
          detail: errored ? String(errored.message || errored.error || "stream error").slice(0, 120) : `${events.length} SSE events`,
        });

        // Routing evidence from the usage ledger (engine recorded per dispatch).
        const usage = await api.get(`/api/chat/usage/${projectId}`);
        const latestEngine = usage?.latest?.engine || usage?.last_turn?.engine || null;
        checks.push({
          name: `Usage ledger records engine=${engine}`,
          passed: latestEngine === engine,
          detail: `latest.engine=${JSON.stringify(latestEngine)}`,
        });
      } catch (e) {
        checks.push({
          name: `Chat turn executes on engine=${engine}`,
          passed: false,
          detail: String(e.message).slice(0, 140),
        });
      }
    }
    await screenshot("79-behavioral-engine-turns");
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
