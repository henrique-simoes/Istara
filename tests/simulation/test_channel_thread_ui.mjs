import { chromium } from "playwright";

const BASE_URL = process.env.BASE_URL || "http://127.0.0.1:3000";
const PROJECT_ID = "proj-st150-pi-dd6bf277";
const SCREENSHOT_PATH = "/tmp/04_channel_messages_thread_verified.png";

async function run() {
  console.log("[QA] Testing Channel Messages UI in live browser...");
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
    localStorage.setItem("istara_active_view", "integrations");
  }, { tok: token, proj: PROJECT_ID });

  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  // Click Messaging tab
  const messagingTabBtn = page.locator('button:has-text("Messaging")').first();
  await messagingTabBtn.click();
  await page.waitForTimeout(1500);

  // Click channel card button
  const channelCardBtn = page.locator('button:has(h3:has-text("CareNav Participant Channel"))').first();
  console.log("[QA] Channel card button visible:", await channelCardBtn.isVisible());
  if (await channelCardBtn.isVisible()) {
    await channelCardBtn.click();
    await page.waitForTimeout(2000);
  }

  // Type a simulated participant question in the composer
  const composerInput = page.locator('textarea[placeholder*="message" i], input[placeholder*="message" i]').first();
  console.log("[QA] Composer input visible:", await composerInput.isVisible());
  if (await composerInput.isVisible()) {
    await composerInput.fill("Could you please send the consent form in advance?");
    await page.waitForTimeout(500);

    const simInboundBtn = page.locator('button:has-text("Simulate Inbound Participant")').first();
    if (await simInboundBtn.isVisible()) {
      console.log("[QA] Clicking 'Simulate Inbound Participant'...");
      await simInboundBtn.click();
      await page.waitForTimeout(2500);
    }
  }

  await page.screenshot({ path: SCREENSHOT_PATH });
  console.log(`[QA] Saved screenshot to ${SCREENSHOT_PATH}`);
  await browser.close();
}

run().catch((err) => {
  console.error(err);
  process.exit(1);
});
