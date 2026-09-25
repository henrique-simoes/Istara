/**
 * Scenario 86 — Evidence provenance health in the Memory view (measurement 5, 2026-09-25 spine
 * findings and retrieval measurements).
 *
 * Hybrid RAG is the Research Spine's exact-evidence retriever: a retrieved passage must trace back
 * to the evidence unit it was cut from. Before this change no ingestion path set
 * `evidence_unit_id` on a chunk (0% coverage) and nothing reported it. The Memory view's Health
 * tab now shows the invariant as an "Evidence Provenance" card. This scenario drives it the way a
 * researcher does:
 *
 *   1. a fresh project shows the honest empty state ("No source chunks yet", no percentage);
 *   2. two synthetic transcripts uploaded through the Documents view's real file chooser are
 *      indexed with provenance: the card reads 100% and "All traceable", and the API it renders
 *      agrees (with_evidence_unit == source_chunks > 0);
 *   3. loading and error states render and recover (the stats request is held, then failed once,
 *      and Retry recovers). The degraded branch is rendered from a fixture payload, labelled so;
 *   4. the matrix AGENTS.md asks of a changed surface: roles (admin, researcher, viewer see the
 *      card; a stranger is held at login), keyboard Tab reaches the Health tab with visible focus
 *      and Enter opens it, at 375px the Health tab is on screen and usable (the tab row used to be
 *      clipped by an `overflow-hidden` parent without any page scroll, which a scroll-width check
 *      alone cannot see), light and dark themes, and axe-core WCAG 2.1 AA finds no serious or
 *      critical violation in either theme.
 *
 * Setup and cleanup (creating and deleting the scenario's own "[SIM-86]" project, and one read of
 * the stats API to cross-check the card) are labelled API-behind-browser. Synthetic data only.
 * Runs in the credential-free QA lane: provenance does not depend on embedding quality.
 */

import { getApiBase, authHeaders } from "../lib/api-client.mjs";
import { reflow375Check, keyboardFocusCheck } from "../lib/matrix-checks.mjs";
import { createVariantLedger } from "../lib/variant-obligations.mjs";
import { ensureRoleAccounts, driveRoleCell } from "../lib/role-variants.mjs";

export const name = "Evidence provenance health (Memory)";
export const id = "86-evidence-provenance-health";

const PROJECT_NAME = "[SIM-86] Provenance health";
const HEALTH_TAB = 'button[aria-label="Switch to Health tab"]';
const KNOWLEDGE_TAB = 'button[aria-label="Switch to Knowledge Base tab"]';
const CARD = '[data-testid="provenance-card"]';
const COVERAGE = '[data-testid="provenance-coverage"]';

function transcript(participant, topic, turns) {
  const lines = [`# Scenario86 interview ${participant}: ${topic}`, ""];
  turns.forEach(([question, answer], index) => {
    lines.push(`## Exchange ${index + 1}`, "", `Interviewer: ${question}`, "", `${participant}: ${answer}`, "");
  });
  return lines.join("\n");
}

const FILES = [
  {
    name: "s86-p1-invoicing.md",
    text: transcript("P1", "chasing invoices", [
      ["How do you follow up on late invoices?", "I phone every client on Friday afternoon because email reminders get ignored. It takes about two hours and I keep a paper list next to the till so I remember who promised what."],
      ["What happens when a client pays late?", "Payroll lands on Thursday and client money arrives on Friday, so for one night the account is short. I move money from savings and hope the bank does not charge a fee for the overdraft."],
      ["Which tool do you use for reminders?", "A spreadsheet with conditional colours. Red means more than thirty days late. I tried the reminder feature in the accounting app, but it sent the same message to everyone and one client was offended."],
      ["What would make this easier?", "Seeing which invoices are likely to be late before they are late. If I knew on Monday, I could call on Tuesday instead of panicking on Thursday night."],
    ]),
  },
  {
    name: "s86-p2-receipts.md",
    text: transcript("P2", "receipts and the quarter close", [
      ["How do you keep receipts?", "They go into a shoebox under the counter. The thermal paper fades before the quarter closes, so by the time my accountant asks, half of them are blank strips."],
      ["Have you tried photographing them?", "I photograph the big ones with my phone, but the photos end up mixed with pictures of my kids and I cannot find them in March. A folder for each month would help, but I never remember to move them."],
      ["What does your accountant need from you?", "Totals per category and the receipts behind anything over fifty. She sends the list twice and then charges me for the extra hours it takes to chase me."],
      ["What would you change first?", "Capturing the receipt at the counter, the moment I pay, so nothing waits for the shoebox. If it read the total and the date for me, I would do it every time."],
    ]),
  },
];

async function navigateTo(page, label, viewId) {
  const nav = page.locator(`nav[aria-label="Views"] button[aria-label="${label}"]`).first();
  if (await nav.isVisible({ timeout: 3000 }).catch(() => false)) {
    await nav.click();
  } else {
    await page.evaluate((detail) => window.dispatchEvent(new CustomEvent("istara:navigate", { detail })), viewId);
  }
}

async function openHealth(page) {
  await navigateTo(page, "Memory", "memory");
  await page.locator(HEALTH_TAB).first().waitFor({ state: "visible", timeout: 15000 });
  // Re-mount the tab so it fetches fresh stats (the tab is keyed by project).
  await page.locator(KNOWLEDGE_TAB).first().click();
  await page.locator(HEALTH_TAB).first().click();
}

async function readCard(page, timeout = 20000) {
  const card = page.locator(CARD).first();
  const visible = await card.waitFor({ state: "visible", timeout }).then(() => true).catch(() => false);
  if (!visible) return { visible: false, text: "", coverage: "" };
  return {
    visible: true,
    text: await card.innerText(),
    coverage: (await page.locator(COVERAGE).first().innerText()).trim(),
  };
}

async function selectProject(page, projectName) {
  const button = page.locator('[aria-label="Projects list"] button', { hasText: projectName }).first();
  await button.waitFor({ state: "visible", timeout: 15000 });
  await button.click();
  await page.waitForTimeout(800);
}

async function axeScan(page) {
  try {
    const { default: AxeBuilder } = await import("@axe-core/playwright");
    const result = await new AxeBuilder({ page }).include("main").withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
    const blocking = result.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    return {
      passed: blocking.length === 0,
      detail: blocking.length
        ? blocking
            .map((v) => `${v.id}(${v.nodes.length}): ${v.nodes.slice(0, 8).map((n) => `${n.target.join(" ")} ${(n.any?.[0]?.message || "").slice(0, 90)}`).join(" | ")}`)
            .join("; ")
        : `0 serious/critical; ${result.violations.length} minor/moderate`,
    };
  } catch (e) {
    return { passed: false, detail: `axe unavailable: ${e.message}` };
  }
}

export async function run(ctx) {
  const checks = [];
  const ledger = createVariantLedger(id, [
    { variantId: "role=admin", expectation: "admin drives empty → upload → 100% traceable, loading/error recovery and the display matrix" },
    { variantId: "role=researcher", expectation: "researcher opens Memory → Health and sees the provenance card" },
    { variantId: "role=viewer", expectation: "viewer opens Memory → Health and sees the provenance card (read path)" },
    { variantId: "role=stranger", expectation: "unauthenticated stranger is held at the login screen" },
  ]);

  const adminOutcome = await driveAdminCell(ctx, checks);

  const provisioning = await ensureRoleAccounts(ctx);
  for (const role of ["researcher", "viewer"]) {
    await driveRoleCell(ctx, {
      ledger,
      role,
      provisioning,
      shotName: `86-role-${role}`,
      drive: async (rolePage) => driveRoleHealthCell(rolePage),
    });
  }
  await driveRoleCell(ctx, { ledger, role: "stranger", provisioning, shotName: "86-role-stranger" });

  ledger.record({
    variantId: "role=admin",
    result: adminOutcome.ok ? "pass" : "fail",
    detail: adminOutcome.detail,
    artifacts: [
      "screenshots/86-health-empty.png",
      "screenshots/86-health-traceable.png",
      "screenshots/86-health-375px.png",
      "screenshots/86-health-dark.png",
    ],
  });
  checks.push(...ledger.finalize());

  const passed = checks.filter((c) => c.passed).length;
  return { checks, passed, failed: checks.length - passed };
}

async function driveAdminCell(ctx, checks) {
  const start = checks.length;
  const projectId = await createProject(ctx, checks);
  if (!projectId) return { ok: false, detail: "no project" };
  try {
    await ctx.page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
    await selectProject(ctx.page, PROJECT_NAME);
    const steps = [checkEmptyState, uploadThroughFileChooser, checkTraceable, checkLoadingAndError, checkDegraded, checkKeyboard, checkNarrow, checkThemes];
    for (const step of steps) await step(ctx, checks, projectId);
  } catch (e) {
    checks.push({ name: "Admin journey completed without an exception", passed: false, detail: e.message });
  } finally {
    await cleanup(ctx, checks, projectId);
  }
  const failed = checks.slice(start).filter((c) => !c.passed).length;
  return { ok: failed === 0, detail: failed === 0 ? "admin provenance journey clean" : `${failed} admin-cell check(s) failed` };
}

/** SETUP (API-behind-browser): the scenario's own fresh project. */
async function createProject(ctx, checks) {
  const name = "[API-behind-browser] SETUP: create a fresh synthetic project";
  try {
    const created = await ctx.api.post("/api/projects", {
      name: PROJECT_NAME,
      description: "Scenario 86 evidence-provenance health (synthetic data)",
    });
    checks.push({ name, passed: !!created.id, detail: `id=${created.id}` });
    return created.id || null;
  } catch (e) {
    checks.push({ name, passed: false, detail: e.message });
    return null;
  }
}

/** 1. A fresh project states the empty case, with no percentage. */
async function checkEmptyState(ctx, checks) {
  await openHealth(ctx.page);
  const empty = await readCard(ctx.page);
  await ctx.screenshot("86-health-empty");
  checks.push({
    name: "Fresh project: the card states the empty case, with no percentage",
    passed: empty.visible && empty.text.includes("No source chunks yet") && empty.coverage === "—",
    detail: `coverage=${JSON.stringify(empty.coverage)} text=${empty.text.slice(0, 140)}`,
  });
}

/** 2. Upload through the Documents view's real file chooser. */
async function uploadThroughFileChooser(ctx, checks, projectId) {
  const { page } = ctx;
  await navigateTo(page, "Documents", "documents");
  const uploadButton = page.locator('button[aria-label="Upload research files"]').first();
  await uploadButton.waitFor({ state: "visible", timeout: 15000 });
  const uploads = [];
  const onResponse = (r) => {
    if (r.url().includes(`/api/files/upload/${projectId}`) && r.request().method() === "POST") uploads.push(r.status());
  };
  page.on("response", onResponse);
  const [chooser] = await Promise.all([page.waitForEvent("filechooser", { timeout: 10000 }), uploadButton.click()]);
  await chooser.setFiles(FILES.map((f) => ({ name: f.name, mimeType: "text/markdown", buffer: Buffer.from(f.text, "utf-8") })));
  const toast = await page.getByText("Files Uploaded", { exact: true }).first()
    .waitFor({ state: "visible", timeout: 90000 }).then(() => true).catch(() => false);
  page.off("response", onResponse);
  checks.push({
    name: "Upload two synthetic transcripts through the file chooser",
    passed: toast && uploads.length === FILES.length && uploads.every((s) => s >= 200 && s < 300),
    detail: `toast=${toast} statuses=${JSON.stringify(uploads)}`,
  });
}

/** 3. The card reports full provenance, and agrees with the API it renders. */
async function checkTraceable(ctx, checks, projectId) {
  const { page } = ctx;
  let traced = { visible: false, text: "", coverage: "" };
  const deadline = Date.now() + 60000;
  while (Date.now() < deadline) {
    await openHealth(page);
    traced = await readCard(page);
    if (traced.coverage !== "—" && traced.coverage !== "") break;
    await page.waitForTimeout(2000);
  }
  await ctx.screenshot("86-health-traceable");
  checks.push({
    name: "After upload the card reads 100% and 'All traceable'",
    passed: traced.coverage === "100%" && traced.text.includes("All traceable"),
    detail: `coverage=${JSON.stringify(traced.coverage)} text=${traced.text.slice(0, 160)}`,
  });
  const stats = await ctx.api.get(`/api/memory/${projectId}/stats`).catch((e) => ({ error: e.message }));
  const prov = stats.provenance || {};
  checks.push({
    name: "[API-behind-browser] the stats the card renders agree: every source chunk has an evidence unit",
    passed: prov.source_chunks > 0 && prov.with_evidence_unit === prov.source_chunks && prov.status === "ok",
    detail: JSON.stringify(prov).slice(0, 200),
  });
  checks.push({
    name: "The card's count line matches the API",
    passed: traced.text.includes(`${prov.with_evidence_unit} of ${prov.source_chunks} source chunks`),
    detail: traced.text.slice(0, 200),
  });
  // One ingestion writer per upload: the Health tab's Vector Chunks and Keyword Chunks cards agree.
  // The watcher used to index uploads too, racing the route and duplicating every vector.
  const counts = await page.evaluate(() => {
    const read = (label) => {
      const el = [...document.querySelectorAll("p")].find((n) => n.textContent.trim() === label);
      return el ? Number(el.previousElementSibling?.textContent.trim()) : NaN;
    };
    return { vector: read("Vector Chunks"), keyword: read("Keyword Chunks") };
  });
  checks.push({
    name: "After upload the Vector Chunks and Keyword Chunks cards agree (indexed once)",
    passed: counts.vector > 0 && counts.vector === counts.keyword,
    detail: `vector=${counts.vector} keyword=${counts.keyword}`,
  });
}

async function remountHealth(page) {
  await page.locator(KNOWLEDGE_TAB).first().click();
  await page.locator(HEALTH_TAB).first().click();
}

/** 4-5. Loading → content, then error → Retry recovers. */
async function checkLoadingAndError(ctx, checks, projectId) {
  const { page } = ctx;
  const statsGlob = `**/api/memory/${projectId}/stats`;
  await page.route(statsGlob, async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 2500));
    await route.continue();
  });
  await remountHealth(page);
  const loadingShown = await page.getByText("Loading health data...").first()
    .waitFor({ state: "visible", timeout: 2000 }).then(() => true).catch(() => false);
  const afterLoading = await readCard(page);
  await page.unroute(statsGlob);
  checks.push({
    name: "Loading state renders, then the card replaces it",
    passed: loadingShown && afterLoading.visible,
    detail: `loading=${loadingShown} card=${afterLoading.visible}`,
  });

  await page.route(statsGlob, (route) => route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "Scenario86 injected failure" }) }), { times: 1 });
  await remountHealth(page);
  const retry = page.locator('button[aria-label="Retry loading health data"]').first();
  const errorShown = await retry.waitFor({ state: "visible", timeout: 10000 }).then(() => true).catch(() => false);
  if (errorShown) await retry.click();
  const recovered = await readCard(page);
  await page.unroute(statsGlob).catch(() => {});
  checks.push({
    name: "Error state offers Retry, and Retry recovers the card",
    passed: errorShown && recovered.visible && recovered.coverage === "100%",
    detail: `error=${errorShown} recovered=${recovered.visible} coverage=${recovered.coverage}`,
  });
}

/** 6. Degraded branch (FIXTURE: the real response with provenance rewritten). */
async function checkDegraded(ctx, checks, projectId) {
  const { page } = ctx;
  const statsGlob = `**/api/memory/${projectId}/stats`;
  await page.route(statsGlob, async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    const total = body.provenance?.source_chunks || 2;
    body.provenance = { ...body.provenance, with_evidence_unit: total - 1, coverage: 0.5, status: "degraded", legacy_derived_rows: 3 };
    await route.fulfill({ response, json: body });
  }, { times: 1 });
  await remountHealth(page);
  const degraded = await readCard(page);
  await page.unroute(statsGlob).catch(() => {});
  const text = degraded.text;
  checks.push({
    name: "[fixture] a degraded payload renders 'Needs re-index', the remedy and the legacy-row note",
    passed: ["Needs re-index", "Reprocess the files listed under Sources", "3 older rows"].every((t) => text.includes(t)) && degraded.coverage === "50%",
    detail: text.slice(0, 220),
  });
}

/** 7. Keyboard: Tab reaches the Health tab with visible focus; Enter opens it. */
async function checkKeyboard(ctx, checks) {
  const { page } = ctx;
  await page.locator(KNOWLEDGE_TAB).first().click();
  await page.locator("body").click({ position: { x: 5, y: 5 } }).catch(() => {});
  await keyboardFocusCheck(page, checks, { name: "Memory Health tab", targetSelector: HEALTH_TAB, maxTabs: 120 });
  await page.keyboard.press("Enter");
  const byKeyboard = await readCard(page, 10000);
  checks.push({ name: "Enter on the focused Health tab opens it", passed: byKeyboard.visible, detail: `card=${byKeyboard.visible}` });
}

/** 8. 375px: the Health tab is on screen and usable, and the page does not scroll sideways. */
async function checkNarrow(ctx, checks) {
  const { page } = ctx;
  await reflow375Check(page, checks, {
    name: "Memory Health",
    onNarrow: async () => {
      await navigateTo(page, "Memory", "memory");
      const tab = page.locator(HEALTH_TAB).first();
      await tab.waitFor({ state: "attached", timeout: 10000 }).catch(() => {});
      const box = await tab.boundingBox().catch(() => null);
      const width = page.viewportSize()?.width || 375;
      const inView = !!box && box.x >= 0 && box.x + box.width <= width + 1;
      if (inView) await tab.click();
      const opened = inView && (await readCard(page, 10000)).visible;
      checks.push({
        name: "375px: the Health tab is fully on screen and opens the card",
        passed: opened,
        detail: box ? `tab x=${Math.round(box.x)}..${Math.round(box.x + box.width)} viewport=${width} opened=${opened}` : "tab not rendered",
      });
      await ctx.screenshot("86-health-375px");
    },
  });
}

/** 9. Light and dark themes, axe in both. */
async function checkThemes(ctx, checks) {
  const { page } = ctx;
  await openHealth(page);
  await readCard(page);
  checks.push({ name: "axe-core WCAG 2.1 AA (light): no serious or critical violation on the Health tab", ...(await axeScan(page)) });
  const toDark = page.locator('button[aria-label="Switch to dark mode"]').first();
  const wasLight = await toDark.isVisible({ timeout: 3000 }).catch(() => false);
  if (wasLight) await toDark.click();
  await page.waitForTimeout(600); // let the colour transition settle before evidence is captured
  const isDark = await page.evaluate(() => document.documentElement.classList.contains("dark"));
  const darkCard = await readCard(page);
  const cardBg = await page.locator(CARD).first().evaluate((el) => getComputedStyle(el).backgroundColor).catch(() => "");
  await ctx.screenshot("86-health-dark");
  checks.push({
    name: "Dark theme renders the card",
    passed: isDark && darkCard.visible && !/rgb\(255, 255, 255\)/.test(cardBg),
    detail: `html.dark=${isDark} cardBg=${cardBg}`,
  });
  checks.push({ name: "axe-core WCAG 2.1 AA (dark): no serious or critical violation on the Health tab", ...(await axeScan(page)) });
  if (wasLight) await page.locator('button[aria-label="Switch to light mode"]').first().click().catch(() => {});
}

/** CLEANUP: return to the shared simulation project, then delete this scenario's own. */
async function cleanup(ctx, checks, projectId) {
  const { page } = ctx;
  await page.setViewportSize({ width: 1280, height: 800 }).catch(() => {});
  try {
    const shared = await ctx.api.get(`/api/projects/${ctx.projectId}`);
    await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
    await selectProject(page, shared.name);
  } catch {}
  const res = await fetch(`${getApiBase()}/api/projects/${projectId}`, { method: "DELETE", headers: authHeaders() }).catch((e) => ({ ok: false, status: e.message }));
  checks.push({ name: "[API-behind-browser] CLEANUP: delete the scenario's synthetic project", passed: !!res.ok, detail: `status=${res.status}` });
}

/** Researcher/viewer cells: the card renders on the shared simulation project for the role. */
async function driveRoleHealthCell(rolePage) {
  try {
    await navigateTo(rolePage, "Memory", "memory");
    const tab = rolePage.locator(HEALTH_TAB).first();
    await tab.waitFor({ state: "visible", timeout: 15000 });
    await tab.click();
    const card = await readCard(rolePage, 20000);
    return {
      ok: card.visible && /Evidence Provenance/i.test(await rolePage.locator("#provenance-heading").innerText().catch(() => "")),
      detail: card.visible ? `card renders for the role: coverage=${card.coverage}` : "provenance card not visible for the role",
    };
  } catch (e) {
    return { ok: false, detail: e.message };
  }
}
