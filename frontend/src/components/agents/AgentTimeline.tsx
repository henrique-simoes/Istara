"use client";

import { useState, useEffect } from "react";
import { Clock, RotateCcw, Filter, CheckCircle, FileText, MessageSquare, ListTodo, ChevronDown } from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { findings as findingsApi, tasks as tasksApi } from "@/lib/api";
import { cn } from "@/lib/utils";

interface TimelineEntry {
  id: string;
  type: "nugget" | "fact" | "insight" | "recommendation" | "task";
  title: string;
  agent_id: string | null;
  agent_name: string;
  created_at: string;
  selected: boolean;
}

const TYPE_ICONS: Record<string, typeof FileText> = {
  nugget: FileText,
  fact: CheckCircle,
  insight: CheckCircle,
  recommendation: CheckCircle,
  task: ListTodo,
};

const TYPE_COLORS: Record<string, string> = {
  nugget: "text-blue-500",
  fact: "text-purple-500",
  insight: "text-amber-500",
  recommendation: "text-green-500",
  task: "text-istara-500",
};

export default function AgentTimeline() {
  const { activeProjectId } = useProjectStore();
  const [entries, setEntries] = useState<TimelineEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterAgent, setFilterAgent] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showFilter, setShowFilter] = useState(false);

  useEffect(() => {
    if (!activeProjectId) return;
    loadTimeline();
  }, [activeProjectId]);

  const loadTimeline = async () => {
    if (!activeProjectId) return;
    setLoading(true);
    try {
      const [nuggets, facts, insights, recs, taskList] = await Promise.all([
        findingsApi.nuggets(activeProjectId),
        findingsApi.facts(activeProjectId),
        findingsApi.insights(activeProjectId),
        findingsApi.recommendations(activeProjectId),
        tasksApi.list(activeProjectId).then((r: any) => r.tasks || r || []),
      ]);

      const all: TimelineEntry[] = [];

      for (const n of nuggets) {
        all.push({ id: n.id, type: "nugget", title: n.text?.slice(0, 80) || "Nugget", agent_id: n.agent_id || null, agent_name: n.agent_id || "Istara", created_at: n.created_at, selected: false });
      }
      for (const f of facts) {
        all.push({ id: f.id, type: "fact", title: f.text?.slice(0, 80) || "Fact", agent_id: f.agent_id || null, agent_name: f.agent_id || "Istara", created_at: f.created_at, selected: false });
      }
      for (const i of insights) {
        all.push({ id: i.id, type: "insight", title: i.text?.slice(0, 80) || "Insight", agent_id: i.agent_id || null, agent_name: i.agent_id || "Istara", created_at: i.created_at, selected: false });
      }
      for (const r of recs) {
        all.push({ id: r.id, type: "recommendation", title: r.text?.slice(0, 80) || "Recommendation", agent_id: r.agent_id || null, agent_name: r.agent_id || "Istara", created_at: r.created_at, selected: false });
      }
      for (const t of taskList) {
        all.push({ id: t.id, type: "task", title: t.title || "Task", agent_id: t.agent_id || null, agent_name: t.agent_id || "Istara", created_at: t.created_at, selected: false });
      }

      all.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      setEntries(all);
    } catch (e) {
      console.error("Failed to load timeline:", e);
    }
    setLoading(false);
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    const filtered = filteredEntries.map((e) => e.id);
    setSelectedIds(new Set(filtered));
  };

  const handleRollback = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`Roll back ${selectedIds.size} item(s)? This will delete the selected findings/tasks.`)) return;

    for (const id of Array.from(selectedIds)) {
      const entry = entries.find((e) => e.id === id);
      if (!entry || !activeProjectId) continue;
      try {
        if (entry.type === "task") {
          await tasksApi.delete(id);
        } else {
          await findingsApi.delete(entry.type, id);
        }
      } catch {
        // continue with others
      }
    }

    setSelectedIds(new Set());
    await loadTimeline();
  };

  const agents = Array.from(new Set(entries.map((e) => e.agent_name)));
  const filteredEntries = filterAgent
    ? entries.filter((e) => e.agent_name === filterAgent)
    : entries;

  const formatTime = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  };

  if (!activeProjectId) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        <p>Select a project to view agent timeline.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto p-6 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <Clock size={20} className="text-istara-600" />
              Agent Timeline
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              View and roll back actions performed by agents.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {/* Agent filter */}
            <div className="relative">
              <button
                onClick={() => setShowFilter(!showFilter)}
                className="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                <Filter size={12} />
                {filterAgent || "All agents"}
                <ChevronDown size={10} />
              </button>
              {showFilter && (
                <div className="absolute right-0 mt-1 z-50 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg py-1 min-w-[140px]">
                  <button
                    onClick={() => { setFilterAgent(null); setShowFilter(false); }}
                    className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-100 dark:hover:bg-slate-700"
                  >
                    All agents
                  </button>
                  {agents.map((a) => (
                    <button
                      key={a}
                      onClick={() => { setFilterAgent(a); setShowFilter(false); }}
                      className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-100 dark:hover:bg-slate-700"
                    >
                      {a}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {selectedIds.size > 0 && (
              <button
                onClick={handleRollback}
                className="flex items-center gap-1 px-3 py-1.5 text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-lg hover:bg-red-200"
              >
                <RotateCcw size={12} />
                Roll back ({selectedIds.size})
              </button>
            )}
          </div>
        </div>

        {/* Timeline */}
        {loading ? (
          <p className="text-sm text-slate-400 text-center py-8">Loading timeline...</p>
        ) : filteredEntries.length === 0 ? (
          <p className="text-sm text-slate-400 text-center py-8">No agent actions found.</p>
        ) : (
          <div className="relative">
            {/* Vertical line */}
            <div className="absolute left-5 top-0 bottom-0 w-px bg-slate-200 dark:bg-slate-700" />

            <div className="space-y-1">
              {filteredEntries.map((entry) => {
                const Icon = TYPE_ICONS[entry.type] || FileText;
                const isSelected = selectedIds.has(entry.id);

                return (
                  <div
                    key={`${entry.type}-${entry.id}`}
                    className={cn(
                      "flex items-start gap-3 pl-2 pr-3 py-2 rounded-lg transition-colors cursor-pointer",
                      isSelected ? "bg-red-50 dark:bg-red-900/10" : "hover:bg-slate-50 dark:hover:bg-slate-800/50"
                    )}
                    onClick={() => toggleSelect(entry.id)}
                  >
                    {/* Checkbox */}
                    <div className={cn(
                      "w-3 h-3 mt-1 rounded border flex-shrink-0 flex items-center justify-center",
                      isSelected ? "bg-red-500 border-red-500" : "border-slate-300 dark:border-slate-600"
                    )}>
                      {isSelected && <span className="text-white text-[8px]">✓</span>}
                    </div>

                    {/* Icon */}
                    <div className={cn("mt-0.5 flex-shrink-0", TYPE_COLORS[entry.type])}>
                      <Icon size={14} />
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] uppercase font-semibold text-slate-400">{entry.type}</span>
                        <span className="text-[10px] text-slate-400">{formatTime(entry.created_at)}</span>
                      </div>
                      <p className="text-xs text-slate-700 dark:text-slate-300 truncate">{entry.title}</p>
                    </div>

                    {/* Agent badge */}
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-500 flex-shrink-0">
                      {entry.agent_name}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
