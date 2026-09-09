import { chromium } from "playwright";
import { writeFileSync, mkdirSync } from "fs";

async function run() {
  console.log("=== PHASE 10 PROOF: collapse + chat picker ===");
  const outDir = "/work/tests/simulation/.results/phase10_screenshots";
  mkdirSync(outDir, { recursive: true });
  const report = { startedAt: new Date().toISOString(), checks: {}, errors: [], netFails: [] };
  const BACKEND = process.env.ISTARA_API_URL || "http://127.0.0.1:8000";
  const FRONT = process.env.ISTARA_FRONTEND_URL || "http://127.0.0.1:3000";

  const lr = await fetch(`${BACKEND}/api/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username: "admin", password: "admin" }) });
  const { token, user } = await lr.json();
  const PROJECT = "proj-st150-pi-dd6bf277";

  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox", "--disable-gpu"] });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  await ctx.addInitScript(({ t, u }) => {
    try {
      localStorage.setItem("istara_token", t);
      localStorage.setItem("istara_auth_user_id", u);
      localStorage.setItem(`istara_tour_completed_${u}`, "true");
      localStorage.setItem("istara_tour_completed_admin", "true");
      localStorage.setItem("istara_tour_state", JSON.stringify({ active: false, isOnboarding: false, step: 16, hasExistingProjects: true }));
      localStorage.setItem("istara-active-project", PROJECT);
    } catch {}
  }, { t: token, u: user.id });
  const page = await ctx.newPage();
  page.on("console", (m) => { if (m.type() === "error" && !/ERR_CONNECTION_REFUSED|1234|11434|8080|30000/.test(m.text())) report.errors.push(m.text().slice(0, 200)); });
  page.on("pageerror", (e) => report.errors.push("pageerror:" + String(e).slice(0, 200)));
  page.on("response", (r) => { if (r.status() >= 500) report.netFails.push(`${r.status()} ${r.url().slice(0, 120)}`); });
  const goto = async (view) => {
    await page.goto(FRONT, { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1200);
    await page.evaluate((v) => window.dispatchEvent(new CustomEvent("istara:navigate", { detail: v })), view);
    await page.waitForTimeout(2500);
  };

  // --- 1. Settings collapse ---
  await goto("settings");
  const labels = await page.locator("button:has-text('Click to see')").allTextContents().catch(() => []);
  report.checks.collapseButtons = labels.map((s) => s.trim());
  console.log(`collapse toggles: ${JSON.stringify(report.checks.collapseButtons)}`);
  for (let i = 0; i < labels.length; i++) {
    const btn = page.locator("button:has-text('Click to see')").first();
    const label = ((await btn.textContent().catch(() => "")) || "").trim();
    const expandedBefore = await btn.getAttribute("aria-expanded").catch(() => null);
    await btn.scrollIntoViewIfNeeded().catch(() => {});
    await btn.click().catch(() => {});
    await page.waitForTimeout(500);
    const lessCount = await page.locator("button:has-text('Show fewer')").count();
    console.log(`toggle: ${label} aria-expanded was ${expandedBefore}, showFewer=${lessCount}`);
    report.checks[`toggle:${label}`] = { expandedBefore, lessCount };
    const less = page.locator("button:has-text('Show fewer')").first();
    if (await less.isVisible().catch(() => false)) { await less.click().catch(() => {}); await page.waitForTimeout(400); }
    const backCount = await page.locator("button:has-text('Click to see')").count();
    report.checks[`toggle:${label}`].restored = backCount;
  }
  await page.screenshot({ path: `${outDir}/settings_collapse.png` });

  // --- 2. Chat picker: previously-invisible ready model now listed & enabled ---
  await goto("chat");
  const pickerBtn = page.locator("button[aria-haspopup='listbox']").nth(1);
  report.checks.pickerButton = await pickerBtn.isVisible().catch(() => false);
  await pickerBtn.click().catch(() => {});
  await page.waitForTimeout(800);
  report.checks.listbox = await page.locator("[role='listbox']").first().isVisible().catch(() => false);
  const combo = page.locator("[role='combobox']").first();
  for (const q of ["glm-5.3-flash", "gpt-5.6-luna", "custom"]) {
    await combo.fill(q).catch(() => {});
    await page.waitForTimeout(500);
    const options = page.locator("[role='option']");
    const count = await options.count().catch(() => 0);
    let enabledCount = 0, badgeCount = 0, firstEnabled = null, badge = false;
    for (let i = 0; i < count; i++) {
      const opt = options.nth(i);
      if (await opt.isEnabled().catch(() => false)) {
        enabledCount++;
        if (firstEnabled === null) firstEnabled = true;
      } else if (firstEnabled === null) firstEnabled = false;
      if ((await opt.locator("text=Configured").count().catch(() => 0)) > 0) {
        badgeCount++;
        badge = badge || (await opt.isEnabled().catch(() => false));
      }
    }
    console.log(`search ${q}: options=${count} enabled=${enabledCount} badges=${badgeCount} firstEnabled=${firstEnabled} badgeEnabled=${badge}`);
    report.checks[`search:${q}`] = { count, enabledCount, badgeCount, firstEnabled, badge };
  }
  await page.screenshot({ path: `${outDir}/chat_picker.png` });

  report.finishedAt = new Date().toISOString();
  writeFileSync("/work/tests/simulation/.results/phase10_proof_report.json", JSON.stringify(report, null, 2));
  console.log("ERRORS:", JSON.stringify(report.errors.slice(0, 8)));
  console.log("NETFAILS:", JSON.stringify(report.netFails.slice(0, 8)));
  await browser.close();
}
run().catch((e) => { console.error("FATAL", e); process.exit(1); });
