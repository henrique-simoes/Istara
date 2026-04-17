"use client";

import { useEffect, useState } from "react";
import {
  CheckCircle,
  AlertTriangle,
  Zap,
  Clock,
  Gauge,
  TrendingUp,
  Brain,
  Shield,
  Search,
  ChevronDown,
  ChevronRight,
  Activity,
  BarChart3,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { validation, telemetry } from "@/lib/api";

interface MethodStat {
  method: string;
  skill_name: string;
  agent_id: string;
  total_runs: number;
  success_rate: number;
  avg_consensus_score: number;
  last_used: string;
  recency_weight: number;
}

export default function QualityView() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const [toolStats, setToolStats] = useState<any[]>([]);
  const [methods, setMethods] = useState<MethodStat[]>([]);
  const [loading, setLoading] = useState(false);
  const [thresholds, setThresholds] = useState<Record<string, number>>({ nugget: 0.70, fact: 0.65, insight: 0.55, recommendation: 0.50 });

  useEffect(() => {
    try {
      const { useProjectStore } = require("@/stores/projectStore");
      const pid = useProjectStore.getState().activeProjectId;
      setProjectId(pid);
    } catch {}
  }, []);

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    
    // Fetch both model intelligence and ensemble metrics
    Promise.all([
      validation.modelIntelligence(projectId),
      validation.metrics(projectId)
    ]).then(([intel, metrics]) => {
      setLeaderboard(intel.leaderboard);
      setToolStats(intel.tool_success_rates);
      
      const stats: MethodStat[] = metrics.method_stats.map((s: any) => ({
        method: s.method,
        skill_name: s.skill_name,
        agent_id: s.agent_id,
        total_runs: s.total_runs,
        success_rate: s.success_rate,
        avg_consensus_score: s.avg_consensus_score,
        last_used: s.last_used || "",
        recency_weight: s.weight,
      }));
      setMethods(stats);
      setThresholds(metrics.confidence_thresholds);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [projectId]);

  const confidenceColor = (score: number) => {
    if (score >= 0.7) return "text-green-600 dark:text-green-400";
    if (score >= 0.5) return "text-yellow-600 dark:text-yellow-400";
    return "text-red-600 dark:text-red-400";
  };

  const VALIDATION_METHODS = [
    { id: "self_moa", name: "Self-MoA", icon: Brain, desc: "Same model, temp variation" },
    { id: "dual_run", name: "Dual Run", icon: Activity, desc: "Two model comparison" },
    { id: "adversarial_review", name: "Adversarial", icon: AlertTriangle, desc: "Model-on-model critique" },
    { id: "full_ensemble", name: "Full Ensemble", icon: BarChart3, desc: "3+ models (Fleiss' Kappa)" },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-5xl mx-auto space-y-6 text-slate-900 dark:text-slate-100">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Quality Dashboard</h2>
          <p className="text-sm text-slate-500 mt-1">
            Research rigor, model intelligence, and simulation benchmarks.
          </p>
        </div>
        <div className="flex items-center gap-2 bg-istara-50 dark:bg-istara-900/20 px-3 py-1.5 rounded-full border border-istara-100 dark:border-istara-800">
          <Shield size={16} className="text-istara-600" />
          <span className="text-xs font-semibold text-istara-700 dark:text-istara-300">Phase Beta Verified</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Main Quality Column */}
        <div className="md:col-span-2 space-y-6">
          {/* Methodology Rigor */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm">
            <div className="flex items-center gap-2 mb-6">
              <Brain size={18} className="text-slate-500" />
              <h3 className="font-semibold">Methodology Rigor</h3>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {VALIDATION_METHODS.map(m => {
                const stat = methods.find(s => s.method === m.id);
                const score = stat?.avg_consensus_score || 0;
                return (
                  <div key={m.id} className="p-4 rounded-lg border border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/30">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <m.icon size={14} className="text-slate-400" />
                        <span className="text-xs font-bold uppercase tracking-wider text-slate-500">{m.name}</span>
                      </div>
                      <span className={cn("text-sm font-bold", confidenceColor(score))}>
                        {score > 0 ? `${(score * 100).toFixed(0)}%` : "N/A"}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400 mb-2 truncate">{m.desc}</div>
                    <div className="h-1.5 w-full bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                      <div className="h-full bg-istara-500 rounded-full" style={{ width: `${score * 100}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Leaderboard */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp size={18} className="text-slate-500" />
              <h3 className="font-semibold">Model Performance Leaderboard</h3>
            </div>
            
            <div className="space-y-4">
              {leaderboard.length > 0 ? (
                leaderboard.slice(0, 5).map((entry, i) => (
                  <div key={i} className="flex items-center gap-4">
                    <div className="w-8 h-8 rounded bg-slate-100 dark:bg-slate-700 flex items-center justify-center text-xs font-bold text-slate-500">
                      {i + 1}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">{entry.model_name}</div>
                      <div className="text-xs text-slate-500">{entry.skill_name}</div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={cn("text-sm font-bold w-10 text-right", confidenceColor(entry.quality_ema))}>
                        {Math.round(entry.quality_ema * 100)}%
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <div className="py-8 text-center text-slate-400 text-sm">
                  Enable telemetry in Settings to track performance.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Sidebar Status Column */}
        <div className="space-y-6">
          <div className="bg-istara-50 dark:bg-istara-900/10 rounded-xl border border-istara-100 dark:border-istara-800 p-5">
            <h4 className="text-sm font-bold text-istara-800 dark:text-istara-300 flex items-center gap-2 mb-3">
              <Shield size={16} />
              Consensus Thresholds
            </h4>
            <div className="space-y-3">
              {[
                { label: "Nuggets", val: thresholds.nugget || "0.70", desc: "Raw extraction requires high kappa." },
                { label: "Facts", val: thresholds.fact || "0.65", desc: "Verified claims." },
                { label: "Insights", val: thresholds.insight || "0.55", desc: "Analytical conclusions." },
              ].map(row => (
                <div key={row.label}>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="font-semibold">{row.label}</span>
                    <span className="font-mono font-bold text-istara-600">{"\u03BA"} {row.val}</span>
                  </div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400">{row.desc}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-amber-50 dark:bg-amber-900/10 rounded-xl border border-amber-100 dark:border-amber-800 p-5">
            <h4 className="text-sm font-bold text-amber-800 dark:text-amber-300 flex items-center gap-2 mb-3">
              <Activity size={16} />
              Game Theory Status
            </h4>
            <p className="text-xs text-amber-700/80 dark:text-amber-400 leading-relaxed mb-4">
              Strategic simulation personas are active to stress-test your instruments.
            </p>
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-[10px] font-bold text-amber-600">
                <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                SATISFICER PROTECTION ACTIVE
              </div>
              <div className="flex items-center gap-2 text-[10px] font-bold text-amber-600">
                <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                ADVERSARIAL COHORTS READY
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
