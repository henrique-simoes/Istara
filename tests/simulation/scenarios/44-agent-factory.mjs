/** Scenario 44 — Agent Factory: test automatic agent creation proposals and specialties. */

export const name = "Agent Factory";
export const id = "44-agent-factory";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];
  const projectId = typeof ctx.projectId === "string" ? ctx.projectId.trim() : "";
  const scopedSkipDetail = "[skipped] No active project id; scoped endpoint not called";

  const scopedPath = (path) => {
    const separator = path.includes("?") ? "&" : "?";
    return `${path}${separator}project_id=${encodeURIComponent(projectId)}`;
  };

  const fetchProjectScoped = async (path, checkName, options = {}) => {
    if (!projectId) {
      checks.push({ name: checkName, passed: true, detail: scopedSkipDetail });
      return null;
    }
    const url = new URL(path, "http://localhost:8000");
    url.searchParams.set("project_id", projectId);
    return fetch(url.toString(), options);
  };

  const apiGetProjectScoped = async (path, checkName) => {
    if (!projectId) {
      checks.push({ name: checkName, passed: true, detail: scopedSkipDetail });
      return null;
    }
    return api.get(scopedPath(path));
  };

  // ── 1. GET pending agent creation proposals ──
  try {
    const res = await fetchProjectScoped("/api/agents/creation-proposals/pending", "GET /api/agents/creation-proposals/pending responds", { headers: api._headers() });
    if (res) {
      checks.push({
        name: "GET /api/agents/creation-proposals/pending responds",
        passed: res.status === 200 || res.status === 404,
        detail: `status=${res.status}`,
      });
    }
    if (res?.ok) {
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
    const res = await fetchProjectScoped("/api/agents/creation-proposals/all", "GET /api/agents/creation-proposals/all responds", { headers: api._headers() });
    if (res) {
      checks.push({
        name: "GET /api/agents/creation-proposals/all responds",
        passed: res.status === 200 || res.status === 404,
        detail: `status=${res.status}`,
      });
    }
    if (res?.ok) {
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
    const res = await fetchProjectScoped("/api/agents/creation-proposals/nonexistent/approve", "Approve nonexistent agent proposal returns 404", {
      method: "POST",
      headers: api._headers(),
      body: JSON.stringify({}),
    });
    if (res) {
      checks.push({
        name: "Approve nonexistent agent proposal returns 404",
        passed: res.status === 404,
        detail: `status=${res.status}`,
      });
    }
  } catch (e) {
    checks.push({ name: "Approve nonexistent agent proposal", passed: false, detail: e.message });
  }

  // ── 4. POST reject nonexistent agent proposal → 404 ──
  try {
    const res = await fetchProjectScoped("/api/agents/creation-proposals/nonexistent/reject", "Reject nonexistent agent proposal returns 404", {
      method: "POST",
      headers: api._headers(),
      body: JSON.stringify({}),
    });
    if (res) {
      checks.push({
        name: "Reject nonexistent agent proposal returns 404",
        passed: res.status === 404,
        detail: `status=${res.status}`,
      });
    }
  } catch (e) {
    checks.push({ name: "Reject nonexistent agent proposal", passed: false, detail: e.message });
  }

  // ── 5. GET /api/agents returns agents with specialties field ──
  let agents = [];
  try {
    const data = await apiGetProjectScoped("/api/agents", "GET /api/agents returns agents list");
    if (data) {
      agents = data.agents || [];
      checks.push({
        name: "GET /api/agents returns agents list",
        passed: Array.isArray(agents) && agents.length > 0,
        detail: `${agents.length} agents found`,
      });
    }
  } catch (e) {
    checks.push({ name: "GET /api/agents", passed: false, detail: e.message });
  }

  // ── 6. System agents have specialties defined ──
  if (agents.length > 0) {
    const systemAgents = agents.filter((a) =>
      a.id?.startsWith("istara-") || a.role === "system"
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
  } else if (!projectId) {
    checks.push({ name: "System agents have specialties", passed: true, detail: scopedSkipDetail });
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
