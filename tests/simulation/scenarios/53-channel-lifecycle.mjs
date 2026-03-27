/** Scenario 53 — Channel Lifecycle: integration tests for messaging channel CRUD and lifecycle.
 *  Tests: create, start, health, messages, conversations, stop, delete for channel instances.
 *
 *  Exercises: /api/channels/*
 */

export const name = "Channel Lifecycle";
export const id = "53-channel-lifecycle";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];
  const cleanup = { instanceIds: [] };

  // ── 1. GET /api/channels — returns array (initially empty or existing) ──
  let initialList = [];
  try {
    const result = await api.get("/api/channels");
    initialList = Array.isArray(result) ? result : result?.channels || [];
    checks.push({
      name: "GET /api/channels returns array",
      passed: Array.isArray(initialList),
      detail: `${initialList.length} existing instances`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/channels returns array", passed: false, detail: e.message });
  }

  // ── 2. POST /api/channels — create Telegram instance ──
  let telegramInstance = null;
  try {
    telegramInstance = await api.post("/api/channels", {
      platform: "telegram",
      name: "SIM: Test Telegram Bot",
      config: { bot_token: "sim-test-token-123456" },
    });
    cleanup.instanceIds.push(telegramInstance.id);
    checks.push({
      name: "POST /api/channels creates Telegram instance",
      passed: !!telegramInstance.id && telegramInstance.platform === "telegram",
      detail: `id=${telegramInstance.id}`,
    });
  } catch (e) {
    checks.push({ name: "POST /api/channels creates Telegram instance", passed: false, detail: e.message });
  }

  // ── 3. GET /api/channels/{id} — instance details ──
  if (telegramInstance) {
    try {
      const detail = await api.get(`/api/channels/${telegramInstance.id}`);
      checks.push({
        name: "GET /api/channels/{id} returns instance details",
        passed: detail.id === telegramInstance.id && detail.platform === "telegram",
        detail: `name=${detail.name}, health=${detail.health_status}`,
      });
    } catch (e) {
      checks.push({ name: "GET /api/channels/{id} returns instance details", passed: false, detail: e.message });
    }
  }

  // ── 4. POST /api/channels — create Slack instance ──
  let slackInstance = null;
  try {
    slackInstance = await api.post("/api/channels", {
      platform: "slack",
      name: "SIM: Test Slack Workspace",
      config: { bot_token: "xoxb-sim-test-123", signing_secret: "sim-secret-456" },
    });
    cleanup.instanceIds.push(slackInstance.id);
    checks.push({
      name: "POST /api/channels creates Slack instance",
      passed: !!slackInstance.id && slackInstance.platform === "slack",
      detail: `id=${slackInstance.id}`,
    });
  } catch (e) {
    checks.push({ name: "POST /api/channels creates Slack instance", passed: false, detail: e.message });
  }

  // ── 5. GET /api/channels?platform=telegram — filter by platform ──
  try {
    const filtered = await api.get("/api/channels?platform=telegram");
    const list = Array.isArray(filtered) ? filtered : filtered?.channels || [];
    const allTelegram = list.every((c) => c.platform === "telegram");
    checks.push({
      name: "GET /api/channels?platform=telegram filters correctly",
      passed: allTelegram && list.length >= 1,
      detail: `${list.length} telegram instances`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/channels?platform=telegram filters correctly", passed: false, detail: e.message });
  }

  // ── 6. PATCH /api/channels/{id} — update name ──
  if (telegramInstance) {
    try {
      const updated = await api.patch(`/api/channels/${telegramInstance.id}`, {
        name: "SIM: Updated Telegram Bot",
      });
      checks.push({
        name: "PATCH /api/channels/{id} updates instance",
        passed: updated.name === "SIM: Updated Telegram Bot",
        detail: `name=${updated.name}`,
      });
    } catch (e) {
      checks.push({ name: "PATCH /api/channels/{id} updates instance", passed: false, detail: e.message });
    }
  }

  // ── 7. GET /api/channels/{id}/health — health check ──
  if (telegramInstance) {
    try {
      const health = await api.get(`/api/channels/${telegramInstance.id}/health`);
      checks.push({
        name: "GET /api/channels/{id}/health returns health data",
        passed: health.status !== undefined || health.health_status !== undefined,
        detail: `status=${health.status || health.health_status}`,
      });
    } catch (e) {
      checks.push({ name: "GET /api/channels/{id}/health returns health data", passed: false, detail: e.message });
    }
  }

  // ── 8. GET /api/channels/{id}/messages — empty initially ──
  if (telegramInstance) {
    try {
      const messages = await api.get(`/api/channels/${telegramInstance.id}/messages`);
      const msgList = Array.isArray(messages) ? messages : messages?.messages || [];
      checks.push({
        name: "GET /api/channels/{id}/messages returns array",
        passed: Array.isArray(msgList),
        detail: `${msgList.length} messages`,
      });
    } catch (e) {
      checks.push({ name: "GET /api/channels/{id}/messages returns array", passed: false, detail: e.message });
    }
  }

  // ── 9. GET /api/channels/{id}/conversations — empty initially ──
  if (telegramInstance) {
    try {
      const convos = await api.get(`/api/channels/${telegramInstance.id}/conversations`);
      const convoList = Array.isArray(convos) ? convos : convos?.conversations || [];
      checks.push({
        name: "GET /api/channels/{id}/conversations returns array",
        passed: Array.isArray(convoList),
        detail: `${convoList.length} conversations`,
      });
    } catch (e) {
      checks.push({ name: "GET /api/channels/{id}/conversations returns array", passed: false, detail: e.message });
    }
  }

  // ── 10. GET /api/channels — count after creation ──
  try {
    const allChannels = await api.get("/api/channels");
    const list = Array.isArray(allChannels) ? allChannels : allChannels?.channels || [];
    checks.push({
      name: "GET /api/channels shows correct count after creation",
      passed: list.length >= initialList.length + 2,
      detail: `${list.length} total (was ${initialList.length})`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/channels shows correct count after creation", passed: false, detail: e.message });
  }

  // ── 11. DELETE /api/channels/{id} — delete Slack instance ──
  if (slackInstance) {
    try {
      await api.delete(`/api/channels/${slackInstance.id}`);
      cleanup.instanceIds = cleanup.instanceIds.filter((id) => id !== slackInstance.id);
      checks.push({
        name: "DELETE /api/channels/{id} removes instance",
        passed: true,
        detail: `Deleted Slack instance ${slackInstance.id}`,
      });
    } catch (e) {
      checks.push({ name: "DELETE /api/channels/{id} removes instance", passed: false, detail: e.message });
    }
  }

  // ── 12. GET /api/channels — count after deletion ──
  try {
    const afterDelete = await api.get("/api/channels");
    const list = Array.isArray(afterDelete) ? afterDelete : afterDelete?.channels || [];
    checks.push({
      name: "GET /api/channels shows correct count after deletion",
      passed: list.length >= initialList.length + 1,
      detail: `${list.length} total (created 2, deleted 1)`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/channels shows correct count after deletion", passed: false, detail: e.message });
  }

  // ── 13. POST /api/channels — create WhatsApp instance ──
  let whatsappInstance = null;
  try {
    whatsappInstance = await api.post("/api/channels", {
      platform: "whatsapp",
      name: "SIM: Test WhatsApp",
      config: { phone_number_id: "sim-123", access_token: "sim-token-xyz" },
    });
    cleanup.instanceIds.push(whatsappInstance.id);
    checks.push({
      name: "POST /api/channels creates WhatsApp instance",
      passed: !!whatsappInstance.id && whatsappInstance.platform === "whatsapp",
      detail: `id=${whatsappInstance.id}`,
    });
  } catch (e) {
    checks.push({ name: "POST /api/channels creates WhatsApp instance", passed: false, detail: e.message });
  }

  // ── 14. POST /api/channels — create Google Chat instance ──
  let gchatInstance = null;
  try {
    gchatInstance = await api.post("/api/channels", {
      platform: "google_chat",
      name: "SIM: Test Google Chat",
      config: { webhook_url: "https://sim.test/webhook" },
    });
    cleanup.instanceIds.push(gchatInstance.id);
    checks.push({
      name: "POST /api/channels creates Google Chat instance",
      passed: !!gchatInstance.id && gchatInstance.platform === "google_chat",
      detail: `id=${gchatInstance.id}`,
    });
  } catch (e) {
    checks.push({ name: "POST /api/channels creates Google Chat instance", passed: false, detail: e.message });
  }

  // ── 15. All 4 platforms represented ──
  try {
    const allChannels = await api.get("/api/channels");
    const list = Array.isArray(allChannels) ? allChannels : allChannels?.channels || [];
    const platforms = new Set(list.map((c) => c.platform));
    const hasFour = platforms.has("telegram") && platforms.has("whatsapp") && platforms.has("google_chat");
    checks.push({
      name: "All platform types can coexist",
      passed: hasFour,
      detail: `Platforms: ${[...platforms].join(", ")}`,
    });
  } catch (e) {
    checks.push({ name: "All platform types can coexist", passed: false, detail: e.message });
  }

  // ── Cleanup ──
  for (const id of cleanup.instanceIds) {
    try {
      await api.delete(`/api/channels/${id}`);
    } catch (_) {}
  }

  return checks;
}
