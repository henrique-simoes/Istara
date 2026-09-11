import { chromium } from "playwright";

async function testCoding() {
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  page.on("console", msg => console.log("[BROWSER]", msg.type(), msg.text()));
  page.on("pageerror", err => console.error("[PAGEERROR]", err.message));

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
    localStorage.setItem("istara_active_view", "documents");
  }, { token: tok });

  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  // 1. Click first document row
  const firstDoc = page.locator('div[role="listitem"]').first();
  await firstDoc.waitFor({ state: "visible", timeout: 10000 });
  const title = await firstDoc.innerText();
  console.log("Found document to open:", title.replace(/\n/g, " | "));

  await firstDoc.click();
  await page.waitForTimeout(2000);

  // 2. Check if Document Preview opened
  const backBtn = page.locator('button[aria-label="Back to documents list"]');
  const previewOpened = await backBtn.isVisible();
  console.log("Document preview opened:", previewOpened);

  // 3. Open the Qualitative Coding details summary if present
  const codingDetails = page.locator("summary:has-text('Qualitative Coding & Annotation')");
  if (await codingDetails.isVisible().catch(() => false)) {
    console.log("Expanding Qualitative Coding accordion...");
    await codingDetails.click();
    await page.waitForTimeout(1000);
  }

  await page.screenshot({ path: "/tmp/doc-preview-coding-open.png", fullPage: true });
  console.log("Screenshot saved to /tmp/doc-preview-coding-open.png");

  // 4. Check if QualitativeCodingText container is visible
  const codingContainer = page.locator('[data-qualitative-coding="true"]');
  const codingVis = await codingContainer.isVisible().catch(() => false);
  console.log("Qualitative coding container visible:", codingVis);

  if (codingVis) {
    const textSnippet = (await codingContainer.innerText()).slice(0, 200);
    console.log("Coding text snippet:", textSnippet.replace(/\n/g, " "));

    // Select text in the coding container
    console.log("Selecting text in qualitative coding container...");
    await page.evaluate(() => {
      const el = document.querySelector('[data-qualitative-coding="true"]');
      if (!el) return;
      const range = document.createRange();
      const p = el.querySelector("p") || el;
      if (p.firstChild) {
        range.setStart(p.firstChild, 0);
        range.setEnd(p.firstChild, Math.min(40, p.firstChild.textContent?.length || 10));
        const sel = window.getSelection();
        sel?.removeAllRanges();
        sel?.addRange(range);
        el.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
      }
    });

    await page.waitForTimeout(1000);

    // Check if floating popover appeared
    const popover = page.locator("button:has-text('Apply Code'), button:has-text('Tag Selection'), div:has-text('Apply Code')").first();
    const popoverVis = await popover.isVisible().catch(() => false);
    console.log("Floating coding popover visible:", popoverVis);

    await page.screenshot({ path: "/tmp/doc-preview-popover-open.png", fullPage: true });
    console.log("Screenshot saved to /tmp/doc-preview-popover-open.png");
  }

  await browser.close();
}

testCoding().catch(err => {
  console.error("Test coding failed:", err);
  process.exit(1);
});
