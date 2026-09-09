import { chromium } from "playwright";
import { mkdirSync } from "fs";

async function run() {
  console.log("=== STARTING PHASE 4 INTERFACES & DESIGN HANDOFF SURFACES VERIFICATION ===");
  const outDir = "/work/tests/simulation/.results/phase4_screenshots";
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
        localStorage.setItem("istara_active_view", "interfaces");
        localStorage.setItem("istara-interfaces-onboarding-dismissed", "true");
        localStorage.setItem("istara-interfaces-privacy-acknowledged", "true");
      } catch (e) {}
    },
    { tok: token, uId: user.id, pId: PROJECT_ID, pName: targetProj.name }
  );

  const page = await context.newPage();
  page.on("console", (msg) => {
    if (msg.type() === "error") console.log(`[BROWSER ERROR] ${msg.text()}`);
  });

  console.log("Navigating to frontend root...");
  await page.goto(`${FRONTEND_URL}/`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  // If not on interfaces view yet, click Interfaces nav item
  const interfacesBtn = page.locator('button:has-text("Interfaces")').first();
  if (await interfacesBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    console.log("Clicking Interfaces in sidebar...");
    await interfacesBtn.click();
    await page.waitForTimeout(1500);
  }

  // Dismiss onboarding if shown
  const dismissBtn = page.locator('button[aria-label="Skip Interfaces setup"], button:has-text("Skip"), button:has-text("Get Started")').first();
  if (await dismissBtn.isVisible({ timeout: 1500 }).catch(() => false)) {
    console.log("Dismissing onboarding modal...");
    await dismissBtn.click();
    await page.waitForTimeout(800);
  }

  // Helper for theme toggle
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

  // ── TAB 1: DESIGN CHAT ──
  console.log("--- Testing Tab 1: Design Chat ---");
  const chatTab = page.locator('button:has-text("Design Chat")').first();
  if (await chatTab.isVisible({ timeout: 2000 }).catch(() => false)) {
    await chatTab.click();
    await page.waitForTimeout(800);
  }

  const chatInput = page.locator('input[placeholder*="Ask about design"], textarea[placeholder*="Ask about design"], input[type="text"]').first();
  if (await chatInput.isVisible({ timeout: 2000 }).catch(() => false)) {
    await chatInput.fill("Propose a simplified patient oversight dashboard layout focusing on adherence notifications");
    await page.waitForTimeout(500);
  }

  await setTheme(false);
  await page.screenshot({ path: `${outDir}/01_interfaces_design_chat_light.png`, fullPage: false });
  console.log("Captured 01_interfaces_design_chat_light.png");

  await setTheme(true);
  await page.screenshot({ path: `${outDir}/01_interfaces_design_chat_dark.png`, fullPage: false });
  console.log("Captured 01_interfaces_design_chat_dark.png");

  // ── TAB 2: GENERATE TAB & FINDINGS PICKER ──
  console.log("--- Testing Tab 2: Generate Tab & Findings Picker ---");
  const genTab = page.locator('button:has-text("Generate")').first();
  if (await genTab.isVisible({ timeout: 2000 }).catch(() => false)) {
    await genTab.click();
    await page.waitForTimeout(800);
  }

  const addFindingsBtn = page.locator('button:has-text("Add Findings"), button:has-text("Add from Research"), button:has-text("Select Findings")').first();
  if (await addFindingsBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
    console.log("Opening FindingsPicker...");
    await addFindingsBtn.click();
    await page.waitForTimeout(800);

    const findingCheckbox = page.locator('input[type="checkbox"]').first();
    if (await findingCheckbox.isVisible({ timeout: 1000 }).catch(() => false)) {
      await findingCheckbox.check();
      await page.waitForTimeout(300);
    }
  }

  await setTheme(false);
  await page.screenshot({ path: `${outDir}/02_interfaces_generate_findings_picker.png`, fullPage: false });
  console.log("Captured 02_interfaces_generate_findings_picker.png");

  // Close picker
  const donePickerBtn = page.locator('button:has-text("Done"), button:has-text("Close"), button[aria-label="Close"]').first();
  if (await donePickerBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
    await donePickerBtn.click();
    await page.waitForTimeout(500);
  }

  // ── TAB 3: SCREENS GALLERY & DETAIL ──
  console.log("--- Testing Tab 3: Screens Gallery Tab ---");
  const screensTab = page.locator('button:has-text("Screens")').first();
  if (await screensTab.isVisible({ timeout: 2000 }).catch(() => false)) {
    await screensTab.click();
    await page.waitForTimeout(1000);
  }

  await setTheme(false);
  await page.screenshot({ path: `${outDir}/03_interfaces_screens_gallery_light.png`, fullPage: false });
  console.log("Captured 03_interfaces_screens_gallery_light.png");

  await setTheme(true);
  await page.screenshot({ path: `${outDir}/03_interfaces_screens_gallery_dark.png`, fullPage: false });
  console.log("Captured 03_interfaces_screens_gallery_dark.png");

  // Click seeded screen card to inspect detail view
  console.log("Testing Screen Detail preview...");
  const screenCard = page.locator('h3:has-text("CareNav Clinical Oversight"), div:has-text("CareNav Clinical Oversight")').first();
  if (await screenCard.isVisible({ timeout: 3000 }).catch(() => false)) {
    await screenCard.click();
    await page.waitForTimeout(1000);

    // Switch to tablet view
    const tabletBtn = page.locator('button[title*="Tablet"], button:has-text("Tablet")').first();
    if (await tabletBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
      await tabletBtn.click();
      await page.waitForTimeout(500);
    }

    await setTheme(false);
    await page.screenshot({ path: `${outDir}/04_interfaces_screen_detail_light.png`, fullPage: false });
    console.log("Captured 04_interfaces_screen_detail_light.png");

    const backBtn = page.locator('button:has-text("Back"), button[aria-label="Close"], button:has-text("Close")').first();
    if (await backBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
      await backBtn.click();
      await page.waitForTimeout(500);
    }
  }

  // ── TAB 4: HANDOFF & DEV SPEC ──
  console.log("--- Testing Tab 4: Handoff Tab & Dev Spec Generation ---");
  const handoffTab = page.locator('button:has-text("Handoff")').first();
  if (await handoffTab.isVisible({ timeout: 2000 }).catch(() => false)) {
    await handoffTab.click();
    await page.waitForTimeout(1200);
  }

  // Expand the first Design Brief
  const briefItem = page.locator('button:has-text("Design Brief"), div:has-text("Design Brief")').first();
  if (await briefItem.isVisible({ timeout: 2000 }).catch(() => false)) {
    await briefItem.click();
    await page.waitForTimeout(800);
  }

  // Select screen for Dev Spec generation
  const screenSelect = page.locator('select').first();
  if (await screenSelect.isVisible({ timeout: 2000 }).catch(() => false)) {
    const options = await screenSelect.locator('option').allInnerTexts();
    console.log(`Available dev spec screen options: ${options.join(", ")}`);
    if (options.length > 1) {
      await screenSelect.selectOption({ index: 1 });
      await page.waitForTimeout(500);

      const genSpecBtn = page.locator('button:has-text("Generate Dev Spec"), button:has-text("Generate Spec")').first();
      if (await genSpecBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        console.log("Triggering Generate Dev Spec...");
        await genSpecBtn.click();
        await page.waitForTimeout(2000);
      }
    }
  }

  await setTheme(false);
  await page.screenshot({ path: `${outDir}/05_interfaces_handoff_brief_and_spec_light.png`, fullPage: false });
  console.log("Captured 05_interfaces_handoff_brief_and_spec_light.png");

  await setTheme(true);
  await page.screenshot({ path: `${outDir}/05_interfaces_handoff_brief_and_spec_dark.png`, fullPage: false });
  console.log("Captured 05_interfaces_handoff_brief_and_spec_dark.png");

  // ── TAB 5: CONFIGURATION ──
  console.log("--- Testing Tab 5: Configuration Tab ---");
  const configTab = page.locator('button:has-text("Configuration")').first();
  if (await configTab.isVisible({ timeout: 2000 }).catch(() => false)) {
    await configTab.click();
    await page.waitForTimeout(1000);
  }

  await setTheme(false);
  await page.screenshot({ path: `${outDir}/06_interfaces_configuration_light.png`, fullPage: false });
  console.log("Captured 06_interfaces_configuration_light.png");

  await browser.close();
  console.log("=== PHASE 4 VERIFICATION COMPLETE ===");
}

run().catch((err) => {
  console.error("Simulation run failed:", err);
  process.exit(1);
});
