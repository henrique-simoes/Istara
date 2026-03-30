"use client";

import { useEffect, useState } from "react";
import { Activity, RefreshCw, CheckCircle2, XCircle, Clock } from "lucide-react";
import { mcp as mcpApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { MCPAuditEntry } from "@/lib/types";

export default function MCPAuditLog() {
  const [entries, setEntries] = useState<MCPAuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [limit, setLimit] = useState(50);

  const fetchAudit = async () => {
    setLoading(true);
    try {
      const data = await mcpApi.server.audit(limit);
      setEntries(data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAudit();
  }, [limit]);

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity size={18} className="text-istara-500" />
          <h2 className="text-lg font-bold text-slate-900 dark:text-white">Audit Log</h2>
        </div>
        <button
          onClick={fetchAudit}
          aria-label="Refresh audit log"
          className="p-2 rounded-lg text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <RefreshCw size={14} />
        </button>
      </div>

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-14 rounded-lg bg-slate-100 dark:bg-slate-800 animate-pulse" />
          ))}
        </div>
      ) : entries.length === 0 ? (
        <div className="text-center py-12">
          <Activity size={32} className="mx-auto mb-3 text-slate-300 dark:text-slate-600" />
          <p className="text-sm text-slate-500 dark:text-slate-400">No audit entries yet.</p>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
            Entries will appear as external tools access Istara via MCP.
          </p>
        </div>
      ) : (
        <div className="space-y-1">
          {entries.map((entry) => (
            <div
              key={entry.id}
              className="flex items-center gap-3 px-4 py-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg"
            >
              {/* Granted/Denied icon */}
              <div className="shrink-0">
                {entry.access_granted ? (
                  <CheckCircle2 size={16} className="text-green-500" />
                ) : (
                  <XCircle size={16} className="text-red-500" />
                )}
              </div>

              {/* Details */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-sm font-medium text-slate-900 dark:text-white font-mono">{entry.tool_name}</span>
                  <span className={cn(
                    "text-[10px] px-1.5 py-0.5 rounded-full font-medium",
                    entry.access_granted
                      ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400"
                      : "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"
                  )}>
                    {entry.access_granted ? "GRANTED" : "DENIED"}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                  <span>Caller: {entry.caller_info}</span>
                  {entry.duration_ms > 0 && <span>{entry.duration_ms}ms</span>}
                </div>
                {entry.result_summary && (
                  <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5 truncate">{entry.result_summary}</p>
                )}
              </div>

              {/* Timestamp */}
              <div className="flex items-center gap-1 text-xs text-slate-400 dark:text-slate-500 shrink-0">
                <Clock size={10} />
                {new Date(entry.timestamp).toLocaleString()}
              </div>
            </div>
          ))}

          {/* Load more */}
          {entries.length >= limit && (
            <button
              onClick={() => setLimit(limit + 50)}
              className="w-full py-2 text-xs text-istara-600 hover:text-istara-700 dark:text-istara-400 transition-colors"
            >
              Load more...
            </button>
          )}
        </div>
      )}
    </div>
  );
}
