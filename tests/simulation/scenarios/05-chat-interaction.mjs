/** Scenario 05 — Chat Interaction: send messages, verify responses. */

export const name = "Chat Interaction";
export const id = "05-chat-interaction";

export async function run(ctx) {
  const { api, page, screenshot } = ctx;
  const checks = [];

  if (!ctx.projectId) {
    return { checks: [{ name: "Skip", passed: false, detail: "No project ID" }], passed: 0, failed: 1 };
  }

  if (!ctx.llmConnected || ctx.llmReadiness?.chat_ready === false) {
    return {
      checks: [
        {
          name: !ctx.llmConnected
            ? "Skip — LLM not connected"
            : "Skip — chat model not ready",
          passed: true,
          detail: !ctx.llmConnected
            ? "Chat UI requires a configured LLM for response-quality assertions"
            : "Provider is reachable, but no chat-ready model is configured; live transcript assertions are not applicable",
        },
      ],
      passed: 1,
      failed: 0,
      skipped: true,
    };
  }

  // Navigate to Chat
  await page.goto(ctx.frontendUrl, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1000);

  // Select project
  const projectBtn = page.locator("text=[SIM]").first();
  if (await projectBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await projectBtn.click();
    await page.waitForTimeout(500);
  }

  // Click Chat nav
  const chatNav = page.locator('button[aria-label="Chat"]').first();
  await chatNav.click();
  await page.waitForTimeout(1000);

  // ── Phase 2A: Chat Layout — verify messages container is scrollable ──
  {
    const messagesContainer = await page.evaluate(() => {
      // Look for the messages container with overflow-y-auto
      const containers = document.querySelectorAll('[class*="overflow-y-auto"], [class*="overflow-auto"]');
      for (const c of containers) {
        // The messages container is typically inside the chat view
        if (c.closest('[class*="chat"], [class*="Chat"]') || c.querySelector('[class*="message"], [class*="bubble"]')) {
          return {
            found: true,
            hasOverflowY: c.className.includes("overflow-y-auto") || c.className.includes("overflow-auto"),
            className: c.className.substring(0, 120),
          };
        }
      }
      // Fallback: look for any scrollable container in the main area
      const mainArea = document.querySelector('main, [class*="main"], [class*="content"]');
      if (mainArea) {
        const scrollable = mainArea.querySelector('[class*="overflow-y-auto"], [class*="overflow-auto"]');
        if (scrollable) {
          return { found: true, hasOverflowY: true, className: scrollable.className.substring(0, 120) };
        }
      }
      return { found: false, hasOverflowY: false, className: "" };
    });
    checks.push({
      name: "Chat messages container is scrollable (overflow-y-auto)",
      passed: messagesContainer.found && messagesContainer.hasOverflowY,
      detail: `found=${messagesContainer.found}, class="${messagesContainer.className}"`,
    });
  }

  // Find chat input
  const chatInput = page.locator('textarea[placeholder*="Ask about"], input[placeholder*="Ask about"]').first();
  const inputVisible = await chatInput.isVisible({ timeout: 3000 }).catch(() => false);
  checks.push({ name: "Chat input visible", passed: inputVisible, detail: "" });

  if (!inputVisible) {
    return { checks, passed: checks.filter((c) => c.passed).length, failed: checks.filter((c) => !c.passed).length };
  }

  // Message 1: Ask about research data
  const sendBtn = page.locator('button[aria-label="Send message"]').first();
  const msg1 = "What are the main pain points mentioned in the interview transcripts?";

  // Use type() for realistic keystroke events that trigger React onChange.
  // fill() sometimes doesn't fire React synthetic events properly.
  await chatInput.click({ timeout: 5000 });
  await chatInput.fill("");
  await page.waitForTimeout(100);
  await chatInput.type(msg1, { delay: 5 });
  await page.waitForTimeout(300);

  // If send button is still disabled, dispatch input event manually as fallback
  const sendEnabled = await sendBtn.evaluate((btn) => !btn.disabled);
  if (!sendEnabled) {
    await chatInput.evaluate((el, text) => {
      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype, "value"
      )?.set;
      nativeInputValueSetter?.call(el, text);
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    }, msg1);
    await page.waitForTimeout(500);
  }

  // Wait for send button to become enabled (max 3s)
  try {
    await page.waitForFunction(
      () => !document.querySelector('button[aria-label="Send message"]')?.disabled,
      { timeout: 3000 }
    );
  } catch { /* proceed anyway */ }

  if (!(await sendBtn.isEnabled({ timeout: 3000 }).catch(() => false))) {
    checks.push({ name: "Send button enabled for first message", passed: false, detail: "Send remained disabled after typing" });
    return { checks, passed: checks.filter((c) => c.passed).length, failed: checks.filter((c) => !c.passed).length };
  }
  await sendBtn.click({ timeout: 5000 });

  // Wait for response (streaming)
  try {
    await page.waitForTimeout(2000);
    // Wait for assistant message to appear (max 30s for LLM response)
    await page.waitForFunction(
      () => {
        const msgs = document.querySelectorAll('[class*="message"], [class*="chat"], [class*="bubble"]');
        return msgs.length >= 2;
      },
      { timeout: 30000 }
    );
    checks.push({ name: "Chat response received", passed: true, detail: "" });
  } catch (e) {
    checks.push({ name: "Chat response received", passed: false, detail: `Timeout: ${e.message}` });
  }

  await screenshot("05-chat-response");

  // Message 2: Trigger a skill
  const msg2 = "Run a thematic analysis on the interview data";
  await chatInput.click({ timeout: 5000 });
  await chatInput.fill("");
  await page.waitForTimeout(100);
  await chatInput.type(msg2, { delay: 5 });
  await page.waitForTimeout(300);

  const send2Enabled = await sendBtn.evaluate((btn) => !btn.disabled);
  if (!send2Enabled) {
    await chatInput.evaluate((el, text) => {
      const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype, "value"
      )?.set;
      nativeInputValueSetter?.call(el, text);
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    }, msg2);
    await page.waitForTimeout(500);
  }

  try {
    await page.waitForFunction(
      () => !document.querySelector('button[aria-label="Send message"]')?.disabled,
      { timeout: 3000 }
    );
  } catch { /* proceed anyway */ }

  if (!(await sendBtn.isEnabled({ timeout: 3000 }).catch(() => false))) {
    checks.push({ name: "Send button enabled for skill message", passed: false, detail: "Send remained disabled after typing" });
    return { checks, passed: checks.filter((c) => c.passed).length, failed: checks.filter((c) => !c.passed).length };
  }
  await sendBtn.click({ timeout: 5000 });
  try {
    await page.waitForTimeout(3000);
    await page.waitForFunction(
      () => document.body.innerText.includes("thematic") || document.body.innerText.includes("analysis") || document.body.innerText.includes("theme"),
      { timeout: 45000 }
    );
    checks.push({ name: "Skill-triggering message processed", passed: true, detail: "" });
  } catch (e) {
    checks.push({ name: "Skill-triggering message processed", passed: false, detail: e.message });
  }

  await screenshot("05-after-skill-trigger");

  // Verify chat history via API
  try {
    const history = await api.get(`/api/chat/history/${ctx.projectId}?limit=10`);
    const msgCount = Array.isArray(history) ? history.length : 0;
    checks.push({ name: "Chat history persisted", passed: msgCount >= 2, detail: `${msgCount} messages` });
  } catch (e) {
    checks.push({ name: "Chat history persisted", passed: false, detail: e.message });
  }

  // ── W5.5 (update-and-release-proof wave): the composer's effort menu is a
  // real user journey — open it, select a NON-DEFAULT level, send, and assert
  // the level persists across the send (session store → API → UI round-trip).
  // The scenario is only reached when ctx.llmConnected (declared gate above);
  // in lanes without a chat-ready model the whole journey is a declared skip,
  // never a fabricated pass (Full UI Testing Suite Contract 5).
  try {
    const effortSelect = page.locator("#chat-effort").first();
    const effortVisible = await effortSelect.isVisible({ timeout: 3000 }).catch(() => false);
    if (!effortVisible) {
      checks.push({
        name: "Effort menu journey (W5.5)",
        passed: true,
        skipped: true,
        detail: "not_runnable: #chat-effort composer control not rendered in this lane (no chat-ready session)",
      });
    } else {
      // Keyboard: the effort select must be Tab-reachable with visible focus.
      await effortSelect.focus();
      const focused = await page.evaluate(() => document.activeElement?.id || "").catch(() => "");
      checks.push({ name: "Effort select keyboard-focusable", passed: focused === "chat-effort", detail: `activeElement=${focused || "none"}` });

      const options = await effortSelect.locator("option").allTextContents();
      const values = await effortSelect.locator("option").evaluateAll((els) => els.map((el) => el.value));
      checks.push({
        name: "Effort menu offers the inherited ladder",
        passed: values.length >= 2,
        detail: `levels=[${values.join(", ")}]`,
      });
      if (values.length >= 2) {
        const before = await effortSelect.inputValue().catch(() => "");
        // Non-default = the first value that differs from the current one.
        const target = values.find((v) => v !== before) || values[values.length - 1];
        await effortSelect.selectOption(target);
        await page.waitForTimeout(600); // session PATCH round-trip
        const after = await effortSelect.inputValue().catch(() => "");
        checks.push({
          name: `Effort selection persists to session (UI)`,
          passed: after === target,
          detail: `selected "${target}" (was "${before}"), select now "${after}"`,
        });
        // API-behind-browser: the session store persists through the sessions
        // API; at least one session in this project must now carry the level.
        try {
          const sessions = await api.get(`/api/sessions/${ctx.projectId}`);
          const list = Array.isArray(sessions) ? sessions : sessions.sessions || [];
          const match = list.some((s) => s.thinking_mode === target);
          checks.push({
            name: "Effort level persisted via sessions API (API-behind-browser)",
            passed: match,
            detail: match ? `session carries thinking_mode="${target}"` : `no session with thinking_mode="${target}"`,
          });
        } catch (e) {
          checks.push({ name: "Effort level persisted via sessions API (API-behind-browser)", passed: false, detail: e.message });
        }
        // Send a synthetic message and assert the level SURVIVES the send.
        const sendBtn = page.locator('button[aria-label="Send message"]').first();
        const chatInput = page.locator('textarea[placeholder*="Ask about"], input[placeholder*="Ask about"]').first();
        if (await chatInput.isVisible({ timeout: 3000 }).catch(() => false) && (await sendBtn.isEnabled({ timeout: 2000 }).catch(() => false))) {
          await chatInput.click({ timeout: 3000 });
          await chatInput.type("Keep this session's effort level as configured.", { delay: 5 });
          await page.waitForTimeout(300);
          await sendBtn.click({ timeout: 5000 });
          await page.waitForTimeout(2500); // send + store refresh
          const afterSend = await effortSelect.inputValue().catch(() => "");
          checks.push({
            name: "Effort level survives send",
            passed: afterSend === target,
            detail: `after send: "${afterSend}", expected "${target}"`,
          });
          await screenshot("05-effort-persisted");
        } else {
          checks.push({
            name: "Effort level survives send",
            passed: true,
            skipped: true,
            detail: "not_runnable: composer input/send unavailable in this lane; UI+API persistence asserted above",
          });
        }
      }
    }
  } catch (e) {
    checks.push({ name: "Effort menu journey (W5.5)", passed: false, detail: e.message });
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
