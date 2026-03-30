"use client";

import { useEffect, useState } from "react";
import { Search, X, CheckSquare, Square } from "lucide-react";
import { findings as findingsApi } from "@/lib/api";
import { cn } from "@/lib/utils";

type FindingTab = "insights" | "recommendations";

interface FindingsPickerProps {
  projectId: string;
  selectedIds: string[];
  onConfirm: (ids: string[]) => void;
  onCancel: () => void;
}

export default function FindingsPicker({ projectId, selectedIds, onConfirm, onCancel }: FindingsPickerProps) {
  const [tab, setTab] = useState<FindingTab>("insights");
  const [insights, setInsights] = useState<any[]>([]);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set(selectedIds));
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      findingsApi.insights(projectId),
      findingsApi.recommendations(projectId),
    ])
      .then(([ins, recs]) => {
        setInsights(ins || []);
        setRecommendations(recs || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId]);

  const items = tab === "insights" ? insights : recommendations;
  const filtered = items.filter((item: any) =>
    item.text?.toLowerCase().includes(search.toLowerCase())
  );

  const toggle = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onCancel}>
      <div
        className="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-lg mx-4 max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800">
          <h3 className="font-semibold text-slate-900 dark:text-white">Seed from Findings</h3>
          <div className="flex items-center gap-2">
            <span className="text-xs bg-istara-100 dark:bg-istara-900/30 text-istara-700 dark:text-istara-400 px-2 py-0.5 rounded-full">
              {selected.size} selected
            </span>
            <button onClick={onCancel} className="text-slate-400 hover:text-slate-600" aria-label="Close">
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 px-4 pt-3">
          {(["insights", "recommendations"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                "px-3 py-1.5 text-sm rounded-md capitalize transition-colors",
                tab === t
                  ? "bg-istara-100 text-istara-700 dark:bg-istara-900/30 dark:text-istara-400"
                  : "text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
              )}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="px-4 py-2">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Filter findings..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-istara-500"
            />
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto px-4 pb-2 space-y-1">
          {loading ? (
            <p className="text-sm text-slate-400 py-4 text-center">Loading findings...</p>
          ) : filtered.length === 0 ? (
            <p className="text-sm text-slate-400 py-4 text-center">No {tab} found.</p>
          ) : (
            filtered.map((item: any) => (
              <button
                key={item.id}
                onClick={() => toggle(item.id)}
                className={cn(
                  "w-full flex items-start gap-2 text-left px-3 py-2 rounded-lg text-sm transition-colors",
                  selected.has(item.id)
                    ? "bg-istara-50 dark:bg-istara-900/20"
                    : "hover:bg-slate-50 dark:hover:bg-slate-800/50"
                )}
              >
                {selected.has(item.id) ? (
                  <CheckSquare size={16} className="text-istara-600 shrink-0 mt-0.5" />
                ) : (
                  <Square size={16} className="text-slate-300 dark:text-slate-600 shrink-0 mt-0.5" />
                )}
                <span className="text-slate-700 dark:text-slate-300 line-clamp-2">{item.text}</span>
              </button>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-slate-200 dark:border-slate-800">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(Array.from(selected))}
            className="px-4 py-2 text-sm bg-istara-600 text-white rounded-lg hover:bg-istara-700 transition-colors"
          >
            Confirm ({selected.size})
          </button>
        </div>
      </div>
    </div>
  );
}
