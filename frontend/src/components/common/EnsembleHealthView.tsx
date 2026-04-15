"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  CheckCircle,
  AlertTriangle,
  XCircle,
  BarChart3,
  Brain,
  ChevronDown,
  ChevronRight,
  HelpCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { validation } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface MethodStatRow {
  method: string;
  skill_name: string;
  agent_id: string;
  total_runs: number;
  success_count: number;
  fail_count: number;
  avg_consensus_score: number;
  success_rate: number;
  last_used: string | null;
  weight: number;
}

interface RecentValidation {
  task_id: string;
  task_title: string;
  skill_name: string;
  validation_method: string;
  consensus_score: number | null;
  status: string;
  updated_at: string | null;
}

interface ValidationData {
  project_id: string;
  methods: { id: string; name: string; description: string }[];
  method_stats: MethodStatRow[];
  recent_validations: RecentValidation[];
  confidence_thresholds: Record<string, number>;
}

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

// --- Expandable section component ---
function ExpandableInfo({
  children,
  label = "Learn more",
}: {
  children: React.ReactNode;
  label?: string;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-2">
      <button
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
      >
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <span>{label}</span>
      </button>
      <div
        className={cn(
          "overflow-hidden transition-all duration-200 ease-in-out",
          open ? "max-h-96 opacity-100 mt-2" : "max-h-0 opacity-0"
        )}
      >
        {children}
      </div>
    </div>
  );
}

// --- Tooltip-style inline help ---
function MetricLabel({ label, tooltip }: { label: string; tooltip: string }) {
  const [show, setShow] = useState(false);

  return (
    <span className="relative inline-flex items-center gap-1">
      <span>{label}</span>
      <button
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        onFocus={() => setShow(true)}
        onBlur={() => setShow(false)}
        className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
        aria-label={`Info: ${label}`}
      >
        <HelpCircle size={12} />
      </button>
      {show && (
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-2.5 py-1.5 text-xs text-white bg-slate-800 dark:bg-slate-700 rounded-md shadow-lg whitespace-nowrap z-50 pointer-events-none">
          {tooltip}
          <span className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-800 dark:border-t-slate-700" />
        </span>
      )}
    </span>
  );
}

export default function EnsembleHealthView() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [methods, setMethods] = useState<MethodStat[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedMethod, setExpandedMethod] = useState<string | null>(null);
  const [thresholds, setThresholds] = useState<Record<string, number>>({ nugget: 0.70, fact: 0.65, insight: 0.55, recommendation: 0.50 });
  const [recentValidations, setRecentValidations] = useState<RecentValidation[]>([]);

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
    validation.metrics(projectId)
      .then((data: ValidationData) => {
        const stats: MethodStat[] = data.method_stats.map((s) => ({
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
        setThresholds(data.confidence_thresholds);
        setRecentValidations(data.recent_validations);
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  }, [projectId]);

  const VALIDATION_METHODS = [
    {
      id: "self_moa",
      name: "Self-MoA",
      description: "Same model, temperature variation (Li et al., 2025)",
      detail:
        "Runs the same model 3 times at different temperatures (0.3, 0.7, 1.0) and aggregates results. Good for single-model setups.",
      icon: Brain,
    },
    {
      id: "dual_run",
      name: "Dual Run",
      description: "Two models, same prompt comparison",
      detail:
        "Sends the same prompt to 2 different models and compares outputs. Catches model-specific biases.",
      icon: Activity,
    },
    {
      id: "adversarial_review",
      name: "Adversarial Review",
      description: "One model critiques another (Du et al., 2024)",
      detail:
        "First model generates, second model critiques and identifies flaws. Based on multi-agent debate research.",
      icon: AlertTriangle,
    },
    {
      id: "full_ensemble",
      name: "Full Ensemble",
      description: "3+ models with Fleiss' Kappa (Wang et al., 2025)",
      detail:
        "3+ models all process the same task. Uses Fleiss' Kappa to measure agreement across all responses.",
      icon: BarChart3,
    },
    {
      id: "debate_rounds",
      name: "Debate Rounds",
      description: "Iterative refinement between models (Du et al., 2024)",
      detail:
        "Models take turns arguing and refining positions over 2+ rounds until convergence.",
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

  const toggleMethod = (id: string) => {
    setExpandedMethod((prev) => (prev === id ? null : id));
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-5xl mx-auto space-y-6">
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
            { type: "Nuggets", threshold: thresholds.nugget || 0.70, color: "bg-purple-100 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300" },
            { type: "Facts", threshold: thresholds.fact || 0.65, color: "bg-blue-100 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300" },
            { type: "Insights", threshold: thresholds.insight || 0.55, color: "bg-amber-100 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300" },
            { type: "Recommendations", threshold: thresholds.recommendation || 0.50, color: "bg-green-100 dark:bg-green-900/20 text-green-700 dark:text-green-300" },
          ].map((item) => (
            <div key={item.type} className={cn("rounded-lg p-3 text-center", item.color)}>
              <div className="text-sm font-medium">{item.type}</div>
              <div className="text-lg font-bold">{"\u03BA"} {"\u2265"} {item.threshold}</div>
            </div>
          ))}
        </div>

        {/* Fleiss' Kappa explanation */}
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-3">
          Fleiss&apos; Kappa ({"\u03BA"}) measures inter-rater agreement between multiple LLM validators.
        </p>
        <ExpandableInfo label="Why different thresholds?">
          <div className="text-xs text-slate-500 dark:text-slate-400 space-y-1.5 pl-5">
            <p>
              <strong className="text-slate-600 dark:text-slate-300">Nuggets (0.70)</strong> &mdash;
              Raw evidence extracted from sources. Requires the strongest agreement because errors here
              propagate to all downstream findings.
            </p>
            <p>
              <strong className="text-slate-600 dark:text-slate-300">Facts (0.65)</strong> &mdash;
              Verified factual claims. High threshold since factual accuracy is critical.
            </p>
            <p>
              <strong className="text-slate-600 dark:text-slate-300">Insights (0.55)</strong> &mdash;
              Analytical conclusions drawn from facts. Some interpretive latitude is expected.
            </p>
            <p>
              <strong className="text-slate-600 dark:text-slate-300">Recommendations (0.50)</strong> &mdash;
              Actionable suggestions. More subjective by nature, so moderate agreement is acceptable.
            </p>
          </div>
        </ExpandableInfo>
      </div>

      {/* Color Legend */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 dark:text-slate-400 px-1">
        <span className="text-slate-600 dark:text-slate-300 font-medium">Score legend:</span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-green-500" />
          <span>{"\u2265"}70% Strong agreement</span>
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-yellow-500" />
          <span>{"\u2265"}50% Moderate</span>
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-orange-500" />
          <span>{"\u2265"}30% Weak</span>
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
          <span>&lt;30% Poor</span>
        </span>
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
          const isExpanded = expandedMethod === method.id;

          return (
            <div
              key={method.id}
              className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700"
            >
              <div className="flex items-center gap-4 p-4">
                <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
                  <Icon size={20} className="text-slate-600 dark:text-slate-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-slate-900 dark:text-white">{method.name}</div>
                  <div className="text-xs text-slate-500">{method.description}</div>
                </div>
                <div className="text-right shrink-0">
                  {stat ? (
                    <>
                      <div className={cn("text-lg font-bold", confidenceColor(score))}>
                        <MetricLabel
                          label={`${(score * 100).toFixed(0)}%`}
                          tooltip="Agreement level across validators (higher = more agreement)"
                        />
                      </div>
                      <div className="text-xs text-slate-400 flex items-center justify-end gap-2">
                        <MetricLabel
                          label={`${stat.total_runs} runs`}
                          tooltip="Number of validation runs completed"
                        />
                        <span>|</span>
                        <MetricLabel
                          label={`${(stat.success_rate * 100).toFixed(0)}% success`}
                          tooltip="% of runs where consensus exceeded the threshold"
                        />
                      </div>
                    </>
                  ) : (
                    <div className="text-sm text-slate-400">No data yet</div>
                  )}
                </div>
                <StatusIcon
                  size={20}
                  className={cn(
                    "shrink-0",
                    stat ? confidenceColor(score) : "text-slate-300 dark:text-slate-600"
                  )}
                />
                <button
                  onClick={() => toggleMethod(method.id)}
                  className="shrink-0 p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
                  aria-label={`${isExpanded ? "Collapse" : "Expand"} details for ${method.name}`}
                >
                  {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </button>
              </div>

              {/* Expandable detail panel */}
              <div
                className={cn(
                  "overflow-hidden transition-all duration-200 ease-in-out",
                  isExpanded ? "max-h-40 opacity-100" : "max-h-0 opacity-0"
                )}
              >
                <div className="px-4 pb-4 pt-0 ml-14 border-t border-slate-100 dark:border-slate-700/50">
                  <p className="text-xs text-slate-500 dark:text-slate-400 pt-3 leading-relaxed">
                    {method.detail}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Recent Validations */}
      {recentValidations.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">
            Recent Validations
          </h3>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {recentValidations.slice(0, 10).map((v) => {
              const score = v.consensus_score || 0;
              return (
                <div key={v.task_id} className="flex items-center gap-3 text-xs">
                  <span className={cn("font-mono px-1.5 py-0.5 rounded", score >= 0.7 ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300" : score >= 0.5 ? "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300" : score >= 0.3 ? "bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300" : "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300")}>
                    {score > 0 ? `${Math.round(score * 100)}%` : "—"}
                  </span>
                  <span className="flex-1 truncate text-slate-700 dark:text-slate-300">{v.task_title || v.task_id.slice(0, 8)}</span>
                  <span className="text-slate-400 dark:text-slate-500 shrink-0">{v.validation_method?.replace("_", " ")}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Adaptive Learning Info */}
      <div className="bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-blue-800 dark:text-blue-300 mb-1">
          Adaptive Method Learning
        </h3>
        <p className="text-xs text-blue-600 dark:text-blue-400">
          Istara automatically learns which validation method works best for each project,
          skill, and agent combination. Methods are scored with recency-weighted performance
          metrics (exponential decay, 30-day half-life). The system improves over time.
        </p>
      </div>
    </div>
  );
}
