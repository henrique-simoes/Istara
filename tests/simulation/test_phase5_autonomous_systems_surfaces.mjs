import { chromium } from "playwright";
import { mkdirSync } from "fs";

async function run() {
  console.log("=== STARTING PHASE 5 AUTONOMOUS SYSTEMS & SELF-EVOLUTION SURFACES VERIFICATION ===");
  const outDir = "/work/tests/simulation/.results/phase5_screenshots";
  mkdirSync(outDir, { recursive: true });

  const BACKEND_URL = process.env.ISTARA_API_URL || "http://127.0.0.1:8000";
  const FRONTEND_URL = process.env.ISTARA_FRONTEND_URL || "http://127.0.0.1:3000";

  // 1. Authenticate via backend API
  const loginRes = await fetch(`${BACKEND_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: "admin", password: "admin" }),
  });
  if (!loginRes.ok) throw new Error(`Login failed: ${loginRes.status}`);
  const { token, user } = await loginRes.json();
  console.log(`Authenticated as admin: ${user.id}`);

  // 2. Locate target project
  const projRes = await fetch(`${BACKEND_URL}/api/projects`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const projs = await projRes.json();
  const targetProj = projs.find((p) => p.id === "proj-st150-pi-dd6bf277") || projs[0];
  const PROJECT_ID = targetProj.id;
  console.log(`Using Project: ${PROJECT_ID} (${targetProj.name})`);

  // 3. Launch browser with initScript for auth and state
  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
  });

  await context.addInitScript(
    ({ tok, uId, pId, pName }) => {
      try {
        localStorage.setItem("istara_token", tok);
        localStorage.setItem("istara_auth_user_id", uId);
        localStorage.setItem(`istara_tour_completed_${uId}`, "true");
        localStorage.setItem("istara_tour_completed_admin", "true");
        localStorage.setItem("istara_tour_completed_anonymous", "true");
        localStorage.setItem(
          "istara_tour_state",
          JSON.stringify({ active: false, isOnboarding: false, step: 16, hasExistingProjects: true })
        );
        localStorage.setItem(
          "istara_project_storage",
          JSON.stringify({
            state: {
              activeProjectId: pId,
              projects: [{ id: pId, name: pName }],
            },
            version: 0,
          })
        );
        localStorage.setItem("istara-active-project", pId);
        localStorage.setItem("istara_active_view", "loops");
      } catch (e) {}
    },
    { tok: token, uId: user.id, pId: PROJECT_ID, pName: targetProj.name }
  );

  const page = await context.newPage();
  page.on("console", (msg) => {
    if (msg.type() === "error") console.log(`[BROWSER ERROR] ${msg.text()}`);
  });

  const setTheme = async (dark) => {
    await page.evaluate((isDark) => {
      if (isDark) {
        document.documentElement.classList.add("dark");
      } else {
        document.documentElement.classList.remove("dark");
      }
    }, dark);
    await page.waitForTimeout(500);
  };

  const navigateToView = async (viewId, labelText) => {
    console.log(`Navigating to view: ${viewId} (${labelText})...`);
    await page.evaluate((vId) => {
      localStorage.setItem("istara_active_view", vId);
      window.dispatchEvent(new Event("storage"));
    }, viewId);

    const navBtn = page.locator(`button:has-text("${labelText}"), a:has-text("${labelText}")`).first();
    if (await navBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
      await navBtn.click();
    } else {
      // Direct store update if sidebar item is behind more menu
      await page.evaluate(() => {
        const store = window.__ZUSTAND_STORE__ || null;
      });
      await page.goto(`${FRONTEND_URL}/`, { waitUntil: "networkidle" });
    }
    await page.waitForTimeout(1500);
  };

  // ═════════════════════════════════════════════════════════════
  // SURFACE 1: LOOPS VIEW
  // ═════════════════════════════════════════════════════════════
  console.log("--- Surface 1: Loops View ---");
  await page.goto(`${FRONTEND_URL}/`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  // Ensure on loops view
  const loopsNav = page.locator('button:has-text("Loops")').first();
  if (await loopsNav.isVisible({ timeout: 2000 }).catch(() => false)) {
    await loopsNav.click();
    await page.waitForTimeout(1200);
  }

  // 1A. Overview Tab
  const overviewTabBtn = page.locator('button:has-text("Overview")').first();
  if (await overviewTabBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
    await overviewTabBtn.click();
    await page.waitForTimeout(800);
  }

  await setTheme(false);
  await page.screenshot({ path: `${outDir}/01_loops_overview_light.png`, fullPage: false });
  console.log("Captured 01_loops_overview_light.png");

  await setTheme(true);
  await page.screenshot({ path: `${outDir}/01_loops_overview_dark.png`, fullPage: false });
  console.log("Captured 01_loops_overview_dark.png");

  // 1B. Custom Loops Tab & Form Panel
  console.log("Testing Custom Loops tab...");
  const customTabBtn = page.locator('button:has-text("Custom")').first();
  if (await customTabBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
    await customTabBtn.click();
    await page.waitForTimeout(1000);

    const createLoopBtn = page.locator('button:has-text("Create Loop")').first();
    if (await createLoopBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
      await createLoopBtn.click();
      await page.waitForTimeout(800);
    }

    await setTheme(false);
    await page.screenshot({ path: `${outDir}/02_loops_custom_form_light.png`, fullPage: false });
    console.log("Captured 02_loops_custom_form_light.png");
  }

  // ═════════════════════════════════════════════════════════════
  // SURFACE 2: AUTORESEARCH VIEW
  // ═════════════════════════════════════════════════════════════
  console.log("--- Surface 2: Autoresearch View ---");
  const moreBtn1 = page.locator('aside button[aria-label="More views"]').first();
  if (await moreBtn1.isVisible({ timeout: 1500 }).catch(() => false)) {
    const isExpanded = await moreBtn1.getAttribute("aria-expanded");
    if (isExpanded !== "true") {
      await moreBtn1.click();
      await page.waitForTimeout(500);
    }
  }

  const autoNav = page.locator('aside button[role="tab"][aria-label="Autoresearch"]').first();
  await autoNav.scrollIntoViewIfNeeded();
  await autoNav.click();
  await page.waitForTimeout(2000);

  // 2A. Dashboard Tab
  const dashTabBtn = page.locator('#main-content button[aria-label="Dashboard"]').first();
  if (await dashTabBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
    await dashTabBtn.click();
    await page.waitForTimeout(1000);
  }

  await setTheme(false);
  await page.screenshot({ path: `${outDir}/03_autoresearch_dashboard_light.png`, fullPage: false });
  console.log("Captured 03_autoresearch_dashboard_light.png");

  await setTheme(true);
  await page.screenshot({ path: `${outDir}/03_autoresearch_dashboard_dark.png`, fullPage: false });
  console.log("Captured 03_autoresearch_dashboard_dark.png");

  // 2B. Leaderboard Tab
  console.log("Testing Autoresearch Leaderboard tab...");
  const leaderTabBtn = page.locator('#main-content button[aria-label="Leaderboard"]').first();
  if (await leaderTabBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
    await leaderTabBtn.click();
    await page.waitForTimeout(1200);

    await setTheme(false);
    await page.screenshot({ path: `${outDir}/04_autoresearch_leaderboard_light.png`, fullPage: false });
    console.log("Captured 04_autoresearch_leaderboard_light.png");
  }

  // ═════════════════════════════════════════════════════════════
  // SURFACE 3: META-HYPERAGENT VIEW
  // ═════════════════════════════════════════════════════════════
  console.log("--- Surface 3: Meta-Hyperagent View ---");
  const moreBtn2 = page.locator('aside button[aria-label="More views"]').first();
  if (await moreBtn2.isVisible({ timeout: 1500 }).catch(() => false)) {
    const isExpanded = await moreBtn2.getAttribute("aria-expanded");
    if (isExpanded !== "true") {
      await moreBtn2.click();
      await page.waitForTimeout(500);
    }
  }

  const metaNav = page.locator('aside button[role="tab"][aria-label="Meta-Agent"]').first();
  await metaNav.scrollIntoViewIfNeeded();
  await metaNav.click();
  await page.waitForTimeout(2000);

  await setTheme(false);
  await page.screenshot({ path: `${outDir}/05_meta_hyperagent_dashboard_light.png`, fullPage: false });
  console.log("Captured 05_meta_hyperagent_dashboard_light.png");

  await setTheme(true);
  await page.screenshot({ path: `${outDir}/05_meta_hyperagent_dashboard_dark.png`, fullPage: false });
  console.log("Captured 05_meta_hyperagent_dashboard_dark.png");

  // ═════════════════════════════════════════════════════════════
  // SURFACE 4: MEMORY VIEW (REASONING BANK & HEALTH)
  // ═════════════════════════════════════════════════════════════
  console.log("--- Surface 4: Memory View & Reasoning Bank ---");
  const memNav = page.locator('aside button[role="tab"][aria-label="Memory"]').first();
  await memNav.scrollIntoViewIfNeeded();
  await memNav.click();
  await page.waitForTimeout(2000);

  // 4A. Agent / Reasoning Bank Tab
  console.log("Testing Reasoning Bank / Agent Memory tab...");
  const agentMemTab = page.locator('#main-content button[aria-label="Switch to Agent Memory tab"]').first();
  if (await agentMemTab.isVisible({ timeout: 2000 }).catch(() => false)) {
    await agentMemTab.click();
    await page.waitForTimeout(1500);
  }

  await setTheme(false);
  await page.screenshot({ path: `${outDir}/06_memory_reasoning_bank_light.png`, fullPage: false });
  console.log("Captured 06_memory_reasoning_bank_light.png");

  await setTheme(true);
  await page.screenshot({ path: `${outDir}/06_memory_reasoning_bank_dark.png`, fullPage: false });
  console.log("Captured 06_memory_reasoning_bank_dark.png");

  // 4B. Health & Hybrid Retrieval Weights Tab
  console.log("Testing Memory Health tab...");
  const healthTab = page.locator('#main-content button[aria-label="Switch to Health tab"]').first();
  if (await healthTab.isVisible({ timeout: 2000 }).catch(() => false)) {
    await healthTab.click();
    await page.waitForTimeout(1500);

    await setTheme(false);
    await page.screenshot({ path: `${outDir}/07_memory_health_and_weights_light.png`, fullPage: false });
    console.log("Captured 07_memory_health_and_weights_light.png");
  }

  await browser.close();
  console.log("=== PHASE 5 VERIFICATION COMPLETE ===");
}

run().catch((err) => {
  console.error("Simulation run failed:", err);
  process.exit(1);
});
