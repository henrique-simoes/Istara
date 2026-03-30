"use client";

import { useEffect } from "react";
import { History, ChevronLeft, ChevronRight, AlertTriangle } from "lucide-react";
import { useLoopsStore } from "@/stores/loopsStore";
import { cn, formatDate } from "@/lib/utils";
import type { ExecutionStatus } from "@/lib/types";

const STATUS_BADGE: Record<ExecutionStatus, string> = {
  success: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  failure: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  running: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
  skipped: "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400",
};

function formatDuration(ms: number | null): string {
  if (ms === null || ms === undefined) return "-";
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60_000)}m ${Math.round((ms % 60_000) / 1000)}s`;
}

export default function ExecutionHistoryTab() {
  const {
    executions, executionPage, executionTotalPages, executionFilters,
    fetchExecutions, setExecutionFilter, loading,
  } = useLoopsStore();

  useEffect(() => {
    fetchExecutions(1);
  }, [fetchExecutions]);

  const handleFilterChange = (key: string, value: string) => {
    setExecutionFilter(key, value);
  };

  const applyFilters = () => {
    fetchExecutions(1);
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <select
          value={executionFilters.source_type}
          onChange={(e) => handleFilterChange("source_type", e.target.value)}
          className="px-3 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
        >
          <option value="">All Types</option>
          <option value="agent">Agent</option>
          <option value="scheduled">Scheduled</option>
          <option value="custom">Custom</option>
        </select>
        <select
          value={executionFilters.status}
          onChange={(e) => handleFilterChange("status", e.target.value)}
          className="px-3 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
        >
          <option value="">All Statuses</option>
          <option value="success">Success</option>
          <option value="failure">Failure</option>
          <option value="running">Running</option>
          <option value="skipped">Skipped</option>
        </select>
        <input
          type="date"
          value={executionFilters.from_date}
          onChange={(e) => handleFilterChange("from_date", e.target.value)}
          className="px-3 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
          placeholder="From"
        />
        <input
          type="date"
          value={executionFilters.to_date}
          onChange={(e) => handleFilterChange("to_date", e.target.value)}
          className="px-3 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
          placeholder="To"
        />
        <button
          onClick={applyFilters}
          className="px-3 py-1.5 text-xs font-medium rounded-lg bg-istara-600 text-white hover:bg-istara-700"
        >
          Filter
        </button>
      </div>

      {/* Table */}
      {executions.length === 0 && !loading ? (
        <div className="flex flex-col items-center justify-center py-16 text-slate-400 dark:text-slate-500">
          <History size={40} className="mb-3 opacity-50" />
          <p className="text-sm">No execution history yet.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
                <th className="text-left px-3 py-2 text-xs font-medium text-slate-500 dark:text-slate-400">Time</th>
                <th className="text-left px-3 py-2 text-xs font-medium text-slate-500 dark:text-slate-400">Name</th>
                <th className="text-left px-3 py-2 text-xs font-medium text-slate-500 dark:text-slate-400">Type</th>
                <th className="text-left px-3 py-2 text-xs font-medium text-slate-500 dark:text-slate-400">Status</th>
                <th className="text-left px-3 py-2 text-xs font-medium text-slate-500 dark:text-slate-400">Duration</th>
                <th className="text-left px-3 py-2 text-xs font-medium text-slate-500 dark:text-slate-400">Findings</th>
                <th className="text-left px-3 py-2 text-xs font-medium text-slate-500 dark:text-slate-400">Error</th>
              </tr>
            </thead>
            <tbody>
              {executions.map((exec) => (
                <tr
                  key={exec.id}
                  className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50"
                >
                  <td className="px-3 py-2 text-xs text-slate-600 dark:text-slate-400 whitespace-nowrap">
                    {formatDate(exec.started_at)}
                  </td>
                  <td className="px-3 py-2 text-xs font-medium text-slate-900 dark:text-white">
                    {exec.source_name}
                  </td>
                  <td className="px-3 py-2">
                    <span className={cn(
                      "text-[10px] px-1.5 py-0.5 rounded-full font-medium",
                      exec.source_type === "agent"
                        ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                        : exec.source_type === "scheduled"
                        ? "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400"
                        : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                    )}>
                      {exec.source_type}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <span className={cn(
                      "text-[10px] px-1.5 py-0.5 rounded-full font-medium",
                      STATUS_BADGE[exec.status as ExecutionStatus] || STATUS_BADGE.skipped
                    )}>
                      {exec.status}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-xs text-slate-600 dark:text-slate-400">
                    {formatDuration(exec.duration_ms)}
                  </td>
                  <td className="px-3 py-2 text-xs text-slate-600 dark:text-slate-400">
                    {exec.findings_count > 0 ? exec.findings_count : "-"}
                  </td>
                  <td className="px-3 py-2 text-xs max-w-[200px]">
                    {exec.error_message ? (
                      <span className="flex items-center gap-1 text-red-600 dark:text-red-400 truncate" title={exec.error_message}>
                        <AlertTriangle size={10} />
                        {exec.error_message}
                      </span>
                    ) : (
                      <span className="text-slate-400">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {executionTotalPages > 1 && (
        <div className="flex items-center justify-center gap-3 pt-2">
          <button
            onClick={() => fetchExecutions(executionPage - 1)}
            disabled={executionPage <= 1}
            className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed text-slate-600 dark:text-slate-400"
            aria-label="Previous page"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="text-xs text-slate-600 dark:text-slate-400">
            Page {executionPage} of {executionTotalPages}
          </span>
          <button
            onClick={() => fetchExecutions(executionPage + 1)}
            disabled={executionPage >= executionTotalPages}
            className="p-1.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed text-slate-600 dark:text-slate-400"
            aria-label="Next page"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
