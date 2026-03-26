"use client";

import { useEffect, useRef } from "react";
import { Activity, Pause, AlertTriangle, Clock, RefreshCw } from "lucide-react";
import { useLoopsStore } from "@/stores/loopsStore";
import { cn } from "@/lib/utils";
import type { LoopHealthItem, LoopStatus } from "@/lib/types";

const STATUS_DOT: Record<LoopStatus, string> = {
  active: "bg-green-500",
  paused: "bg-yellow-500",
  behind_schedule: "bg-red-500",
  stopped: "bg-slate-400",
  error: "bg-red-600",
};

const STATUS_LABEL: Record<LoopStatus, string> = {
  active: "Active",
  paused: "Paused",
  behind_schedule: "Behind Schedule",
  stopped: "Stopped",
  error: "Error",
};

function formatInterval(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

function formatTimeAgo(dateStr: string | null): string {
  if (!dateStr) return "Never";
  const diff = Date.now() - new Date(dateStr).getTime();
  if (diff < 60_000) return "Just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  return new Date(dateStr).toLocaleDateString();
}

function formatTimeUntil(dateStr: string | null): string {
  if (!dateStr) return "N/A";
  const diff = new Date(dateStr).getTime() - Date.now();
  if (diff < 0) return "Overdue";
  if (diff < 60_000) return "< 1m";
  if (diff < 3_600_000) return `in ${Math.floor(diff / 60_000)}m`;
  return `in ${Math.floor(diff / 3_600_000)}h`;
}

export default function LoopOverviewTab() {
  const { health, overview, fetchHealth, fetchOverview, loading } = useLoopsStore();
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Auto-refresh every 15s
  useEffect(() => {
    intervalRef.current = setInterval(() => {
      fetchHealth();
      fetchOverview();
    }, 15000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchHealth, fetchOverview]);

  const activeCount = health.filter((h) => h.status === "active").length;
  const pausedCount = health.filter((h) => h.status === "paused").length;
  const behindCount = health.filter((h) => h.status === "behind_schedule" || h.status === "error").length;

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {/* Summary bar */}
      <div className="flex items-center gap-4 p-3 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-2 text-sm">
          <span className="w-2 h-2 rounded-full bg-green-500" />
          <span className="font-medium text-slate-700 dark:text-slate-300">{activeCount} active</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="w-2 h-2 rounded-full bg-yellow-500" />
          <span className="font-medium text-slate-700 dark:text-slate-300">{pausedCount} paused</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="w-2 h-2 rounded-full bg-red-500" />
          <span className="font-medium text-slate-700 dark:text-slate-300">{behindCount} behind schedule</span>
        </div>
        {overview && (
          <>
            <div className="ml-auto text-xs text-slate-500 dark:text-slate-400">
              {overview.total_executions_24h ?? 0} executions (24h)
            </div>
            <div className="text-xs text-slate-500 dark:text-slate-400">
              {overview.success_rate != null ? `${Math.round(overview.success_rate * 100)}% success` : ""}
            </div>
          </>
        )}
        <button
          onClick={() => { fetchHealth(); fetchOverview(); }}
          className="p-1 rounded hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-400"
          aria-label="Refresh"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {/* Health cards grid */}
      {health.length === 0 && !loading ? (
        <div className="flex flex-col items-center justify-center py-16 text-slate-400 dark:text-slate-500">
          <Activity size={40} className="mb-3 opacity-50" />
          <p className="text-sm">No loops or schedules configured yet.</p>
          <p className="text-xs mt-1">Create agent loops or custom schedules to see health data here.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {health.map((item) => (
            <HealthCard key={`${item.source_type}-${item.source_id}`} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

function HealthCard({ item }: { item: LoopHealthItem }) {
  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className={cn("w-2.5 h-2.5 rounded-full shrink-0", STATUS_DOT[item.status] || "bg-slate-400")} />
          <h3 className="text-sm font-medium text-slate-900 dark:text-white truncate">
            {item.source_name}
          </h3>
        </div>
        <span className={cn(
          "text-xs px-2 py-0.5 rounded-full font-medium",
          item.status === "active" ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400" :
          item.status === "paused" ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400" :
          item.status === "behind_schedule" || item.status === "error" ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" :
          "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
        )}>
          {STATUS_LABEL[item.status] || item.status}
        </span>
      </div>

      <div className="space-y-1.5 text-xs text-slate-600 dark:text-slate-400">
        <div className="flex items-center justify-between">
          <span className="flex items-center gap-1"><Clock size={12} /> Interval</span>
          <span className="font-medium">{formatInterval(item.interval_seconds)}</span>
        </div>
        <div className="flex items-center justify-between">
          <span>Last execution</span>
          <span className="font-medium">{formatTimeAgo(item.last_execution_at)}</span>
        </div>
        <div className="flex items-center justify-between">
          <span>Next expected</span>
          <span className="font-medium">{formatTimeUntil(item.next_expected_at)}</span>
        </div>
        {item.behind_by_seconds > 0 && (
          <div className="flex items-center gap-1 text-red-600 dark:text-red-400 mt-1">
            <AlertTriangle size={12} />
            <span>Behind by {formatInterval(item.behind_by_seconds)}</span>
          </div>
        )}
      </div>

      <div className="mt-3 pt-2 border-t border-slate-100 dark:border-slate-800">
        <span className="text-[10px] uppercase tracking-wider text-slate-400 dark:text-slate-500">
          {item.source_type}
        </span>
      </div>
    </div>
  );
}
