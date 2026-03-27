"use client";

import { useEffect, useState } from "react";
import {
  FlaskConical,
  CheckCircle2,
  TrendingUp,
  Activity,
  Play,
  Square,
  Loader2,
} from "lucide-react";
import { useAutoresearchStore } from "@/stores/autoresearchStore";
import { cn, formatDate } from "@/lib/utils";
import type { AutoresearchLoopType } from "@/lib/types";

const LOOP_TYPES: { value: AutoresearchLoopType; label: string }[] = [
  { value: "skill_prompt", label: "Skill Prompt" },
  { value: "model_temp", label: "Model Temp" },
  { value: "rag_params", label: "RAG Params" },
  { value: "persona", label: "Persona" },
  { value: "question_bank", label: "Question Bank" },
  { value: "ui_sim", label: "UI Sim" },
];

export default function ExperimentDashboard() {
  const { status, experiments, fetchStatus, fetchExperiments, startLoop, stopLoop, error } =
    useAutoresearchStore();

  const [loopType, setLoopType] = useState<string>("model_temp");
  const [target, setTarget] = useState("");
  const [maxIterations, setMaxIterations] = useState(20);

  useEffect(() => {
    fetchStatus();
    fetchExperiments({ limit: 20 });
  }, [fetchStatus, fetchExperiments]);

  // Refresh status periodically when a loop is running
  useEffect(() => {
    if (!status?.running) return;
    const interval = setInterval(() => {
      fetchStatus();
      fetchExperiments({ limit: 20 });
    }, 5000);
    return () => clearInterval(interval);
  }, [status?.running, fetchStatus, fetchExperiments]);

  const totalExperiments = experiments.length;
  const keptCount = experiments.filter((e) => e.kept).length;
  const successRate = totalExperiments > 0 ? Math.round((keptCount / totalExperiments) * 100) : 0;
  const bestDelta = experiments.length > 0
    ? Math.max(...experiments.filter((e) => e.kept).map((e) => e.delta), 0)
    : 0;

  const handleStart = () => {
    if (!target.trim()) return;
    startLoop({ loop_type: loopType, target: target.trim(), max_iterations: maxIterations });
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6">
      {/* Active experiment card */}
      {status?.running && status.current_experiment && (
        <div className="rounded-lg border border-reclaw-300 dark:border-reclaw-700 bg-reclaw-50 dark:bg-reclaw-900/20 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Loader2 size={18} className="animate-spin text-reclaw-600 dark:text-reclaw-400" />
              <h3 className="font-semibold text-reclaw-700 dark:text-reclaw-400">
                Experiment Running
              </h3>
            </div>
            <button
              onClick={stopLoop}
              aria-label="Stop experiment loop"
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
            >
              <Square size={14} />
              Stop
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div>
              <span className="text-slate-500 dark:text-slate-400">Loop Type</span>
              <p className="font-medium text-slate-900 dark:text-white">
                {status.current_experiment.loop_type}
              </p>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400">Target</span>
              <p className="font-medium text-slate-900 dark:text-white">
                {status.current_experiment.target_name}
              </p>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400">Hypothesis</span>
              <p className="font-medium text-slate-900 dark:text-white truncate">
                {status.current_experiment.hypothesis}
              </p>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400">Baseline</span>
              <p className="font-medium text-slate-900 dark:text-white">
                {status.current_experiment.baseline_score.toFixed(3)}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 mb-1">
            <FlaskConical size={16} />
            <span className="text-xs font-medium uppercase">Total Experiments</span>
          </div>
          <p className="text-2xl font-bold text-slate-900 dark:text-white">{totalExperiments}</p>
        </div>
        <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 mb-1">
            <CheckCircle2 size={16} />
            <span className="text-xs font-medium uppercase">Kept Improvements</span>
          </div>
          <p className="text-2xl font-bold text-green-600 dark:text-green-400">{keptCount}</p>
        </div>
        <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 mb-1">
            <TrendingUp size={16} />
            <span className="text-xs font-medium uppercase">Success Rate</span>
          </div>
          <p className="text-2xl font-bold text-slate-900 dark:text-white">{successRate}%</p>
        </div>
        <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 mb-1">
            <Activity size={16} />
            <span className="text-xs font-medium uppercase">Best Delta</span>
          </div>
          <p className="text-2xl font-bold text-reclaw-600 dark:text-reclaw-400">
            +{bestDelta.toFixed(3)}
          </p>
        </div>
      </div>

      {/* Start new loop */}
      {!status?.running && (
        <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
          <h3 className="font-semibold text-slate-900 dark:text-white mb-3">
            Start Experiment Loop
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div>
              <label
                htmlFor="ar-loop-type"
                className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1"
              >
                Loop Type
              </label>
              <select
                id="ar-loop-type"
                value={loopType}
                onChange={(e) => setLoopType(e.target.value)}
                aria-label="Experiment loop type"
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-reclaw-500"
              >
                {LOOP_TYPES.map((lt) => (
                  <option key={lt.value} value={lt.value}>
                    {lt.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label
                htmlFor="ar-target"
                className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1"
              >
                Target
              </label>
              <input
                id="ar-target"
                type="text"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder="skill name, agent id..."
                aria-label="Experiment target"
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
              />
            </div>
            <div>
              <label
                htmlFor="ar-max-iter"
                className="block text-xs font-medium text-slate-500 dark:text-slate-400 mb-1"
              >
                Max Iterations
              </label>
              <input
                id="ar-max-iter"
                type="number"
                value={maxIterations}
                onChange={(e) => setMaxIterations(Number(e.target.value))}
                min={1}
                max={200}
                aria-label="Maximum iterations"
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-reclaw-500"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={handleStart}
                disabled={!target.trim() || !status?.enabled}
                aria-label="Start experiment loop"
                className={cn(
                  "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors w-full justify-center",
                  target.trim() && status?.enabled
                    ? "bg-reclaw-600 text-white hover:bg-reclaw-700"
                    : "bg-slate-200 dark:bg-slate-700 text-slate-400 dark:text-slate-500 cursor-not-allowed"
                )}
              >
                <Play size={14} />
                Start
              </button>
            </div>
          </div>
          {!status?.enabled && (
            <p className="mt-2 text-xs text-amber-600 dark:text-amber-400">
              Autoresearch is disabled. Enable it in the Config tab first.
            </p>
          )}
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="rounded-lg border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-900/20 p-3 text-sm text-red-700 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Recent experiments timeline */}
      <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
        <h3 className="font-semibold text-slate-900 dark:text-white mb-3">
          Recent Experiments
        </h3>
        {experiments.length === 0 ? (
          <p className="text-sm text-slate-400 dark:text-slate-500 text-center py-8">
            No experiments yet. Start a loop to begin self-improvement.
          </p>
        ) : (
          <div className="space-y-2">
            {experiments.slice(0, 15).map((exp) => (
              <div
                key={exp.id}
                className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
              >
                {/* Status indicator */}
                <div
                  className={cn(
                    "w-2.5 h-2.5 rounded-full shrink-0",
                    exp.status === "running"
                      ? "bg-blue-500 animate-pulse"
                      : exp.kept
                        ? "bg-green-500"
                        : exp.status === "failed"
                          ? "bg-red-500"
                          : "bg-slate-300 dark:bg-slate-600"
                  )}
                  aria-label={exp.kept ? "Kept" : exp.status === "failed" ? "Failed" : "Discarded"}
                />

                {/* Loop type badge */}
                <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 whitespace-nowrap">
                  {exp.loop_type}
                </span>

                {/* Target */}
                <span className="text-sm text-slate-700 dark:text-slate-300 truncate min-w-0">
                  {exp.target_name}
                </span>

                {/* Hypothesis (truncated) */}
                <span className="text-xs text-slate-400 dark:text-slate-500 truncate hidden md:block flex-1 min-w-0">
                  {exp.hypothesis}
                </span>

                {/* Score delta */}
                <span
                  className={cn(
                    "text-sm font-mono whitespace-nowrap",
                    exp.delta > 0
                      ? "text-green-600 dark:text-green-400"
                      : exp.delta < 0
                        ? "text-red-600 dark:text-red-400"
                        : "text-slate-400"
                  )}
                >
                  {exp.delta > 0 ? "+" : ""}
                  {exp.delta.toFixed(3)}
                </span>

                {/* Timestamp */}
                <span className="text-xs text-slate-400 dark:text-slate-500 whitespace-nowrap hidden lg:block">
                  {exp.started_at ? formatDate(exp.started_at) : ""}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
