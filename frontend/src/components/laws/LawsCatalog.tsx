"use client";

import { useState, useMemo } from "react";
import { Search, ChevronDown, ChevronUp, BookOpen } from "lucide-react";
import { useLawsStore } from "@/stores/lawsStore";
import { cn } from "@/lib/utils";
import type { LawCategory, UXLaw } from "@/lib/types";
import LawBadge from "./LawBadge";

const CATEGORY_META: {
  id: LawCategory;
  label: string;
  color: string;
  activeColor: string;
}[] = [
  {
    id: "perception",
    label: "Perception",
    color: "text-blue-600 dark:text-blue-400",
    activeColor: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 ring-2 ring-blue-500/50",
  },
  {
    id: "cognitive",
    label: "Cognitive",
    color: "text-purple-600 dark:text-purple-400",
    activeColor: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 ring-2 ring-purple-500/50",
  },
  {
    id: "behavioral",
    label: "Behavioral",
    color: "text-green-600 dark:text-green-400",
    activeColor: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 ring-2 ring-green-500/50",
  },
  {
    id: "principles",
    label: "Principles",
    color: "text-amber-600 dark:text-amber-400",
    activeColor: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 ring-2 ring-amber-500/50",
  },
];

const CATEGORY_BADGE_COLORS: Record<string, string> = {
  perception: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  cognitive: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  behavioral: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  principles: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
};

export default function LawsCatalog() {
  const { laws, loading, error, categoryFilter, setCategoryFilter, searchQuery, setSearchQuery } = useLawsStore();
  const [expandedLawId, setExpandedLawId] = useState<string | null>(null);

  const filteredLaws = useMemo(() => {
    let result = laws;
    if (categoryFilter) {
      result = result.filter((l) => l.category === categoryFilter);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (l) =>
          l.name.toLowerCase().includes(q) ||
          l.description.toLowerCase().includes(q) ||
          l.cluster.toLowerCase().includes(q) ||
          l.detection_keywords?.some((kw) => kw.toLowerCase().includes(q))
      );
    }
    return result;
  }, [laws, categoryFilter, searchQuery]);

  const toggleExpand = (id: string) => {
    setExpandedLawId(expandedLawId === id ? null : id);
  };

  if (loading && laws.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="h-10 bg-slate-200 dark:bg-slate-700 rounded-lg animate-pulse" />
        <div className="flex gap-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-8 w-24 bg-slate-200 dark:bg-slate-700 rounded-lg animate-pulse" />
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-48 bg-slate-200 dark:bg-slate-700 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center text-red-500 dark:text-red-400 p-4">
        <p>Failed to load UX Laws: {error}</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {/* Search bar */}
      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          placeholder="Search laws by name, description, or keyword..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full pl-9 pr-4 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-reclaw-500"
          aria-label="Search UX laws"
        />
      </div>

      {/* Category filter buttons */}
      <div className="flex flex-wrap gap-2">
        {CATEGORY_META.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setCategoryFilter(categoryFilter === cat.id ? null : cat.id)}
            className={cn(
              "px-3 py-1.5 rounded-lg text-sm font-medium transition-colors",
              categoryFilter === cat.id
                ? cat.activeColor
                : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700"
            )}
            aria-label={`Filter by ${cat.label}`}
            aria-pressed={categoryFilter === cat.id}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* Laws grid */}
      {filteredLaws.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-slate-400">
          <BookOpen size={40} className="mb-3 opacity-50" />
          <p className="text-sm">No UX laws match your search.</p>
          {(searchQuery || categoryFilter) && (
            <button
              onClick={() => {
                setSearchQuery("");
                setCategoryFilter(null);
              }}
              className="mt-2 text-sm text-reclaw-600 dark:text-reclaw-400 hover:underline"
            >
              Clear filters
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredLaws.map((law) => (
            <LawCard
              key={law.id}
              law={law}
              expanded={expandedLawId === law.id}
              onToggle={() => toggleExpand(law.id)}
            />
          ))}
        </div>
      )}

      {/* Attribution footer */}
      <div className="pt-4 pb-2 text-center">
        <p className="text-xs text-slate-400 dark:text-slate-500">
          Based on Laws of UX by Jon Yablonski (lawsofux.com)
        </p>
      </div>
    </div>
  );
}

function LawCard({
  law,
  expanded,
  onToggle,
}: {
  law: UXLaw;
  expanded: boolean;
  onToggle: () => void;
}) {
  const categoryColor = CATEGORY_BADGE_COLORS[law.category] || "bg-slate-100 text-slate-600";

  return (
    <div
      className={cn(
        "border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-800/50 transition-shadow",
        expanded && "shadow-md ring-1 ring-reclaw-200 dark:ring-reclaw-800"
      )}
    >
      {/* Card header */}
      <button
        onClick={onToggle}
        className="w-full text-left p-4 focus:outline-none focus:ring-2 focus:ring-reclaw-500 rounded-t-lg"
        aria-expanded={expanded}
        aria-label={`${law.name} - click to ${expanded ? "collapse" : "expand"} details`}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white truncate">
              {law.name}
            </h3>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 line-clamp-2">
              {law.description}
            </p>
          </div>
          {expanded ? (
            <ChevronUp size={16} className="shrink-0 text-slate-400 mt-0.5" />
          ) : (
            <ChevronDown size={16} className="shrink-0 text-slate-400 mt-0.5" />
          )}
        </div>

        {/* Meta row */}
        <div className="flex flex-wrap items-center gap-2 mt-3">
          <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium", categoryColor)}>
            {law.category}
          </span>
          {law.origin && (
            <span className="text-xs text-slate-400">
              {law.origin.author}, {law.origin.year}
            </span>
          )}
        </div>

        {/* Heuristic badges */}
        {law.related_nielsen_heuristics && law.related_nielsen_heuristics.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {law.related_nielsen_heuristics.map((h) => (
              <span
                key={h}
                className="text-[10px] bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 rounded px-1.5 py-0.5"
              >
                {h}
              </span>
            ))}
          </div>
        )}
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-slate-200 dark:border-slate-700 p-4 space-y-4">
          {/* Key takeaways */}
          {law.key_takeaways && law.key_takeaways.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400 mb-1">
                Key Takeaways
              </h4>
              <ul className="space-y-1">
                {law.key_takeaways.map((t, i) => (
                  <li key={i} className="text-xs text-slate-700 dark:text-slate-300 flex items-start gap-1.5">
                    <span className="text-reclaw-500 mt-0.5 shrink-0">-</span>
                    <span>{t}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Design implications */}
          {law.design_implications && law.design_implications.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400 mb-1">
                Design Implications
              </h4>
              <ul className="space-y-1">
                {law.design_implications.map((d, i) => (
                  <li key={i} className="text-xs text-slate-700 dark:text-slate-300 flex items-start gap-1.5">
                    <span className="text-reclaw-500 mt-0.5 shrink-0">-</span>
                    <span>{d}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Severity indicators */}
          {law.severity_indicators && Object.keys(law.severity_indicators).length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400 mb-1">
                Severity Indicators
              </h4>
              <div className="space-y-1">
                {Object.entries(law.severity_indicators).map(([level, desc]) => (
                  <div key={level} className="flex items-start gap-2 text-xs">
                    <span
                      className={cn(
                        "font-medium capitalize shrink-0",
                        level === "critical" && "text-red-600 dark:text-red-400",
                        level === "major" && "text-orange-600 dark:text-orange-400",
                        level === "minor" && "text-yellow-600 dark:text-yellow-400",
                        level === "cosmetic" && "text-slate-500 dark:text-slate-400"
                      )}
                    >
                      {level}:
                    </span>
                    <span className="text-slate-700 dark:text-slate-300">{desc}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Examples */}
          {law.examples && law.examples.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400 mb-1">
                Examples
              </h4>
              <ul className="space-y-1">
                {law.examples.map((ex, i) => (
                  <li key={i} className="text-xs text-slate-700 dark:text-slate-300 flex items-start gap-1.5">
                    <span className="text-reclaw-500 mt-0.5 shrink-0">-</span>
                    <span>{ex}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Academic references */}
          {law.academic_references && law.academic_references.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase text-slate-500 dark:text-slate-400 mb-1">
                Academic References
              </h4>
              <ul className="space-y-1">
                {law.academic_references.map((ref, i) => (
                  <li key={i} className="text-xs text-slate-500 dark:text-slate-400 italic">
                    {ref}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
