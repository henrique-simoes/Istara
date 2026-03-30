"use client";

import { useEffect, useState, useMemo } from "react";
import { BarChart3, ChevronDown, ChevronRight, ArrowUpDown } from "lucide-react";
import { useLawsStore } from "@/stores/lawsStore";
import { useProjectStore } from "@/stores/projectStore";
import { cn } from "@/lib/utils";

const CATEGORY_BADGE_COLORS: Record<string, string> = {
  perception: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  cognitive: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  behavioral: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  principles: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
};

const CATEGORY_CARD_COLORS: Record<string, { bg: string; text: string; bar: string }> = {
  perception: {
    bg: "bg-blue-50 dark:bg-blue-900/20",
    text: "text-blue-700 dark:text-blue-400",
    bar: "bg-blue-500",
  },
  cognitive: {
    bg: "bg-purple-50 dark:bg-purple-900/20",
    text: "text-purple-700 dark:text-purple-400",
    bar: "bg-purple-500",
  },
  behavioral: {
    bg: "bg-green-50 dark:bg-green-900/20",
    text: "text-green-700 dark:text-green-400",
    bar: "bg-green-500",
  },
  principles: {
    bg: "bg-amber-50 dark:bg-amber-900/20",
    text: "text-amber-700 dark:text-amber-400",
    bar: "bg-amber-500",
  },
};

function scoreColor(score: number): string {
  if (score >= 80) return "text-green-600 dark:text-green-400";
  if (score >= 50) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

function scoreBarColor(score: number): string {
  if (score >= 80) return "bg-green-500";
  if (score >= 50) return "bg-amber-500";
  return "bg-red-500";
}

export default function ComplianceProfile() {
  const { compliance, loading, error, fetchCompliance } = useLawsStore();
  const { activeProjectId } = useProjectStore();
  const [sortAsc, setSortAsc] = useState(true);
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  useEffect(() => {
    if (activeProjectId) {
      fetchCompliance(activeProjectId);
    }
  }, [activeProjectId, fetchCompliance]);

  const sortedLaws = useMemo(() => {
    if (!compliance?.by_law) return [];
    const items = [...compliance.by_law];
    items.sort((a, b) => (sortAsc ? a.score - b.score : b.score - a.score));
    return items;
  }, [compliance, sortAsc]);

  if (!activeProjectId) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400 p-4">
        <p>Select a project to view compliance data.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="h-24 bg-slate-200 dark:bg-slate-700 rounded-lg animate-pulse" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-20 bg-slate-200 dark:bg-slate-700 rounded-lg animate-pulse" />
          ))}
        </div>
        <div className="h-64 bg-slate-200 dark:bg-slate-700 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center text-red-500 dark:text-red-400 p-4">
        <p>Failed to load compliance data: {error}</p>
      </div>
    );
  }

  if (!compliance) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-slate-400 p-8">
        <BarChart3 size={40} className="mb-3 opacity-50" />
        <p className="text-sm font-medium text-slate-600 dark:text-slate-300 mb-1">
          No Compliance Data Yet
        </p>
        <p className="text-xs text-center max-w-sm">
          Run a UX Law Compliance Audit or Heuristic Evaluation to generate compliance data for this project.
        </p>
      </div>
    );
  }

  const categories = compliance.by_category ? Object.entries(compliance.by_category) : [];

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-6">
      {/* Overall score */}
      <div className="flex items-center gap-4 p-4 bg-white dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-lg">
        <div className="text-center">
          <p className={cn("text-4xl font-bold", scoreColor(compliance.overall_score))}>
            {Math.round(compliance.overall_score)}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Overall Score</p>
        </div>
        <div className="flex-1">
          <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
            <div
              className={cn("h-full rounded-full transition-all", scoreBarColor(compliance.overall_score))}
              style={{ width: `${Math.min(100, compliance.overall_score)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Category score cards */}
      {categories.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {categories.map(([cat, data]) => {
            const colors = CATEGORY_CARD_COLORS[cat] || {
              bg: "bg-slate-50 dark:bg-slate-800",
              text: "text-slate-700 dark:text-slate-300",
              bar: "bg-slate-500",
            };
            return (
              <div key={cat} className={cn("rounded-lg p-3", colors.bg)}>
                <p className={cn("text-xs font-semibold uppercase", colors.text)}>{cat}</p>
                <p className={cn("text-2xl font-bold mt-1", scoreColor(data.score))}>
                  {Math.round(data.score)}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] text-slate-500 dark:text-slate-400">
                    {data.laws_evaluated} laws
                  </span>
                  {data.violations > 0 && (
                    <span className="text-[10px] text-red-500 dark:text-red-400">
                      {data.violations} violations
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Per-law score table */}
      {sortedLaws.length > 0 && (
        <div className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
          {/* Table header */}
          <div className="grid grid-cols-[1fr_100px_120px_80px] gap-2 px-4 py-2 bg-slate-50 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-700">
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
              Law Name
            </span>
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
              Category
            </span>
            <button
              onClick={() => setSortAsc(!sortAsc)}
              className="flex items-center gap-1 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
              aria-label={`Sort by score ${sortAsc ? "descending" : "ascending"}`}
            >
              Score
              <ArrowUpDown size={12} />
            </button>
            <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">
              Violations
            </span>
          </div>

          {/* Table rows */}
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            {sortedLaws.map((item) => {
              const isExpanded = expandedRow === item.law_id;
              const badgeColor = CATEGORY_BADGE_COLORS[item.category] || "bg-slate-100 text-slate-600";

              return (
                <div key={item.law_id}>
                  <button
                    onClick={() => setExpandedRow(isExpanded ? null : item.law_id)}
                    className="w-full grid grid-cols-[1fr_100px_120px_80px] gap-2 px-4 py-3 text-left hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors"
                    aria-expanded={isExpanded}
                    aria-label={`${item.law_name} - ${item.violation_count} violations`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      {isExpanded ? (
                        <ChevronDown size={14} className="shrink-0 text-slate-400" />
                      ) : (
                        <ChevronRight size={14} className="shrink-0 text-slate-400" />
                      )}
                      <span className="text-sm text-slate-900 dark:text-white truncate">
                        {item.law_name}
                      </span>
                    </div>
                    <span className={cn("inline-flex items-center self-center px-2 py-0.5 rounded-full text-xs font-medium w-fit", badgeColor)}>
                      {item.category}
                    </span>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className={cn("h-full rounded-full", scoreBarColor(item.score))}
                          style={{ width: `${Math.min(100, item.score)}%` }}
                        />
                      </div>
                      <span className={cn("text-xs font-medium w-8 text-right", scoreColor(item.score))}>
                        {Math.round(item.score)}
                      </span>
                    </div>
                    <span className={cn(
                      "text-sm text-center",
                      item.violation_count > 0 ? "text-red-600 dark:text-red-400" : "text-slate-400"
                    )}>
                      {item.violation_count}
                    </span>
                  </button>

                  {/* Expanded row: linked finding IDs */}
                  {isExpanded && item.finding_ids && item.finding_ids.length > 0 && (
                    <div className="px-4 pb-3 pl-10">
                      <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">Linked Findings:</p>
                      <div className="flex flex-wrap gap-1">
                        {item.finding_ids.map((fid) => (
                          <span
                            key={fid}
                            className="text-[10px] bg-istara-50 dark:bg-istara-900/20 text-istara-600 dark:text-istara-400 rounded px-1.5 py-0.5 font-mono"
                          >
                            {fid.slice(0, 8)}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {isExpanded && (!item.finding_ids || item.finding_ids.length === 0) && (
                    <div className="px-4 pb-3 pl-10">
                      <p className="text-xs text-slate-400 italic">No linked findings.</p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
