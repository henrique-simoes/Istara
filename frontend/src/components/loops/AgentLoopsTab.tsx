"use client";

import { useEffect, useState } from "react";
import { Pause, Play, RefreshCw, Clock, Activity } from "lucide-react";
import { useLoopsStore } from "@/stores/loopsStore";
import { useAgentStore } from "@/stores/agentStore";
import { cn } from "@/lib/utils";
import type { Agent } from "@/lib/types";

const INTERVAL_PRESETS = [15, 30, 60, 120, 300];

function formatTimeAgo(dateStr: string | null): string {
  if (!dateStr) return "Never";
  const diff = Date.now() - new Date(dateStr).getTime();
  if (diff < 60_000) return "Just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return new Date(dateStr).toLocaleDateString();
}

const ROLE_COLORS: Record<string, string> = {
  task_executor: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  devops_audit: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  ui_audit: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  ux_evaluation: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400",
  user_simulation: "bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400",
  custom: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
};

export default function AgentLoopsTab() {
  const { agentLoops, fetchAgentLoops, updateAgentConfig, pauseAgent, resumeAgent, loading } = useLoopsStore();
  const { agents, fetchAgents } = useAgentStore();

  useEffect(() => {
    fetchAgentLoops();
    fetchAgents();
  }, [fetchAgentLoops, fetchAgents]);

  // Merge agent data with loop config
  const agentWithLoops = agents.map((agent) => {
    const loopConfig = agentLoops.find((l) => l.agent_id === agent.id);
    return { agent, loopConfig };
  });

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Agent Loop Configuration</h2>
        <button
          onClick={() => fetchAgentLoops()}
          className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-400"
          aria-label="Refresh"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {agents.length === 0 && !loading ? (
        <div className="flex flex-col items-center justify-center py-16 text-slate-400 dark:text-slate-500">
          <Activity size={40} className="mb-3 opacity-50" />
          <p className="text-sm">No agents found.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {agentWithLoops.map(({ agent, loopConfig }) => (
            <AgentLoopCard
              key={agent.id}
              agent={agent}
              loopConfig={loopConfig || null}
              onUpdateConfig={(data) => updateAgentConfig(agent.id, data)}
              onPause={() => pauseAgent(agent.id)}
              onResume={() => resumeAgent(agent.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function AgentLoopCard({
  agent,
  loopConfig,
  onUpdateConfig,
  onPause,
  onResume,
}: {
  agent: Agent;
  loopConfig: {
    id: string;
    agent_id: string;
    loop_interval_seconds: number;
    paused: boolean;
    skills_to_run: string[];
    project_filter: string;
    last_cycle_at: string | null;
    cycle_count: number;
  } | null;
  onUpdateConfig: (data: Record<string, unknown>) => void;
  onPause: () => void;
  onResume: () => void;
}) {
  const interval = loopConfig?.loop_interval_seconds ?? agent.heartbeat_interval_seconds ?? 60;
  const paused = loopConfig?.paused ?? agent.state === "paused";
  const [localInterval, setLocalInterval] = useState(interval);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    setLocalInterval(interval);
    setDirty(false);
  }, [interval]);

  const handleIntervalChange = (val: number) => {
    const clamped = Math.min(600, Math.max(10, val));
    setLocalInterval(clamped);
    setDirty(clamped !== interval);
  };

  const applyInterval = () => {
    onUpdateConfig({ loop_interval_seconds: localInterval });
    setDirty(false);
  };

  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3 min-w-0">
          <span className={cn(
            "w-2.5 h-2.5 rounded-full shrink-0",
            paused ? "bg-yellow-500" : agent.state === "error" ? "bg-red-500" : "bg-green-500"
          )} />
          <div className="min-w-0">
            <h3 className="text-sm font-medium text-slate-900 dark:text-white truncate">
              {agent.name}
            </h3>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={cn(
                "text-[10px] px-1.5 py-0.5 rounded-full font-medium",
                ROLE_COLORS[agent.role] || ROLE_COLORS.custom
              )}>
                {agent.role.replace(/_/g, " ")}
              </span>
              {agent.is_system && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500">
                  system
                </span>
              )}
            </div>
          </div>
        </div>

        <button
          onClick={paused ? onResume : onPause}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
            paused
              ? "bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400 dark:hover:bg-green-900/50"
              : "bg-yellow-100 text-yellow-700 hover:bg-yellow-200 dark:bg-yellow-900/30 dark:text-yellow-400 dark:hover:bg-yellow-900/50"
          )}
        >
          {paused ? <Play size={12} /> : <Pause size={12} />}
          {paused ? "Resume" : "Pause"}
        </button>
      </div>

      {/* Interval control */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <label className="text-xs text-slate-600 dark:text-slate-400 shrink-0">
            <Clock size={12} className="inline mr-1" />
            Interval
          </label>
          <input
            type="range"
            min={10}
            max={600}
            step={5}
            value={localInterval}
            onChange={(e) => handleIntervalChange(parseInt(e.target.value, 10))}
            className="flex-1 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-istara-600"
          />
          <div className="flex items-center gap-1">
            <input
              type="number"
              min={10}
              max={600}
              value={localInterval}
              onChange={(e) => handleIntervalChange(parseInt(e.target.value, 10) || 10)}
              className="w-16 text-xs px-2 py-1 rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-right focus:outline-none focus:ring-2 focus:ring-istara-500"
            />
            <span className="text-xs text-slate-500 dark:text-slate-400">sec</span>
          </div>
          {dirty && (
            <button
              onClick={applyInterval}
              className="px-2 py-1 text-xs font-medium rounded bg-istara-600 text-white hover:bg-istara-700"
            >
              Apply
            </button>
          )}
        </div>

        {/* Preset buttons */}
        <div className="flex items-center gap-1.5 pl-16">
          {INTERVAL_PRESETS.map((preset) => (
            <button
              key={preset}
              type="button"
              onClick={() => handleIntervalChange(preset)}
              className={cn(
                "text-[10px] px-2 py-0.5 rounded border transition-colors",
                localInterval === preset
                  ? "bg-istara-100 border-istara-300 text-istara-700 dark:bg-istara-900/30 dark:border-istara-600 dark:text-istara-400"
                  : "border-slate-200 dark:border-slate-700 text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800"
              )}
            >
              {preset}s
            </button>
          ))}
        </div>
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-4 mt-3 pt-3 border-t border-slate-100 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400">
        <span>Last cycle: {formatTimeAgo(loopConfig?.last_cycle_at ?? null)}</span>
        <span>Cycles: {loopConfig?.cycle_count ?? 0}</span>
        {loopConfig?.skills_to_run && loopConfig.skills_to_run.length > 0 && (
          <span>Skills: {loopConfig.skills_to_run.length}</span>
        )}
      </div>
    </div>
  );
}
