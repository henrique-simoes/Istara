/**
 * Heartbeat — sends system stats to the server periodically.
 *
 * Uses vm_stat on macOS for accurate available memory (freemem() only
 * reports truly free pages, ignoring reclaimable cache).
 */

import { hostname } from "os";
import { cpus, totalmem, freemem, platform } from "os";
import { execSync } from "child_process";

/**
 * Get available RAM in bytes — macOS-aware.
 *
 * Node's os.freemem() on macOS returns only "free" pages, which is
 * near-zero because macOS aggressively caches files. The actual
 * available memory = free + inactive + purgeable (reclaimable cache).
 */
function getAvailableMemory() {
  if (platform() === "darwin") {
    try {
      const vmStat = execSync("vm_stat", { encoding: "utf-8" });
      const pageSize = 16384; // Default on Apple Silicon; 4096 on Intel
      // Try to detect page size from output
      const pageSizeMatch = vmStat.match(/page size of (\d+) bytes/);
      const actualPageSize = pageSizeMatch ? parseInt(pageSizeMatch[1]) : pageSize;

      const parse = (label) => {
        const match = vmStat.match(new RegExp(`${label}:\\s+(\\d+)`));
        return match ? parseInt(match[1]) * actualPageSize : 0;
      };

      const free = parse("Pages free");
      const inactive = parse("Pages inactive");
      const purgeable = parse("Pages purgeable");
      // Available = free + inactive + purgeable (what macOS can reclaim)
      return free + inactive + purgeable;
    } catch {
      // Fallback to Node's freemem
      return freemem();
    }
  }
  // Linux/Windows: freemem() is accurate
  return freemem();
}

export async function getSystemStats() {
  const stats = {
    hostname: hostname(),
    ram_total_gb: Math.round(totalmem() / (1024 ** 3) * 10) / 10,
    ram_available_gb: Math.round(getAvailableMemory() / (1024 ** 3) * 10) / 10,
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
