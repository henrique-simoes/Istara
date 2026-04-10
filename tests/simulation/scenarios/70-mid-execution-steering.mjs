/** Scenario 70 — Mid-Execution Steering: verify steering message injection, follow-up queues, abort, and API endpoints. */

export const name = "Mid-Execution Steering";
export const id = "70-mid-execution-steering";

export async function run(ctx) {
  const { api, page, report } = ctx;
  const checks = [];

  // 1. Queue a steering message
  try {
    const resp = await api.post("/api/steering/istara-main", {
      message: "Check the new UI for WCAG contrast issues",
      mode: "one-at-a-time",
    });
    checks.push({
      name: "Queue steering message",
      passed: resp.status === "queued" && resp.queue_count >= 1,
      detail: JSON.stringify(resp),
    });
  } catch (e) {
    checks.push({ name: "Queue steering message", passed: false, detail: e.message });
  }

  // 2. Queue a follow-up message
  try {
    const resp = await api.post("/api/steering/istara-main/follow-up", {
      message: "Run final accessibility audit after all tasks complete",
    });
    checks.push({
      name: "Queue follow-up message",
      passed: resp.status === "queued" && resp.queue_count >= 1,
      detail: JSON.stringify(resp),
    });
  } catch (e) {
    checks.push({ name: "Queue follow-up message", passed: false, detail: e.message });
  }

  // 3. Get steering status
  try {
    const status = await api.get("/api/steering/istara-main/status");
    checks.push({
      name: "Get steering status",
      passed: status.steering_queue_count >= 1 && status.follow_up_queue_count >= 1,
      detail: `Steering: ${status.steering_queue_count}, Follow-up: ${status.follow_up_queue_count}`,
    });
  } catch (e) {
    checks.push({ name: "Get steering status", passed: false, detail: e.message });
  }

  // 4. Get steering queues — verify message content
  try {
    const queues = await api.get("/api/steering/istara-main/queues");
    const hasSteer = queues.steering_queue.some((m) => m.message.includes("WCAG"));
    const hasFollow = queues.follow_up_queue.some((m) => m.message.includes("accessibility"));
    checks.push({
      name: "Get steering queues with content",
      passed: hasSteer && hasFollow,
      detail: `Steering: ${queues.steering_queue.length}, Follow-up: ${queues.follow_up_queue.length}`,
    });
  } catch (e) {
    checks.push({ name: "Get steering queues", passed: false, detail: e.message });
  }

  // 5. Abort clears queues
  try {
    const abortResp = await api.post("/api/steering/istara-main/abort", {});
    const afterStatus = await api.get("/api/steering/istara-main/status");
    checks.push({
      name: "Abort clears queues",
      passed: abortResp.cleared_steering_count >= 1 && afterStatus.steering_queue_count === 0 && afterStatus.follow_up_queue_count === 0,
      detail: `Cleared: steering=${abortResp.cleared_steering_count}, follow-up=${abortResp.cleared_follow_up_count}`,
    });
  } catch (e) {
    checks.push({ name: "Abort clears queues", passed: false, detail: e.message });
  }

  // 6. Clear queues endpoint
  try {
    await api.post("/api/steering/istara-main", { message: "test msg" });
    const clearResp = await api.delete("/api/steering/istara-main/queues");
    checks.push({
      name: "Clear queues endpoint",
      passed: clearResp.status === "cleared",
      detail: JSON.stringify(clearResp),
    });
  } catch (e) {
    checks.push({ name: "Clear queues endpoint", passed: false, detail: e.message });
  }

  // 7. Unknown agent returns 404
  try {
    await api.post("/api/steering/nonexistent-agent", { message: "test" });
    checks.push({ name: "Unknown agent returns 404", passed: false, detail: "Expected 404" });
  } catch (e) {
    checks.push({
      name: "Unknown agent returns 404",
      passed: e.message.includes("404"),
      detail: e.message,
    });
  }

  // 8. Frontend SteeringInput renders on Agents view
  try {
    await page.goto("http://localhost:3000", { waitUntil: "networkidle", timeout: 15000 });
    // Look for the steering input placeholder text
    const inputExists = await page.getByPlaceholder(/steering message|follow-up message/i)
      .isVisible({ timeout: 5000 })
      .catch(() => false);
    checks.push({
      name: "SteeringInput visible on Agents view",
      passed: inputExists,
      detail: inputExists ? "Steering input found" : "Steering input not visible (agent may be idle)",
    });
  } catch (e) {
    checks.push({ name: "SteeringInput visible on Agents view", passed: false, detail: e.message });
  }

  // Report results
  const passed = checks.filter((c) => c.passed).length;
  const total = checks.length;
  report(name, checks);
  console.log(`  ✅ ${passed}/${total} steering checks passed`);

  return checks;
}
