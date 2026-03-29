"use client";

import { useEffect, useState } from "react";
import {
  Cpu,
  HardDrive,
  Wifi,
  WifiOff,
  Server,
  Zap,
  AlertTriangle,
  Camera,
  Wrench,
  Globe,
  Monitor,
  Radio,
} from "lucide-react";
import { useComputeStore } from "@/stores/computeStore";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

const SOURCE_BADGES: Record<string, { label: string; icon: typeof Monitor; className: string }> = {
  local: {
    label: "Local",
    icon: Monitor,
    className: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  },
  network: {
    label: "Network",
    icon: Globe,
    className: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  },
  relay: {
    label: "Relay",
    icon: Radio,
    className: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  },
};

interface ModelWarning {
  model: string;
  server: string;
  warning: string;
  severity: "high" | "medium" | "low";
}

export default function ComputePoolView() {
  const { stats, loading, fetchStats } = useComputeStore();
  const [warnings, setWarnings] = useState<ModelWarning[]>([]);
  const [showWarnings, setShowWarnings] = useState(false);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 15000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  useEffect(() => {
    const token = localStorage.getItem("reclaw_token");
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    fetch(`${API_BASE}/api/compute/model-warnings`, { headers })
      .then((r) => r.json())
      .then((d) => setWarnings(d.warnings || []))
      .catch(() => {});
  }, []);

  const tier = stats?.swarm_tier
    ? SWARM_TIERS[stats.swarm_tier] || SWARM_TIERS.local_only
    : SWARM_TIERS.local_only;

  return (
    <div className="flex-1 overflow-y-auto">
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Compute Pool</h2>
        <p className="text-sm text-slate-500 mt-1">
          LLM servers and relay nodes powering your agent compute
        </p>
      </div>

      {/* Model Warnings — collapsed summary */}
      {warnings.length > 0 && (
        <div role="alert" aria-label="Model warnings">
          <button
            onClick={() => setShowWarnings(!showWarnings)}
            className="w-full flex items-center justify-between p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 text-sm hover:bg-amber-100 dark:hover:bg-amber-900/30 transition-colors"
          >
            <div className="flex items-center gap-2">
              <AlertTriangle size={14} />
              <span className="font-medium">{warnings.length} model warning{warnings.length !== 1 ? "s" : ""}</span>
              <span className="text-amber-500 dark:text-amber-400">
                — {warnings.filter(w => w.severity === "high").length} high, {warnings.filter(w => w.severity === "medium").length} medium
              </span>
            </div>
            <span className="text-xs">{showWarnings ? "Hide" : "Show details"}</span>
          </button>
          {showWarnings && (
          <div className="mt-2 space-y-1.5">
          {warnings.map((w, i) => (
            <div
              key={i}
              className={cn(
                "flex items-start gap-2 p-2 rounded-lg text-xs",
                w.severity === "high"
                  ? "bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300"
                  : w.severity === "medium"
                    ? "bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300"
                    : "bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300"
              )}
            >
              <AlertTriangle size={12} className="shrink-0 mt-0.5" aria-hidden="true" />
              <div>
                <span className="font-medium">{w.model}</span> on {w.server}: {w.warning}
              </div>
            </div>
          ))}
        </div>
          )}
        </div>
      )}

      {/* Swarm Tier */}
      <div
        className={cn(
          "rounded-lg p-4 border",
          tier.color.includes("bg-") ? "" : "bg-slate-50 dark:bg-slate-800/50",
          tier.color
            .split(" ")
            .filter((c) => c.startsWith("bg-") || c.startsWith("dark:bg-"))
            .join(" ")
        )}
      >
        <div className="flex items-center gap-3">
          <Zap
            size={24}
            className={tier.color
              .split(" ")
              .filter((c) => c.startsWith("text-") || c.startsWith("dark:text-"))
              .join(" ")}
          />
          <div>
            <div
              className={cn(
                "text-lg font-bold",
                tier.color
                  .split(" ")
                  .filter((c) => c.startsWith("text-") || c.startsWith("dark:text-"))
                  .join(" ")
              )}
            >
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
          <div className="space-y-3">
            {stats.nodes.map((node) => {
              const sourceBadge = SOURCE_BADGES[node.source || "relay"] || SOURCE_BADGES.relay;
              const SourceIcon = sourceBadge.icon;
              const capabilities = node.model_capabilities || {};

              return (
                <div
                  key={node.node_id}
                  className="p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700"
                >
                  {/* Node Header */}
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full",
                          sourceBadge.className
                        )}
                        aria-label={`Source: ${sourceBadge.label}`}
                      >
                        <SourceIcon size={10} aria-hidden="true" />
                        {sourceBadge.label}
                      </span>
                      <span className="font-medium text-slate-900 dark:text-white">
                        {node.hostname}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="text-xs text-slate-400">
                        Score {node.score?.toFixed(2)}
                      </div>
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 text-xs font-medium",
                          node.alive ? "text-green-600 dark:text-green-400" : "text-red-500 dark:text-red-400"
                        )}
                        aria-label={node.alive ? "Healthy" : "Offline"}
                      >
                        {node.alive ? (
                          <Wifi size={12} aria-hidden="true" />
                        ) : (
                          <WifiOff size={12} aria-hidden="true" />
                        )}
                        {node.alive ? "healthy" : "offline"}
                      </span>
                    </div>
                  </div>

                  {/* Host URL for local/network nodes */}
                  {node.host && (
                    <div className="text-xs text-slate-400 mb-2 font-mono">{node.host}</div>
                  )}

                  {/* Resource summary */}
                  <div className="text-xs text-slate-500 mb-3">
                    {node.ram_available_gb?.toFixed(1)} GB free | CPU {node.cpu_load_pct?.toFixed(0)}%
                  </div>

                  {/* Model Capabilities */}
                  {node.loaded_models && node.loaded_models.length > 0 && (
                    <div>
                      <div className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-1.5">
                        Models
                      </div>
                      <div className="space-y-1.5">
                        {node.loaded_models.map((modelName) => {
                          const caps = capabilities[modelName];
                          return (
                            <div
                              key={modelName}
                              className="flex items-center gap-2 flex-wrap"
                            >
                              <span className="text-sm font-mono text-slate-700 dark:text-slate-300">
                                {modelName}
                              </span>
                              {caps ? (
                                <ModelBadges
                                  supportsTools={caps.supports_tools}
                                  supportsVision={caps.supports_vision}
                                  parameterCount={caps.parameter_count}
                                  contextLength={caps.context_length}
                                />
                              ) : (
                                <span className="text-xs text-slate-400 italic">
                                  no capability info
                                </span>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-10 text-slate-400">
            <Server size={40} className="mx-auto mb-3 opacity-30" aria-hidden="true" />
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
              No LLM servers detected
            </p>
            <p className="text-xs mt-1.5 max-w-sm mx-auto">
              Start LM Studio or Ollama to add local compute, or connect relay nodes from team
              machines.
            </p>
          </div>
        )}
      </div>
    </div>
    </div>
  );
}

/* ---------- Model Capability Badges ---------- */

function ModelBadges({
  supportsTools,
  supportsVision,
  parameterCount,
  contextLength,
}: {
  supportsTools: boolean;
  supportsVision: boolean;
  parameterCount: string | null;
  contextLength: number | null;
}) {
  const formatContext = (len: number) => {
    if (len >= 1000) return `${Math.round(len / 1000)}K ctx`;
    return `${len} ctx`;
  };

  return (
    <div className="flex items-center gap-1 flex-wrap">
      {/* Parameter count */}
      {parameterCount && (
        <span
          className="inline-flex px-1.5 py-0.5 text-[10px] font-semibold rounded bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300"
          aria-label={`${parameterCount} parameters`}
        >
          {parameterCount}
        </span>
      )}

      {/* Tool support */}
      <span
        className={cn(
          "inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium rounded",
          supportsTools
            ? "bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400"
            : "bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400"
        )}
        aria-label={supportsTools ? "Supports tool use" : "No tool support"}
      >
        <Wrench size={9} aria-hidden="true" />
        {supportsTools ? "tools \u2713" : "tools \u2717"}
      </span>

      {/* Vision */}
      {supportsVision && (
        <span
          className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-medium rounded bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400"
          aria-label="Supports vision input"
        >
          <Camera size={9} aria-hidden="true" />
          vision
        </span>
      )}

      {/* Context length */}
      {contextLength != null && (
        <span
          className="inline-flex px-1.5 py-0.5 text-[10px] font-medium rounded bg-slate-50 text-slate-500 dark:bg-slate-700 dark:text-slate-400"
          aria-label={`${formatContext(contextLength)} context window`}
        >
          {formatContext(contextLength)}
        </span>
      )}
    </div>
  );
}

/* ---------- Stat Card ---------- */

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
