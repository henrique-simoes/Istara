import { chromium } from "playwright";
import { writeFileSync, mkdirSync } from "fs";

async function audit() {
  const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  const outDir = "/tmp/istara-audit";
  mkdirSync(outDir, { recursive: true });

  const auditLog = [];
  function log(area, status, message, data = null) {
    const entry = { area, status, message, data, time: new Date().toISOString() };
    auditLog.push(entry);
    console.log(`[${status}] [${area}] ${message}`);
  }

  page.on("console", msg => {
    if (msg.type() === "error") {
      log("BROWSER_CONSOLE", "ERROR", msg.text());
    }
  });
  page.on("pageerror", err => {
    log("BROWSER_PAGEERROR", "CRASH", err.message);
  });

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

  // ==========================================
  // AREA 1: INTERVIEWS & QUALITATIVE CODING UX
  // ==========================================
  console.log("\n--- AUDITING AREA 1: INTERVIEWS & QUALITATIVE CODING ---");
  await page.evaluate(() => {
    window.dispatchEvent(new CustomEvent("istara:navigate", { detail: "interviews" }));
  });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${outDir}/1-interviews-view.png` });

  const interviewsViewVisible = await page.locator("text=Interviews").first().isVisible().catch(() => false);
  log("INTERVIEWS", interviewsViewVisible ? "PASS" : "FAIL", "Interviews view loaded", { visible: interviewsViewVisible });

  // Check if any interviews/transcripts are visible
  const interviewItems = await page.locator("button, div").filter({ hasText: /Interview|Participant|Transcript|User/i }).allInnerTexts().catch(() => []);
  log("INTERVIEWS", "INFO", `Found ${interviewItems.length} candidate interview elements`, { samples: interviewItems.slice(0, 5) });

  // Check if transcript text is present or upload button is present
  const hasUploadAudio = await page.locator("text=Upload Audio").first().isVisible().catch(() => false);
  const hasTranscripts = await page.locator("text=Transcript").first().isVisible().catch(() => false);
  log("INTERVIEWS", "INFO", "Interviews controls", { hasUploadAudio, hasTranscripts });

  // Check Documents view for qualitative coding
  console.log("\n--- AUDITING DOCUMENTS QUALITATIVE CODING ---");
  await page.evaluate(() => {
    window.dispatchEvent(new CustomEvent("istara:navigate", { detail: "documents" }));
  });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${outDir}/1b-documents-view.png` });

  const docItems = await page.locator("text=Document").count();
  log("DOCUMENTS", "INFO", `Documents count indicators: ${docItems}`);

  // Let's click on the first document in list if available
  const firstDocItem = page.locator("div.cursor-pointer, button.text-left").first();
  if (await firstDocItem.isVisible().catch(() => false)) {
    await firstDocItem.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${outDir}/1c-document-detail.png` });

    // Check if qualitative coding span/highlight exists or text selection works
    const codingTextEl = page.locator(".prose, [data-qualitative-coding='true']").first();
    const codingTextExists = await codingTextEl.isVisible().catch(() => false);
    log("DOCUMENTS_CODING", codingTextExists ? "PASS" : "WARN", "Document body rendered with qualitative coding capability", { exists: codingTextExists });
  }

  // ==========================================
  // AREA 2: INTEGRATIONS (CHANNELS & SURVEYS)
  // ==========================================
  console.log("\n--- AUDITING AREA 2: INTEGRATIONS ---");
  await page.evaluate(() => {
    window.dispatchEvent(new CustomEvent("istara:navigate", { detail: "integrations" }));
  });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${outDir}/2-integrations-overview.png` });

  // Inspect sub-tabs: Overview, Messaging, Surveys, Deployments, MCP
  const tabs = ["Overview", "Messaging", "Surveys", "Deployments", "MCP"];
  for (const tab of tabs) {
    const tabBtn = page.locator(`button:has-text("${tab}")`).first();
    const isTabVis = await tabBtn.isVisible().catch(() => false);
    log("INTEGRATIONS_TAB", isTabVis ? "PASS" : "FAIL", `Subtab ${tab} button present`, { visible: isTabVis });
  }

  // Test Messaging tab
  const msgTab = page.locator('button:has-text("Messaging")').first();
  if (await msgTab.isVisible().catch(() => false)) {
    await msgTab.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${outDir}/2b-integrations-messaging.png` });

    const connectBtn = page.locator('button:has-text("Connect Channel"), button:has-text("Add Channel")').first();
    const canConnect = await connectBtn.isVisible().catch(() => false);
    log("INTEGRATIONS_MESSAGING", canConnect ? "PASS" : "WARN", "Connect Channel button present", { canConnect });

    if (canConnect) {
      await connectBtn.click();
      await page.waitForTimeout(800);
      await page.screenshot({ path: `${outDir}/2b2-channel-wizard.png` });

      // Check wizard channels: Telegram, Slack, WhatsApp
      const hasTelegram = await page.locator("text=Telegram").first().isVisible().catch(() => false);
      const hasSlack = await page.locator("text=Slack").first().isVisible().catch(() => false);
      const hasWhatsApp = await page.locator("text=WhatsApp").first().isVisible().catch(() => false);
      log("INTEGRATIONS_MESSAGING", "INFO", "Channel options in wizard", { hasTelegram, hasSlack, hasWhatsApp });

      // Close wizard modal
      const closeBtn = page.locator('button:has-text("Cancel"), button[aria-label="Close"]').first();
      if (await closeBtn.isVisible().catch(() => false)) await closeBtn.click();
      await page.waitForTimeout(500);
    }
  }

  // Test Surveys tab
  const surveysTab = page.locator('button:has-text("Surveys")').first();
  if (await surveysTab.isVisible().catch(() => false)) {
    await surveysTab.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${outDir}/2c-integrations-surveys.png` });

    const createSurveyBtn = page.locator('button:has-text("Create Survey"), button:has-text("New Survey")').first();
    const canCreateSurvey = await createSurveyBtn.isVisible().catch(() => false);
    log("INTEGRATIONS_SURVEYS", canCreateSurvey ? "PASS" : "WARN", "Create Survey button present", { canCreateSurvey });
  }

  // Test Deployments tab
  const depTab = page.locator('button:has-text("Deployments")').first();
  if (await depTab.isVisible().catch(() => false)) {
    await depTab.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${outDir}/2d-integrations-deployments.png` });

    const deployBtn = page.locator('button:has-text("New Deployment"), button:has-text("Deploy Research")').first();
    const canDeploy = await deployBtn.isVisible().catch(() => false);
    log("INTEGRATIONS_DEPLOYMENTS", canDeploy ? "PASS" : "WARN", "Deployment button present", { canDeploy });
  }

  // ==========================================
  // AREA 3: AGENT MEMORY & REASONING NOTES
  // ==========================================
  console.log("\n--- AUDITING AREA 3: AGENT MEMORY ---");
  await page.evaluate(() => {
    window.dispatchEvent(new CustomEvent("istara:navigate", { detail: "agent-memory" }));
  });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${outDir}/3-agent-memory-view.png` });

  const memoryHeading = await page.locator("text=Agent Memory").first().isVisible().catch(() => false);
  log("AGENT_MEMORY", memoryHeading ? "PASS" : "FAIL", "Agent Memory view loaded", { visible: memoryHeading });

  // Check tabs inside Memory: Knowledge Base, Agent Memory (Working Notes vs Reasoning)
  const kbTab = await page.locator("text=Knowledge Base").first().isVisible().catch(() => false);
  const reindexBtn = await page.locator("text=Re-index Knowledge Base").first().isVisible().catch(() => false);
  log("AGENT_MEMORY", "INFO", "Memory controls", { kbTab, reindexBtn });

  const reasoningToggle = page.locator("text=Reasoning & Process Memory").first();
  if (await reasoningToggle.isVisible().catch(() => false)) {
    await reasoningToggle.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${outDir}/3b-reasoning-memory-tab.png` });
    const notesCount = await page.locator("div.p-4, div.rounded-lg").count();
    log("AGENT_MEMORY", "INFO", `Reasoning & Process Memory cards count: ${notesCount}`);
  }

  // ==========================================
  // AREA 4: CODEBOOK STUDIO & TASK ASSIGNMENT
  // ==========================================
  console.log("\n--- AUDITING AREA 4: CODEBOOK STUDIO & TASKS ---");
  await page.evaluate(() => {
    window.dispatchEvent(new CustomEvent("istara:navigate", { detail: { view: "findings" } }));
  });
  await page.waitForTimeout(2000);

  // Click Codebook tab
  const codebookTab = page.locator('button:has-text("Codebook"), button:has-text("Codebook Studio")').first();
  if (await codebookTab.isVisible().catch(() => false)) {
    await codebookTab.click();
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${outDir}/4-codebook-studio.png` });

    const createCodebookBtn = page.locator('button:has-text("Create Codebook")').first();
    const canCreateCodebook = await createCodebookBtn.isVisible().catch(() => false);
    log("CODEBOOK_STUDIO", canCreateCodebook ? "PASS" : "FAIL", "Create Codebook button present", { canCreateCodebook });

    if (canCreateCodebook) {
      await createCodebookBtn.click();
      await page.waitForTimeout(800);
      await page.screenshot({ path: `${outDir}/4b-create-codebook-modal.png` });

      const hasMethodology = await page.locator("text=Methodology").first().isVisible().catch(() => false);
      log("CODEBOOK_STUDIO", hasMethodology ? "PASS" : "WARN", "Methodology options in Create Codebook modal", { hasMethodology });

      // Close modal
      const cancelBtn = page.locator('button:has-text("Cancel")').first();
      if (await cancelBtn.isVisible().catch(() => false)) await cancelBtn.click();
      await page.waitForTimeout(500);
    }
  }

  // Audit Kanban Tasks codebook binding
  await page.evaluate(() => {
    window.dispatchEvent(new CustomEvent("istara:navigate", { detail: "tasks" }));
  });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${outDir}/4c-kanban-tasks.png` });

  const firstTaskCard = page.locator("div[role='button'], div.cursor-pointer").filter({ hasText: /Task|Analyze|Synthesize|Review/i }).first();
  if (await firstTaskCard.isVisible().catch(() => false)) {
    await firstTaskCard.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${outDir}/4d-task-editor-modal.png` });

    const hasGoverningCodebook = await page.locator("text=Governing Codebook").first().isVisible().catch(() => false);
    log("KANBAN_TASKS", hasGoverningCodebook ? "PASS" : "WARN", "Governing Codebook dropdown present in Task Editor", { hasGoverningCodebook });

    const closeTaskBtn = page.locator('button:has-text("Cancel"), button[aria-label="Close"]').first();
    if (await closeTaskBtn.isVisible().catch(() => false)) await closeTaskBtn.click();
    await page.waitForTimeout(500);
  }

  // ==========================================
  // AREA 5: FINDINGS REPORTS SLIDE INSTRUCTIONS
  // ==========================================
  console.log("\n--- AUDITING AREA 5: FINDINGS REPORTS SLIDES ---");
  await page.evaluate(() => {
    window.dispatchEvent(new CustomEvent("istara:navigate", { detail: { view: "findings" } }));
  });
  await page.waitForTimeout(2000);

  const reportsTab = page.locator('button:has-text("Reports")').first();
  if (await reportsTab.isVisible().catch(() => false)) {
    await reportsTab.click();
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${outDir}/5-reports-view.png` });

    const slideInstructionsBtn = page.locator('button:has-text("Instructions to create slides"), button:has-text("Slide Instructions")').first();
    const hasSlideBtn = await slideInstructionsBtn.isVisible().catch(() => false);
    log("REPORTS_SLIDES", hasSlideBtn ? "PASS" : "WARN", "Instructions to create slides button present", { hasSlideBtn });

    if (hasSlideBtn) {
      await slideInstructionsBtn.click();
      await page.waitForTimeout(1500);
      await page.screenshot({ path: `${outDir}/5b-slide-instructions-open.png` });

      const instructionsContent = await page.locator("text=Minto|Situation|Complication|Executive|Slide").first().isVisible().catch(() => false);
      log("REPORTS_SLIDES", instructionsContent ? "PASS" : "WARN", "Slide instructions loaded content", { instructionsContent });
    }
  }

  // ==========================================
  // AREA 6: GOVERNED EVOLUTION INSPECTOR
  // ==========================================
  console.log("\n--- AUDITING AREA 6: GOVERNED EVOLUTION ---");
  await page.evaluate(() => {
    window.dispatchEvent(new CustomEvent("istara:navigate", { detail: "settings" }));
  });
  await page.waitForTimeout(2000);

  const govSection = page.locator("text=Governed Evolution").first();
  await govSection.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${outDir}/6-governed-evolution-section.png` });

  const proposalCard = page.locator("div.cursor-pointer, button").filter({ hasText: /Proposal|PROPOSAL|improvement/i }).first();
  if (await proposalCard.isVisible().catch(() => false)) {
    await proposalCard.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${outDir}/6b-proposal-detail-modal.png` });

    const modalTabs = ["Overview & Rationale", "State Changes & Diffs", "Evidence & ReasoningBank", "Sandbox Evaluation"];
    let tabsFound = 0;
    for (const mt of modalTabs) {
      if (await page.locator(`text=${mt}`).first().isVisible().catch(() => false)) tabsFound++;
    }
    log("GOVERNED_EVOLUTION", tabsFound >= 3 ? "PASS" : "WARN", `Proposal detail modal tabs: ${tabsFound}/${modalTabs.length}`, { tabsFound });
  }

  writeFileSync(`${outDir}/audit_results.json`, JSON.stringify(auditLog, null, 2));
  console.log("\n=== AUDIT FINISHED ===");
  console.log(`Results saved to ${outDir}/audit_results.json and screenshots in ${outDir}/`);

  await browser.close();
}

audit().catch(err => {
  console.error("Audit script failed:", err);
  process.exit(1);
});
