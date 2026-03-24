"use client";

import { useEffect } from "react";
import { Cpu, HardDrive, Wifi, WifiOff, Server, Zap } from "lucide-react";
import { useComputeStore } from "@/stores/computeStore";
import { cn } from "@/lib/utils";

const SWARM_TIERS: Record<string, { label: string; color: string; description: string }> = {
  full_swarm: {
    label: "Full Swarm",
    color: "text-green-600 bg-green-50 dark:text-green-400 dark:bg-green-900/20",
    description: "8+ nodes — maximum parallel agent capacity",
  },
  standard: {
    label: "Standard",
    color: "text-blue-600 bg-blue-50 dark:text-blue-400 dark:bg-blue-900/20",
    description: "4-7 nodes — good parallel capacity",
  },
  conservative: {
    label: "Conservative",
    color: "text-amber-600 bg-amber-50 dark:text-amber-400 dark:bg-amber-900/20",
    description: "2-3 nodes — limited parallel capacity",
  },
  minimal: {
    label: "Minimal",
    color: "text-orange-600 bg-orange-50 dark:text-orange-400 dark:bg-orange-900/20",
    description: "1 node — single-threaded execution",
  },
  local_only: {
    label: "Local Only",
    color: "text-slate-600 bg-slate-50 dark:text-slate-400 dark:bg-slate-800",
    description: "No relay nodes — using local compute only",
  },
};

export default function ComputePoolView() {
  const { stats, loading, fetchStats } = useComputeStore();

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  const tier = stats?.swarm_tier
    ? SWARM_TIERS[stats.swarm_tier] || SWARM_TIERS.local_only
    : SWARM_TIERS.local_only;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Compute Pool</h2>
        <p className="text-sm text-slate-500 mt-1">
          Connected relay nodes donating LLM compute power
        </p>
      </div>

      {/* Swarm Tier */}
      <div className={cn("rounded-lg p-4 border", tier.color.includes("bg-") ? "" : "bg-slate-50 dark:bg-slate-800/50", tier.color.split(" ").filter(c => c.startsWith("bg-") || c.startsWith("dark:bg-")).join(" "))}>
        <div className="flex items-center gap-3">
          <Zap size={24} className={tier.color.split(" ").filter(c => c.startsWith("text-") || c.startsWith("dark:text-")).join(" ")} />
          <div>
            <div className={cn("text-lg font-bold", tier.color.split(" ").filter(c => c.startsWith("text-") || c.startsWith("dark:text-")).join(" "))}>
              {tier.label}
            </div>
            <div className="text-sm text-slate-500">{tier.description}</div>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon={Server}
          label="Total Nodes"
          value={stats?.total_nodes || 0}
          sub={`${stats?.alive_nodes || 0} alive`}
        />
        <StatCard
          icon={HardDrive}
          label="Total RAM"
          value={`${stats?.total_ram_gb?.toFixed(1) || 0} GB`}
          sub={`${stats?.available_ram_gb?.toFixed(1) || 0} GB free`}
        />
        <StatCard
          icon={Cpu}
          label="CPU Cores"
          value={stats?.total_cpu_cores || 0}
        />
        <StatCard
          icon={Zap}
          label="Models"
          value={stats?.available_models?.length || 0}
          sub="across pool"
        />
      </div>

      {/* Available Models */}
      {stats?.available_models && stats.available_models.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
            Available Models
          </h3>
          <div className="flex flex-wrap gap-2">
            {stats.available_models.map((model) => (
              <span
                key={model}
                className="px-2 py-1 text-xs rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
              >
                {model}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Node List */}
      <div>
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
          Connected Nodes
        </h3>
        {stats?.nodes && stats.nodes.length > 0 ? (
          <div className="space-y-2">
            {stats.nodes.map((node) => (
              <div
                key={node.node_id}
                className="flex items-center gap-4 p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700"
              >
                <div className="flex items-center gap-2">
                  {node.alive ? (
                    <Wifi size={16} className="text-green-500" aria-label="Online" />
                  ) : (
                    <WifiOff size={16} className="text-red-500" aria-label="Offline" />
                  )}
                </div>
                <div className="flex-1">
                  <div className="font-medium text-slate-900 dark:text-white">{node.hostname}</div>
                  <div className="text-xs text-slate-500">
                    {node.state} | {node.loaded_models?.join(", ") || "no models"}
                  </div>
                </div>
                <div className="text-right text-sm">
                  <div className="text-slate-600 dark:text-slate-400">
                    {node.ram_available_gb?.toFixed(1)} GB free
                  </div>
                  <div className="text-xs text-slate-400">
                    CPU {node.cpu_load_pct?.toFixed(0)}% | Score {node.score?.toFixed(2)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-slate-400">
            <Server size={40} className="mx-auto mb-2 opacity-30" />
            <p>No relay nodes connected</p>
            <p className="text-xs mt-1">
              Run <code className="bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded">reclaw-relay --server ws://your-server:8000/ws/relay</code> on team machines
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: any;
  label: string;
  value: string | number;
  sub?: string;
}) {
  return (
    <div className="p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
      <div className="flex items-center gap-2 text-slate-500 mb-1">
        <Icon size={14} />
        <span className="text-xs">{label}</span>
      </div>
      <div className="text-2xl font-bold text-slate-900 dark:text-white">{value}</div>
      {sub && <div className="text-xs text-slate-400">{sub}</div>}
    </div>
  );
}
