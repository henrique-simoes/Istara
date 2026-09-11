/** Scenario 78 — Real-Time Voice: verify mic recording flow, states, and cancelation. */

export const name = "Real-Time Voice Recording";
export const id = "78-real-time-voice";

export async function run(ctx) {
  const { page, screenshot } = ctx;
  const checks = [];
  if (!ctx.projectId) {
    return {
      checks: [{ name: "Project available for real-time voice", passed: false, detail: "No persistent project from runner" }],
      passed: 0,
      failed: 1,
      summary: "Real-Time Voice: 0/1 passed",
    };
  }

  try {
    // 1. Navigate to Chat directly
    await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded", timeout: 15000 });
    await page.evaluate((projectId) => {
      localStorage.setItem("istara-active-project", projectId);
      localStorage.setItem("istara_active_view", "chat");
      localStorage.setItem("istara_tour_state", JSON.stringify({ active: false, isOnboarding: false, step: 16, hasExistingProjects: true }));
    }, ctx.projectId).catch(() => {});
    await page.reload({ waitUntil: "domcontentloaded", timeout: 15000 }).catch(() => {});
    await page.waitForSelector('button[aria-label="Chat"], main', { timeout: 15000 }).catch(() => {});
    await page.evaluate(() => window.dispatchEvent(new CustomEvent("istara:navigate", { detail: "chat" })));
    await Promise.any([
      page.locator('button[aria-label="Start recording"]').first().waitFor({ state: "visible", timeout: 15000 }),
      page.locator('textarea[placeholder*="Ask about your research"]').first().waitFor({ state: "visible", timeout: 15000 }),
      page.getByText("Your Research Assistant").first().waitFor({ state: "visible", timeout: 15000 }),
    ]).catch(() => {});
    // Next dev renders the controls before React has always finished binding
    // delegated event handlers. Give hydration a short, explicit settle window
    // before clicking the microphone control.
    await page.waitForTimeout(1500);
    const chatVisible = await page.locator(
      'button[aria-label="Start recording"], textarea[placeholder*="Ask about your research"]'
    ).evaluateAll((els) => els.some((el) => {
      const rect = el.getBoundingClientRect();
      const style = window.getComputedStyle(el);
      return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" && style.display !== "none";
    })).catch(() => false);
    checks.push({ name: "Navigated to Chat", passed: chatVisible, detail: page.url() });

    // 2. Locate Mic Button
    const micButton = page.locator('button[aria-label="Start recording"], button[title="Voice input"]').first();
    await micButton.waitFor({ state: "visible", timeout: 10000 }).catch(() => {});
    await page.waitForFunction(() => {
      const button = document.querySelector('button[aria-label="Start recording"], button[title="Voice input"]');
      return button && !(button instanceof HTMLButtonElement && button.disabled);
    }, null, { timeout: 10000 }).catch(() => {});
    const isVisible = await micButton.isVisible();
    const isEnabled = await micButton.isEnabled().catch(() => false);
    checks.push({
      name: "Mic button visible",
      passed: isVisible && isEnabled,
      detail: isVisible ? (isEnabled ? "Found and enabled" : "Found but disabled") : "Not found",
    });

    if (isVisible && isEnabled) {
      // 3. Start Recording
      await micButton.click();
      await Promise.any([
        page.locator('button[aria-label="Stop recording"]').first().waitFor({ state: "visible", timeout: 10000 }),
        page.getByText("Recording voice...").first().waitFor({ state: "visible", timeout: 10000 }),
      ]).catch(() => {});
      
      const isRecording = await page.locator('button[aria-label="Stop recording"]').isVisible() || 
                          await page.locator('text=Recording voice...').isVisible();
      
      checks.push({
        name: "Recording state triggered",
        passed: isRecording,
        detail: isRecording ? "UI reflects recording" : "No recording UI seen",
      });

      if (isRecording) {
        await screenshot("78-recording-state");

        // 4. Cancel Recording
        const cancelBtn = page.locator('button:has-text("Cancel")');
        if (await cancelBtn.isVisible()) {
          await cancelBtn.click();
          await page.waitForTimeout(1000);
          
          const stillRecording = await page.locator('text=Recording voice...').isVisible();
          checks.push({
            name: "Cancel recording works",
            passed: !stillRecording,
            detail: !stillRecording ? "Recording stopped" : "Recording still active after cancel",
          });
        }
      }
    }
  } catch (e) {
    checks.push({ name: "Voice Recording flow error", passed: false, detail: e.message });
  }

  return { 
    checks, 
    passed: checks.filter(c => c.passed).length, 
    failed: checks.filter(c => !c.passed).length, 
    summary: `Real-Time Voice: ${checks.filter(c => c.passed).length}/${checks.length} passed` 
  };
}
