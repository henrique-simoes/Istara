/**
 * Heartbeat — sends system stats to the server periodically.
 */

import { hostname } from "os";
import { cpus, totalmem, freemem } from "os";

export async function getSystemStats() {
  const stats = {
    hostname: hostname(),
    ram_total_gb: Math.round(totalmem() / (1024 ** 3) * 10) / 10,
    ram_available_gb: Math.round(freemem() / (1024 ** 3) * 10) / 10,
    cpu_cores: cpus().length,
    cpu_load_pct: 0,
    gpu_name: "",
    gpu_vram_mb: 0,
  };

  // Try to get detailed stats with systeminformation
  try {
    const si = await import("systeminformation");
    const load = await si.default.currentLoad();
    stats.cpu_load_pct = Math.round(load.currentLoad * 10) / 10;

    const gpu = await si.default.graphics();
    if (gpu.controllers && gpu.controllers.length > 0) {
      const g = gpu.controllers[0];
      stats.gpu_name = g.model || "";
      stats.gpu_vram_mb = g.vram || 0;
    }
  } catch {
    // systeminformation is optional — use basic os module data
    const cpuInfo = cpus();
    if (cpuInfo.length > 0) {
      const total = cpuInfo.reduce((sum, c) => {
        const t = Object.values(c.times).reduce((a, b) => a + b, 0);
        return sum + (t - c.times.idle) / t;
      }, 0);
      stats.cpu_load_pct = Math.round(total / cpuInfo.length * 100 * 10) / 10;
    }
  }

  return stats;
}

export function startHeartbeat(ws, intervalMs, llmProxy) {
  setInterval(async () => {
    try {
      const stats = await getSystemStats();
      const models = await llmProxy.listModels();

      ws.send(JSON.stringify({
        type: "heartbeat",
        stats: {
          ram_available_gb: stats.ram_available_gb,
          cpu_load_pct: stats.cpu_load_pct,
          loaded_models: models,
          state: "idle",
        },
      }));
    } catch {
      // Ignore heartbeat errors
    }
  }, intervalMs);
}
