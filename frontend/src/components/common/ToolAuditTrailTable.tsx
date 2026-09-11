"use client";

import { useState, useMemo } from "react";
import {
  Zap,
  CheckCircle,
  XCircle,
  Clock,
  Search,
  Filter,
  ChevronDown,
  ChevronRight,
  Shield,
  Layers,
  Bot,
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface ToolAuditEntry {
  id: string;
  tool_name: string;
  status: "success" | "failure";
  duration_ms: number;
  model_name: string;
  agent_id: string;
  task_id: string;
  skill_name: string;
  timestamp: string | null;
  arguments_summary: string;
  reasoning_bank_id?: string | null;
  error_type?: string | null;
}

interface ToolAuditTrailProps {
  entries: ToolAuditEntry[];
  summary?: {
    total_calls?: number;
    overall_success_rate?: number;
    distinct_tools?: number;
    avg_duration_ms?: number;
  };
}

export default function ToolAuditTrailTable({ entries = [], summary }: ToolAuditTrailProps) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "success" | "failure">("all");
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const filtered = useMemo(() => {
    return entries.filter((e) => {
      if (statusFilter !== "all" && e.status !== statusFilter) return false;
      if (!search) return true;
      const q = search.toLowerCase();
      return (
        e.tool_name.toLowerCase().includes(q) ||
        e.model_name.toLowerCase().includes(q) ||
        (e.agent_id && e.agent_id.toLowerCase().includes(q)) ||
        (e.task_id && e.task_id.toLowerCase().includes(q)) ||
        (e.skill_name && e.skill_name.toLowerCase().includes(q)) ||
        (e.arguments_summary && e.arguments_summary.toLowerCase().includes(q))
      );
    });
  }, [entries, search, statusFilter]);

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Zap size={18} className="text-amber-500" />
          <h3 className="font-semibold text-sm text-slate-800 dark:text-slate-100">
            Tool Reliability & Telemetry Audit Trail
          </h3>
          <span className="text-xs text-slate-400 font-normal">
            ({filtered.length} of {entries.length} calls{entries.length > 50 ? ", showing first 50" : ""})
          </span>
        </div>

        {summary && (
          <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
            {summary.overall_success_rate !== undefined && (
              <span className="flex items-center gap-1 font-medium">
                Success Rate:{" "}
                <span
                  className={cn(
                    "font-bold",
                    summary.overall_success_rate >= 0.9
                      ? "text-green-600 dark:text-green-400"
                      : summary.overall_success_rate >= 0.7
                        ? "text-yellow-600 dark:text-yellow-400"
                        : "text-red-600 dark:text-red-400"
                  )}
                >
                  {(summary.overall_success_rate * 100).toFixed(0)}%
                </span>
              </span>
            )}
            {summary.avg_duration_ms !== undefined && (
              <span>Avg: {summary.avg_duration_ms.toFixed(0)}ms</span>
            )}
          </div>
        )}
      </div>

      {/* Controls: Search & Status Filters */}
      <div className="flex flex-wrap items-center gap-2 pt-1">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            aria-label="Search tool calls"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by tool, model, agent, or arguments..."
            className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-1 focus:ring-istara-500 text-slate-800 dark:text-slate-200 placeholder-slate-400"
          />
        </div>

        <div className="flex items-center rounded-lg border border-slate-200 dark:border-slate-700 p-0.5 bg-slate-50 dark:bg-slate-900 text-xs">
          {(
            [
              { id: "all", label: "All" },
              { id: "success", label: "Success" },
              { id: "failure", label: "Failed" },
            ] as const
          ).map((t) => (
            <button
              key={t.id}
              type="button"
              aria-pressed={statusFilter === t.id}
              onClick={() => setStatusFilter(t.id)}
              className={cn(
                "px-2.5 py-1 rounded-md font-medium transition-colors",
                statusFilter === t.id
                  ? "bg-white dark:bg-slate-800 text-slate-900 dark:text-white shadow-xs"
                  : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div className="py-8 text-center text-xs text-slate-400 dark:text-slate-500">
          {entries.length === 0
            ? "No tool calls recorded in telemetry yet. Tool invocations across ReAct and agent loops will appear here."
            : "No tool calls matching the current search/filter."}
        </div>
      ) : (
        <div className="overflow-x-auto border border-slate-200 dark:border-slate-700 rounded-lg">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-900/60 text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700 uppercase text-[10px] tracking-wider">
              <tr>
                <th scope="col" className="p-2.5 w-8"></th>
                <th scope="col" className="p-2.5">Tool</th>
                <th scope="col" className="p-2.5">Status</th>
                <th scope="col" className="p-2.5">Duration</th>
                <th scope="col" className="p-2.5">Model</th>
                <th scope="col" className="p-2.5">Skill / Task</th>
                <th scope="col" className="p-2.5">Arguments Summary</th>
                <th scope="col" className="p-2.5">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {filtered.slice(0, 50).map((e) => {
                const isExpanded = expandedRow === e.id;
                return (
                  <>
                    <tr
                      key={e.id}
                      className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors cursor-pointer"
                      onClick={() => setExpandedRow(isExpanded ? null : e.id)}
                    >
                      <td className="p-2.5 text-slate-400 text-center">
                        {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                      </td>
                      <td className="p-2.5 font-mono font-medium text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                        <Zap size={12} className="text-slate-400 shrink-0" />
                        <span className="truncate max-w-[140px]">{e.tool_name}</span>
                      </td>
                      <td className="p-2.5">
                        <span
                          className={cn(
                            "inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold",
                            e.status === "success"
                              ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300"
                              : "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300"
                          )}
                        >
                          {e.status === "success" ? (
                            <CheckCircle size={10} className="shrink-0" />
                          ) : (
                            <XCircle size={10} className="shrink-0" />
                          )}
                          {e.status}
                        </span>
                      </td>
                      <td className="p-2.5 font-mono text-slate-600 dark:text-slate-400 whitespace-nowrap">
                        {e.duration_ms}ms
                      </td>
                      <td className="p-2.5 font-mono text-slate-600 dark:text-slate-400 truncate max-w-[110px]">
                        {e.model_name}
                      </td>
                      <td className="p-2.5 text-slate-500 dark:text-slate-400 truncate max-w-[130px]">
                        {e.skill_name || e.task_id ? (
                          <span>
                            {e.skill_name || "task:"}
                            {e.task_id && (
                              <span className="font-mono ml-1 text-slate-400 text-[10px]">
                                {e.task_id.slice(0, 8)}
                              </span>
                            )}
                          </span>
                        ) : (
                          "-"
                        )}
                      </td>
                      <td className="p-2.5 text-slate-500 dark:text-slate-400 font-mono text-[11px] truncate max-w-[200px]">
                        {e.arguments_summary || "-"}
                      </td>
                      <td className="p-2.5 text-slate-400 whitespace-nowrap text-[10px]">
                        {e.timestamp ? new Date(e.timestamp).toLocaleTimeString() : "-"}
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr key={`${e.id}-detail`}>
                        <td colSpan={8} className="bg-slate-50 dark:bg-slate-900/60 px-4 py-3 text-[11px]">
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 font-mono text-slate-600 dark:text-slate-400">
                            <span><span className="font-semibold">task_id:</span> {e.task_id || "-"}</span>
                            <span><span className="font-semibold">skill:</span> {e.skill_name || "-"}</span>
                            <span><span className="font-semibold">arguments:</span> {e.arguments_summary || "-"}</span>
                            <span><span className="font-semibold">reasoning_bank:</span> {e.reasoning_bank_id || "-"}</span>
                            {e.error_type && (
                              <span className="text-red-600 dark:text-red-400"><span className="font-semibold">error:</span> {e.error_type}</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
