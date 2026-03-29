"use client";

import { useEffect, useState, useCallback } from "react";
import {
  FileStack,
  AlertCircle,
  Layers,
  TriangleAlert,
  ArrowUpRight,
} from "lucide-react";
import { reports as reportsApi } from "@/lib/api";
import type { ProjectReport } from "@/lib/types";
import { cn, formatDate } from "@/lib/utils";

interface ProjectReportsViewProps {
  projectId: string;
}

const LAYER_CONFIG: Record<
  number,
  { label: string; color: string; bgColor: string; borderColor: string; description: string }
> = {
  2: {
    label: "L2 - Study Analysis",
    color: "text-blue-700 dark:text-blue-400",
    bgColor: "bg-blue-50 dark:bg-blue-900/20",
    borderColor: "border-blue-200 dark:border-blue-800",
    description: "Individual study analyses",
  },
  3: {
    label: "L3 - Synthesis",
    color: "text-purple-700 dark:text-purple-400",
    bgColor: "bg-purple-50 dark:bg-purple-900/20",
    borderColor: "border-purple-200 dark:border-purple-800",
    description: "Cross-study synthesis reports",
  },
  4: {
    label: "L4 - Final Report",
    color: "text-reclaw-700 dark:text-reclaw-400",
    bgColor: "bg-reclaw-50 dark:bg-reclaw-900/20",
    borderColor: "border-reclaw-200 dark:border-reclaw-800",
    description: "Executive-level final reports",
  },
};

const STATUS_BADGE: Record<
  string,
  { label: string; className: string }
> = {
  draft: {
    label: "Draft",
    className:
      "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400",
  },
  in_progress: {
    label: "In Progress",
    className:
      "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400",
  },
  review: {
    label: "Review",
    className:
      "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400",
  },
  final: {
    label: "Final",
    className:
      "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400",
  },
};

export default function ProjectReportsView({
  projectId,
}: ProjectReportsViewProps) {
  const [allReports, setAllReports] = useState<ProjectReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadReports = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await reportsApi.list(projectId);
      setAllReports(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load reports"
      );
    }
    setLoading(false);
  }, [projectId]);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  // Group reports by layer
  const l2Reports = allReports.filter((r) => r.layer === 2);
  const l3Reports = allReports.filter((r) => r.layer === 3);
  const l4Reports = allReports.filter((r) => r.layer === 4);

  // Loading state
  if (loading) {
    return (
      <div className="flex-1 overflow-y-auto" role="status" aria-live="polite" aria-label="Loading reports">
        <span className="sr-only">Loading project reports...</span>
        <div className="p-4 border-b border-slate-200 dark:border-slate-800">
          <div className="h-6 w-48 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
        </div>
        {/* Skeleton pyramid */}
        <div className="p-6 space-y-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="space-y-2">
              <div className="h-4 w-32 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
              <div className="flex gap-3">
                {Array.from({ length: 4 - i }).map((_, j) => (
                  <div
                    key={j}
                    className="flex-1 h-28 bg-slate-100 dark:bg-slate-800 rounded-lg animate-pulse"
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center p-8" role="alert">
        <div className="text-center">
          <AlertCircle
            size={32}
            className="mx-auto text-red-500 dark:text-red-400 mb-3"
            aria-hidden="true"
          />
          <p className="text-sm text-red-600 dark:text-red-400 font-medium mb-1">
            Failed to load reports
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
            {error}
          </p>
          <button
            onClick={loadReports}
            aria-label="Retry loading reports"
            className="text-xs px-3 py-1.5 rounded-md bg-reclaw-600 text-white hover:bg-reclaw-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-reclaw-500 focus-visible:ring-offset-1"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Empty state
  if (allReports.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-8" role="status">
        <div className="text-center">
          <FileStack
            size={32}
            className="mx-auto text-slate-300 dark:text-slate-600 mb-3"
            aria-hidden="true"
          />
          <p className="text-sm text-slate-500 dark:text-slate-400 font-medium">
            No reports yet
          </p>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-1">
            Findings will converge as analyses complete
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto" role="region" aria-label="Convergence pyramid reports">
      {/* Header */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-2">
          <FileStack
            size={18}
            className="text-reclaw-600 dark:text-reclaw-400"
            aria-hidden="true"
          />
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
            Convergence Pyramid
          </h2>
          <span className="text-xs bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 px-2 py-0.5 rounded-full">
            {allReports.length} report{allReports.length !== 1 ? "s" : ""}
          </span>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Reports converge from individual analyses to final synthesis
        </p>
      </div>

      {/* Convergence pyramid visualization */}
      <div className="p-6 space-y-8">
        {/* L4 — top of the pyramid (narrowest) */}
        <PyramidLayer
          layer={4}
          reports={l4Reports}
          totalWidth="max-w-md"
        />

        {/* Visual connector */}
        {(l4Reports.length > 0 || l3Reports.length > 0) && (
          <div className="flex justify-center" aria-hidden="true">
            <div className="flex flex-col items-center gap-1">
              <ArrowUpRight
                size={16}
                className="text-slate-300 dark:text-slate-600 rotate-[-45deg]"
              />
              <span className="text-[10px] text-slate-400 dark:text-slate-500">
                converges
              </span>
            </div>
          </div>
        )}

        {/* L3 — middle of the pyramid */}
        <PyramidLayer
          layer={3}
          reports={l3Reports}
          totalWidth="max-w-2xl"
        />

        {/* Visual connector */}
        {(l3Reports.length > 0 || l2Reports.length > 0) && (
          <div className="flex justify-center" aria-hidden="true">
            <div className="flex flex-col items-center gap-1">
              <ArrowUpRight
                size={16}
                className="text-slate-300 dark:text-slate-600 rotate-[-45deg]"
              />
              <span className="text-[10px] text-slate-400 dark:text-slate-500">
                synthesizes
              </span>
            </div>
          </div>
        )}

        {/* L2 — base of the pyramid (widest) */}
        <PyramidLayer
          layer={2}
          reports={l2Reports}
          totalWidth="max-w-4xl"
        />
      </div>
    </div>
  );
}

// --- Sub-components ---

function PyramidLayer({
  layer,
  reports,
  totalWidth,
}: {
  layer: number;
  reports: ProjectReport[];
  totalWidth: string;
}) {
  const config = LAYER_CONFIG[layer];

  if (!config) return null;

  return (
    <div className={cn("mx-auto w-full", totalWidth)} role="region" aria-label={config.label}>
      {/* Layer label */}
      <div className="flex items-center gap-2 mb-3">
        <Layers size={14} className={config.color} aria-hidden="true" />
        <h3 className={cn("text-sm font-semibold", config.color)}>
          {config.label}
        </h3>
        <span className="text-xs text-slate-400 dark:text-slate-500">
          {config.description}
        </span>
        {reports.length > 0 && (
          <span
            className={cn(
              "text-[10px] font-medium px-1.5 py-0.5 rounded-full",
              config.bgColor,
              config.color
            )}
          >
            <span className="sr-only">{reports.length} reports</span>
            <span aria-hidden="true">{reports.length}</span>
          </span>
        )}
      </div>

      {/* Report cards */}
      {reports.length === 0 ? (
        <div
          role="status"
          className={cn(
            "border border-dashed rounded-lg p-4 text-center",
            config.borderColor
          )}
        >
          <p className="text-xs text-slate-400 dark:text-slate-500">
            No {config.label.toLowerCase()} reports yet
          </p>
        </div>
      ) : (
        <div
          role="list"
          aria-label={`${config.label} reports`}
          className="grid gap-3"
          style={{
            gridTemplateColumns: `repeat(${Math.min(reports.length, 3)}, minmax(0, 1fr))`,
          }}
        >
          {reports.map((report) => (
            <ReportCard key={report.id} report={report} layer={layer} />
          ))}
        </div>
      )}
    </div>
  );
}

function ReportCard({
  report,
  layer,
}: {
  report: ProjectReport;
  layer: number;
}) {
  const config = LAYER_CONFIG[layer];
  const statusConfig = STATUS_BADGE[report.status] || STATUS_BADGE.draft;

  return (
    <article
      role="listitem"
      tabIndex={0}
      className={cn(
        "border rounded-lg p-4 transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-reclaw-500 focus-visible:ring-offset-1",
        config?.borderColor || "border-slate-200 dark:border-slate-700",
        config?.bgColor || "bg-white dark:bg-slate-900"
      )}
      aria-label={`Report: ${report.title}`}
    >
      {/* Title + badges */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <h4 className="text-sm font-semibold text-slate-900 dark:text-white leading-tight line-clamp-2">
          {report.title}
        </h4>
        <div className="flex items-center gap-1 shrink-0">
          {/* Triangulated badge for L3 */}
          {layer === 3 && (
            <span className="text-[10px] font-medium bg-purple-200 dark:bg-purple-800/40 text-purple-700 dark:text-purple-300 px-1.5 py-0.5 rounded-full whitespace-nowrap">
              Triangulated
            </span>
          )}
          {/* Status badge */}
          <span
            role="status"
            className={cn(
              "text-[10px] font-medium px-1.5 py-0.5 rounded-full whitespace-nowrap",
              statusConfig.className
            )}
          >
            <span className="sr-only">Status: </span>
            {statusConfig.label}
          </span>
        </div>
      </div>

      {/* Scope */}
      {report.scope && (
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-2 line-clamp-2">
          {report.scope}
        </p>
      )}

      {/* Executive summary preview */}
      {report.executive_summary && (
        <p className="text-xs text-slate-600 dark:text-slate-300 mb-3 line-clamp-3 leading-relaxed">
          {report.executive_summary}
        </p>
      )}

      {/* Metadata row */}
      <div className="flex items-center flex-wrap gap-x-3 gap-y-1 text-[10px] text-slate-400 dark:text-slate-500">
        <span>
          {report.finding_count} finding
          {report.finding_count !== 1 ? "s" : ""}
        </span>
        <span>v{report.version}</span>
        <span>{formatDate(report.updated_at)}</span>
      </div>

      {/* MECE categories preview */}
      {report.mece_categories && report.mece_categories.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1" role="list" aria-label="MECE categories">
          {report.mece_categories.slice(0, 3).map((cat) => (
            <span
              key={cat.name}
              role="listitem"
              className="text-[10px] bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 px-1.5 py-0.5 rounded"
              title={cat.description}
            >
              {cat.name}
              {cat.finding_ids.length > 0 && (
                <span className="ml-0.5 opacity-70">
                  ({cat.finding_ids.length}<span className="sr-only"> findings</span>)
                </span>
              )}
            </span>
          ))}
          {report.mece_categories.length > 3 && (
            <span className="text-[10px] text-slate-400 dark:text-slate-500">
              +{report.mece_categories.length - 3} more
            </span>
          )}
        </div>
      )}
    </article>
  );
}
