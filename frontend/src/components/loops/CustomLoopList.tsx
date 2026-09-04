"use client";

import { RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

interface CustomLoop {
  source_type: string;
  source_id: string;
  source_name: string;
  status: string;
  interval_seconds?: number | null;
  cron_expression?: string | null;
}

interface CustomLoopListProps {
  loops: CustomLoop[];
  loading: boolean;
}

export default function CustomLoopList({ loops, loading }: CustomLoopListProps) {
  if (loops.length === 0 && !loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-slate-400 dark:text-slate-500">
        <RefreshCw size={40} className="mb-3 opacity-50" />
        <p className="text-sm">No custom loops yet.</p>
        <p className="text-xs mt-1">Create a custom loop to run skills on a schedule.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {loops.map((loop) => (
        <div
          key={`${loop.source_type}-${loop.source_id}`}
          className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-4"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 min-w-0">
              <span className={cn(
                "w-2 h-2 rounded-full shrink-0",
                loop.status === "active" ? "bg-green-500" : loop.status === "paused" ? "bg-yellow-500" : "bg-red-500",
              )} />
              <div className="min-w-0">
                <h3 className="text-sm font-medium text-slate-900 dark:text-white truncate">{loop.source_name}</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  {loop.interval_seconds ? `${loop.interval_seconds}s interval` : loop.cron_expression || "cron schedule"}
                </p>
              </div>
            </div>
            <span className={cn(
              "text-xs px-2 py-0.5 rounded-full",
              loop.status === "active"
                ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                : "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
            )}>
              {loop.status}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
