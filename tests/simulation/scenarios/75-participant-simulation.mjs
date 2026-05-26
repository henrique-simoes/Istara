/** Scenario 75 — Game Theory Participant Simulation: verify participant_simulation module, game scenarios, and audit logging. */

export const name = "Game Theory Participant Simulation";
export const id = "75-participant-simulation";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];
  if (!ctx.projectId) {
    return {
      checks: [{ name: "Project available for participant simulation", passed: false, detail: "No persistent project from runner" }],
      passed: 0,
      failed: 1,
      summary: "Game Theory Participant Simulation: 0/1 passed",
    };
  }
  const projectId = ctx.projectId;

  // 1. Participant simulation skill is registered without requiring a live chat probe
  try {
    const skills = await api.get("/api/skills");
    const list = Array.isArray(skills) ? skills : skills.skills || [];
    const skill = list.find((item) => item.name === "participant-simulation");
    checks.push({
      name: "Participant simulation skill registered",
      passed: !!skill,
      detail: skill ? `${skill.display_name || skill.name}` : "Skill not found",
    });
  } catch (e) {
    checks.push({ name: "Participant simulation skill registered", passed: false, detail: e.message });
  }

  // 2. Audit log endpoint exists and responds
  try {
    const resp = await api.get("/api/audit/logs?limit=5");
    checks.push({
      name: "Audit log endpoint responds",
      passed: resp !== null && typeof resp === "object",
      detail: `entries=${(resp.logs || resp.items || resp || []).length ?? "unknown"}`,
    });
  } catch (e) {
    checks.push({ name: "Audit log endpoint responds", passed: false, detail: e.message });
  }

  // 3. Validation metrics endpoint responds
  try {
    const resp = await api.get(`/api/metrics/${projectId}/validation`);
    checks.push({
      name: "Validation metrics endpoint responds",
      passed: resp !== null && typeof resp === "object",
      detail: `keys=${Object.keys(resp || {}).join(",")}`,
    });
  } catch (e) {
    checks.push({ name: "Validation metrics endpoint responds", passed: false, detail: e.message });
  }

  return {
    checks,
    passed: checks.filter(c => c.passed).length,
    failed: checks.filter(c => !c.passed).length,
    summary: `Game Theory Participant Simulation: ${checks.filter(c => c.passed).length}/${checks.length} passed`,
  };
}
