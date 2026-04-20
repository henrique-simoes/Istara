"use client";

import { useEffect, useState, useCallback } from "react";
import {
  FileStack,
  AlertCircle,
  Layers,
  TriangleAlert,
  ArrowUpRight,
  Presentation,
  ClipboardCopy,
  Check,
} from "lucide-react";
import { reports as reportsApi, presentation as presentationApi } from "@/lib/api";
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
    color: "text-istara-700 dark:text-istara-400",
    bgColor: "bg-istara-50 dark:bg-istara-900/20",
    borderColor: "border-istara-200 dark:border-istara-800",
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
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [slideInstructions, setSlideInstructions] = useState<{title: string, content: string} | null>(null);
  const [loadingSlides, setLoadingSlides] = useState(false);
  const [copied, setCopied] = useState(false);

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

  const fetchSlideInstructions = async (reportId: string) => {
    setLoadingSlides(true);
    try {
      const data = await presentationApi.slideInstructions(reportId);
      setSlideInstructions({
        title: data.title,
        content: data.instructions,
      });
    } catch (err) {
      console.error("Failed to fetch slide instructions:", err);
    }
    setLoadingSlides(false);
  };

  const copyToClipboard = () => {
    if (!slideInstructions) return;
    navigator.clipboard.writeText(slideInstructions.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

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
            className="text-xs px-3 py-1.5 rounded-md bg-istara-600 text-white hover:bg-istara-700 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-istara-500 focus-visible:ring-offset-1"
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
            className="text-istara-600 dark:text-istara-400"
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
          selectedReportId={selectedReportId}
          onSelectReport={setSelectedReportId}
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
          selectedReportId={selectedReportId}
          onSelectReport={setSelectedReportId}
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
          selectedReportId={selectedReportId}
          onSelectReport={setSelectedReportId}
        />

        {/* Selected report detail panel */}
        {selectedReportId && (() => {
          const report = allReports.find((r) => r.id === selectedReportId);
          if (!report) return null;
          const layerConfig = LAYER_CONFIG[report.layer];
          const statusConfig = STATUS_BADGE[report.status] || STATUS_BADGE.draft;

          // Compute finding counts by type from mece_categories
          const totalFindings = report.finding_count;
          const meceCategories = report.mece_categories || [];

          return (
            <div className="transition-all duration-200 mt-4 mx-auto max-w-4xl bg-white dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm">
              <div className="flex items-start justify-between gap-4 mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    {layerConfig && (
                      <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", layerConfig.bgColor, layerConfig.color)}>
                        {layerConfig.label}
                      </span>
                    )}
                    <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", statusConfig.className)}>
                      {statusConfig.label}
                    </span>
                  </div>
                  <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                    {report.title}
                  </h3>
                </div>
                <button
                  onClick={() => setSelectedReportId(null)}
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 p-1"
                  aria-label="Close detail panel"
                >
                  <span className="text-sm">Close</span>
                </button>
              </div>

              {/* Executive summary */}
              {report.executive_summary && (
                <div className="mb-4">
                  <h4 className="text-xs font-semibold uppercase text-slate-500 mb-1">Executive Summary</h4>
                  <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                    {report.executive_summary}
                  </p>
                </div>
              )}

              {/* Stats grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                <div className="text-center p-2 rounded-lg bg-slate-50 dark:bg-slate-900/50">
                  <p className="text-lg font-semibold text-slate-900 dark:text-white">{totalFindings}</p>
                  <p className="text-[10px] text-slate-500">Total Findings</p>
                </div>
                <div className="text-center p-2 rounded-lg bg-slate-50 dark:bg-slate-900/50">
                  <p className="text-lg font-semibold text-slate-900 dark:text-white">v{report.version}</p>
                  <p className="text-[10px] text-slate-500">Version</p>
                </div>
                <div className="text-center p-2 rounded-lg bg-slate-50 dark:bg-slate-900/50">
                  <p className="text-lg font-semibold text-slate-900 dark:text-white">{meceCategories.length}</p>
                  <p className="text-[10px] text-slate-500">MECE Categories</p>
                </div>
                <div className="text-center p-2 rounded-lg bg-slate-50 dark:bg-slate-900/50">
                  <p className="text-sm font-medium text-slate-700 dark:text-slate-300">{formatDate(report.updated_at)}</p>
                  <p className="text-[10px] text-slate-500">Last Updated</p>
                </div>
              </div>

              {/* MECE Categories */}
              {meceCategories.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-xs font-semibold uppercase text-slate-500 mb-2">MECE Categories</h4>
                  <div className="flex flex-wrap gap-2">
                    {meceCategories.map((cat) => (
                      <div
                        key={cat.name}
                        className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-700 border border-slate-200 dark:border-slate-600"
                        title={cat.description}
                      >
                        <span className="text-xs font-medium text-slate-700 dark:text-slate-300">
                          {cat.name}
                        </span>
                        {cat.finding_ids.length > 0 && (
                          <span className="ml-1.5 text-[10px] text-slate-500">
                            ({cat.finding_ids.length} findings)
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Scope */}
              {report.scope && (
                <div className="mb-6">
                  <h4 className="text-xs font-semibold uppercase text-slate-500 mb-1">Scope</h4>
                  <p className="text-xs text-slate-600 dark:text-slate-400">{report.scope}</p>
                </div>
              )}

              {/* Presentation Feature */}
              <div className="pt-4 border-t border-slate-100 dark:border-slate-800 flex justify-center">
                <button
                  onClick={() => fetchSlideInstructions(report.id)}
                  disabled={loadingSlides}
                  className="flex items-center gap-2 px-4 py-2 bg-istara-600 hover:bg-istara-700 text-white rounded-lg text-sm font-medium transition-all shadow-sm hover:shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loadingSlides ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Presentation size={18} />
                  )}
                  {loadingSlides ? "Generating..." : "Instructions to create slides"}
                </button>
              </div>
            </div>
          );
        })()}
      </div>

      {/* Slide Instructions Modal */}
      {slideInstructions && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white dark:bg-slate-900 w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden border border-slate-200 dark:border-slate-800 flex flex-col max-h-[85vh]">
            <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Presentation className="text-istara-600" size={20} />
                <h3 className="font-bold text-slate-900 dark:text-white truncate max-w-[400px]">
                  {slideInstructions.title}
                </h3>
              </div>
              <button 
                onClick={() => setSlideInstructions(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                Close
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto bg-slate-50 dark:bg-slate-950 flex-1">
              <div className="flex items-center justify-between mb-4">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Minto Pyramid / Action Titles / SCR Instructions
                </span>
                <button
                  onClick={copyToClipboard}
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all",
                    copied 
                      ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                      : "bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 hover:border-istara-500"
                  )}
                >
                  {copied ? <Check size={14} /> : <ClipboardCopy size={14} />}
                  {copied ? "Copied!" : "Copy Instructions"}
                </button>
              </div>
              <pre className="text-sm text-slate-800 dark:text-slate-300 whitespace-pre-wrap font-sans leading-relaxed">
                {slideInstructions.content}
              </pre>
            </div>
            
            <div className="p-4 border-t border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900 text-center">
              <p className="text-[11px] text-slate-400">
                Paste these instructions into another AI to generate a professional executive slide deck.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// --- Sub-components ---

function PyramidLayer({
  layer,
  reports,
  totalWidth,
  selectedReportId,
  onSelectReport,
}: {
  layer: number;
  reports: ProjectReport[];
  totalWidth: string;
  selectedReportId: string | null;
  onSelectReport: (id: string) => void;
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
            <ReportCard
              key={report.id}
              report={report}
              layer={layer}
              isSelected={selectedReportId === report.id}
              onSelect={() => onSelectReport(report.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ReportCard({
  report,
  layer,
  isSelected,
  onSelect,
}: {
  report: ProjectReport;
  layer: number;
  isSelected: boolean;
  onSelect: () => void;
}) {
  const config = LAYER_CONFIG[layer];
  const statusConfig = STATUS_BADGE[report.status] || STATUS_BADGE.draft;

  return (
    <article
      role="listitem"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(); } }}
      className={cn(
        "border rounded-lg p-4 transition-all duration-200 cursor-pointer hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-istara-500 focus-visible:ring-offset-1",
        config?.borderColor || "border-slate-200 dark:border-slate-700",
        config?.bgColor || "bg-white dark:bg-slate-900",
        isSelected && "ring-2 ring-istara-500 shadow-md"
      )}
      aria-label={`Report: ${report.title}`}
      aria-selected={isSelected}
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
