import { chromium } from "playwright";
import { writeFileSync, mkdirSync } from "fs";

async function run() {
  console.log("=== PHASE 8 DEPTH: QUALITY / ENSEMBLE / SETTINGS / HISTORY ===");
  const outDir = "/work/tests/simulation/.results/phase8_screenshots";
  mkdirSync(outDir, { recursive: true });
  const report = { startedAt: new Date().toISOString(), surfaces: {} };

  const BACKEND_URL = process.env.ISTARA_API_URL || "http://127.0.0.1:8000";
  const FRONTEND_URL = process.env.ISTARA_FRONTEND_URL || "http://127.0.0.1:3000";

  const loginRes = await fetch(`${BACKEND_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: "admin", password: "admin" }),
  });
  if (!loginRes.ok) throw new Error(`Login failed: ${loginRes.status}`);
  const { token, user } = await loginRes.json();
  console.log(`Authenticated: ${user.id}`);

  const projRes = await fetch(`${BACKEND_URL}/api/projects`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const projs = await projRes.json();
  const target = projs.find((p) => p.id === "proj-st150-pi-dd6bf277") || projs[0];
  const PROJECT_ID = target.id;
  console.log(`Project: ${PROJECT_ID} (${target.name})`);

  // API cross-checks (DB vs API agreement for slice 7)
  const apiChecks = {};
  for (const [name, url] of [
    ["metrics", `${BACKEND_URL}/api/metrics/${PROJECT_ID}`],
    ["validation", `${BACKEND_URL}/api/metrics/${PROJECT_ID}/validation`],
    ["intelligence", `${BACKEND_URL}/api/metrics/${PROJECT_ID}/model-intelligence?limit=50`],
    ["auditLogs", `${BACKEND_URL}/api/audit/logs?project_id=${PROJECT_ID}&limit=5`],
    ["auditSpans", `${BACKEND_URL}/api/audit/spans?project_id=${PROJECT_ID}&limit=5`],
  ]) {
    try {
      const r = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      const j = await r.json().catch(() => null);
      apiChecks[name] = { status: r.status, ok: r.ok, keys: j ? Object.keys(j) : [] };
      if (name === "metrics" && j?.evidence_chain) {
        apiChecks.metrics.evidence_chain = j.evidence_chain;
      }
      if (name === "intelligence" && j) {
        apiChecks.intelligence.status_field = j.status || "(missing)";
        apiChecks.intelligence.tool_calls = j.tool_summary?.total_calls ?? null;
        apiChecks.intelligence.audit_len = (j.tool_audit_trail || []).length;
      }
      console.log(`API ${name}: ${r.status} keys=${apiChecks[name].keys.join(",")}`);
    } catch (e) {
      apiChecks[name] = { error: String(e) };
      console.log(`API ${name} ERROR: ${e}`);
    }
  }
  report.apiChecks = apiChecks;

  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox", "--disable-gpu"] });

  async function newTrackedPage(viewport, tag) {
    const context = await browser.newContext({ viewport });
    await context.addInitScript(
      ({ tok, uId, pId }) => {
        try {
          localStorage.setItem("istara_token", tok);
          localStorage.setItem("istara_auth_user_id", uId);
          localStorage.setItem(`istara_tour_completed_${uId}`, "true");
          localStorage.setItem("istara_tour_completed_admin", "true");
          localStorage.setItem("istara_tour_completed_anonymous", "true");
          localStorage.setItem("istara_tour_state", JSON.stringify({ active: false, isOnboarding: false, step: 16, hasExistingProjects: true }));
          localStorage.setItem("istara-active-project", pId);
          localStorage.setItem("istara_active_view", "quality");
        } catch {}
      },
      { tok: token, uId: user.id, pId: PROJECT_ID }
    );
    const page = await context.newPage();
    const errors = [];
    const netFails = [];
    page.on("console", (m) => { if (m.type() === "error") errors.push(m.text().slice(0, 300)); });
    page.on("pageerror", (e) => errors.push(`pageerror: ${String(e).slice(0, 300)}`));
    page.on("requestfailed", (r) => netFails.push(`${r.method()} ${r.url().slice(0, 160)} :: ${r.failure()?.errorText}`));
    page.on("response", (r) => { if (r.status() >= 400) netFails.push(`${r.status()} ${r.url().slice(0, 160)}`); });
    return { page, context, errors, netFails, tag };
  }

  async function gotoView(page, view) {
    await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1200);
    await page.evaluate((v) => window.dispatchEvent(new CustomEvent("istara:navigate", { detail: v })), view);
    await page.waitForTimeout(2200);
  }

  async function keyboardSweep(page, label) {
    // Tab through first 12 focusables, report focus visibility
    let visibleFocus = 0;
    for (let i = 0; i < 12; i++) {
      await page.keyboard.press("Tab").catch(() => {});
      await page.waitForTimeout(80);
      const f = await page.evaluate(() => {
        const el = document.activeElement;
        if (!el || el === document.body) return null;
        const cs = getComputedStyle(el);
        const r = el.getBoundingClientRect();
        return { tag: el.tagName, outline: cs.outlineStyle, boxShadow: cs.boxShadow.slice(0, 40), w: Math.round(r.width), h: Math.round(r.height) };
      }).catch(() => null);
      if (f && f.w >= 24 && f.h >= 24) visibleFocus++;
    }
    console.log(`${label} keyboard sweep: focusable-with-target-size=${visibleFocus}/12`);
    await page.keyboard.press("Escape").catch(() => {});
    return visibleFocus;
  }

  const surfaces = ["quality", "ensemble", "project-settings", "history"];
  for (const view of surfaces) {
    const s = { errors: [], netFails: [], shots: [], checks: {} };
    try {
      const { page, context, errors, netFails } = await newTrackedPage({ width: 1280, height: 900 }, view);
      await gotoView(page, view);

      if (view === "quality") {
        s.checks.dashboard = await page.locator("text=Quality Dashboard").first().isVisible().catch(() => false);
        // Filter/search the audit table if present
        const search = page.locator("input[placeholder*='Search by tool']").first();
        if (await search.isVisible().catch(() => false)) {
          await search.fill("search");
          await page.waitForTimeout(400);
          await search.fill("");
          s.checks.auditSearch = true;
        }
        const firstRow = page.locator("table tbody tr").first();
        if (await firstRow.isVisible().catch(() => false)) {
          await firstRow.click().catch(() => {});
          await page.waitForTimeout(400);
          s.checks.rowExpand = await page.locator("text=reasoning_bank").first().isVisible().catch(() => false);
        }
        s.checks.keyboard = await keyboardSweep(page, "quality");
      }
      if (view === "ensemble") {
        s.checks.intel = await page.locator("text=Model Intelligence").first().isVisible().catch(() => false);
        s.checks.adaptive = await page.locator("text=Adaptive Method Learning").first().isVisible().catch(() => false);
        s.checks.keyboard = await keyboardSweep(page, "ensemble");
      }
      if (view === "project-settings") {
        s.checks.metrics = await page.locator("text=Total Findings").first().isVisible().catch(() => false);
        s.checks.spine = await page.locator("text=Research Spine Evidence-Chain Health").first().isVisible().catch(() => false);
        s.checks.errorBanner = await page.locator("[role='alert']:has-text('Could not load')").first().isVisible().catch(() => false);
        s.checks.keyboard = await keyboardSweep(page, "project-settings");
      }
      if (view === "history") {
        for (const tab of ["API Audit Logs", "AI Agent Traces", "Git Commits"]) {
          const b = page.locator(`button:has-text('${tab}')`).first();
          if (await b.isVisible().catch(() => false)) {
            await b.click().catch(() => {});
            await page.waitForTimeout(800);
            s.checks[`tab:${tab}`] = true;
          }
        }
        const hsearch = page.locator("input[type='text']").first();
        if (await hsearch.isVisible().catch(() => false)) {
          await hsearch.fill("tool_call").catch(() => {});
          await page.waitForTimeout(400);
          await hsearch.fill("").catch(() => {});
          s.checks.search = true;
        }
        s.checks.errorBanner = await page.locator("[role='alert']:has-text('Could not load')").first().isVisible().catch(() => false);
        s.checks.keyboard = await keyboardSweep(page, "history");
      }

      await page.screenshot({ path: `${outDir}/${view}_1280_light.png` });
      s.shots.push(`${view}_1280_light.png`);
      await page.evaluate(() => document.documentElement.classList.add("dark"));
      await page.waitForTimeout(500);
      await page.screenshot({ path: `${outDir}/${view}_1280_dark.png` });
      s.shots.push(`${view}_1280_dark.png`);
      await page.evaluate(() => document.documentElement.classList.remove("dark"));

      // Narrow viewport reflow check on the same view
      await page.setViewportSize({ width: 375, height: 812 });
      await page.waitForTimeout(600);
      const noHScroll = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1).catch(() => null);
      s.checks.reflow375 = noHScroll;
      await page.screenshot({ path: `${outDir}/${view}_375_light.png` });
      s.shots.push(`${view}_375_light.png`);

      s.errors = errors.slice(0, 10);
      s.netFails = netFails.slice(0, 10);
      console.log(`${view}: checks=${JSON.stringify(s.checks)} errors=${errors.length} netFails=${netFails.length}`);
      await context.close();
    } catch (e) {
      s.fatal = String(e).slice(0, 400);
      console.log(`${view} FATAL: ${s.fatal}`);
    }
    report.surfaces[view] = s;
  }

  // 320px spot check on history (contract minimum)
  try {
    const { page, context, errors, netFails } = await newTrackedPage({ width: 320, height: 700 }, "history320");
    await gotoView(page, "history");
    const ok = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1).catch(() => null);
    report.surfaces.history320 = { reflow320: ok, errors: errors.slice(0, 5), netFails: netFails.slice(0, 5) };
    await page.screenshot({ path: `${outDir}/history_320_light.png` });
    await context.close();
  } catch (e) {
    report.surfaces.history320 = { fatal: String(e).slice(0, 300) };
  }

  report.finishedAt = new Date().toISOString();
  writeFileSync("/work/tests/simulation/.results/phase8_depth_report.json", JSON.stringify(report, null, 2));
  console.log("=== PHASE 8 DEPTH DONE ===");
  console.log(JSON.stringify({ api: report.apiChecks, views: Object.fromEntries(Object.entries(report.surfaces).map(([k, v]) => [k, v.checks || v])) }, null, 2));
  await browser.close();
}

run().catch((e) => { console.error("FATAL", e); process.exit(1); });
