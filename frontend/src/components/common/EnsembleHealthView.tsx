"use client";

import { useEffect, useState } from "react";
import { Activity, CheckCircle, AlertTriangle, XCircle, BarChart3, Brain } from "lucide-react";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface MethodStats {
  method: string;
  skill_name: string;
  agent_id: string;
  total_runs: number;
  success_rate: number;
  avg_consensus_score: number;
  last_used: string;
  recency_weight: number;
}

export default function EnsembleHealthView() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [methods, setMethods] = useState<MethodStats[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Get active project from store
    try {
      const { useProjectStore } = require("@/stores/projectStore");
      const pid = useProjectStore.getState().activeProjectId;
      setProjectId(pid);
    } catch {}
  }, []);

  useEffect(() => {
    if (!projectId) return;
    setLoading(true);
    // Fetch adaptive learning stats
    fetch(`${API_BASE}/api/compute/stats`)
      .then((r) => r.json())
      .then((data) => {
        // For now, show compute stats + method overview
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [projectId]);

  const VALIDATION_METHODS = [
    {
      id: "self_moa",
      name: "Self-MoA",
      description: "Same model, temperature variation (Li et al., 2025)",
      icon: Brain,
    },
    {
      id: "dual_run",
      name: "Dual Run",
      description: "Two models, same prompt comparison",
      icon: Activity,
    },
    {
      id: "adversarial_review",
      name: "Adversarial Review",
      description: "One model critiques another (Du et al., 2024)",
      icon: AlertTriangle,
    },
    {
      id: "full_ensemble",
      name: "Full Ensemble",
      description: "3+ models with Fleiss' Kappa (Wang et al., 2025)",
      icon: BarChart3,
    },
    {
      id: "debate_rounds",
      name: "Debate Rounds",
      description: "Iterative refinement between models (Du et al., 2024)",
      icon: Activity,
    },
  ];

  const confidenceColor = (score: number) => {
    if (score >= 0.7) return "text-green-600 dark:text-green-400";
    if (score >= 0.5) return "text-yellow-600 dark:text-yellow-400";
    if (score >= 0.3) return "text-orange-600 dark:text-orange-400";
    return "text-red-600 dark:text-red-400";
  };

  const confidenceIcon = (score: number) => {
    if (score >= 0.7) return CheckCircle;
    if (score >= 0.5) return AlertTriangle;
    return XCircle;
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Ensemble Health</h2>
        <p className="text-sm text-slate-500 mt-1">
          Multi-model validation status and consensus metrics
        </p>
      </div>

      {/* Confidence Thresholds Reference */}
      <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
          Confidence Thresholds by Finding Type
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { type: "Nuggets", threshold: 0.70, color: "bg-purple-100 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300" },
            { type: "Facts", threshold: 0.65, color: "bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300" },
            { type: "Insights", threshold: 0.55, color: "bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300" },
            { type: "Recommendations", threshold: 0.50, color: "bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-300" },
          ].map((item) => (
            <div key={item.type} className={cn("rounded-lg p-3 text-center", item.color)}>
              <div className="text-sm font-medium">{item.type}</div>
              <div className="text-lg font-bold">{"\u03BA"} {"\u2265"} {item.threshold}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Validation Methods */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
          Validation Methods
        </h3>
        {VALIDATION_METHODS.map((method) => {
          const stat = methods.find((m) => m.method === method.id);
          const Icon = method.icon;
          const score = stat?.avg_consensus_score || 0;
          const StatusIcon = confidenceIcon(score);

          return (
            <div
              key={method.id}
              className="flex items-center gap-4 p-4 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700"
            >
              <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
                <Icon size={20} className="text-slate-600 dark:text-slate-400" />
              </div>
              <div className="flex-1">
                <div className="font-medium text-slate-900 dark:text-white">{method.name}</div>
                <div className="text-xs text-slate-500">{method.description}</div>
              </div>
              <div className="text-right">
                {stat ? (
                  <>
                    <div className={cn("text-lg font-bold", confidenceColor(score))}>
                      {(score * 100).toFixed(0)}%
                    </div>
                    <div className="text-xs text-slate-400">
                      {stat.total_runs} runs | {(stat.success_rate * 100).toFixed(0)}% success
                    </div>
                  </>
                ) : (
                  <div className="text-sm text-slate-400">No data yet</div>
                )}
              </div>
              <StatusIcon
                size={20}
                className={stat ? confidenceColor(score) : "text-slate-300 dark:text-slate-600"}
              />
            </div>
          );
        })}
      </div>

      {/* Adaptive Learning Info */}
      <div className="bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-blue-800 dark:text-blue-300 mb-1">
          Adaptive Method Learning
        </h3>
        <p className="text-xs text-blue-600 dark:text-blue-400">
          ReClaw automatically learns which validation method works best for each project,
          skill, and agent combination. Methods are scored with recency-weighted performance
          metrics (exponential decay, 30-day half-life). The system improves over time.
        </p>
      </div>
    </div>
  );
}
