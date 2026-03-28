"use client";

import { useEffect, useState } from "react";
import { BarChart3, Target, TrendingUp, CheckCircle, MessageSquare, Loader2, AlertCircle } from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { cn } from "@/lib/utils";
import { ApiError } from "@/hooks/useApiCall";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ProjectMetrics {
  findings: { nuggets: number; facts: number; insights: number; recommendations: number; total: number };
  tasks: { total: number; done: number; in_progress: number; completion_rate: number };
  quality: { avg_confidence: number; messages: number };
  by_phase: Record<string, { nuggets: number; facts: number; insights: number; recommendations: number; total: number }>;
}

export default function MetricsView() {
  const { activeProjectId } = useProjectStore();
  const [metrics, setMetrics] = useState<ProjectMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!activeProjectId) return;
    setLoading(true);
    setError(null);
    const _t = localStorage.getItem("reclaw_token");
    const _h: Record<string, string> = {};
    if (_t) _h["Authorization"] = `Bearer ${_t}`;
    fetch(`${API_BASE}/api/metrics/${activeProjectId}`, { headers: _h })
      .then((r) => { if (!r.ok) throw new Error("Failed to load metrics"); return r.json(); })
      .then(setMetrics)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [activeProjectId]);

  if (!activeProjectId) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        <p>Select a project to view metrics.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        <Loader2 size={20} className="animate-spin mr-2" /> Loading metrics...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 p-6">
        <ApiError error={error} onRetry={() => window.location.reload()} />
      </div>
    );
  }

  if (!metrics) return null;

  const maxPhaseTotal = Math.max(...Object.values(metrics.by_phase).map((p) => p.total), 1);

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2 mb-6">
          <BarChart3 size={20} /> 📊 Research Metrics
        </h2>

        {/* Top-level cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <MetricCard emoji="📊" label="Total Findings" value={metrics.findings.total} color="border-reclaw-500" />
          <MetricCard emoji="✅" label="Task Completion" value={`${metrics.tasks.completion_rate}%`}
            sub={`${metrics.tasks.done}/${metrics.tasks.total} tasks`}
            color={metrics.tasks.completion_rate >= 75 ? "border-green-500" : metrics.tasks.completion_rate >= 50 ? "border-yellow-500" : "border-red-500"} />
          <MetricCard emoji="🎯" label="Avg Confidence" value={`${Math.round(metrics.quality.avg_confidence * 100)}%`}
            color={metrics.quality.avg_confidence >= 0.7 ? "border-green-500" : "border-yellow-500"} />
          <MetricCard emoji="💬" label="Messages" value={metrics.quality.messages} color="border-blue-500" />
        </div>

        {/* Findings breakdown */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 mb-6">
          <h3 className="font-medium text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <Target size={16} /> Atomic Research Breakdown
          </h3>
          <div className="grid grid-cols-4 gap-4 text-center">
            {[
              { emoji: "✨", label: "Nuggets", value: metrics.findings.nuggets, color: "text-purple-600" },
              { emoji: "📄", label: "Facts", value: metrics.findings.facts, color: "text-blue-600" },
              { emoji: "💡", label: "Insights", value: metrics.findings.insights, color: "text-yellow-600" },
              { emoji: "🎯", label: "Recommendations", value: metrics.findings.recommendations, color: "text-green-600" },
            ].map((item) => (
              <div key={item.label} className="bg-slate-50 dark:bg-slate-900 rounded-lg p-4">
                <span className="text-2xl">{item.emoji}</span>
                <p className={cn("text-3xl font-bold mt-1", item.color)}>{item.value}</p>
                <p className="text-xs text-slate-500 mt-1">{item.label}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Phase coverage */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 mb-6">
          <h3 className="font-medium text-slate-900 dark:text-white mb-4">
            💎 Double Diamond Coverage
          </h3>
          <div className="space-y-4">
            {Object.entries(metrics.by_phase).map(([phase, data]) => (
              <div key={phase}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-slate-700 dark:text-slate-300 capitalize font-medium">
                    💎 {phase}
                  </span>
                  <span className="text-xs text-slate-500">{data.total} findings</span>
                </div>
                <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-3">
                  <div
                    className="bg-reclaw-500 h-3 rounded-full transition-all duration-500"
                    style={{ width: `${(data.total / maxPhaseTotal) * 100}%` }}
                  />
                </div>
                <div className="flex gap-4 mt-1 text-[10px] text-slate-400">
                  <span>✨ {data.nuggets}</span>
                  <span>📄 {data.facts}</span>
                  <span>💡 {data.insights}</span>
                  <span>🎯 {data.recommendations}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Tasks overview */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
          <h3 className="font-medium text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <CheckCircle size={16} /> Task Progress
          </h3>
          <div className="flex items-center gap-6">
            {/* Circular progress */}
            <div className="relative w-24 h-24">
              <svg className="w-24 h-24 -rotate-90" viewBox="0 0 36 36">
                <path
                  className="text-slate-200 dark:text-slate-700"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none" stroke="currentColor" strokeWidth="3"
                />
                <path
                  className="text-reclaw-500"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none" stroke="currentColor" strokeWidth="3"
                  strokeDasharray={`${metrics.tasks.completion_rate}, 100`}
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-lg font-bold text-slate-900 dark:text-white">
                  {Math.round(metrics.tasks.completion_rate)}%
                </span>
              </div>
            </div>
            <div className="space-y-2 text-sm">
              <p className="text-slate-600 dark:text-slate-400">
                <span className="font-semibold text-slate-900 dark:text-white">{metrics.tasks.done}</span> completed
              </p>
              <p className="text-slate-600 dark:text-slate-400">
                <span className="font-semibold text-blue-600">{metrics.tasks.in_progress}</span> in progress
              </p>
              <p className="text-slate-600 dark:text-slate-400">
                <span className="font-semibold text-slate-500">{metrics.tasks.total - metrics.tasks.done - metrics.tasks.in_progress}</span> remaining
              </p>
            </div>
          </div>
        </div>

        {/* Empty state hint */}
        {metrics.findings.total === 0 && (
          <div className="mt-6 bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800 rounded-xl p-5">
            <div className="flex items-start gap-3">
              <AlertCircle size={20} className="text-amber-600 shrink-0 mt-0.5" />
              <div>
                <h4 className="font-medium text-amber-800 dark:text-amber-300">Get started</h4>
                <p className="text-sm text-amber-700 dark:text-amber-400 mt-1">
                  Upload research files and run skills to populate these metrics. Try typing in chat:
                  "analyze my interviews" or "run competitive analysis".
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function MetricCard({ emoji, label, value, sub, color }: { emoji: string; label: string; value: number | string; sub?: string; color: string }) {
  return (
    <div className={cn("rounded-xl border-l-4 bg-white dark:bg-slate-800 p-4", color)}>
      <span className="text-xl">{emoji}</span>
      <p className="text-3xl font-bold text-slate-900 dark:text-white mt-1">{value}</p>
      <p className="text-xs text-slate-500 mt-0.5">{label}</p>
      {sub && <p className="text-[10px] text-slate-400">{sub}</p>}
    </div>
  );
}
