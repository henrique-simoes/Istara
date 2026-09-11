import { chromium } from "playwright";
import { mkdirSync } from "fs";

async function run() {
  console.log("=== STARTING PHASE 7 SYSTEMWIDE RESPONSIVE & DESIGN SYSTEM VERIFICATION ===");
  const outDir = "/work/tests/simulation/.results/phase7_screenshots";
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

  // 3. Launch browser
  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
  });

  const initSession = async (context, defaultView = "chat") => {
    await context.addInitScript(
      ({ tok, uId, pId, pName, vId }) => {
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
          localStorage.setItem("istara_active_view", vId);
        } catch (e) {}
      },
      { tok: token, uId: user.id, pId: PROJECT_ID, pName: targetProj.name, vId: defaultView }
    );
  };

  const setTheme = async (page, dark) => {
    await page.evaluate((isDark) => {
      if (isDark) {
        document.documentElement.classList.add("dark");
      } else {
        document.documentElement.classList.remove("dark");
      }
    }, dark);
    await page.waitForTimeout(400);
  };

  // ═════════════════════════════════════════════════════════════
  // VIEWPORT 1: 320px (Compact Mobile / iPhone SE)
  // ═════════════════════════════════════════════════════════════
  console.log("--- Testing Viewport 1: 320px (Compact Mobile) ---");
  const ctx320 = await browser.newContext({ viewport: { width: 320, height: 568 }, deviceScaleFactor: 1 });
  await initSession(ctx320, "findings");
  const page320 = await ctx320.newPage();
  await page320.goto(`${FRONTEND_URL}/`, { waitUntil: "networkidle" });
  await page320.waitForTimeout(1500);

  // 1A. Light mode
  await setTheme(page320, false);
  await page320.screenshot({ path: `${outDir}/01_responsive_320_compact_mobile_light.png`, fullPage: false });
  console.log("Captured 01_responsive_320_compact_mobile_light.png");

  // 1B. Dark mode
  await setTheme(page320, true);
  await page320.screenshot({ path: `${outDir}/01_responsive_320_compact_mobile_dark.png`, fullPage: false });
  console.log("Captured 01_responsive_320_compact_mobile_dark.png");

  // 1C. Mobile Drawer Open
  console.log("Opening Mobile Drawer at 320px...");
  await setTheme(page320, false);
  const moreBtn320 = page320.locator('nav[aria-label="Mobile navigation"] button[aria-label="More views"]').first();
  if (await moreBtn320.isVisible({ timeout: 1500 }).catch(() => false)) {
    await moreBtn320.click();
    await page320.waitForTimeout(800);
    await page320.screenshot({ path: `${outDir}/02_responsive_320_mobile_drawer_open.png`, fullPage: false });
    console.log("Captured 02_responsive_320_mobile_drawer_open.png");
  }
  await ctx320.close();

  // ═════════════════════════════════════════════════════════════
  // VIEWPORT 2: 375px (Standard Mobile / iPhone 8/SE3)
  // ═════════════════════════════════════════════════════════════
  console.log("--- Testing Viewport 2: 375px (Standard Mobile) ---");
  const ctx375 = await browser.newContext({ viewport: { width: 375, height: 667 }, deviceScaleFactor: 1 });
  await initSession(ctx375, "tasks");
  const page375 = await ctx375.newPage();
  await page375.goto(`${FRONTEND_URL}/`, { waitUntil: "networkidle" });
  await page375.waitForTimeout(1500);

  await setTheme(page375, false);
  await page375.screenshot({ path: `${outDir}/03_responsive_375_standard_mobile_light.png`, fullPage: false });
  console.log("Captured 03_responsive_375_standard_mobile_light.png");

  await setTheme(page375, true);
  await page375.screenshot({ path: `${outDir}/03_responsive_375_standard_mobile_dark.png`, fullPage: false });
  console.log("Captured 03_responsive_375_standard_mobile_dark.png");
  await ctx375.close();

  // ═════════════════════════════════════════════════════════════
  // VIEWPORT 3: 414px (Large Mobile / iPhone Plus/Max)
  // ═════════════════════════════════════════════════════════════
  console.log("--- Testing Viewport 3: 414px (Large Mobile) ---");
  const ctx414 = await browser.newContext({ viewport: { width: 414, height: 896 }, deviceScaleFactor: 1 });
  await initSession(ctx414, "interfaces");
  const page414 = await ctx414.newPage();
  await page414.goto(`${FRONTEND_URL}/`, { waitUntil: "networkidle" });
  await page414.waitForTimeout(1500);

  await setTheme(page414, false);
  await page414.screenshot({ path: `${outDir}/04_responsive_414_large_mobile_light.png`, fullPage: false });
  console.log("Captured 04_responsive_414_large_mobile_light.png");
  await ctx414.close();

  // ═════════════════════════════════════════════════════════════
  // VIEWPORT 4: 768px (Tablet Portrait / iPad)
  // ═════════════════════════════════════════════════════════════
  console.log("--- Testing Viewport 4: 768px (Tablet Portrait) ---");
  const ctx768 = await browser.newContext({ viewport: { width: 768, height: 1024 }, deviceScaleFactor: 1 });
  await initSession(ctx768, "findings");
  const page768 = await ctx768.newPage();
  await page768.goto(`${FRONTEND_URL}/`, { waitUntil: "networkidle" });
  await page768.waitForTimeout(1500);

  await setTheme(page768, false);
  await page768.screenshot({ path: `${outDir}/05_responsive_768_tablet_portrait_light.png`, fullPage: false });
  console.log("Captured 05_responsive_768_tablet_portrait_light.png");

  await setTheme(page768, true);
  await page768.screenshot({ path: `${outDir}/05_responsive_768_tablet_portrait_dark.png`, fullPage: false });
  console.log("Captured 05_responsive_768_tablet_portrait_dark.png");
  await ctx768.close();

  // ═════════════════════════════════════════════════════════════
  // VIEWPORT 5: 1280px (Desktop Standard)
  // ═════════════════════════════════════════════════════════════
  console.log("--- Testing Viewport 5: 1280px (Desktop Standard) ---");
  const ctx1280 = await browser.newContext({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1 });
  await initSession(ctx1280, "chat");
  const page1280 = await ctx1280.newPage();
  await page1280.goto(`${FRONTEND_URL}/`, { waitUntil: "networkidle" });
  await page1280.waitForTimeout(1500);

  await setTheme(page1280, false);
  await page1280.screenshot({ path: `${outDir}/06_responsive_1280_desktop_standard_light.png`, fullPage: false });
  console.log("Captured 06_responsive_1280_desktop_standard_light.png");

  await setTheme(page1280, true);
  await page1280.screenshot({ path: `${outDir}/06_responsive_1280_desktop_standard_dark.png`, fullPage: false });
  console.log("Captured 06_responsive_1280_desktop_standard_dark.png");
  await ctx1280.close();

  await browser.close();
  console.log("=== PHASE 7 VERIFICATION COMPLETE ===");
}

run().catch((err) => {
  console.error("Simulation run failed:", err);
  process.exit(1);
});
