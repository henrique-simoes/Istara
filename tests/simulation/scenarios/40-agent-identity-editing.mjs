/** Scenario 40 — Agent Identity Editing: test persona file CRUD via API and UI. */

export const name = "Agent Identity Editing";
export const id = "40-agent-identity-editing";

export async function run(ctx) {
  const { api, page, screenshot } = ctx;
  const checks = [];

  // ── 1. GET identity returns all 4 files ──
  try {
    const identity = await api.get("/api/agents/reclaw-main/identity");
    checks.push({
      name: "GET identity returns files",
      passed: identity.files && Object.keys(identity.files).length === 4,
      detail: `files: ${Object.keys(identity.files || {}).join(", ")}`,
    });
    checks.push({
      name: "CORE.md present and substantive",
      passed: (identity.files?.["CORE.md"] || "").length > 500,
      detail: `${(identity.files?.["CORE.md"] || "").length} chars`,
    });
    checks.push({
      name: "SKILLS.md present and substantive",
      passed: (identity.files?.["SKILLS.md"] || "").length > 300,
      detail: `${(identity.files?.["SKILLS.md"] || "").length} chars`,
    });
    checks.push({
      name: "PROTOCOLS.md present and substantive",
      passed: (identity.files?.["PROTOCOLS.md"] || "").length > 300,
      detail: `${(identity.files?.["PROTOCOLS.md"] || "").length} chars`,
    });
  } catch (e) {
    checks.push({ name: "GET identity", passed: false, detail: e.message });
  }

  // ── 2. PUT identity updates files ──
  let originalCore = "";
  try {
    const identity = await api.get("/api/agents/reclaw-main/identity");
    originalCore = identity.files?.["CORE.md"] || "";

    // Update with test content appended
    const testMarker = "\n\n<!-- SIM TEST MARKER -->";
    const updated = await api.put("/api/agents/reclaw-main/identity", {
      files: {
        "CORE.md": originalCore + testMarker,
      },
    });

    // Verify the update persisted
    const verify = await api.get("/api/agents/reclaw-main/identity");
    const hasMarker = (verify.files?.["CORE.md"] || "").includes("SIM TEST MARKER");
    checks.push({
      name: "PUT identity saves changes",
      passed: hasMarker,
      detail: hasMarker ? "Test marker found" : "Test marker not found",
    });

    // Restore original
    await api.put("/api/agents/reclaw-main/identity", {
      files: { "CORE.md": originalCore },
    });
    checks.push({ name: "Identity restore after test", passed: true, detail: "Restored" });
  } catch (e) {
    checks.push({ name: "PUT identity", passed: false, detail: e.message });
    // Attempt restore
    if (originalCore) {
      try {
        await api.put("/api/agents/reclaw-main/identity", {
          files: { "CORE.md": originalCore },
        });
      } catch {}
    }
  }

  // ── 3. PUT identity rejects invalid file names ──
  try {
    await api.put("/api/agents/reclaw-main/identity", {
      files: { "EVIL.md": "hacker content" },
    });
    checks.push({ name: "Rejects invalid file names", passed: false, detail: "Should have thrown" });
  } catch (e) {
    checks.push({
      name: "Rejects invalid file names",
      passed: true,
      detail: `Rejected: ${e.message}`,
    });
  }

  // ── 4. User-created agent gets scaffolded persona ──
  let testAgentId = null;
  try {
    const agent = await api.post("/api/agents", {
      name: "[SIM] Persona Test Agent",
      role: "custom",
      system_prompt: "A test agent for persona scaffolding.",
      capabilities: ["skill_execution", "chat"],
    });
    testAgentId = agent.id;

    // Check identity was scaffolded
    const identity = await api.get(`/api/agents/${agent.id}/identity`);
    checks.push({
      name: "New agent gets persona scaffold",
      passed: identity.has_persona === true,
      detail: `files: ${Object.keys(identity.files || {}).join(", ")}`,
    });
    checks.push({
      name: "Scaffold CORE.md has agent name",
      passed: (identity.files?.["CORE.md"] || "").includes("Persona Test Agent"),
      detail: "",
    });
    checks.push({
      name: "Scaffold has all 4 files",
      passed: Object.keys(identity.files || {}).length === 4,
      detail: `${Object.keys(identity.files || {}).length} files`,
    });
  } catch (e) {
    checks.push({ name: "Persona scaffolding", passed: false, detail: e.message });
  }

  // ── 5. UI — Identity tab visible in Agents view ──
  try {
    await page.goto("http://localhost:3000", { waitUntil: "networkidle", timeout: 10000 });
    await page.waitForTimeout(2000);

    // Navigate to Agents view using keyboard shortcut
    await page.keyboard.press("Meta+7");
    await page.waitForTimeout(2000);

    // Look for any agent card to click on — try multiple selectors
    let agentFound = false;
    const agentSelectors = [
      'text=ReClaw',
      '[data-agent-id="reclaw-main"]',
      'text=Sentinel',
      'text=reclaw-main',
    ];

    for (const sel of agentSelectors) {
      const el = page.locator(sel).first();
      if (await el.isVisible({ timeout: 2000 }).catch(() => false)) {
        await el.click();
        agentFound = true;
        await page.waitForTimeout(1000);
        break;
      }
    }

    if (agentFound) {
      // Look for Identity tab with case-insensitive matching
      const tabSelectors = [
        'button:has-text("Identity")',
        'button:has-text("identity")',
        '[role="tab"]:has-text("Identity")',
        'text=Identity',
      ];

      let tabFound = false;
      for (const sel of tabSelectors) {
        const tab = page.locator(sel).first();
        if (await tab.isVisible({ timeout: 2000 }).catch(() => false)) {
          tabFound = true;
          checks.push({ name: "Identity tab visible in agent detail", passed: true, detail: "Tab found" });
          break;
        }
      }

      if (!tabFound) {
        checks.push({ name: "Identity tab visible in agent detail", passed: false, detail: "Tab not found after clicking agent" });
      }
    } else {
      // If we can't find agent cards, still pass the API tests — UI may differ in CI
      checks.push({
        name: "Identity tab visible in agent detail",
        passed: false,
        detail: "Could not locate agent card in UI",
      });
    }

    await screenshot("40-agent-identity-tab").catch(() => {});
  } catch (e) {
    checks.push({ name: "Identity tab visible in agent detail", passed: false, detail: `UI error: ${e.message}` });
  }

  // ── Cleanup ──
  if (testAgentId) {
    try { await api.delete(`/api/agents/${testAgentId}`); } catch {}
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
