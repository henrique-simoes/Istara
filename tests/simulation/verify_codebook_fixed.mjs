import { chromium } from "playwright";

async function run() {
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
    localStorage.setItem("istara_active_view", "findings");
  }, { token: tok });
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(1000);

  const codebookSubtab = page.locator('button[role="tab"]:has-text("Codebook")').first();
  await codebookSubtab.click();
  await page.waitForTimeout(1000);

  const firstCode = page.locator('button:has-text("caregiver-privacy")').first();
  await firstCode.click();
  await page.waitForTimeout(800);

  const expandedDetails = await page.locator('[role="region"]').innerText();
  console.log("Expanded details:\n---\n" + expandedDetails + "\n---");

  await page.screenshot({ path: "/tmp/codebook-expanded.png" });
  await browser.close();
}

run().catch(console.error);
