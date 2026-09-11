"use client";

import { useEffect, useState, useMemo } from "react";
import {
  History,
  Bot,
  User,
  RotateCcw,
  ChevronDown,
  ChevronRight,
  FileText,
  Activity,
  Cpu,
  Shield,
  Search,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Clock,
} from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { projects as projectsApi, audit as auditApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import ViewOnboarding from "@/components/common/ViewOnboarding";

interface VersionEntry {
  commit_hash: string;
  message: string;
  author: string;
  timestamp: string;
  files_changed: string[];
}

interface AuditLogEntry {
  id: string;
  timestamp: string;
  user_id: string;
  method: string;
  path: string;
  status_code: number;
  duration_ms: number;
  ip_address: string;
  project_id?: string;
  event_type?: string;
  details?: string | Record<string, any>;
}

interface TelemetrySpanEntry {
  id: string;
  trace_id: string;
  parent_id?: string;
  operation: string;
  skill_name?: string;
  model_name?: string;
  agent_id?: string;
  started_at: string;
  duration_ms: number;
  status: string;
  quality_score?: number;
  consensus_score?: number;
  reliability_score?: number;
  error_type?: string;
  error_message?: string;
  project_id?: string;
  task_id?: string;
  tool_name?: string;
  tool_success?: boolean;
  tool_duration_ms?: number;
  source?: string;
}

type TabType = "commits" | "api_logs" | "agent_traces";

export default function VersionHistory() {
  const { activeProjectId } = useProjectStore();
  const [activeTab, setActiveTab] = useState<TabType>("commits");

  // Commits state
  const [versions, setVersions] = useState<VersionEntry[]>([]);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const [versionsError, setVersionsError] = useState<string | null>(null);
  const [expandedHash, setExpandedHash] = useState<string | null>(null);

  // API logs state
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [logsError, setLogsError] = useState<string | null>(null);
  const [logSearch, setLogSearch] = useState("");
  const [logMethodFilter, setLogMethodFilter] = useState<string>("ALL");
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  // Agent spans state
  const [spans, setSpans] = useState<TelemetrySpanEntry[]>([]);
  const [loadingSpans, setLoadingSpans] = useState(false);
  const [spansError, setSpansError] = useState<string | null>(null);
  const [spanSearch, setSpanSearch] = useState("");
  const [spanStatusFilter, setSpanStatusFilter] = useState<string>("ALL");
  const [expandedSpanId, setExpandedSpanId] = useState<string | null>(null);

  // Load versions
  const loadVersions = () => {
    if (!activeProjectId) return;
    setLoadingVersions(true);
    setVersionsError(null);
    projectsApi
      .versions(activeProjectId)
      .then(setVersions)
      .catch((e) => {
        setVersions([]);
        setVersionsError(e instanceof Error ? e.message : "Could not load version history");
      })
      .finally(() => setLoadingVersions(false));
  };

  // Load audit logs
  const loadAuditLogs = () => {
    if (!activeProjectId) return;
    setLoadingLogs(true);
    setLogsError(null);
    auditApi
      .logs({ project_id: activeProjectId, limit: 150 })
      .then((res) => setAuditLogs(res?.entries || []))
      .catch((e) => {
        setAuditLogs([]);
        setLogsError(e instanceof Error ? e.message : "Could not load audit logs");
      })
      .finally(() => setLoadingLogs(false));
  };

  // Load agent spans
  const loadSpans = () => {
    if (!activeProjectId) return;
    setLoadingSpans(true);
    setSpansError(null);
    auditApi
      .spans({ project_id: activeProjectId, limit: 150 })
      .then((res) => setSpans(res?.entries || []))
      .catch((e) => {
        setSpans([]);
        setSpansError(e instanceof Error ? e.message : "Could not load agent traces");
      })
      .finally(() => setLoadingSpans(false));
  };

  useEffect(() => {
    if (!activeProjectId) return;
    loadVersions();
    loadAuditLogs();
    loadSpans();
  }, [activeProjectId]);

  const refreshActiveTab = () => {
    if (activeTab === "commits") loadVersions();
    else if (activeTab === "api_logs") loadAuditLogs();
    else if (activeTab === "agent_traces") loadSpans();
  };

  // Filtered logs
  const filteredLogs = useMemo(() => {
    return auditLogs.filter((log) => {
      const matchesSearch =
        !logSearch ||
        log.path.toLowerCase().includes(logSearch.toLowerCase()) ||
        log.user_id.toLowerCase().includes(logSearch.toLowerCase()) ||
        (log.event_type && log.event_type.toLowerCase().includes(logSearch.toLowerCase()));
      const matchesMethod =
        logMethodFilter === "ALL" || log.method.toUpperCase() === logMethodFilter;
      return matchesSearch && matchesMethod;
    });
  }, [auditLogs, logSearch, logMethodFilter]);

  // Filtered spans
  const filteredSpans = useMemo(() => {
    return spans.filter((span) => {
      const matchesSearch =
        !spanSearch ||
        span.operation.toLowerCase().includes(spanSearch.toLowerCase()) ||
        (span.model_name && span.model_name.toLowerCase().includes(spanSearch.toLowerCase())) ||
        (span.skill_name && span.skill_name.toLowerCase().includes(spanSearch.toLowerCase())) ||
        (span.tool_name && span.tool_name.toLowerCase().includes(spanSearch.toLowerCase()));
      const matchesStatus =
        spanStatusFilter === "ALL" || span.status.toLowerCase() === spanStatusFilter.toLowerCase();
      return matchesSearch && matchesStatus;
    });
  }, [spans, spanSearch, spanStatusFilter]);

  if (!activeProjectId) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        <p>Select a project to view activity and audit logs.</p>
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

  const getMethodBadge = (method: string) => {
    const m = method.toUpperCase();
    switch (m) {
      case "GET":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 border-blue-200 dark:border-blue-800";
      case "POST":
        return "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800";
      case "PUT":
      case "PATCH":
        return "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 border-amber-200 dark:border-amber-800";
      case "DELETE":
        return "bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300 border-rose-200 dark:border-rose-800";
      default:
        return "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300 border-slate-200 dark:border-slate-700";
    }
  };

  const getStatusBadge = (code: number) => {
    if (code >= 200 && code < 300) {
      return "text-emerald-600 dark:text-emerald-400 font-semibold";
    }
    if (code >= 400 && code < 500) {
      return "text-amber-600 dark:text-amber-400 font-semibold";
    }
    if (code >= 500) {
      return "text-rose-600 dark:text-rose-400 font-semibold";
    }
    return "text-slate-600 dark:text-slate-400";
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <Activity size={22} className="text-istara-600 dark:text-istara-400" />
              Activity & Audit Dashboard
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Comprehensive operational audit trail covering Git versions, system requests, and AI agent execution spans.
            </p>
          </div>
          <button
            onClick={refreshActiveTab}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 transition-colors"
          >
            <RefreshCw size={13} className={loadingVersions || loadingLogs || loadingSpans ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>

        <ViewOnboarding
          viewId="history"
          title="Activity & Audit Dashboard"
          description="Track every workspace modification across Git commits, HTTP API audit logs, and fine-grained AI agent telemetry spans."
          chatPrompt="Explain how to audit recent agent tool calls and API activity in this workspace."
        />

        {/* Navigation Tabs */}
        <div role="tablist" aria-label="History views" className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 mb-6 mt-4">
          <button
            role="tab"
            aria-selected={activeTab === "commits"}
            onClick={() => setActiveTab("commits")}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors",
              activeTab === "commits"
                ? "border-istara-600 text-istara-600 dark:border-istara-400 dark:text-istara-400 font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            )}
          >
            <History size={16} />
            Git Commits
            {versions.length > 0 && (
              <span className="px-1.5 py-0.5 text-xs rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                {versions.length}
              </span>
            )}
          </button>

          <button
            role="tab"
            aria-selected={activeTab === "api_logs"}
            onClick={() => setActiveTab("api_logs")}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors",
              activeTab === "api_logs"
                ? "border-istara-600 text-istara-600 dark:border-istara-400 dark:text-istara-400 font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            )}
          >
            <Shield size={16} />
            API Audit Logs
            {auditLogs.length > 0 && (
              <span className="px-1.5 py-0.5 text-xs rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                {auditLogs.length}
              </span>
            )}
          </button>

          <button
            role="tab"
            aria-selected={activeTab === "agent_traces"}
            onClick={() => setActiveTab("agent_traces")}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors",
              activeTab === "agent_traces"
                ? "border-istara-600 text-istara-600 dark:border-istara-400 dark:text-istara-400 font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
            )}
          >
            <Cpu size={16} />
            AI Agent Traces
            {spans.length > 0 && (
              <span className="px-1.5 py-0.5 text-xs rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                {spans.length}
              </span>
            )}
          </button>
        </div>

        {/* TAB 1: Git Commits */}
        {activeTab === "commits" && (
          <div>
            {loadingVersions ? (
              <div className="flex items-center justify-center py-12 text-slate-400">
                <History size={20} className="animate-spin mr-2" />
                Loading version history...
              </div>
            ) : versionsError ? (
              <div role="alert" className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
                <AlertCircle size={16} className="mt-0.5 shrink-0" />
                <span>Could not load version history: {versionsError}</span>
              </div>
            ) : versions.length === 0 ? (
              <div className="text-center py-12 text-slate-400 border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
                <History size={32} className="mx-auto mb-3 text-slate-300" />
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300">No version history yet.</p>
                <p className="text-xs mt-1">Changes are tracked automatically as research work proceeds.</p>
              </div>
            ) : (
              <div className="space-y-6">
                {Object.entries(groupedByDate).map(([date, entries]) => (
                  <div key={date}>
                    <h3 className="text-xs font-semibold text-slate-500 uppercase mb-3">
                      {date}
                    </h3>
                    <div className="space-y-2">
                      {entries.map((entry) => {
                        const isExpanded = expandedHash === entry.commit_hash;
                        const isAgent = entry.author === "Istara";

                        return (
                          <div
                            key={entry.commit_hash}
                            className="border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden bg-white dark:bg-slate-900/50 shadow-sm"
                          >
                            <button
                              onClick={() =>
                                setExpandedHash(isExpanded ? null : entry.commit_hash)
                              }
                              className="flex items-start gap-3 w-full p-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 text-left transition-colors"
                            >
                              {/* Timeline dot */}
                              <div
                                className={cn(
                                  "w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5",
                                  isAgent
                                    ? "bg-istara-100 dark:bg-istara-900/40 text-istara-600 dark:text-istara-400"
                                    : "bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400"
                                )}
                              >
                                {isAgent ? <Bot size={14} /> : <User size={14} />}
                              </div>

                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium text-slate-900 dark:text-white">
                                  {entry.message}
                                </p>
                                <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                                  <span className="flex items-center gap-1">
                                    <Clock size={11} />
                                    {new Date(entry.timestamp).toLocaleTimeString("en-US", {
                                      hour: "2-digit",
                                      minute: "2-digit",
                                    })}
                                  </span>
                                  <span className="font-mono bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-[11px]">
                                    {entry.commit_hash.slice(0, 7)}
                                  </span>
                                  <span>{entry.author}</span>
                                  {entry.files_changed.length > 0 && (
                                    <span className="text-slate-500">
                                      {entry.files_changed.length} file{entry.files_changed.length > 1 ? "s" : ""}
                                    </span>
                                  )}
                                </div>
                              </div>

                              {isExpanded ? (
                                <ChevronDown size={16} className="text-slate-400 shrink-0 mt-1" />
                              ) : (
                                <ChevronRight size={16} className="text-slate-400 shrink-0 mt-1" />
                              )}
                            </button>

                            {/* Expanded details */}
                            {isExpanded && (
                              <div className="border-t border-slate-200 dark:border-slate-800 p-4 bg-slate-50 dark:bg-slate-900/80">
                                {entry.files_changed.length > 0 && (
                                  <div className="mb-3">
                                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                                      Files Modified
                                    </p>
                                    <div className="space-y-1">
                                      {entry.files_changed.map((file, i) => (
                                        <div
                                          key={i}
                                          className="flex items-center gap-2 text-xs text-slate-700 dark:text-slate-300 font-mono bg-white dark:bg-slate-800/80 px-2.5 py-1.5 rounded border border-slate-200/80 dark:border-slate-700/60"
                                        >
                                          <FileText size={12} className="text-slate-400" />
                                          <span>{file}</span>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}

                                {/* Diff preview */}
                                <div className="mb-3 rounded-lg bg-slate-950 p-3 text-xs font-mono overflow-x-auto text-slate-300 border border-slate-800">
                                  <p className="text-slate-500 mb-1">
                                    commit {entry.commit_hash}
                                  </p>
                                  <p className="text-slate-400 mb-2">Author: {entry.author}</p>
                                  {entry.files_changed.map((file, fi) => (
                                    <p key={fi} className="text-emerald-400">
                                      + {file}
                                    </p>
                                  ))}
                                  {entry.files_changed.length === 0 && (
                                    <p className="text-slate-500">No individual file diffs available</p>
                                  )}
                                </div>

                                <button
                                  onClick={() => {
                                    if (
                                      window.confirm(
                                        `Rollback to ${entry.commit_hash.slice(0, 7)}? This will restore project files to this version.`
                                      )
                                    ) {
                                      console.log("Rollback to:", entry.commit_hash);
                                    }
                                  }}
                                  className="flex items-center gap-1.5 text-xs text-amber-600 hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-300 font-medium px-2 py-1 rounded hover:bg-amber-50 dark:hover:bg-amber-950/30 transition-colors"
                                >
                                  <RotateCcw size={13} />
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
        )}

        {/* TAB 2: API Audit Logs */}
        {activeTab === "api_logs" && (
          <div>
            {/* Filters Bar */}
            <div className="flex items-center gap-3 mb-4">
              <div className="relative flex-1">
                <Search size={14} className="absolute left-3 top-2.5 text-slate-400" />
                <input
                  type="text"
                  aria-label="Search audit logs"
                  placeholder="Search by path, user, or event..."
                  value={logSearch}
                  onChange={(e) => setLogSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-istara-500"
                />
              </div>
              <div className="flex items-center gap-1 text-xs">
                {["ALL", "GET", "POST", "PUT", "DELETE"].map((method) => (
                  <button
                    key={method}
                    onClick={() => setLogMethodFilter(method)}
                    className={cn(
                      "px-2.5 py-1 rounded text-[11px] font-medium transition-colors",
                      logMethodFilter === method
                        ? "bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-semibold"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
                    )}
                  >
                    {method}
                  </button>
                ))}
              </div>
            </div>

            {loadingLogs ? (
              <div className="flex items-center justify-center py-12 text-slate-400">
                <Shield size={20} className="animate-spin mr-2" />
                Loading audit logs...
              </div>
            ) : logsError ? (
              <div role="alert" className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
                <AlertCircle size={16} className="mt-0.5 shrink-0" />
                <span>Could not load audit logs: {logsError}</span>
              </div>
            ) : filteredLogs.length === 0 ? (
              <div className="text-center py-12 text-slate-400 border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
                <Shield size={32} className="mx-auto mb-3 text-slate-300" />
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300">No audit logs found.</p>
                <p className="text-xs mt-1">
                  API requests are recorded automatically to provide an immutable compliance trail.
                </p>
              </div>
            ) : (
              <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-white dark:bg-slate-900/50 shadow-sm">
                <div className="divide-y divide-slate-200 dark:divide-slate-800">
                  {filteredLogs.map((log) => {
                    const isExpanded = expandedLogId === log.id;
                    return (
                      <div key={log.id} className="transition-colors">
                        <button
                          onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                          className="w-full p-3 text-left hover:bg-slate-50 dark:hover:bg-slate-800/40 flex items-center gap-3"
                        >
                          <span
                            className={cn(
                              "px-2 py-0.5 rounded text-[11px] font-mono font-bold border",
                              getMethodBadge(log.method)
                            )}
                          >
                            {log.method}
                          </span>

                          <span className={cn("font-mono text-xs w-8", getStatusBadge(log.status_code))}>
                            {log.status_code}
                          </span>

                          <span className="font-mono text-xs text-slate-800 dark:text-slate-200 flex-1 truncate">
                            {log.path}
                          </span>

                          <span className="text-[11px] text-slate-400 shrink-0">
                            {log.duration_ms} ms
                          </span>

                          <span className="text-[11px] text-slate-400 shrink-0">
                            {new Date(log.timestamp).toLocaleTimeString("en-US", {
                              hour: "2-digit",
                              minute: "2-digit",
                              second: "2-digit",
                            })}
                          </span>

                          {isExpanded ? (
                            <ChevronDown size={14} className="text-slate-400 shrink-0" />
                          ) : (
                            <ChevronRight size={14} className="text-slate-400 shrink-0" />
                          )}
                        </button>

                        {isExpanded && (
                          <div className="p-4 bg-slate-50 dark:bg-slate-950/60 border-t border-slate-200 dark:border-slate-800 text-xs font-mono space-y-2">
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-slate-600 dark:text-slate-400">
                              <div>
                                <span className="font-semibold text-slate-700 dark:text-slate-300">User ID:</span>{" "}
                                {log.user_id || "anonymous"}
                              </div>
                              <div>
                                <span className="font-semibold text-slate-700 dark:text-slate-300">IP:</span>{" "}
                                {log.ip_address || "internal"}
                              </div>
                              <div>
                                <span className="font-semibold text-slate-700 dark:text-slate-300">Event:</span>{" "}
                                {log.event_type || "http_request"}
                              </div>
                              <div>
                                <span className="font-semibold text-slate-700 dark:text-slate-300">Log ID:</span>{" "}
                                {log.id.slice(0, 8)}
                              </div>
                            </div>
                            {((typeof log.details === "string" && log.details.length > 0) ||
                              (log.details && typeof log.details === "object" && Object.keys(log.details).length > 0)) && (
                              <div className="mt-2">
                                <span className="font-semibold text-slate-700 dark:text-slate-300">Payload / Details:</span>
                                <pre className="mt-1 p-2 rounded bg-slate-900 text-slate-200 text-[11px] overflow-x-auto">
                                  {typeof log.details === "string" ? log.details : JSON.stringify(log.details, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: AI Agent Traces */}
        {activeTab === "agent_traces" && (
          <div>
            {/* Filters Bar */}
            <div className="flex items-center gap-3 mb-4">
              <div className="relative flex-1">
                <Search size={14} className="absolute left-3 top-2.5 text-slate-400" />
                <input
                  type="text"
                  aria-label="Search agent traces"
                  placeholder="Search by operation, model, skill, or tool..."
                  value={spanSearch}
                  onChange={(e) => setSpanSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-istara-500"
                />
              </div>
              <div className="flex items-center gap-1 text-xs">
                {["ALL", "success", "error", "degraded"].map((status) => (
                  <button
                    key={status}
                    onClick={() => setSpanStatusFilter(status)}
                    className={cn(
                      "px-2.5 py-1 rounded text-[11px] font-medium capitalize transition-colors",
                      spanStatusFilter === status
                        ? "bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-semibold"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
                    )}
                  >
                    {status}
                  </button>
                ))}
              </div>
            </div>

            {loadingSpans ? (
              <div className="flex items-center justify-center py-12 text-slate-400">
                <Cpu size={20} className="animate-spin mr-2" />
                Loading agent traces...
              </div>
            ) : spansError ? (
              <div role="alert" className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
                <AlertCircle size={16} className="mt-0.5 shrink-0" />
                <span>Could not load agent traces: {spansError}</span>
              </div>
            ) : filteredSpans.length === 0 ? (
              <div className="text-center py-12 text-slate-400 border border-dashed border-slate-200 dark:border-slate-800 rounded-xl">
                <Cpu size={32} className="mx-auto mb-3 text-slate-300" />
                <p className="text-sm font-medium text-slate-700 dark:text-slate-300">No agent traces recorded yet.</p>
                <p className="text-xs mt-1">
                  Traces capture skill execution, multi-model consensus, and tool calls with full provenance.
                </p>
              </div>
            ) : (
              <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-white dark:bg-slate-900/50 shadow-sm">
                <div className="divide-y divide-slate-200 dark:divide-slate-800">
                  {filteredSpans.map((span) => {
                    const isExpanded = expandedSpanId === span.id;
                    const isSuccess = span.status === "success";

                    return (
                      <div key={span.id} className="transition-colors">
                        <button
                          onClick={() => setExpandedSpanId(isExpanded ? null : span.id)}
                          className="w-full p-3 text-left hover:bg-slate-50 dark:hover:bg-slate-800/40 flex items-center gap-3"
                        >
                          <div
                            className={cn(
                              "w-6 h-6 rounded-full flex items-center justify-center shrink-0",
                              isSuccess
                                ? "bg-emerald-100 text-emerald-600 dark:bg-emerald-950/50 dark:text-emerald-400"
                                : "bg-rose-100 text-rose-600 dark:bg-rose-950/50 dark:text-rose-400"
                            )}
                          >
                            {isSuccess ? <CheckCircle2 size={13} /> : <AlertCircle size={13} />}
                          </div>

                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-semibold text-slate-900 dark:text-white">
                                {span.operation}
                              </span>
                              {span.skill_name && (
                                <span className="px-1.5 py-0.5 rounded text-[10px] bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 font-mono">
                                  {span.skill_name}
                                </span>
                              )}
                              {span.tool_name && (
                                <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-mono">
                                  tool: {span.tool_name}
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-3 mt-1 text-[11px] text-slate-400">
                              {span.model_name && <span>{span.model_name}</span>}
                              <span>{Math.round(span.duration_ms)} ms</span>
                              {span.consensus_score !== null && span.consensus_score !== undefined && (
                                <span>consensus: {(span.consensus_score * 100).toFixed(0)}%</span>
                              )}
                            </div>
                          </div>

                          <span className="text-[11px] text-slate-400 shrink-0">
                            {new Date(span.started_at).toLocaleTimeString("en-US", {
                              hour: "2-digit",
                              minute: "2-digit",
                              second: "2-digit",
                            })}
                          </span>

                          {isExpanded ? (
                            <ChevronDown size={14} className="text-slate-400 shrink-0" />
                          ) : (
                            <ChevronRight size={14} className="text-slate-400 shrink-0" />
                          )}
                        </button>

                        {isExpanded && (
                          <div className="p-4 bg-slate-50 dark:bg-slate-950/60 border-t border-slate-200 dark:border-slate-800 text-xs font-mono space-y-2">
                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-slate-600 dark:text-slate-400">
                              <div>
                                <span className="font-semibold text-slate-700 dark:text-slate-300">Span ID:</span>{" "}
                                {span.id.slice(0, 8)}
                              </div>
                              <div>
                                <span className="font-semibold text-slate-700 dark:text-slate-300">Trace ID:</span>{" "}
                                {span.trace_id.slice(0, 12)}
                              </div>
                              <div>
                                <span className="font-semibold text-slate-700 dark:text-slate-300">Status:</span>{" "}
                                <span
                                  className={cn(
                                    "font-semibold uppercase text-[10px]",
                                    isSuccess ? "text-emerald-500" : "text-rose-500"
                                  )}
                                >
                                  {span.status}
                                </span>
                              </div>
                              <div>
                                <span className="font-semibold text-slate-700 dark:text-slate-300">Agent ID:</span>{" "}
                                {span.agent_id || "orchestrator"}
                              </div>
                              <div>
                                <span className="font-semibold text-slate-700 dark:text-slate-300">Source:</span>{" "}
                                {span.source || "production"}
                              </div>
                              {span.task_id && (
                                <div>
                                  <span className="font-semibold text-slate-700 dark:text-slate-300">Task ID:</span>{" "}
                                  {span.task_id.slice(0, 8)}
                                </div>
                              )}
                            </div>

                            {span.error_message && (
                              <div className="mt-2 p-2.5 rounded bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 text-rose-700 dark:text-rose-300 text-[11px]">
                                <span className="font-semibold">Error ({span.error_type || "unknown"}):</span>{" "}
                                {span.error_message}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
