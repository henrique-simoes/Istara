/** Scenario 12 — Chat Sessions: CRUD, star, rename, delete, ensure-default. */

export const name = "Chat Sessions";
export const id = "12-chat-sessions";

export async function run(ctx) {
  const { api, page, screenshot } = ctx;
  const checks = [];

  if (!ctx.projectId) {
    return { checks: [{ name: "Skip — no project", passed: false, detail: "No project ID" }], passed: 0, failed: 1 };
  }

  // 1. Ensure default session
  let defaultSession = null;
  try {
    defaultSession = await api.get(`/api/sessions/${ctx.projectId}/ensure-default`);
    checks.push({
      name: "Ensure default session",
      passed: !!defaultSession.id,
      detail: `id=${defaultSession.id}, title=${defaultSession.title}`,
    });
  } catch (e) {
    checks.push({ name: "Ensure default session", passed: false, detail: e.message });
  }

  // 2. Create a new session
  let testSession = null;
  try {
    testSession = await api.post("/api/sessions", {
      project_id: ctx.projectId,
      title: "[SIM] Test Session",
    });
    checks.push({
      name: "Create session",
      passed: !!testSession.id && testSession.title === "[SIM] Test Session",
      detail: `id=${testSession.id}`,
    });
  } catch (e) {
    checks.push({ name: "Create session", passed: false, detail: e.message });
  }

  // 3. List sessions
  try {
    const sessions = await api.get(`/api/sessions/${ctx.projectId}`);
    const list = sessions.sessions || sessions;
    checks.push({
      name: "List sessions",
      passed: Array.isArray(list) && list.length >= 1,
      detail: `${list.length} sessions`,
    });
  } catch (e) {
    checks.push({ name: "List sessions", passed: false, detail: e.message });
  }

  // 4. Get session details
  if (testSession) {
    try {
      const detail = await api.get(`/api/sessions/detail/${testSession.id}`);
      checks.push({
        name: "Get session details",
        passed: detail.id === testSession.id,
        detail: `messages=${(detail.messages || []).length}`,
      });
    } catch (e) {
      checks.push({ name: "Get session details", passed: false, detail: e.message });
    }
  }

  // 5. Rename session
  if (testSession) {
    try {
      const updated = await api.patch(`/api/sessions/${testSession.id}`, {
        title: "[SIM] Renamed Session",
      });
      checks.push({
        name: "Rename session",
        passed: updated.title === "[SIM] Renamed Session",
        detail: "",
      });
    } catch (e) {
      checks.push({ name: "Rename session", passed: false, detail: e.message });
    }
  }

  // 6. Star session
  if (testSession) {
    try {
      const starResult = await api.post(`/api/sessions/${testSession.id}/star`, {});
      checks.push({
        name: "Star session",
        passed: typeof starResult.starred === "boolean",
        detail: `starred=${starResult.starred}`,
      });
    } catch (e) {
      checks.push({ name: "Star session", passed: false, detail: e.message });
    }
  }

  // 7. UI: navigate to Chat view and check session sidebar
  await page.goto("http://localhost:3000", { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);

  // Select the SIM project
  const projectBtn = page.locator("text=[SIM]").first();
  if (await projectBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await projectBtn.click();
    await page.waitForTimeout(500);
  }

  // Navigate to Chat
  await page.keyboard.press("Meta+1");
  await page.waitForTimeout(1000);

  const chatArea = await page.locator("text=CHATS").isVisible({ timeout: 3000 }).catch(() => false)
    || await page.locator('textarea').first().isVisible({ timeout: 2000 }).catch(() => false);
  checks.push({
    name: "Chat view loads",
    passed: chatArea,
    detail: "",
  });
  await screenshot("12-chat-sessions");

  // 8. Delete test session (cleanup)
  if (testSession) {
    try {
      await api.delete(`/api/sessions/${testSession.id}`);
      checks.push({ name: "Delete session", passed: true, detail: "" });
    } catch (e) {
      checks.push({ name: "Delete session", passed: false, detail: e.message });
    }
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
