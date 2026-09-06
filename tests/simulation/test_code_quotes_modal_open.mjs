import { chromium } from "playwright";

const BASE_URL = process.env.BASE_URL || "http://127.0.0.1:3000";
const PROJECT_ID = "proj-st150-pi-dd6bf277";
const SCREENSHOT_PATH = "/tmp/02b_code_quotes_modal_open.png";

async function run() {
  console.log("[QA] Testing Code Quotes Modal in live browser...");
  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"],
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 960 },
  });
  const page = await context.newPage();

  const token = process.env.TOK;
  if (!token) throw new Error("Missing TOK env var");

  await page.goto(BASE_URL, { waitUntil: "domcontentloaded" });
  await page.evaluate(({ tok, proj }) => {
    localStorage.clear();
    localStorage.setItem("istara_token", tok);
    localStorage.setItem("istara_auth_user_id", "simulation-admin");
    localStorage.setItem("istara_tour_completed_simulation-admin", "true");
    localStorage.setItem("istara_tour_completed_admin", "true");
    localStorage.setItem("istara_tour_completed_anonymous", "true");
    localStorage.setItem("istara_tour_state", JSON.stringify({ active: false, isOnboarding: false, step: 16, hasExistingProjects: true }));
    localStorage.setItem("istara-active-project", proj);
    localStorage.setItem("istara_active_view", "findings");
  }, { tok: token, proj: PROJECT_ID });

  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  // Click Codebook tab
  const codebookTab = page.locator('button:has-text("Codebook")').first();
  await codebookTab.click();
  await page.waitForTimeout(1500);

  // Click Quotes button
  const quotesBtn = page.locator('button:has-text("Quotes")').first();
  console.log("[QA] Quotes button visible:", await quotesBtn.isVisible());
  if (await quotesBtn.isVisible()) {
    await quotesBtn.click();
    await page.waitForTimeout(2000);
  }

  await page.screenshot({ path: SCREENSHOT_PATH });
  console.log(`[QA] Saved screenshot to ${SCREENSHOT_PATH}`);
  await browser.close();
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
