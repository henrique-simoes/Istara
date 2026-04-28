/** Scenario 78 — Real-Time Voice: verify mic recording flow, states, and cancelation. */

export const name = "Real-Time Voice Recording";
export const id = "78-real-time-voice";

export async function run(ctx) {
  const { page, screenshot } = ctx;
  const checks = [];

  try {
    // 1. Navigate to Chat directly
    await page.goto("http://localhost:3000/chat", { waitUntil: "load", timeout: 15000 });
    await page.waitForTimeout(2000);
    checks.push({ name: "Navigated to Chat", passed: page.url().includes("/chat"), detail: page.url() });

    // 2. Locate Mic Button — use the new aria-label we added
    const micButton = page.locator('button[aria-label="Voice input"]');
    await micButton.waitFor({ state: "visible", timeout: 10000 }).catch(() => {});
    const isVisible = await micButton.isVisible();
    checks.push({
      name: "Mic button visible",
      passed: isVisible,
      detail: isVisible ? "Found" : "Not found",
    });

    if (isVisible) {
      // 3. Start Recording
      await micButton.click();
      await page.waitForTimeout(1000);
      
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
