/** Scenario 41 — Autonomous Skill Creation: test skill creation proposal system and registry. */

export const name = "Autonomous Skill Creation";
export const id = "41-skill-creation";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // ── 1. GET pending skill creation proposals ──
  try {
    const res = await fetch(`http://localhost:8000/api/skills/creation-proposals/pending`, { headers: api._headers() });
    checks.push({
      name: "GET /api/skills/creation-proposals/pending responds",
      passed: res.status === 200 || res.status === 404,
      detail: `status=${res.status}`,
    });
    if (res.ok) {
      const data = await res.json();
      checks.push({
        name: "Pending proposals returns array",
        passed: Array.isArray(data.proposals || data),
        detail: `type=${typeof data}`,
      });
    }
  } catch (e) {
    checks.push({ name: "GET pending proposals", passed: false, detail: e.message });
  }

  // ── 2. GET all skill creation proposals ──
  try {
    const res = await fetch(`http://localhost:8000/api/skills/creation-proposals/all`, { headers: api._headers() });
    checks.push({
      name: "GET /api/skills/creation-proposals/all responds",
      passed: res.status === 200 || res.status === 404,
      detail: `status=${res.status}`,
    });
    if (res.ok) {
      const data = await res.json();
      checks.push({
        name: "All proposals returns array",
        passed: Array.isArray(data.proposals || data),
        detail: `count=${(data.proposals || data).length}`,
      });
    }
  } catch (e) {
    checks.push({ name: "GET all proposals", passed: false, detail: e.message });
  }

  // ── 3. POST reject nonexistent proposal → 404 ──
  try {
    const res = await fetch(`http://localhost:8000/api/skills/creation-proposals/nonexistent/reject`, {
      method: "POST",
      headers: api._headers(),
      body: JSON.stringify({}),
    });
    checks.push({
      name: "Reject nonexistent proposal returns 404",
      passed: res.status === 404,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Reject nonexistent proposal", passed: false, detail: e.message });
  }

  // ── 4. POST approve nonexistent proposal → 404 ──
  try {
    const res = await fetch(`http://localhost:8000/api/skills/creation-proposals/nonexistent/approve`, {
      method: "POST",
      headers: api._headers(),
      body: JSON.stringify({}),
    });
    checks.push({
      name: "Approve nonexistent proposal returns 404",
      passed: res.status === 404,
      detail: `status=${res.status}`,
    });
  } catch (e) {
    checks.push({ name: "Approve nonexistent proposal", passed: false, detail: e.message });
  }

  // ── 5. Skill registry — GET /api/skills returns skills list ──
  try {
    const skills = await api.get("/api/skills");
    const skillList = skills.skills || skills;
    checks.push({
      name: "Skill registry returns skills list",
      passed: Array.isArray(skillList) && skillList.length > 0,
      detail: `${skillList.length} skills registered`,
    });
    // Verify skills have expected structure
    if (skillList.length > 0) {
      const first = skillList[0];
      checks.push({
        name: "Skills have name and phase fields",
        passed: !!first.name && !!first.phase,
        detail: `first=${first.name}, phase=${first.phase}`,
      });
    }
  } catch (e) {
    checks.push({ name: "Skill registry", passed: false, detail: e.message });
  }

  // ── 6. GET /api/skills/health/all returns health data ──
  try {
    const res = await fetch(`http://localhost:8000/api/skills/health/all`, { headers: api._headers() });
    checks.push({
      name: "GET /api/skills/health/all responds",
      passed: res.status === 200 || res.status === 404,
      detail: `status=${res.status}`,
    });
    if (res.ok) {
      const data = await res.json();
      checks.push({
        name: "Skills health returns data",
        passed: data !== null && typeof data === "object",
        detail: `keys=${Object.keys(data).slice(0, 5).join(", ")}`,
      });
    }
  } catch (e) {
    checks.push({ name: "Skills health endpoint", passed: false, detail: e.message });
  }

  return {
    checks,
    passed: checks.filter((c) => c.passed).length,
    failed: checks.filter((c) => !c.passed).length,
    summary: checks.map((c) => `${c.passed ? "PASS" : "FAIL"} ${c.name}`).join("\n"),
  };
}
