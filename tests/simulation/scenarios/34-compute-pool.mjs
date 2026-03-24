/** Scenario 34 — Compute Pool: verify compute pool endpoints. */

export const name = "Compute Pool";
export const id = "34-compute-pool";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // 1. Compute nodes endpoint
  try {
    const nodes = await api.get("/api/compute/nodes");
    checks.push({
      name: "Compute nodes endpoint",
      passed: nodes.total_nodes !== undefined && Array.isArray(nodes.nodes),
      detail: `total=${nodes.total_nodes}, alive=${nodes.alive_nodes}`,
    });
  } catch (e) {
    checks.push({ name: "Compute nodes endpoint", passed: false, detail: e.message });
  }

  // 2. Compute stats endpoint
  try {
    const stats = await api.get("/api/compute/stats");
    checks.push({
      name: "Compute stats endpoint",
      passed: stats.swarm_tier !== undefined,
      detail: `tier=${stats.swarm_tier}, nodes=${stats.alive_nodes}`,
    });
  } catch (e) {
    checks.push({ name: "Compute stats endpoint", passed: false, detail: e.message });
  }

  // 3. Swarm tier is valid
  try {
    const stats = await api.get("/api/compute/stats");
    const validTiers = ["full_swarm", "standard", "conservative", "minimal", "local_only"];
    checks.push({
      name: "Valid swarm tier",
      passed: validTiers.includes(stats.swarm_tier),
      detail: `tier=${stats.swarm_tier}`,
    });
  } catch (e) {
    checks.push({ name: "Valid swarm tier", passed: false, detail: e.message });
  }

  const passed = checks.filter((c) => c.passed).length;
  const failed = checks.filter((c) => !c.passed).length;
  return { checks, passed, failed };
}
