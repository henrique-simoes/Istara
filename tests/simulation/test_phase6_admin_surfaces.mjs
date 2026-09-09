import { chromium } from "playwright";
import { mkdirSync } from "fs";

async function run() {
  console.log("=== STARTING PHASE 6 PLATFORM ADMINISTRATION & GOVERNANCE SURFACES VERIFICATION ===");
  const outDir = "/work/tests/simulation/.results/phase6_screenshots";
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
  console.log(`Authenticated as admin: ${user.id} (${user.role})`);

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
        localStorage.setItem("istara_active_view", "admin");
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

  const expandMoreMenuIfNeeded = async () => {
    const moreBtn = page.locator('aside button[aria-label="More views"]').first();
    if (await moreBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
      const isExpanded = await moreBtn.getAttribute("aria-expanded");
      if (isExpanded !== "true") {
        await moreBtn.click();
        await page.waitForTimeout(600);
      }
    }
  };

  // ═════════════════════════════════════════════════════════════
  // SURFACE 1: ADMIN DASHBOARD
  // ═════════════════════════════════════════════════════════════
  console.log("--- Surface 1: Admin Dashboard ---");
  await page.goto(`${FRONTEND_URL}/`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  await expandMoreMenuIfNeeded();
  const adminNav = page.locator('aside button[role="tab"][aria-label="Admin"]').first();
  if (await adminNav.isVisible({ timeout: 2000 }).catch(() => false)) {
    await adminNav.scrollIntoViewIfNeeded();
    await adminNav.click();
    await page.waitForTimeout(1500);
  }

  // 1A. Overview metrics
  await setTheme(false);
  await page.screenshot({ path: `${outDir}/01_admin_dashboard_overview_light.png`, fullPage: false });
  console.log("Captured 01_admin_dashboard_overview_light.png");

  await setTheme(true);
  await page.screenshot({ path: `${outDir}/01_admin_dashboard_overview_dark.png`, fullPage: false });
  console.log("Captured 01_admin_dashboard_overview_dark.png");

  // 1B. Connection Strings Form
  console.log("Testing Connection Strings generation in Admin view...");
  await setTheme(false);
  const labelInput = page.locator('#main-content input[placeholder="Label"]').first();
  if (await labelInput.isVisible({ timeout: 1500 }).catch(() => false)) {
    await labelInput.fill("Clinical Review Lead");
    await page.waitForTimeout(300);

    const generateBtn = page.locator('#main-content button:has-text("Generate Invite")').first();
    if (await generateBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
      await generateBtn.click();
      await page.waitForTimeout(1500);
    }

    await page.screenshot({ path: `${outDir}/02_admin_connection_strings_light.png`, fullPage: false });
    console.log("Captured 02_admin_connection_strings_light.png");
  }

  // ═════════════════════════════════════════════════════════════
  // SURFACE 2: BACKUP VIEW
  // ═════════════════════════════════════════════════════════════
  console.log("--- Surface 2: Backup View ---");
  await expandMoreMenuIfNeeded();
  const backupNav = page.locator('aside button[role="tab"][aria-label="Backup"]').first();
  if (await backupNav.isVisible({ timeout: 2000 }).catch(() => false)) {
    await backupNav.scrollIntoViewIfNeeded();
    await backupNav.click();
    await page.waitForTimeout(1800);
  }

  await setTheme(false);
  await page.screenshot({ path: `${outDir}/03_backup_view_light.png`, fullPage: false });
  console.log("Captured 03_backup_view_light.png");

  await setTheme(true);
  await page.screenshot({ path: `${outDir}/03_backup_view_dark.png`, fullPage: false });
  console.log("Captured 03_backup_view_dark.png");

  // 2B. Configure Panel Toggle
  console.log("Testing Backup Configure panel...");
  await setTheme(false);
  const configToggleBtn = page.locator('#main-content button:has-text("Backup Configuration")').first();
  if (await configToggleBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
    await configToggleBtn.click();
    await page.waitForTimeout(800);

    await page.screenshot({ path: `${outDir}/04_backup_config_panel_light.png`, fullPage: false });
    console.log("Captured 04_backup_config_panel_light.png");
  }

  // ═════════════════════════════════════════════════════════════
  // SURFACE 3: SETTINGS & USER MANAGEMENT (RECOVERY CODES)
  // ═════════════════════════════════════════════════════════════
  console.log("--- Surface 3: Settings & User Management ---");
  const settingsNav = page.locator('aside button[role="tab"][aria-label="Settings"]').first();
  if (await settingsNav.isVisible({ timeout: 2000 }).catch(() => false)) {
    await settingsNav.scrollIntoViewIfNeeded();
    await settingsNav.click();
    await page.waitForTimeout(2000);
  }

  // Scroll to Team Members
  const userMgmtSection = page.locator('#tour-target-user-management').first();
  if (await userMgmtSection.isVisible({ timeout: 2000 }).catch(() => false)) {
    await userMgmtSection.scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
  }

  await setTheme(false);
  await page.screenshot({ path: `${outDir}/05_settings_overview_light.png`, fullPage: false });
  console.log("Captured 05_settings_overview_light.png");

  await setTheme(true);
  await page.screenshot({ path: `${outDir}/05_settings_overview_dark.png`, fullPage: false });
  console.log("Captured 05_settings_overview_dark.png");

  // 3B. Invite Member & Recovery Codes Display
  console.log("Testing Team Member invitation & Recovery Codes...");
  await setTheme(false);
  const inviteMemberBtn = page.locator('button[aria-label="Invite a new team member"]').first();
  if (await inviteMemberBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
    await inviteMemberBtn.click();
    await page.waitForTimeout(600);

    // Fill form
    const usernameInput = page.locator('input#invite-username').first();
    const emailInput = page.locator('input#invite-email').first();
    const passwordInput = page.locator('input#invite-password').first();

    if (await usernameInput.isVisible({ timeout: 1000 }).catch(() => false)) {
      await usernameInput.fill("clinical_lead_eva");
      await emailInput.fill("eva.rostova@carenav.health");
      await passwordInput.fill("CareNavClinical2026!");
      await page.waitForTimeout(400);

      const submitBtn = page.locator('button:has-text("Create Account")').first();
      if (await submitBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
        await submitBtn.click();
        await page.waitForTimeout(1500);
      }
    }

    await page.screenshot({ path: `${outDir}/06_settings_credentials_and_recovery_codes_light.png`, fullPage: false });
    console.log("Captured 06_settings_credentials_and_recovery_codes_light.png");
  }

  // ═════════════════════════════════════════════════════════════
  // SURFACE 4: VERSION HISTORY
  // ═════════════════════════════════════════════════════════════
  console.log("--- Surface 4: Version History ---");
  await expandMoreMenuIfNeeded();
  const historyNav = page.locator('aside button[role="tab"][aria-label="History"]').first();
  if (await historyNav.isVisible({ timeout: 2000 }).catch(() => false)) {
    await historyNav.scrollIntoViewIfNeeded();
    await historyNav.click();
    await page.waitForTimeout(1500);
  }

  // Expand first commit if present
  const firstCommitToggle = page.locator('#main-content button:has-text("Synthesize CareNav Double Diamond Discover findings")').first();
  if (await firstCommitToggle.isVisible({ timeout: 1500 }).catch(() => false)) {
    await firstCommitToggle.click();
    await page.waitForTimeout(600);
  }

  await setTheme(false);
  await page.screenshot({ path: `${outDir}/07_version_history_light.png`, fullPage: false });
  console.log("Captured 07_version_history_light.png");

  await setTheme(true);
  await page.screenshot({ path: `${outDir}/07_version_history_dark.png`, fullPage: false });
  console.log("Captured 07_version_history_dark.png");

  await browser.close();
  console.log("=== PHASE 6 VERIFICATION COMPLETE ===");
}

run().catch((err) => {
  console.error("Simulation run failed:", err);
  process.exit(1);
});
