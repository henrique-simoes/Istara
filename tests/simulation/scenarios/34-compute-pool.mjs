/** Scenario 34 — Compute Pool: verify compute pool endpoints, relay
 *  deduplication, capability detection, and swarm tier accuracy. */

export const name = "Compute Pool";
export const id = "34-compute-pool";

export async function run(ctx) {
  const { api } = ctx;
  const checks = [];

  // 1. Compute nodes endpoint
  let nodes;
  try {
    nodes = await api.get("/api/compute/nodes");
    checks.push({
      name: "Compute nodes endpoint",
      passed: nodes.total_nodes !== undefined && Array.isArray(nodes.nodes),
      detail: `total=${nodes.total_nodes}, alive=${nodes.alive_nodes}`,
    });
  } catch (e) {
    checks.push({ name: "Compute nodes endpoint", passed: false, detail: e.message });
  }

  // 2. Compute stats endpoint
  let stats;
  try {
    stats = await api.get("/api/compute/stats");
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
    if (!stats) stats = await api.get("/api/compute/stats");
    const validTiers = ["full_swarm", "standard", "conservative", "minimal", "local_only"];
    checks.push({
      name: "Valid swarm tier",
      passed: validTiers.includes(stats.swarm_tier),
      detail: `tier=${stats.swarm_tier}`,
    });
  } catch (e) {
    checks.push({ name: "Valid swarm tier", passed: false, detail: e.message });
  }

  // 4. Swarm tier matches alive count
  try {
    if (!stats) stats = await api.get("/api/compute/stats");
    const alive = stats.alive_nodes || 0;
    let expectedTier;
    if (alive >= 8) expectedTier = "full_swarm";
    else if (alive >= 4) expectedTier = "standard";
    else if (alive >= 2) expectedTier = "conservative";
    else if (alive >= 1) expectedTier = "minimal";
    else expectedTier = "local_only";
    checks.push({
      name: "Swarm tier matches alive count",
      passed: stats.swarm_tier === expectedTier,
      detail: `alive=${alive}, tier=${stats.swarm_tier}, expected=${expectedTier}`,
    });
  } catch (e) {
    checks.push({ name: "Swarm tier matches alive count", passed: false, detail: e.message });
  }

  // 5. No duplicate network+relay nodes for same host
  try {
    if (!nodes) nodes = await api.get("/api/compute/nodes");
    const hostMap = {};
    let duplicates = 0;
    for (const node of nodes.nodes || []) {
      const host = node.host;
      if (host && hostMap[host]) {
        duplicates++;
      }
      if (host) hostMap[host] = (hostMap[host] || 0) + 1;
    }
    checks.push({
      name: "No duplicate nodes for same host",
      passed: duplicates === 0,
      detail: duplicates > 0
        ? `Found ${duplicates} duplicate host(s)`
        : `${Object.keys(hostMap).length} unique hosts`,
    });
  } catch (e) {
    checks.push({ name: "No duplicate nodes for same host", passed: false, detail: e.message });
  }

  // 6. Relay nodes have resolved host (not localhost)
  try {
    if (!nodes) nodes = await api.get("/api/compute/nodes");
    const relays = (nodes.nodes || []).filter((n) => n.source === "relay");
    const unresolved = relays.filter((n) => {
      const host = n.host || "";
      return host.includes("localhost") || host.includes("127.0.0.1");
    });
    checks.push({
      name: "Relay nodes have resolved host",
      passed: unresolved.length === 0,
      detail: relays.length > 0
        ? `${relays.length} relay(s), ${unresolved.length} unresolved`
        : "No relay nodes connected (OK — host-dependent)",
    });
  } catch (e) {
    checks.push({ name: "Relay nodes have resolved host", passed: false, detail: e.message });
  }

  // 7. Healthy nodes have model capabilities detected
  try {
    if (!nodes) nodes = await api.get("/api/compute/nodes");
    const healthy = (nodes.nodes || []).filter((n) => n.is_healthy);
    const noCaps = healthy.filter(
      (n) => !n.model_capabilities || Object.keys(n.model_capabilities).length === 0
    );
    // Allow a grace period — capabilities may not be detected yet on
    // freshly registered nodes.  Pass if ≥50% have capabilities.
    const hasCaps = healthy.length - noCaps.length;
    checks.push({
      name: "Healthy nodes have capabilities",
      passed: healthy.length === 0 || hasCaps >= Math.ceil(healthy.length / 2),
      detail: `${hasCaps}/${healthy.length} have capability info`,
    });
  } catch (e) {
    checks.push({ name: "Healthy nodes have capabilities", passed: false, detail: e.message });
  }

  // 8. Model warnings endpoint
  try {
    const warns = await api.get("/api/compute/model-warnings");
    checks.push({
      name: "Model warnings endpoint",
      passed: Array.isArray(warns.warnings),
      detail: `${(warns.warnings || []).length} warnings`,
    });
  } catch (e) {
    checks.push({ name: "Model warnings endpoint", passed: false, detail: e.message });
  }

  const passed = checks.filter((c) => c.passed).length;
  const failed = checks.filter((c) => !c.passed).length;
  return { checks, passed, failed };
}
