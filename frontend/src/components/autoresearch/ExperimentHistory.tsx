"use client";

import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useAutoresearchStore } from "@/stores/autoresearchStore";
import { cn, formatDate } from "@/lib/utils";
import type { AutoresearchLoopType } from "@/lib/types";

const LOOP_TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: "", label: "All Types" },
  { value: "skill_prompt", label: "Skill Prompt" },
  { value: "model_temp", label: "Model Temp" },
  { value: "rag_params", label: "RAG Params" },
  { value: "persona", label: "Persona" },
  { value: "question_bank", label: "Question Bank" },
  { value: "ui_sim", label: "UI Sim" },
];

const PAGE_SIZE = 20;

export default function ExperimentHistory() {
  const { experiments, loading, fetchExperiments } = useAutoresearchStore();
  const [filterType, setFilterType] = useState("");
  const [filterKept, setFilterKept] = useState<string>("");
  const [page, setPage] = useState(0);

  useEffect(() => {
    const params: Record<string, any> = { limit: PAGE_SIZE, offset: page * PAGE_SIZE };
    if (filterType) params.loop_type = filterType;
    if (filterKept === "true") params.kept = true;
    if (filterKept === "false") params.kept = false;
    fetchExperiments(params);
  }, [fetchExperiments, filterType, filterKept, page]);

  const loopTypeBadgeColor = (lt: AutoresearchLoopType): string => {
    const colors: Record<string, string> = {
      skill_prompt: "bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400",
      model_temp: "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400",
      rag_params: "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400",
      persona: "bg-pink-100 dark:bg-pink-900/30 text-pink-700 dark:text-pink-400",
      question_bank: "bg-teal-100 dark:bg-teal-900/30 text-teal-700 dark:text-teal-400",
      ui_sim: "bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-400",
    };
    return colors[lt] || "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400";
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div>
          <label htmlFor="filter-loop-type" className="sr-only">
            Filter by loop type
          </label>
          <select
            id="filter-loop-type"
            value={filterType}
            onChange={(e) => {
              setFilterType(e.target.value);
              setPage(0);
            }}
            aria-label="Filter by loop type"
            className="px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-reclaw-500"
          >
            {LOOP_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="filter-kept" className="sr-only">
            Filter by outcome
          </label>
          <select
            id="filter-kept"
            value={filterKept}
            onChange={(e) => {
              setFilterKept(e.target.value);
              setPage(0);
            }}
            aria-label="Filter by outcome"
            className="px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-reclaw-500"
          >
            <option value="">All Outcomes</option>
            <option value="true">Kept</option>
            <option value="false">Discarded</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm" role="table" aria-label="Experiment history">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
                  Loop Type
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
                  Target
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold uppercase text-slate-500 dark:text-slate-400 hidden md:table-cell">
                  Hypothesis
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
                  Baseline
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
                  Score
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
                  Delta
                </th>
                <th className="text-center px-4 py-3 text-xs font-semibold uppercase text-slate-500 dark:text-slate-400">
                  Outcome
                </th>
                <th className="text-right px-4 py-3 text-xs font-semibold uppercase text-slate-500 dark:text-slate-400 hidden lg:table-cell">
                  Time
                </th>
              </tr>
            </thead>
            <tbody>
              {loading && experiments.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-8 text-slate-400">
                    Loading experiments...
                  </td>
                </tr>
              ) : experiments.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-8 text-slate-400">
                    No experiments found.
                  </td>
                </tr>
              ) : (
                experiments.map((exp) => (
                  <tr
                    key={exp.id}
                    className="border-b border-slate-100 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          "text-xs font-medium px-2 py-1 rounded-full whitespace-nowrap",
                          loopTypeBadgeColor(exp.loop_type)
                        )}
                      >
                        {exp.loop_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-900 dark:text-white font-medium truncate max-w-[140px]">
                      {exp.target_name}
                    </td>
                    <td className="px-4 py-3 text-slate-500 dark:text-slate-400 truncate max-w-[200px] hidden md:table-cell">
                      {exp.hypothesis}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-slate-600 dark:text-slate-300">
                      {exp.baseline_score.toFixed(3)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-slate-600 dark:text-slate-300">
                      {exp.experiment_score !== null ? exp.experiment_score.toFixed(3) : "--"}
                    </td>
                    <td
                      className={cn(
                        "px-4 py-3 text-right font-mono",
                        exp.delta > 0
                          ? "text-green-600 dark:text-green-400"
                          : exp.delta < 0
                            ? "text-red-600 dark:text-red-400"
                            : "text-slate-400"
                      )}
                    >
                      {exp.delta > 0 ? "+" : ""}
                      {exp.delta.toFixed(3)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={cn(
                          "text-xs font-medium px-2 py-1 rounded-full",
                          exp.status === "running"
                            ? "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400"
                            : exp.kept
                              ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                              : exp.status === "failed"
                                ? "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400"
                                : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400"
                        )}
                      >
                        {exp.status === "running"
                          ? "Running"
                          : exp.kept
                            ? "Kept"
                            : exp.status === "failed"
                              ? "Failed"
                              : "Discarded"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right text-xs text-slate-400 dark:text-slate-500 whitespace-nowrap hidden lg:table-cell">
                      {exp.started_at ? formatDate(exp.started_at) : ""}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200 dark:border-slate-800">
          <span className="text-xs text-slate-400 dark:text-slate-500">
            Page {page + 1}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              aria-label="Previous page"
              className={cn(
                "p-1.5 rounded-lg transition-colors",
                page > 0
                  ? "hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400"
                  : "text-slate-300 dark:text-slate-600 cursor-not-allowed"
              )}
            >
              <ChevronLeft size={16} />
            </button>
            <button
              onClick={() => setPage(page + 1)}
              disabled={experiments.length < PAGE_SIZE}
              aria-label="Next page"
              className={cn(
                "p-1.5 rounded-lg transition-colors",
                experiments.length >= PAGE_SIZE
                  ? "hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400"
                  : "text-slate-300 dark:text-slate-600 cursor-not-allowed"
              )}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
