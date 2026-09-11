import { chromium } from "playwright";
import { writeFileSync, mkdirSync } from "fs";

const VIEWS = [
  ["chat", ["Ask about", "Chat"]],
  ["findings", ["Evidence", "Findings"]],
  ["laws", ["Laws of UX Compliance", "Compliance"]],
  ["tasks", ["Backlog", "In Progress"]],
  ["interviews", ["All", "Transcripts"]],
  ["documents", ["Upload", "Documents"]],
  ["context", ["Project Context", "Guardrails"]],
  ["skills", ["Catalog", "Skills"]],
  ["agents", ["System Agents", "Agents"]],
  ["memory", ["Knowledge", "Memory"]],
  ["interfaces", ["Design Chat", "Interfaces"]],
  ["integrations", ["Overview", "Integrations"]],
  ["loops", ["Schedules", "Loops"]],
  ["settings", ["System Status", "Settings"]],
  ["admin", ["Admin", "Users"]],
  ["autoresearch", ["Experiments", "Autoresearch"]],
  ["backup", ["Create Full Backup", "Backup"]],
  ["meta-hyperagent", ["Meta-Hyperagent", "Meta"]],
  ["compute", ["Compute Pool", "Nodes"]],
  ["ensemble", ["Model Intelligence", "Ensemble"]],
  ["quality", ["Quality Dashboard", "Methodology"]],
  ["project-settings", ["Research Spine Evidence-Chain Health", "Total Findings"]],
  ["history", ["Activity & Audit Dashboard", "Git Commits"]],
  ["notifications", ["Notifications", "Preferences"]],
];

async function run() {
  console.log("=== PHASE 9 BROAD 24-VIEW SWEEP ===");
  const outDir = "/work/tests/simulation/.results/phase9_screenshots";
  mkdirSync(outDir, { recursive: true });
  const report = { startedAt: new Date().toISOString(), views: {} };
  const BACKEND_URL = process.env.ISTARA_API_URL || "http://127.0.0.1:8000";
  const FRONTEND_URL = process.env.ISTARA_FRONTEND_URL || "http://127.0.0.1:3000";

  const loginRes = await fetch(`${BACKEND_URL}/api/auth/login`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: "admin", password: "admin" }),
  });
  if (!loginRes.ok) throw new Error(`Login failed: ${loginRes.status}`);
  const { token, user } = await loginRes.json();
  const projRes = await fetch(`${BACKEND_URL}/api/projects`, { headers: { Authorization: `Bearer ${token}` } });
  const projs = await projRes.json();
  const target = projs.find((p) => p.id === "proj-st150-pi-dd6bf277") || projs[0];
  console.log(`Project: ${target.id}`);

  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox", "--disable-gpu"] });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
  await context.addInitScript(({ tok, uId, pId }) => {
    try {
      localStorage.setItem("istara_token", tok);
      localStorage.setItem("istara_auth_user_id", uId);
      localStorage.setItem(`istara_tour_completed_${uId}`, "true");
      localStorage.setItem("istara_tour_completed_admin", "true");
      localStorage.setItem("istara_tour_state", JSON.stringify({ active: false, isOnboarding: false, step: 16, hasExistingProjects: true }));
      localStorage.setItem("istara-active-project", pId);
    } catch {}
  }, { tok: token, uId: user.id, pId: target.id });
  const page = await context.newPage();
  const errors = [];
  const netFails = [];
  page.on("console", (m) => { if (m.type() === "error" && !/ERR_CONNECTION_REFUSED|localhost:1234|11434|8080|30000/.test(m.text())) errors.push(m.text().slice(0, 200)); });
  page.on("pageerror", (e) => errors.push(`pageerror:${String(e).slice(0, 200)}`));
  page.on("requestfailed", (r) => { const u = r.url(); if (!/localhost:1234|127.0.0.1:1234|localhost:11434|127.0.0.1:11434|localhost:8080|127.0.0.1:8080|localhost:30000/.test(u)) netFails.push(`${r.method()} ${u.slice(0, 140)}`); });
  page.on("response", (r) => { if (r.status() >= 500) netFails.push(`${r.status()} ${r.url().slice(0, 140)}`); });

  await page.goto(FRONTEND_URL, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);

  for (const [view, markers] of VIEWS) {
    const v = { checks: {} };
    try {
      await page.evaluate((x) => window.dispatchEvent(new CustomEvent("istara:navigate", { detail: x })), view);
      await page.waitForTimeout(2000);
      let found = false;
      for (const m of markers) {
        if (await page.locator(`text=${m}`).first().isVisible().catch(() => false)) { found = true; v.marker = m; break; }
      }
      v.checks.render = found;
      // keyboard: 6 tabs
      let kf = 0;
      for (let i = 0; i < 6; i++) {
        await page.keyboard.press("Tab").catch(() => {});
        await page.waitForTimeout(60);
        const f = await page.evaluate(() => {
          const el = document.activeElement;
          if (!el || el === document.body) return null;
          const r = el.getBoundingClientRect();
          return { w: Math.round(r.width), h: Math.round(r.height) };
        }).catch(() => null);
        if (f && f.w >= 24 && f.h >= 24) kf++;
      }
      v.checks.keyboard = kf;
      await page.keyboard.press("Escape").catch(() => {});
      await page.screenshot({ path: `${outDir}/${view}_1280_light.png` });
      await page.evaluate(() => document.documentElement.classList.add("dark"));
      await page.waitForTimeout(400);
      v.checks.dark = await page.locator(`text=${v.marker || markers[0]}`).first().isVisible().catch(() => false);
      await page.screenshot({ path: `${outDir}/${view}_1280_dark.png` });
      await page.evaluate(() => document.documentElement.classList.remove("dark"));
      await page.setViewportSize({ width: 375, height: 812 });
      await page.waitForTimeout(500);
      v.checks.reflow375 = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1).catch(() => null);
      await page.screenshot({ path: `${outDir}/${view}_375_light.png` });
      await page.setViewportSize({ width: 1280, height: 900 });
      await page.waitForTimeout(400);
      console.log(`${view}: render=${found} kb=${kf} dark=${v.checks.dark} reflow=${v.checks.reflow375}`);
    } catch (e) {
      v.fatal = String(e).slice(0, 300);
      console.log(`${view} FATAL: ${v.fatal}`);
    }
    report.views[view] = v;
  }

  // 320 + 414 + 768 spot checks on chat (representative)
  for (const w of [320, 414, 768]) {
    await page.evaluate(() => window.dispatchEvent(new CustomEvent("istara:navigate", { detail: "chat" })));
    await page.waitForTimeout(1200);
    await page.setViewportSize({ width: w, height: 800 });
    await page.waitForTimeout(500);
    const ok = await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1).catch(() => null);
    report.views[`chat_${w}`] = { reflow: ok };
    await page.screenshot({ path: `${outDir}/chat_${w}_light.png` });
  }
  await page.setViewportSize({ width: 1280, height: 900 });

  report.globalErrors = errors.slice(0, 20);
  report.globalNetFails = netFails.slice(0, 20);
  report.finishedAt = new Date().toISOString();
  writeFileSync("/work/tests/simulation/.results/phase9_broad_report.json", JSON.stringify(report, null, 2));
  const failed = Object.entries(report.views).filter(([k, v]) => v.checks && v.checks.render === false).map(([k]) => k);
  console.log(`=== SWEEP DONE: ${VIEWS.length} views, render-fail=${JSON.stringify(failed)}, console-errors=${errors.length}, netFails=${netFails.length} ===`);
  for (const err of errors.slice(0, 10)) console.log(`  console-error: ${err}`);
  await browser.close();
}

run().catch((e) => { console.error("FATAL", e); process.exit(1); });
