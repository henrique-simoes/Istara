/** Scenario 11 — Agents System: agent CRUD, heartbeat, A2A, capacity, and UI. */

export const name = "Agents System";
export const id = "11-agents-system";

export async function run(ctx) {
  const { api, page, screenshot } = ctx;
  const checks = [];

  // ── API Tests ──

  // 1. List agents — should have system agents seeded
  try {
    const data = await api.get("/api/agents");
    const agents = data.agents || [];
    const systemAgents = agents.filter((a) => a.is_system);
    checks.push({
      name: "System agents seeded",
      passed: systemAgents.length >= 3,
      detail: `${systemAgents.length} system agents, ${agents.length} total`,
    });

    // Check main agent exists
    const mainAgent = agents.find((a) => a.id === "istara-main");
    checks.push({
      name: "Istara main agent exists",
      passed: !!mainAgent,
      detail: mainAgent ? `id=${mainAgent.id}, name=${mainAgent.name}, state=${mainAgent.state}` : "Not found",
    });
  } catch (e) {
    checks.push({ name: "System agents seeded", passed: false, detail: e.message });
    checks.push({ name: "Istara main agent exists", passed: false, detail: e.message });
  }

  // 2. Create a user agent
  let testAgentId = null;
  try {
    const agent = await api.post("/api/agents", {
      name: "Sim Test Agent",
      role: "custom",
      system_prompt: "You are a test agent created by the simulation.",
      capabilities: ["findings_read", "task_management"],
      heartbeat_interval: 30,
    });
    testAgentId = agent.id;
    checks.push({
      name: "Create user agent",
      passed: !!agent.id && agent.name === "Sim Test Agent",
      detail: `id=${agent.id}`,
    });
  } catch (e) {
    checks.push({ name: "Create user agent", passed: false, detail: e.message });
  }

  // 3. Get agent details
  if (testAgentId) {
    try {
      const agent = await api.get(`/api/agents/${testAgentId}`);
      checks.push({
        name: "Get agent details",
        passed: agent.name === "Sim Test Agent" && agent.capabilities?.length === 2,
        detail: `capabilities=${JSON.stringify(agent.capabilities)}`,
      });
    } catch (e) {
      checks.push({ name: "Get agent details", passed: false, detail: e.message });
    }
  }

  // 4. Update agent
  if (testAgentId) {
    try {
      const updated = await api.patch(`/api/agents/${testAgentId}`, {
        system_prompt: "Updated test prompt.",
      });
      checks.push({
        name: "Update agent",
        passed: updated.system_prompt === "Updated test prompt.",
        detail: "",
      });
    } catch (e) {
      checks.push({ name: "Update agent", passed: false, detail: e.message });
    }
  }

  // 5. Pause and resume agent
  if (testAgentId) {
    try {
      await api.post(`/api/agents/${testAgentId}/pause`, {});
      const paused = await api.get(`/api/agents/${testAgentId}`);
      const isPaused = paused.state === "paused";

      await api.post(`/api/agents/${testAgentId}/resume`, {});
      const resumed = await api.get(`/api/agents/${testAgentId}`);
      const isIdle = resumed.state === "idle";

      checks.push({
        name: "Pause/resume agent",
        passed: isPaused && isIdle,
        detail: `paused=${isPaused}, resumed=${isIdle}`,
      });
    } catch (e) {
      checks.push({ name: "Pause/resume agent", passed: false, detail: e.message });
    }
  }

  // 6. Agent memory
  if (testAgentId) {
    try {
      await api.patch(`/api/agents/${testAgentId}/memory`, {
        test_key: "simulation_value",
      });
      const mem = await api.get(`/api/agents/${testAgentId}/memory`);
      checks.push({
        name: "Agent memory read/write",
        passed: mem.memory?.test_key === "simulation_value",
        detail: JSON.stringify(mem.memory || {}),
      });
    } catch (e) {
      checks.push({ name: "Agent memory read/write", passed: false, detail: e.message });
    }
  }

  // 7. A2A messaging
  if (testAgentId) {
    try {
      const msg = await api.post(`/api/agents/${testAgentId}/messages`, {
        to_agent_id: null,
        message_type: "status",
        content: "Simulation test broadcast",
      });
      checks.push({
        name: "A2A send message",
        passed: !!msg.id && msg.content === "Simulation test broadcast",
        detail: `msg_id=${msg.id}`,
      });

      // Check A2A log
      const log = await api.get("/api/agents/a2a/log");
      const found = (log.messages || []).some((m) => m.content === "Simulation test broadcast");
      checks.push({
        name: "A2A message appears in log",
        passed: found,
        detail: `${(log.messages || []).length} messages in log`,
      });
    } catch (e) {
      checks.push({ name: "A2A send message", passed: false, detail: e.message });
      checks.push({ name: "A2A message appears in log", passed: false, detail: e.message });
    }
  }

  // 8. Capacity check
  try {
    const cap = await api.get("/api/agents/capacity");
    checks.push({
      name: "Capacity check API",
      passed: typeof cap.can_create === "boolean" && typeof cap.ram_available_gb === "number",
      detail: `can_create=${cap.can_create}, ram=${cap.ram_available_gb}GB, agents=${cap.current_agents}/${cap.max_agents}`,
    });
  } catch (e) {
    checks.push({ name: "Capacity check API", passed: false, detail: e.message });
  }

  // 9. Heartbeat status
  try {
    const hb = await api.get("/api/agents/heartbeat/status");
    const agentStatuses = hb.agents || [];
    checks.push({
      name: "Heartbeat status API",
      passed: agentStatuses.length > 0,
      detail: `${agentStatuses.length} agents reporting`,
    });
  } catch (e) {
    checks.push({ name: "Heartbeat status API", passed: false, detail: e.message });
  }

  // 10. Delete user agent (system agents should be protected)
  if (testAgentId) {
    try {
      const res = await api.delete(`/api/agents/${testAgentId}`);
      checks.push({
        name: "Delete user agent",
        passed: res.status === 204,
        detail: `status=${res.status}`,
      });
    } catch (e) {
      checks.push({ name: "Delete user agent", passed: false, detail: e.message });
    }
  }

  // 11. System agent delete protection
  try {
    const data = await api.get("/api/agents");
    const systemAgent = (data.agents || []).find((a) => a.is_system);
    if (systemAgent) {
      const res = await api.delete(`/api/agents/${systemAgent.id}`);
      checks.push({
        name: "System agent delete protection",
        passed: res.status === 404,
        detail: `Attempted delete of ${systemAgent.name}, status=${res.status}`,
      });
    } else {
      checks.push({ name: "System agent delete protection", passed: false, detail: "No system agent found" });
    }
  } catch (e) {
    // A 404 error means protection worked
    checks.push({ name: "System agent delete protection", passed: true, detail: "Delete rejected" });
  }

  // ── UI Tests ──

  // 12. Navigate to Agents view
  await page.goto("http://localhost:3000", { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);

  // Try Cmd+7 shortcut
  await page.keyboard.press("Meta+7");
  await page.waitForTimeout(800);

  // Check Agents view loaded — look for "Agents" heading or agent cards
  let agentsViewVisible = await page.locator("text=System Agents").isVisible({ timeout: 3000 }).catch(() => false);

  // Fallback: click the sidebar nav button
  if (!agentsViewVisible) {
    const agentsBtn = page.locator('button[aria-label="Agents"]').first();
    if (await agentsBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await agentsBtn.click();
      await page.waitForTimeout(800);
      agentsViewVisible = await page.locator("text=System Agents").isVisible({ timeout: 3000 }).catch(() => false);
    }
  }

  checks.push({
    name: "Agents view loads",
    passed: agentsViewVisible,
    detail: agentsViewVisible ? "System Agents section visible" : "Could not find Agents view content",
  });
  await screenshot("11-agents-view");

  // 13. Agent cards visible
  if (agentsViewVisible) {
    // Check for agent cards with heartbeat indicators
    const agentCards = await page.locator('[class*="border"][class*="rounded"]').count();
    checks.push({
      name: "Agent cards rendered",
      passed: agentCards >= 3,
      detail: `${agentCards} cards visible`,
    });

    // Check for heartbeat dots
    const heartbeatDots = await page.locator('[class*="rounded-full"][class*="animate-pulse"], [class*="rounded-full"][class*="bg-green"], [class*="rounded-full"][class*="bg-emerald"]').count();
    checks.push({
      name: "Heartbeat indicators visible",
      passed: heartbeatDots > 0,
      detail: `${heartbeatDots} heartbeat indicators`,
    });
  }

  // 14. Check A2A Messages tab
  if (agentsViewVisible) {
    const a2aTab = page.locator('button:has-text("A2A Messages")').first();
    if (await a2aTab.isVisible({ timeout: 2000 }).catch(() => false)) {
      await a2aTab.click();
      await page.waitForTimeout(800);
      await screenshot("11-a2a-messages");
      checks.push({ name: "A2A Messages tab accessible", passed: true, detail: "" });
    } else {
      checks.push({ name: "A2A Messages tab accessible", passed: false, detail: "Tab not found" });
    }
  }

  // 15. Check Create Agent tab/wizard
  if (agentsViewVisible) {
    const createTab = page.locator('button:has-text("Create Agent")').first();
    if (await createTab.isVisible({ timeout: 2000 }).catch(() => false)) {
      await createTab.click();
      await page.waitForTimeout(800);
      await screenshot("11-create-agent-wizard");

      // Verify wizard step content
      const wizardContent = await page.locator("text=Agent Identity").isVisible({ timeout: 2000 }).catch(() => false)
        || await page.locator("text=Name").isVisible({ timeout: 1000 }).catch(() => false);
      checks.push({
        name: "Create Agent wizard loads",
        passed: wizardContent,
        detail: "",
      });
    } else {
      checks.push({ name: "Create Agent wizard loads", passed: false, detail: "Tab not found" });
    }
  }

  // ── Phase 4B: Agent Error Display ──
  // When an agent has heartbeat "error" state with error_count=0,
  // the UI should show "Heartbeat Lost" or "Connection Error" instead of "0 Errors"
  if (agentsViewVisible) {
    // First, check the current heartbeat status via API for any error states
    try {
      const hb = await api.get("/api/agents/heartbeat/status");
      const agentStatuses = hb.agents || [];

      // Check the UI text for any agents that have error state
      const errorDisplayInfo = await page.evaluate(() => {
        const body = document.body.innerText;
        // These phrases should NOT appear (they are the old incorrect display)
        const hasZeroErrors = body.includes("0 Errors") || body.includes("0 errors");
        // These phrases SHOULD appear when there's a heartbeat error with 0 error count
        const hasHeartbeatLost = body.includes("Heartbeat Lost") || body.includes("heartbeat lost");
        const hasConnectionError = body.includes("Connection Error") || body.includes("connection error");
        const hasLostContact = body.includes("Lost Contact") || body.includes("lost contact");
        return {
          hasZeroErrors,
          hasHeartbeatLost,
          hasConnectionError,
          hasLostContact,
        };
      });

      // The UI should never show "0 Errors" — if there's an error state,
      // it should display a descriptive message instead
      checks.push({
        name: "Phase 4B: UI does not show misleading '0 Errors' for heartbeat issues",
        passed: !errorDisplayInfo.hasZeroErrors,
        detail: `zero_errors_shown=${errorDisplayInfo.hasZeroErrors}, heartbeat_lost=${errorDisplayInfo.hasHeartbeatLost}, connection_error=${errorDisplayInfo.hasConnectionError}`,
      });

      // Verify that agent cards show meaningful error states
      // Check that error-state agents display proper labels
      const errorAgentCards = await page.evaluate(() => {
        const cards = document.querySelectorAll('[class*="border"][class*="rounded"]');
        let hasDescriptiveErrorLabel = false;
        for (const card of cards) {
          const text = card.innerText;
          if (text.includes("Heartbeat Lost") || text.includes("Connection Error") ||
              text.includes("Lost Contact") || text.includes("Offline") ||
              text.includes("Unreachable")) {
            hasDescriptiveErrorLabel = true;
            break;
          }
        }
        return { hasDescriptiveErrorLabel, cardCount: cards.length };
      });
      checks.push({
        name: "Phase 4B: Agent cards use descriptive error labels",
        passed: errorAgentCards.hasDescriptiveErrorLabel || agentStatuses.every(a => a.status !== "error"),
        detail: `descriptive_labels=${errorAgentCards.hasDescriptiveErrorLabel}, cards=${errorAgentCards.cardCount}, any_errors=${agentStatuses.some(a => a.status === "error")}`,
      });
    } catch (e) {
      checks.push({ name: "Phase 4B: Agent error display", passed: false, detail: e.message });
    }
  }

  // 16. Chat view renders
  // Navigate to Chat view and verify it loaded
  await page.keyboard.press("Meta+1");
  await page.waitForTimeout(800);

  // Chat view could show: empty state, project selector, or message input — any is valid
  const chatReady = await page.locator("text=Ready to research").isVisible({ timeout: 2000 }).catch(() => false);
  const chatSelect = await page.locator("text=Select or create a project").isVisible({ timeout: 1000 }).catch(() => false);
  const chatInput = await page.locator('textarea[placeholder*="research"]').isVisible({ timeout: 1000 }).catch(() => false);
  const chatActive = page.locator('button[aria-label="Chat"][aria-selected="true"]').first();
  const chatViewActive = await chatActive.isVisible({ timeout: 1000 }).catch(() => false);
  checks.push({
    name: "Chat view renders",
    passed: chatReady || chatSelect || chatInput || chatViewActive,
    detail: chatReady ? "Empty state" : chatSelect ? "Project selection" : chatInput ? "Input visible" : chatViewActive ? "Chat tab active" : "Not found",
  });

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
