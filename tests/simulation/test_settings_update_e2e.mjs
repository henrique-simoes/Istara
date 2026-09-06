import { chromium } from "playwright";

async function run() {
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const tok = "eyJhbGciOiAiSFMyNTYiLCAidHlwIjogIkpXVCJ9.eyJzdWIiOiAic2ltdWxhdGlvbi1hZG1pbiIsICJ1c2VybmFtZSI6ICJhZG1pbiIsICJyb2xlIjogImFkbWluIiwgIm1mYSI6IHRydWUsICJqdGkiOiAid0tBNEp1R2g1TndHUUR2YXJqcDRsQSIsICJpYXQiOiAxNzg4NzE3NDYyLCAiZXhwIjogMTc4ODgwMzg2Mn0.6GPol5gPCWDNUulHX6ysm6JygGxBUCR4Hmc_gnBJnZk";

  await page.goto("http://127.0.0.1:3000", { waitUntil: "domcontentloaded" });
  await page.evaluate(({ token }) => {
    localStorage.clear();
    localStorage.setItem("istara_token", token);
    localStorage.setItem("istara_auth_user_id", "simulation-admin");
    localStorage.setItem("istara_tour_completed_simulation-admin", "true");
    localStorage.setItem("istara_tour_completed_admin", "true");
    localStorage.setItem("istara_tour_completed_anonymous", "true");
    localStorage.setItem("istara_tour_state", JSON.stringify({ active: false, isOnboarding: false, step: 16, hasExistingProjects: true }));
    localStorage.setItem("istara_active_view", "chat");
  }, { token: tok });

  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(1500);

  // 1. Test Status Bar Version Button in footer
  const statusBarVersion = page.locator('footer button[aria-label*="Istara version"]');
  await statusBarVersion.waitFor({ state: "visible", timeout: 10000 });
  const sbText = await statusBarVersion.innerText();
  console.log("Status bar version text:", sbText);
  if (!sbText.includes("2026.05.27.3")) {
    throw new Error("Status bar missing correct CalVer version! Found: " + sbText);
  }

  // 2. Click status bar version button to navigate into Settings
  console.log("Clicking status bar version button to navigate into Settings view...");
  await statusBarVersion.click();
  await page.waitForTimeout(1500);

  // 3. Verify software updates target is visible in Settings
  const updatesTarget = page.locator('#tour-target-software-updates');
  await updatesTarget.waitFor({ state: "visible", timeout: 10000 });
  const updatesText = await updatesTarget.innerText();
  console.log("Updates section text:\n---\n" + updatesText + "\n---");

  if (!updatesText.includes("2026.05.27.3")) {
    throw new Error("Software updates section missing version 2026.05.27.3");
  }
  if (!updatesText.includes("Docker")) {
    throw new Error("Software updates section missing Docker install type badge");
  }

  // 4. Click 'Check Now' button against live backend
  const checkBtn = page.locator('#tour-target-software-updates button:has-text("Check Now")');
  await checkBtn.click();
  await page.waitForTimeout(1000);
  const upToDateMsg = await page.locator("text=You're running the latest version (v2026.05.27.3)").isVisible();
  console.log("Up to date message visible after Check Now:", upToDateMsg);
  if (!upToDateMsg) {
    throw new Error("Expected 'You\\'re running the latest version (v2026.05.27.3)' to be visible");
  }

  // 5. Test simulated newer release in Docker
  console.log("Simulating newer release in Docker...");
  await page.route("**/api/updates/check", route => {
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        update_available: true,
        current_version: "2026.05.27.3",
        latest_version: "2026.06.01.1",
        release_name: "Istara 2026.06.01.1",
        published_at: "2026-06-01T12:00:00Z",
        release_url: "https://github.com/henrique-simoes/Istara/releases/tag/v2026.06.01.1",
        install_type: "docker",
        can_auto_update: false,
        docker_command: "docker compose pull && docker compose up -d"
      })
    });
  });

  await checkBtn.click();
  await page.waitForTimeout(1000);

  const updateCardVisible = await page.locator("text=Istara 2026.06.01.1 is available").isVisible();
  console.log("Update Available card visible:", updateCardVisible);
  if (!updateCardVisible) {
    throw new Error("Expected 'Istara 2026.06.01.1 is available' card to be visible");
  }

  const dockerGuidanceVisible = await page.locator("text=Run this command on your host machine to update your Docker containers.").isVisible();
  console.log("Docker guidance text visible:", dockerGuidanceVisible);
  if (!dockerGuidanceVisible) {
    throw new Error("Expected Docker host update guidance text to be visible");
  }

  const dockerCmdText = await page.locator('text="docker compose pull && docker compose up -d"').isVisible();
  console.log("Docker compose pull command visible:", dockerCmdText);
  if (!dockerCmdText) {
    throw new Error("Expected 'docker compose pull && docker compose up -d' command to be visible");
  }

  const copyBtn = page.locator('button[title="Copy command"]').first();
  const copyBtnVisible = await copyBtn.isVisible();
  console.log("Copy button visible:", copyBtnVisible);
  if (!copyBtnVisible) {
    throw new Error("Expected Copy command button to be visible");
  }

  await copyBtn.click();
  console.log("Copy button clicked successfully.");
  await page.waitForTimeout(300);

  const copiedVisible = await page.locator("text=Copied").isVisible();
  console.log("'Copied' feedback visible after click:", copiedVisible);

  await page.screenshot({ path: "/tmp/settings-update-complete-e2e.png", fullPage: false });
  console.log("Screenshot saved to /tmp/settings-update-complete-e2e.png");

  await browser.close();
  console.log("ALL Playwright E2E verification checks passed successfully!");
}

run().catch(err => {
  console.error("Playwright verification failed:", err);
  process.exit(1);
});
