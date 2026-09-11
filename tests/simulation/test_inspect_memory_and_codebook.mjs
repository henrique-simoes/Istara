import { chromium } from "playwright";

async function inspect() {
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
  const page = await browser.newPage();
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
    localStorage.setItem("istara-active-project", "proj-st150-pi-dd6bf277");
    localStorage.setItem("istara_active_view", "chat");
  }, { token: tok });
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(1000);

  // 1. Inspect Memory
  console.log("Navigating to Memory...");
  const memBtn = page.locator('button[aria-label="Memory"]').first();
  await memBtn.click();
  await page.waitForTimeout(2000);

  const memText = await page.locator("#main-content").innerText();
  console.log("Memory view loaded:\n---", memText.slice(0, 300), "\n---");
  await page.screenshot({ path: "/tmp/live-memory-clicked.png" });

  // 2. Inspect Findings -> Codebook
  console.log("Navigating to Findings -> Codebook...");
  const findingsBtn = page.locator('button[aria-label="Findings"]').first();
  await findingsBtn.click();
  await page.waitForTimeout(1500);

  const codebookSubtab = page.locator('button[role="tab"]:has-text("Codebook")').first();
  if (await codebookSubtab.isVisible()) {
    await codebookSubtab.click();
    await page.waitForTimeout(2000);
    const cbText = await page.locator("#main-content").innerText();
    console.log("Codebook view loaded:\n---", cbText.slice(0, 400), "\n---");
    await page.screenshot({ path: "/tmp/live-codebook-clicked.png" });
  }

  // 3. Inspect Findings -> Reports
  console.log("Navigating to Findings -> Reports...");
  const reportsSubtab = page.locator('button[role="tab"]:has-text("Reports")').first();
  if (await reportsSubtab.isVisible()) {
    await reportsSubtab.click();
    await page.waitForTimeout(2000);
    const repText = await page.locator("#main-content").innerText();
    console.log("Reports view loaded:\n---", repText.slice(0, 300), "\n---");
    await page.screenshot({ path: "/tmp/live-reports-clicked.png" });

    // Click first report to open report details
    const firstReport = page.locator('div.cursor-pointer, button').filter({ hasText: /Report|CareNav|Executive/i }).first();
    if (await firstReport.isVisible()) {
      await firstReport.click();
      await page.waitForTimeout(1500);
      console.log("Clicked report. Looking for slide instructions button...");
      const slideBtn = page.locator('button:has-text("Instructions to create slides")').first();
      console.log("Slide button visible:", await slideBtn.isVisible());
      if (await slideBtn.isVisible()) {
        await slideBtn.click();
        await page.waitForTimeout(2000);
        console.log("Slide instructions opened! Text snippet:", (await page.locator("#main-content").innerText()).slice(0, 300));
        await page.screenshot({ path: "/tmp/live-slide-instructions.png" });
      }
    }
  }

  await browser.close();
}

inspect().catch(console.error);
