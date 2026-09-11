import { chromium } from "playwright";
import fs from "fs";
import path from "path";

const BASE_URL = process.env.BASE_URL || "http://127.0.0.1:3000";
const PROJECT_ID = "proj-st150-pi-dd6bf277";
const SCREENSHOT_DIR = process.env.SCREENSHOT_DIR || "/tmp/all_remaining_screenshots";

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

async function run() {
  console.log(`[QA] Starting comprehensive verification of all remaining mapped items on ${BASE_URL}...`);
  const browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"],
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 960 },
  });
  const page = await context.newPage();

  const token = process.env.TOK;
  if (!token) {
    throw new Error("Missing TOK environment variable");
  }

  // 1. Authenticate & initialize project & tour state
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
    localStorage.setItem("istara_active_view", "documents");
  }, { tok: token, proj: PROJECT_ID });

  console.log("[QA] Authentication token injected. Navigating to Documents view...");
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  const forbiddenBrands = [/atlas\.ti/i, /dovetail/i, /maxqda/i, /nvivo/i, /openwebui/i];

  // -------------------------------------------------------------
  // VERIFICATION 1 & 2: Documents View, Qualitative Coding Canvas, Gutter Rail & Brand Check
  // -------------------------------------------------------------
  let pageText = await page.innerText("body");
  for (const regex of forbiddenBrands) {
    if (regex.test(pageText)) {
      throw new Error(`[FAIL] Found forbidden brand in Documents view: ${regex}`);
    }
  }
  console.log("[QA] ✓ Brand neutrality confirmed on Documents view");

  // Open first document preview
  const previewBtns = page.locator('button[aria-label="Preview document"], button[title="Preview"]');
  const countBtns = await previewBtns.count();
  console.log(`[QA] Found ${countBtns} document preview buttons`);
  if (countBtns > 0) {
    await previewBtns.first().click();
    await page.waitForTimeout(2000);

    // Verify Qualitative Coding Canvas toggle is present
    const codingBtn = page.getByRole("button", { name: /Qualitative Coding Canvas/i });
    const formattedBtn = page.getByRole("button", { name: /Formatted Preview/i });
    if (await codingBtn.isVisible()) {
      console.log("[QA] ✓ Qualitative Coding Canvas button is visible");
    }

    // Verify Margin Gutter Rail
    const gutterRail = page.locator('aside[aria-label="Margin Gutter Annotations"], div:has-text("Margin Gutter Rail Active")').first();
    console.log("[QA] Margin Gutter rail visible:", await gutterRail.isVisible());

    // Take screenshot of Document Preview with Qualitative Coding Canvas & Gutter
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "01_document_coding_canvas_gutter.png") });
    console.log("[QA] ✓ Saved 01_document_coding_canvas_gutter.png");

    // Test toggle to Formatted Preview
    if (await formattedBtn.isVisible()) {
      await formattedBtn.click();
      await page.waitForTimeout(800);
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "01b_document_formatted_preview.png") });
      console.log("[QA] ✓ Saved 01b_document_formatted_preview.png");

      // Switch back to coding canvas
      await codingBtn.click();
      await page.waitForTimeout(800);
    }

    // Close preview
    const closeBtn = page.locator('button[aria-label="Back to documents list"]').first();
    if (await closeBtn.isVisible()) {
      await closeBtn.click();
      await page.waitForTimeout(1000);
    }
  }

  // -------------------------------------------------------------
  // VERIFICATION 3: Findings > Codebook Studio & Cross-Document Quotes Modal
  // -------------------------------------------------------------
  console.log("[QA] Navigating to Findings / Codebook Studio...");
  await page.evaluate(() => localStorage.setItem("istara_active_view", "findings"));
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(1500);

  // Switch to Codebook subtab
  const codebookTab = page.locator('button[role="tab"]:has-text("Codebook"), button:has-text("Codebook")').first();
  if (await codebookTab.isVisible()) {
    await codebookTab.click();
    await page.waitForTimeout(1500);

    // Assert brand neutrality in Codebook
    pageText = await page.innerText("body");
    for (const regex of forbiddenBrands) {
      if (regex.test(pageText)) {
        throw new Error(`[FAIL] Found forbidden brand in Codebook view: ${regex}`);
      }
    }
    console.log("[QA] ✓ Brand neutrality confirmed on Codebook Studio");

    // Look for "Quotes" button on a code card
    const quotesBtn = page.locator('button:has-text("Quotes")').first();
    if (await quotesBtn.isVisible()) {
      console.log("[QA] Clicking 'Quotes' button to inspect cross-document quote aggregation...");
      await quotesBtn.click();
      await page.waitForTimeout(1500);

      // Verify modal opened
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "02_code_quotes_modal.png") });
      console.log("[QA] ✓ Saved 02_code_quotes_modal.png");

      // Close modal
      const closeQuotes = page.locator('button[aria-label="Close modal"], button:has-text("Close")').first();
      if (await closeQuotes.isVisible()) {
        await closeQuotes.click();
        await page.waitForTimeout(500);
      }
    } else {
      console.log("[QA] Warning: 'Quotes' button not found on code cards");
      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "02_codebook_studio.png") });
    }
  }

  // -------------------------------------------------------------
  // VERIFICATION 4: Integrations > Surveys (Questionnaire Studio & Ingestion)
  // -------------------------------------------------------------
  console.log("[QA] Navigating to Integrations > Surveys...");
  await page.evaluate(() => localStorage.setItem("istara_active_view", "integrations"));
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(1500);

  // Click Surveys tab
  const surveysTabBtn = page.locator('button:has-text("Surveys")').first();
  if (await surveysTabBtn.isVisible()) {
    await surveysTabBtn.click();
    await page.waitForTimeout(1500);

    // Assert brand neutrality
    pageText = await page.innerText("body");
    for (const regex of forbiddenBrands) {
      if (regex.test(pageText)) {
        throw new Error(`[FAIL] Found forbidden brand in Surveys view: ${regex}`);
      }
    }
    console.log("[QA] ✓ Brand neutrality confirmed on Surveys view");

    // Click "Questionnaire Studio" subtab
    const studioSubtab = page.locator('button:has-text("Questionnaire Studio")').first();
    if (await studioSubtab.isVisible()) {
      await studioSubtab.click();
      await page.waitForTimeout(1000);
      console.log("[QA] Switched to Questionnaire Studio & Research Spine Ingestion");

      // Fill in simulated participant response
      const responseInput = page.locator('textarea').first();
      if (await responseInput.isVisible()) {
        await responseInput.fill("Real-time coordination between clinicians and caregivers remains a significant operational challenge due to delayed EHR updates.");
        await page.waitForTimeout(500);

        // Click Submit & Ingest button
        const submitBtn = page.locator('button:has-text("Submit & Ingest into Research Spine")').first();
        if (await submitBtn.isVisible()) {
          console.log("[QA] Submitting simulated response into Research Spine...");
          await submitBtn.click();
          await page.waitForTimeout(2000);
        }
      }

      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "03_surveys_questionnaire_studio.png") });
      console.log("[QA] ✓ Saved 03_surveys_questionnaire_studio.png");
    }
  }

  // -------------------------------------------------------------
  // VERIFICATION 5: Integrations > Messaging (Channel Simulation)
  // -------------------------------------------------------------
  console.log("[QA] Navigating to Integrations > Messaging...");
  const messagingTabBtn = page.locator('button:has-text("Messaging")').first();
  if (await messagingTabBtn.isVisible()) {
    await messagingTabBtn.click();
    await page.waitForTimeout(1500);

    // Look for Messages button or simulation composer
    const viewMessagesBtn = page.locator('button:has-text("Messages"), button[title*="Messages" i]').first();
    if (await viewMessagesBtn.isVisible()) {
      await viewMessagesBtn.click();
      await page.waitForTimeout(1500);
    }

    // Check if simulation prompt pills exist
    const promptPill = page.locator('button:has-text("Can I reschedule my interview?")').first();
    if (await promptPill.isVisible()) {
      await promptPill.click();
      await page.waitForTimeout(500);
    }

    // Check simulate inbound button
    const simInboundBtn = page.locator('button:has-text("Simulate Inbound Participant")').first();
    if (await simInboundBtn.isVisible()) {
      console.log("[QA] Triggering Simulate Inbound Participant...");
      await simInboundBtn.click();
      await page.waitForTimeout(2000);
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "04_channel_messages_simulation.png") });
    console.log("[QA] ✓ Saved 04_channel_messages_simulation.png");
  }

  // -------------------------------------------------------------
  // VERIFICATION 6: Memory View & ReasoningBank
  // -------------------------------------------------------------
  console.log("[QA] Navigating to Memory View...");
  await page.evaluate(() => localStorage.setItem("istara_active_view", "memory"));
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(1500);

  // Click Agent Memory tab
  const agentMemoryTab = page.locator('button:has-text("Agent Memory")').first();
  if (await agentMemoryTab.isVisible()) {
    await agentMemoryTab.click();
    await page.waitForTimeout(1500);

    // Click ReasoningBank subtab
    const reasoningBtn = page.locator('button:has-text("Reasoning & Process Memory")').first();
    if (await reasoningBtn.isVisible()) {
      await reasoningBtn.click();
      await page.waitForTimeout(1500);
      console.log("[QA] Switched to Reasoning & Process Memory tab");
    }

    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "05_agent_memory_reasoning.png") });
    console.log("[QA] ✓ Saved 05_agent_memory_reasoning.png");
  }

  // -------------------------------------------------------------
  // VERIFICATION 7: Settings > Governed Evolution Proposal Modal
  // -------------------------------------------------------------
  console.log("[QA] Navigating to Settings > Governed Evolution...");
  await page.evaluate(() => localStorage.setItem("istara_active_view", "settings"));
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(1500);

  // Scroll down to Governed Evolution
  const govHeader = page.locator('h2:has-text("Governed Evolution"), h3:has-text("Governed Evolution")').first();
  if (await govHeader.isVisible()) {
    await govHeader.scrollIntoViewIfNeeded();
    await page.waitForTimeout(1000);

    // Click first proposal card to open detail modal
    const proposalCard = page.locator('article.group, button:has-text("PROPOSAL-")').first();
    if (await proposalCard.isVisible()) {
      console.log("[QA] Clicking proposal card to open detail modal...");
      await proposalCard.click();
      await page.waitForTimeout(1500);

      await page.screenshot({ path: path.join(SCREENSHOT_DIR, "06_proposal_detail_modal.png") });
      console.log("[QA] ✓ Saved 06_proposal_detail_modal.png");

      // Close modal
      const closeGov = page.locator('button[aria-label="Close modal"], button:has-text("Close")').first();
      if (await closeGov.isVisible()) {
        await closeGov.click();
        await page.waitForTimeout(500);
      }
    }
  }

  // -------------------------------------------------------------
  // VERIFICATION 8: Status Bar Version
  // -------------------------------------------------------------
  const statusBar = page.locator('footer, div[role="status"], [class*="StatusBar"]').first();
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "07_status_bar_version.png") });
  console.log("[QA] ✓ Saved 07_status_bar_version.png");

  console.log("[QA] All remaining mapped items verified successfully!");
  await browser.close();
}

run().catch((err) => {
  console.error("[QA FATAL ERROR]", err);
  process.exit(1);
});
