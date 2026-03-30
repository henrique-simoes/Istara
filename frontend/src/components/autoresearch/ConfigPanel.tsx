"use client";

import { useEffect } from "react";
import { Power, ExternalLink } from "lucide-react";
import { useAutoresearchStore } from "@/stores/autoresearchStore";
import { cn } from "@/lib/utils";

export default function ConfigPanel() {
  const { config, status, fetchConfig, fetchStatus, updateConfig, toggle } =
    useAutoresearchStore();

  useEffect(() => {
    fetchConfig();
    fetchStatus();
  }, [fetchConfig, fetchStatus]);

  const enabled = config?.enabled ?? false;

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 max-w-2xl">
      {/* Enable / Disable toggle */}
      <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-white">Autoresearch Engine</h3>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Enable automated experiment loops for continuous self-improvement.
            </p>
          </div>
          <button
            onClick={() => toggle(!enabled)}
            aria-label={enabled ? "Disable autoresearch" : "Enable autoresearch"}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
              enabled
                ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 hover:bg-green-200 dark:hover:bg-green-900/50"
                : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
            )}
          >
            <Power size={16} />
            {enabled ? "Enabled" : "Disabled"}
          </button>
        </div>
      </div>

      {/* Max experiments per run */}
      <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 space-y-3">
        <h3 className="font-semibold text-slate-900 dark:text-white">Experiment Limits</h3>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label
              htmlFor="max-per-run"
              className="text-sm text-slate-700 dark:text-slate-300"
            >
              Max experiments per run
            </label>
            <span className="text-sm font-mono text-slate-500 dark:text-slate-400">
              {config?.max_experiments_per_run ?? 20}
            </span>
          </div>
          <input
            id="max-per-run"
            type="range"
            min={1}
            max={100}
            value={config?.max_experiments_per_run ?? 20}
            onChange={(e) =>
              updateConfig({ max_experiments_per_run: Number(e.target.value) })
            }
            aria-label="Max experiments per run"
            className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-istara-600"
          />
          <div className="flex justify-between text-xs text-slate-400 mt-1">
            <span>1</span>
            <span>100</span>
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label
              htmlFor="max-daily"
              className="text-sm text-slate-700 dark:text-slate-300"
            >
              Max daily experiments
            </label>
            <span className="text-sm font-mono text-slate-500 dark:text-slate-400">
              {config?.max_daily_experiments ?? 100}
            </span>
          </div>
          <input
            id="max-daily"
            type="range"
            min={1}
            max={500}
            value={config?.max_daily_experiments ?? 100}
            onChange={(e) =>
              updateConfig({ max_daily_experiments: Number(e.target.value) })
            }
            aria-label="Max daily experiments"
            className="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-istara-600"
          />
          <div className="flex justify-between text-xs text-slate-400 mt-1">
            <span>1</span>
            <span>500</span>
          </div>
        </div>
      </div>

      {/* Per-loop enable toggles */}
      <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-4 space-y-3">
        <h3 className="font-semibold text-slate-900 dark:text-white">Loop Types</h3>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Select which experiment loop types are allowed to run.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {[
            { key: "skill_prompt", label: "Skill Prompt Optimization", desc: "Mutate and improve skill prompts" },
            { key: "model_temp", label: "Model & Temperature", desc: "Find best model+temp per skill" },
            { key: "rag_params", label: "RAG Parameters", desc: "Optimize chunk size, overlap, top_k" },
            { key: "persona", label: "Persona Tuning", desc: "Refine agent personas" },
            { key: "question_bank", label: "Question Bank", desc: "Improve interview questions" },
            { key: "ui_sim", label: "UI Simulation", desc: "Test UI flows and interactions" },
          ].map((loop) => (
            <label
              key={loop.key}
              className="flex items-start gap-3 p-3 rounded-lg border border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 cursor-pointer transition-colors"
            >
              <input
                type="checkbox"
                defaultChecked
                aria-label={`Enable ${loop.label}`}
                className="mt-0.5 rounded border-slate-300 dark:border-slate-600 text-istara-600 focus:ring-istara-500"
              />
              <div>
                <span className="text-sm font-medium text-slate-900 dark:text-white">
                  {loop.label}
                </span>
                <p className="text-xs text-slate-500 dark:text-slate-400">{loop.desc}</p>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Attribution */}
      <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 p-4">
        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
          <span>
            Inspired by Karpathy's autoresearch (MIT)
          </span>
          <a
            href="https://github.com/karpathy/autoresearch"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Karpathy autoresearch repository on GitHub"
            className="inline-flex items-center gap-1 text-istara-600 dark:text-istara-400 hover:underline"
          >
            github.com/karpathy/autoresearch
            <ExternalLink size={12} />
          </a>
        </div>
      </div>
    </div>
  );
}
