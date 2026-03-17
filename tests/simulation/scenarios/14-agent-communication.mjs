/** Scenario 14 — Agent Communication: A2A directed + broadcast messages, inbox, log. */

export const name = "Agent Communication";
export const id = "14-agent-communication";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // 1. Create two test agents
  let agentA = null;
  let agentB = null;

  try {
    agentA = await api.post("/api/agents", {
      name: "[SIM] Agent Alpha",
      role: "custom",
      system_prompt: "Test agent Alpha for A2A simulation.",
      capabilities: ["a2a_messaging", "chat"],
      heartbeat_interval: 30,
    });
    checks.push({
      name: "Create Agent Alpha",
      passed: !!agentA.id,
      detail: `id=${agentA.id}`,
    });
  } catch (e) {
    checks.push({ name: "Create Agent Alpha", passed: false, detail: e.message });
  }

  try {
    agentB = await api.post("/api/agents", {
      name: "[SIM] Agent Beta",
      role: "custom",
      system_prompt: "Test agent Beta for A2A simulation.",
      capabilities: ["a2a_messaging", "chat", "findings_write"],
      heartbeat_interval: 30,
    });
    checks.push({
      name: "Create Agent Beta",
      passed: !!agentB.id,
      detail: `id=${agentB.id}`,
    });
  } catch (e) {
    checks.push({ name: "Create Agent Beta", passed: false, detail: e.message });
  }

  // 2. Send directed message A → B
  if (agentA && agentB) {
    try {
      const msg = await api.post(`/api/agents/${agentA.id}/messages`, {
        to_agent_id: agentB.id,
        message_type: "consult",
        content: "[SIM] Alpha consulting Beta on research methodology",
      });
      checks.push({
        name: "Directed message A→B",
        passed: !!msg.id && msg.from_agent_id === agentA.id && msg.to_agent_id === agentB.id,
        detail: `msg_id=${msg.id}`,
      });
    } catch (e) {
      checks.push({ name: "Directed message A→B", passed: false, detail: e.message });
    }
  }

  // 3. Send response B → A
  if (agentA && agentB) {
    try {
      const msg = await api.post(`/api/agents/${agentB.id}/messages`, {
        to_agent_id: agentA.id,
        message_type: "response",
        content: "[SIM] Beta suggests using thematic analysis approach",
      });
      checks.push({
        name: "Response message B→A",
        passed: !!msg.id && msg.message_type === "response",
        detail: `msg_id=${msg.id}`,
      });
    } catch (e) {
      checks.push({ name: "Response message B→A", passed: false, detail: e.message });
    }
  }

  // 4. Send broadcast from A
  if (agentA) {
    try {
      const msg = await api.post(`/api/agents/${agentA.id}/messages`, {
        to_agent_id: null,
        message_type: "finding",
        content: "[SIM] Alpha discovered pattern: users prefer guided onboarding",
      });
      checks.push({
        name: "Broadcast message from A",
        passed: !!msg.id && msg.to_agent_id === null,
        detail: `msg_id=${msg.id}`,
      });
    } catch (e) {
      checks.push({ name: "Broadcast message from A", passed: false, detail: e.message });
    }
  }

  // 5. Check inbox for B — should have directed message from A
  if (agentB) {
    try {
      const inbox = await api.get(`/api/agents/${agentB.id}/messages?limit=10`);
      const messages = inbox.messages || [];
      const hasDirected = messages.some(
        (m) => m.from_agent_id === agentA?.id && m.message_type === "consult"
      );
      checks.push({
        name: "Agent B inbox has directed message",
        passed: hasDirected,
        detail: `${messages.length} messages in inbox`,
      });
    } catch (e) {
      checks.push({ name: "Agent B inbox has directed message", passed: false, detail: e.message });
    }
  }

  // 6. Check A2A log contains all messages
  try {
    const log = await api.get("/api/agents/a2a/log?limit=50");
    const messages = log.messages || [];
    const simMessages = messages.filter((m) => m.content.includes("[SIM]"));
    checks.push({
      name: "A2A log contains simulation messages",
      passed: simMessages.length >= 3,
      detail: `${simMessages.length} SIM messages in log`,
    });
  } catch (e) {
    checks.push({ name: "A2A log contains simulation messages", passed: false, detail: e.message });
  }

  // 7. Different message types
  if (agentA) {
    const types = ["status", "request"];
    for (const msgType of types) {
      try {
        const msg = await api.post(`/api/agents/${agentA.id}/messages`, {
          to_agent_id: agentB?.id || null,
          message_type: msgType,
          content: `[SIM] Test ${msgType} message`,
        });
        checks.push({
          name: `Message type: ${msgType}`,
          passed: msg.message_type === msgType,
          detail: "",
        });
      } catch (e) {
        checks.push({ name: `Message type: ${msgType}`, passed: false, detail: e.message });
      }
    }
  }

  // Cleanup — delete test agents
  for (const agent of [agentA, agentB]) {
    if (agent?.id) {
      try {
        await api.delete(`/api/agents/${agent.id}`);
      } catch {}
    }
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
