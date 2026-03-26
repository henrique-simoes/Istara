/** Scenario 44 — Agent Factory: test automatic agent creation proposals and specialties. */

export const name = "Agent Factory";
export const id = "44-agent-factory";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // ── 1. GET pending agent creation proposals ──
  try {
    const res = await fetch("http://localhost:8000/api/agents/creation-proposals/pending");
    checks.push({
      name: "GET /api/agents/creation-proposals/pending responds",
      passed: res.status === 200 || res.status === 404,
      detail: `status=${res.status}`,
    });
    if (res.ok) {
      const data = await res.json();
      checks.push({
        name: "Pending agent proposals returns array",
        passed: Array.isArray(data.proposals || data),
        detail: `count=${(data.proposals || data).length}`,
      });
    }
  } catch (e) {
    checks.push({ name: "GET pending agent proposals", passed: false, detail: e.message });
  }

  // ── 2. GET all agent creation proposals ──
  try {
    const res = await fetch("http://localhost:8000/api/agents/creation-proposals/all");
    checks.push({
      name: "GET /api/agents/creation-proposals/all responds",
      passed: res.status === 200 || res.status === 404,
      detail: `status=${res.status}`,
    });
    if (res.ok) {
      const data = await res.json();
      checks.push({
        name: "All agent proposals returns array",
        passed: Array.isArray(data.proposals || data),
        detail: `count=${(data.proposals || data).length}`,
      });
    }
  } catch (e) {
    checks.push({ name: "GET all agent proposals", passed: false, detail: e.message });
  }

  // ── 3. POST approve nonexistent agent proposal → 404 ──
  try {
    const res = await fetch("http://localhost:8000/api/agents/creation-proposals/nonexistent/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    checks.push({
      name: "Approve nonexistent agent proposal returns 404",
      passed: res.status === 404,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Approve nonexistent agent proposal", passed: false, detail: e.message });
  }

  // ── 4. POST reject nonexistent agent proposal → 404 ──
  try {
    const res = await fetch("http://localhost:8000/api/agents/creation-proposals/nonexistent/reject", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    checks.push({
      name: "Reject nonexistent agent proposal returns 404",
      passed: res.status === 404,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Reject nonexistent agent proposal", passed: false, detail: e.message });
  }

  // ── 5. GET /api/agents returns agents with specialties field ──
  let agents = [];
  try {
    const data = await api.get("/api/agents");
    agents = data.agents || [];
    checks.push({
      name: "GET /api/agents returns agents list",
      passed: Array.isArray(agents) && agents.length > 0,
      detail: `${agents.length} agents found`,
    });
  } catch (e) {
    checks.push({ name: "GET /api/agents", passed: false, detail: e.message });
  }

  // ── 6. System agents have specialties defined ──
  if (agents.length > 0) {
    const systemAgents = agents.filter((a) =>
      a.id?.startsWith("reclaw-") || a.role === "system"
    );
    const withSpecialties = systemAgents.filter(
      (a) => Array.isArray(a.specialties) && a.specialties.length > 0
    );
    checks.push({
      name: "System agents have specialties defined",
      passed: withSpecialties.length > 0,
      detail: `${withSpecialties.length}/${systemAgents.length} system agents have specialties`,
    });

    // Verify specialties are strings
    if (withSpecialties.length > 0) {
      const first = withSpecialties[0];
      checks.push({
        name: "Specialties are string arrays",
        passed: first.specialties.every((s) => typeof s === "string"),
        detail: `${first.id}: [${first.specialties.slice(0, 3).join(", ")}]`,
      });
    }
  } else {
    checks.push({ name: "System agents have specialties", passed: false, detail: "No agents found" });
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
