"use client";

import { useEffect, useState } from "react";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  BarChart3,
  Target,
  Users,
  Clock,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { useProjectStore } from "@/stores/projectStore";
import { findings as findingsApi } from "@/lib/api";
import { cn } from "@/lib/utils";

interface MetricCard {
  name: string;
  value: number | string;
  unit: string;
  trend: "up" | "down" | "flat";
  trendValue: string;
  benchmark: number | string;
  benchmarkLabel: string;
  status: "good" | "warning" | "bad";
}

export default function MetricsView() {
  const { activeProjectId } = useProjectStore();
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // Placeholder metrics — in production these would come from skill outputs
  const [metrics] = useState<MetricCard[]>([
    {
      name: "SUS Score",
      value: "—",
      unit: "/100",
      trend: "flat",
      trendValue: "No data",
      benchmark: 68,
      benchmarkLabel: "Industry avg",
      status: "warning",
    },
    {
      name: "Task Completion",
      value: "—",
      unit: "%",
      trend: "flat",
      trendValue: "No data",
      benchmark: "78%",
      benchmarkLabel: "Industry avg",
      status: "warning",
    },
    {
      name: "NPS",
      value: "—",
      unit: "",
      trend: "flat",
      trendValue: "No data",
      benchmark: "+20",
      benchmarkLabel: "Good threshold",
      status: "warning",
    },
    {
      name: "Avg Time on Task",
      value: "—",
      unit: "min",
      trend: "flat",
      trendValue: "No data",
      benchmark: "3.5",
      benchmarkLabel: "Industry avg",
      status: "warning",
    },
  ]);

  useEffect(() => {
    if (!activeProjectId) return;
    setLoading(true);
    findingsApi
      .summary(activeProjectId)
      .then(setSummary)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [activeProjectId]);

  if (!activeProjectId) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        <p>Select a project to view metrics.</p>
      </div>
    );
  }

  const TrendIcon = ({ trend }: { trend: string }) => {
    switch (trend) {
      case "up": return <TrendingUp size={14} className="text-green-500" />;
      case "down": return <TrendingDown size={14} className="text-red-500" />;
      default: return <Minus size={14} className="text-slate-400" />;
    }
  };

  const statusColors = {
    good: "border-green-500 bg-green-50 dark:bg-green-900/10",
    warning: "border-slate-300 bg-slate-50 dark:bg-slate-800/50",
    bad: "border-red-500 bg-red-50 dark:bg-red-900/10",
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
              <BarChart3 size={20} />
              📊 Metrics & Benchmarks
            </h2>
            <p className="text-sm text-slate-500 mt-1">
              Quantitative research metrics, benchmarks, and trends
            </p>
          </div>
        </div>

        {/* Metric cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {metrics.map((metric) => (
            <div
              key={metric.name}
              className={cn(
                "rounded-xl border-l-4 p-4",
                statusColors[metric.status]
              )}
            >
              <p className="text-xs text-slate-500 mb-1">{metric.name}</p>
              <div className="flex items-baseline gap-1">
                <span className="text-3xl font-bold text-slate-900 dark:text-white">
                  {metric.value}
                </span>
                <span className="text-sm text-slate-400">{metric.unit}</span>
              </div>
              <div className="flex items-center gap-1 mt-2">
                <TrendIcon trend={metric.trend} />
                <span className="text-xs text-slate-500">{metric.trendValue}</span>
              </div>
              <div className="mt-2 pt-2 border-t border-slate-200 dark:border-slate-700">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-slate-400">{metric.benchmarkLabel}</span>
                  <span className="text-xs font-medium text-slate-600 dark:text-slate-300">
                    {metric.benchmark}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Research coverage */}
        {summary && (
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 mb-6">
            <h3 className="font-medium text-slate-900 dark:text-white mb-4 flex items-center gap-2">
              <Target size={16} /> Research Coverage by Phase
            </h3>
            <div className="space-y-3">
              {Object.entries(summary.by_phase).map(([phase, data]: [string, any]) => {
                const total = data.nuggets + data.facts + data.insights + data.recommendations;
                const maxFindings = Math.max(
                  ...Object.values(summary.by_phase).map(
                    (d: any) => d.nuggets + d.facts + d.insights + d.recommendations
                  )
                );
                const pct = maxFindings > 0 ? (total / maxFindings) * 100 : 0;

                return (
                  <div key={phase}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm text-slate-700 dark:text-slate-300 capitalize">
                        💎 {phase}
                      </span>
                      <span className="text-xs text-slate-500">{total} findings</span>
                    </div>
                    <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-2">
                      <div
                        className="bg-reclaw-500 h-2 rounded-full transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <div className="flex gap-4 mt-1 text-[10px] text-slate-400">
                      <span>✨ {data.nuggets} nuggets</span>
                      <span>📄 {data.facts} facts</span>
                      <span>💡 {data.insights} insights</span>
                      <span>🎯 {data.recommendations} recs</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Empty state / instructions */}
        <div className="bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800 rounded-xl p-5">
          <div className="flex items-start gap-3">
            <AlertCircle size={20} className="text-amber-600 shrink-0 mt-0.5" />
            <div>
              <h4 className="font-medium text-amber-800 dark:text-amber-300 mb-1">
                Populate metrics by running quantitative skills
              </h4>
              <p className="text-sm text-amber-700 dark:text-amber-400">
                Metrics appear here after running quantitative research skills. Try these in chat:
              </p>
              <ul className="mt-2 space-y-1 text-sm text-amber-600 dark:text-amber-400">
                <li>• "Calculate SUS scores" — upload SUS survey responses</li>
                <li>• "Analyze NPS data" — upload NPS survey data</li>
                <li>• "Run task analysis" — upload usability test data</li>
                <li>• "Analyze A/B test results" — upload experiment data</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
