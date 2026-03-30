/** Scenario 27 — Agent Identity System: persona MD files, identity loading, learnings. */

export const name = "Agent Identity & Persona System";
export const id = "27-agent-identity";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // ── 1. All 5 system agents have persona names ──
  try {
    const agentsRes = await api.get("/api/agents");
    const agents = agentsRes.agents || [];
    const systemAgents = agents.filter((a) => a.is_system);

    checks.push({
      name: "All 5 system agents exist",
      passed: systemAgents.length >= 5,
      detail: `Found ${systemAgents.length} system agents`,
    });

    const expectedNames = {
      "istara-main": "Istara",
      "istara-devops": "Sentinel",
      "istara-ui-audit": "Pixel",
      "istara-ux-eval": "Sage",
      "istara-sim": "Echo",
    };

    for (const [agentId, expectedName] of Object.entries(expectedNames)) {
      const agent = agents.find((a) => a.id === agentId);
      checks.push({
        name: `${agentId} has persona name "${expectedName}"`,
        passed: agent && agent.name === expectedName,
        detail: agent ? `Name: ${agent.name}` : "Agent not found",
      });
    }

    // System prompts are substantive (not 1-liners)
    for (const agent of systemAgents) {
      checks.push({
        name: `${agent.name} has substantive system prompt (100+ chars)`,
        passed: agent.system_prompt && agent.system_prompt.length >= 100,
        detail: `${(agent.system_prompt || "").length} chars`,
      });
    }
  } catch (e) {
    checks.push({ name: "Agents list loads", passed: false, detail: e.message });
  }

  // ── 2. Persona MD files loaded via identity endpoint ──
  const agentIds = ["istara-main", "istara-devops", "istara-ui-audit", "istara-ux-eval", "istara-sim"];
  for (const agentId of agentIds) {
    try {
      const identity = await api.get(`/api/agents/${agentId}/identity`);
      checks.push({
        name: `${agentId} has persona files loaded`,
        passed: identity.has_persona === true,
        detail: `${identity.identity_length} chars`,
      });
      checks.push({
        name: `${agentId} identity is 2000+ chars`,
        passed: identity.identity_length >= 2000,
        detail: `${identity.identity_length} chars`,
      });
      checks.push({
        name: `${agentId} has all 4 MD files`,
        passed: identity.files && Object.keys(identity.files).length === 4,
        detail: `Files: ${Object.keys(identity.files || {}).join(", ")}`,
      });
    } catch (e) {
      checks.push({ name: `${agentId} identity endpoint`, passed: false, detail: e.message });
    }
  }

  // ── 3. Personas list endpoint ──
  try {
    const personas = await api.get("/api/agents/personas/list");
    checks.push({
      name: "Personas list returns all 5 agents",
      passed: personas.personas && personas.personas.length >= 5,
      detail: `Found ${(personas.personas || []).length} personas`,
    });
  } catch (e) {
    checks.push({ name: "Personas list endpoint", passed: false, detail: e.message });
  }

  // ── 4. Learnings endpoint ──
  try {
    const learnings = await api.get("/api/agents/istara-main/learnings");
    checks.push({
      name: "Learnings endpoint returns correct structure",
      passed: learnings.agent_id === "istara-main" && Array.isArray(learnings.learnings),
      detail: `agent_id=${learnings.agent_id}, learnings count=${(learnings.learnings || []).length}`,
    });
  } catch (e) {
    checks.push({ name: "Learnings endpoint", passed: false, detail: e.message });
  }

  // ── 5. CORE.md content structure ──
  for (const agentId of agentIds) {
    try {
      const identity = await api.get(`/api/agents/${agentId}/identity`);
      const core = identity.files?.["CORE.md"] || "";
      checks.push({
        name: `${agentId} CORE.md has Identity section`,
        passed: core.includes("## Identity"),
        detail: core.includes("## Identity") ? "Found" : "Missing",
      });

      const protocols = identity.files?.["PROTOCOLS.md"] || "";
      checks.push({
        name: `${agentId} PROTOCOLS.md has error handling`,
        passed: protocols.toLowerCase().includes("error"),
        detail: "Error handling present",
      });
    } catch (e) {
      checks.push({ name: `${agentId} content structure`, passed: false, detail: e.message });
    }
  }

  // ── 6. MEMORY.md has learnings structure ──
  try {
    const identity = await api.get("/api/agents/istara-main/identity");
    const memory = identity.files?.["MEMORY.md"] || "";
    checks.push({
      name: "Istara MEMORY.md has learnings structure",
      passed: memory.includes("Learnings Log") || memory.includes("Error Patterns"),
      detail: "Structure present",
    });
  } catch (e) {
    checks.push({ name: "MEMORY.md structure", passed: false, detail: e.message });
  }

  // ── 7. Enriched persona files are substantive (80+ lines in CORE.md) ──
  for (const agentId of agentIds) {
    try {
      const identity = await api.get(`/api/agents/${agentId}/identity`);
      const core = identity.files?.["CORE.md"] || "";
      const coreLines = core.split("\n").length;
      checks.push({
        name: `${agentId} CORE.md is enriched (60+ lines)`,
        passed: coreLines >= 60,
        detail: `${coreLines} lines`,
      });
      const skills = identity.files?.["SKILLS.md"] || "";
      const skillLines = skills.split("\n").length;
      checks.push({
        name: `${agentId} SKILLS.md is enriched (30+ lines)`,
        passed: skillLines >= 30,
        detail: `${skillLines} lines`,
      });
    } catch (e) {
      checks.push({ name: `${agentId} enrichment check`, passed: false, detail: e.message });
    }
  }

  // ── 8. PUT identity endpoint exists and works ──
  try {
    const identity = await api.get("/api/agents/istara-main/identity");
    const originalCore = identity.files?.["CORE.md"] || "";
    // Save with marker
    await api.put("/api/agents/istara-main/identity", {
      files: { "CORE.md": originalCore + "\n<!-- test27 -->" },
    });
    const verify = await api.get("/api/agents/istara-main/identity");
    const hasMarker = (verify.files?.["CORE.md"] || "").includes("<!-- test27 -->");
    checks.push({
      name: "PUT identity endpoint works",
      passed: hasMarker,
      detail: hasMarker ? "Update confirmed" : "Update not persisted",
    });
    // Restore
    await api.put("/api/agents/istara-main/identity", {
      files: { "CORE.md": originalCore },
    });
  } catch (e) {
    checks.push({ name: "PUT identity endpoint", passed: false, detail: e.message });
  }

  // ── 9. Agent specialties field present ──
  try {
    const agent = await api.get("/api/agents/istara-main");
    checks.push({
      name: "Agent model has specialties field",
      passed: agent.specialties !== undefined,
      detail: `specialties=${JSON.stringify(agent.specialties)}`,
    });
  } catch (e) {
    checks.push({ name: "Agent specialties field", passed: false, detail: e.message });
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
