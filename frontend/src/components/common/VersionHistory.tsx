"use client";

import { useEffect, useState } from "react";
import { History, Bot, User, RotateCcw, ChevronDown, ChevronRight, FileText } from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { projects as projectsApi } from "@/lib/api";
import { cn, formatDate } from "@/lib/utils";

interface VersionEntry {
  commit_hash: string;
  message: string;
  author: string;
  timestamp: string;
  files_changed: string[];
}

export default function VersionHistory() {
  const { activeProjectId } = useProjectStore();
  const [versions, setVersions] = useState<VersionEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedHash, setExpandedHash] = useState<string | null>(null);

  useEffect(() => {
    if (!activeProjectId) return;
    setLoading(true);
    projectsApi
      .versions(activeProjectId)
      .then(setVersions)
      .catch(() => setVersions([]))
      .finally(() => setLoading(false));
  }, [activeProjectId]);

  if (!activeProjectId) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        <p>Select a project to view history.</p>
      </div>
    );
  }

  // Group versions by date
  const groupedByDate: Record<string, VersionEntry[]> = {};
  versions.forEach((v) => {
    const date = new Date(v.timestamp).toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
    if (!groupedByDate[date]) groupedByDate[date] = [];
    groupedByDate[date].push(v);
  });

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-3xl mx-auto">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2 mb-6">
          <History size={20} />
          🔄 Version History
        </h2>

        {loading ? (
          <div className="flex items-center justify-center py-12 text-slate-400">
            <History size={20} className="animate-spin mr-2" />
            Loading history...
          </div>
        ) : versions.length === 0 ? (
          <div className="text-center py-12 text-slate-400">
            <History size={32} className="mx-auto mb-3 text-slate-300" />
            <p className="text-sm">No version history yet.</p>
            <p className="text-xs mt-1">
              Changes are tracked automatically as the agent works.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(groupedByDate).map(([date, entries]) => (
              <div key={date}>
                <h3 className="text-xs font-semibold text-slate-500 uppercase mb-3">
                  {date}
                </h3>
                <div className="space-y-1">
                  {entries.map((entry) => {
                    const isExpanded = expandedHash === entry.commit_hash;
                    const isAgent = entry.author === "ReClaw";

                    return (
                      <div
                        key={entry.commit_hash}
                        className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden"
                      >
                        <button
                          onClick={() =>
                            setExpandedHash(isExpanded ? null : entry.commit_hash)
                          }
                          className="flex items-start gap-3 w-full p-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 text-left"
                        >
                          {/* Timeline dot */}
                          <div
                            className={cn(
                              "w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5",
                              isAgent
                                ? "bg-reclaw-100 dark:bg-reclaw-900/30"
                                : "bg-blue-100 dark:bg-blue-900/30"
                            )}
                          >
                            {isAgent ? (
                              <Bot size={12} className="text-reclaw-600" />
                            ) : (
                              <User size={12} className="text-blue-600" />
                            )}
                          </div>

                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-slate-900 dark:text-white">
                              {entry.message}
                            </p>
                            <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                              <span>
                                {new Date(entry.timestamp).toLocaleTimeString("en-US", {
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })}
                              </span>
                              <span className="font-mono">{entry.commit_hash.slice(0, 7)}</span>
                              {entry.files_changed.length > 0 && (
                                <span>{entry.files_changed.length} file(s)</span>
                              )}
                            </div>
                          </div>

                          {isExpanded ? (
                            <ChevronDown size={16} className="text-slate-400 shrink-0" />
                          ) : (
                            <ChevronRight size={16} className="text-slate-400 shrink-0" />
                          )}
                        </button>

                        {/* Expanded details */}
                        {isExpanded && (
                          <div className="border-t border-slate-200 dark:border-slate-700 p-3 bg-slate-50 dark:bg-slate-800/30">
                            {entry.files_changed.length > 0 && (
                              <div className="mb-3">
                                <p className="text-xs font-medium text-slate-500 mb-1">
                                  Files changed:
                                </p>
                                <div className="space-y-0.5">
                                  {entry.files_changed.map((file, i) => (
                                    <div
                                      key={i}
                                      className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-400"
                                    >
                                      <FileText size={10} />
                                      <span className="font-mono">{file}</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Diff preview */}
                            <div className="mb-3 rounded-lg bg-slate-900 dark:bg-slate-950 p-3 text-xs font-mono overflow-x-auto">
                              <p className="text-slate-500 mb-1">--- {entry.commit_hash.slice(0, 7)}: {entry.message}</p>
                              {entry.files_changed.map((file, fi) => (
                                <p key={fi} className="text-green-400">+ Modified: {file}</p>
                              ))}
                              {entry.files_changed.length === 0 && (
                                <p className="text-slate-500">No file details</p>
                              )}
                            </div>

                            <button
                              onClick={() => {
                                if (window.confirm(`Rollback to ${entry.commit_hash.slice(0, 7)}? This reverts all changes after this point.`)) {
                                  console.log("Rollback to:", entry.commit_hash);
                                }
                              }}
                              className="flex items-center gap-1 text-xs text-amber-600 hover:text-amber-700 font-medium"
                            >
                              <RotateCcw size={12} />
                              Rollback to this version
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
