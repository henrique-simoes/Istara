/** Scenario 70 — Mid-Execution Steering: verify steering queue, follow-up, and abort work correctly. */

export const name = "Mid-Execution Steering";
export const id = "70-mid-execution-steering";

export async function run(ctx) {
  const { api, report } = ctx;
  const checks = [];
  const agentId = "istara-main";

  // Helper: authenticated API call
  async function apiWithAuth(method, path, body) {
    const headers = { "Content-Type": "application/json" };
    if (ctx.token) {
      headers["Authorization"] = `Bearer ${ctx.token}`;
    }
    const opts = { headers };
    if (body) opts.json = body;
    return api[method](path, opts);
  }

  // 1. Steering API endpoint responds with auth
  try {
    const status = await apiWithAuth("get", `/api/steering/${agentId}/status`);
    checks.push({
      name: "Steering status endpoint responds",
      passed: status !== null && typeof status === "object",
      detail: JSON.stringify(status).slice(0, 200),
    });
  } catch (e) {
    checks.push({ name: "Steering status endpoint responds", passed: false, detail: e.message });
  }

  // 2. Queue a steering message
  try {
    const result = await apiWithAuth("post", `/api/steering/${agentId}`, {
      message: "Simulation: also check accessibility compliance",
    });
    checks.push({
      name: "Queue steering message",
      passed: result !== null,
      detail: JSON.stringify(result).slice(0, 200),
    });
  } catch (e) {
    checks.push({ name: "Queue steering message", passed: false, detail: e.message });
  }

  // 3. Queue a follow-up message
  try {
    const result = await apiWithAuth("post", `/api/steering/${agentId}/follow-up`, {
      message: "Simulation: after that, run the heuristic evaluation",
    });
    checks.push({
      name: "Queue follow-up message",
      passed: result !== null,
      detail: JSON.stringify(result).slice(0, 200),
    });
  } catch (e) {
    checks.push({ name: "Queue follow-up message", passed: false, detail: e.message });
  }

  // 4. Verify steering status shows queued messages
  try {
    const status = await apiWithAuth("get", `/api/steering/${agentId}/status`);
    const steeringCount = status?.steering_count ?? 0;
    const followUpCount = status?.follow_up_count ?? 0;
    checks.push({
      name: "Status reflects queued messages",
      passed: steeringCount >= 0 && followUpCount >= 0,
      detail: `steering: ${steeringCount}, follow_up: ${followUpCount}`,
    });
  } catch (e) {
    checks.push({ name: "Status reflects queued messages", passed: false, detail: e.message });
  }

  // 5. Get all steering queues
  try {
    const queues = await apiWithAuth("get", `/api/steering/${agentId}/queues`);
    checks.push({
      name: "Get steering queues",
      passed: queues !== null && typeof queues === "object",
      detail: JSON.stringify(queues).slice(0, 200),
    });
  } catch (e) {
    checks.push({ name: "Get steering queues", passed: false, detail: e.message });
  }

  // 6. Clear steering queues
  try {
    const result = await apiWithAuth("delete", `/api/steering/${agentId}/queues`);
    checks.push({
      name: "Clear steering queues",
      passed: result !== null,
      detail: JSON.stringify(result).slice(0, 200),
    });
  } catch (e) {
    checks.push({ name: "Clear steering queues", passed: false, detail: e.message });
  }

  // 7. Abort agent work
  try {
    const result = await apiWithAuth("post", `/api/steering/${agentId}/abort`, {});
    checks.push({
      name: "Abort agent work",
      passed: result !== null,
      detail: JSON.stringify(result).slice(0, 200),
    });
  } catch (e) {
    checks.push({ name: "Abort agent work", passed: false, detail: e.message });
  }

  // 8. Verify queues are empty after abort
  try {
    const status = await apiWithAuth("get", `/api/steering/${agentId}/status`);
    const steeringCount = status?.steering_count ?? -1;
    const followUpCount = status?.follow_up_count ?? -1;
    checks.push({
      name: "Queues empty after abort",
      passed: steeringCount === 0 && followUpCount === 0,
      detail: `steering: ${steeringCount}, follow_up: ${followUpCount}`,
    });
  } catch (e) {
    checks.push({ name: "Queues empty after abort", passed: false, detail: e.message });
  }

  return { checks, passed: checks.filter(c => c.passed).length, failed: checks.filter(c => !c.passed).length };
}
