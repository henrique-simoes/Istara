"use client";

import { useEffect, useState } from "react";
import {
  Sparkles,
  AlertTriangle,
  Eye,
  GitBranch,
  RotateCcw,
  Check,
  X,
  Activity,
  RefreshCw,
  Clock,
  Shield,
} from "lucide-react";
import { metaHyperagent as metaApi } from "@/lib/api";
import type { MetaProposal, MetaVariant, MetaHyperagentStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

function timeAgo(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

function formatValue(val: any): string {
  if (val === null || val === undefined) return "null";
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}

const SYSTEM_COLORS: Record<string, string> = {
  routing: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  evolution: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  skill_selection: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  quality_eval: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  agent_capabilities: "bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400",
};

export default function MetaHyperagentView() {
  const [status, setStatus] = useState<MetaHyperagentStatus | null>(null);
  const [proposals, setProposals] = useState<MetaProposal[]>([]);
  const [variants, setVariants] = useState<MetaVariant[]>([]);
  const [observations, setObservations] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [toggling, setToggling] = useState(false);
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({});

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [st, props, vars, obs] = await Promise.all([
        metaApi.status().catch(() => null),
        metaApi.proposals().catch(() => []),
        metaApi.variants().catch(() => []),
        metaApi.observations().catch(() => null),
      ]);
      if (st) setStatus(st);
      const proposalArr = Array.isArray(props) ? props : (props as any)?.proposals || [];
      const variantArr = Array.isArray(vars) ? vars : (vars as any)?.variants || [];
      setProposals(proposalArr);
      setVariants(variantArr);
      setObservations(obs);
    } catch (e) {
      console.error("Failed to load meta-hyperagent data:", e);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const handleToggle = async () => {
    if (!status) return;
    setToggling(true);
    try {
      await metaApi.toggle(!status.enabled);
      const st = await metaApi.status();
      setStatus(st);
    } catch (e) {
      console.error("Failed to toggle:", e);
    }
    setToggling(false);
  };

  const handleApprove = async (id: string) => {
    setActionLoading((prev) => ({ ...prev, [`approve-${id}`]: true }));
    try {
      await metaApi.approveProposal(id);
      await fetchAll();
    } catch (e) {
      console.error("Failed to approve:", e);
    }
    setActionLoading((prev) => ({ ...prev, [`approve-${id}`]: false }));
  };

  const handleReject = async (id: string) => {
    setActionLoading((prev) => ({ ...prev, [`reject-${id}`]: true }));
    try {
      await metaApi.rejectProposal(id);
      await fetchAll();
    } catch (e) {
      console.error("Failed to reject:", e);
    }
    setActionLoading((prev) => ({ ...prev, [`reject-${id}`]: false }));
  };

  const handleRevert = async (id: string) => {
    setActionLoading((prev) => ({ ...prev, [`revert-${id}`]: true }));
    try {
      await metaApi.revertVariant(id);
      await fetchAll();
    } catch (e) {
      console.error("Failed to revert:", e);
    }
    setActionLoading((prev) => ({ ...prev, [`revert-${id}`]: false }));
  };

  const handleConfirm = async (id: string) => {
    setActionLoading((prev) => ({ ...prev, [`confirm-${id}`]: true }));
    try {
      await metaApi.confirmVariant(id);
      await fetchAll();
    } catch (e) {
      console.error("Failed to confirm:", e);
    }
    setActionLoading((prev) => ({ ...prev, [`confirm-${id}`]: false }));
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-400">
        <RefreshCw size={20} className="animate-spin mr-2" />
        Loading meta-hyperagent data...
      </div>
    );
  }

  const isEnabled = status?.enabled ?? false;
  const activeVariants = variants.filter((v) => v.status === "active");
  const pendingProposals = proposals.filter((p) => p.status === "pending");

  // Disabled empty state
  if (!isEnabled && activeVariants.length === 0 && pendingProposals.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <Sparkles size={24} className="text-reclaw-600 dark:text-reclaw-400" />
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
            Meta-Hyperagent
          </h2>
        </div>

        {/* Experimental Warning */}
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
          <div className="flex gap-3">
            <AlertTriangle size={20} className="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
            <div className="text-sm text-amber-800 dark:text-amber-200">
              <strong>Experimental Feature</strong> — The Meta-Hyperagent can modify system behavior
              parameters (routing rules, evolution thresholds, skill selection). All changes require
              your approval. Monitor agent behavior carefully and ensure backups are current before
              enabling.
            </div>
          </div>
        </div>

        {/* Centered disabled state */}
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <Sparkles size={48} className="text-slate-300 dark:text-slate-600 mb-4" />
          <h3 className="text-lg font-medium text-slate-600 dark:text-slate-400 mb-2">
            Meta-Hyperagent is disabled
          </h3>
          <p className="text-sm text-slate-400 dark:text-slate-500 mb-6 max-w-md">
            When enabled, the meta-hyperagent observes system behavior and proposes parameter
            optimizations across routing, evolution, skill selection, quality evaluation, and agent
            capabilities.
          </p>
          <button
            onClick={handleToggle}
            disabled={toggling}
            className={cn(
              "flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-colors",
              "bg-reclaw-600 text-white hover:bg-reclaw-700 disabled:opacity-50"
            )}
          >
            {toggling ? <RefreshCw size={16} className="animate-spin" /> : <Sparkles size={16} />}
            Enable Meta-Hyperagent
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Sparkles size={24} className="text-reclaw-600 dark:text-reclaw-400" />
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
          Meta-Hyperagent
        </h2>
      </div>

      {/* Experimental Warning Banner */}
      <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
        <div className="flex gap-3">
          <AlertTriangle size={20} className="text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
          <div className="text-sm text-amber-800 dark:text-amber-200">
            <strong>Experimental Feature</strong> — The Meta-Hyperagent can modify system behavior
            parameters (routing rules, evolution thresholds, skill selection). All changes require
            your approval. Monitor agent behavior carefully and ensure backups are current before
            enabling.
          </div>
        </div>
      </div>

      {/* Toggle Card */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium text-slate-900 dark:text-white">
              Meta-Hyperagent Status
            </div>
            <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Observation interval: {status?.observation_interval_hours || 24}h
              {status?.experimental && (
                <span className="ml-2 px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 text-[10px] font-medium">
                  EXPERIMENTAL
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className={cn("text-xs font-medium", isEnabled ? "text-green-600" : "text-slate-400")}>
              {isEnabled ? "Enabled" : "Disabled"}
            </span>
            <button
              onClick={handleToggle}
              disabled={toggling}
              className={cn(
                "relative w-10 h-5 rounded-full transition-colors",
                isEnabled ? "bg-green-500" : "bg-slate-300 dark:bg-slate-600"
              )}
            >
              <span
                className={cn(
                  "absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform",
                  isEnabled && "translate-x-5"
                )}
              />
            </button>
          </div>
        </div>
      </div>

      {/* Active Variants Section */}
      {activeVariants.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-slate-900 dark:text-white flex items-center gap-2">
            <GitBranch size={16} />
            Active Variants ({activeVariants.length})
          </h3>
          {activeVariants.map((variant) => (
            <div
              key={variant.id}
              className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span
                      className={cn(
                        "inline-flex px-2 py-0.5 rounded-full text-xs font-medium",
                        SYSTEM_COLORS[variant.target_system] || "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300"
                      )}
                    >
                      {variant.target_system}
                    </span>
                    <code className="text-xs text-slate-500 dark:text-slate-400 font-mono">
                      {variant.parameter_path}
                    </code>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-red-500 line-through">{formatValue(variant.old_value)}</span>
                    <span className="text-slate-400">→</span>
                    <span className="text-green-600 font-medium">{formatValue(variant.new_value)}</span>
                  </div>
                  <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
                    <span className="flex items-center gap-1">
                      <Clock size={12} />
                      Applied {timeAgo(variant.applied_at)}
                    </span>
                    <span className="flex items-center gap-1">
                      <Eye size={12} />
                      {variant.observation_window_hours}h observation window
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => handleRevert(variant.id)}
                    disabled={!!actionLoading[`revert-${variant.id}`]}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-orange-100 text-orange-700 hover:bg-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:hover:bg-orange-900/50 transition-colors disabled:opacity-50"
                  >
                    <RotateCcw size={12} />
                    Revert
                  </button>
                  <button
                    onClick={() => handleConfirm(variant.id)}
                    disabled={!!actionLoading[`confirm-${variant.id}`]}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400 dark:hover:bg-green-900/50 transition-colors disabled:opacity-50"
                  >
                    <Check size={12} />
                    Confirm
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pending Proposals Section */}
      {pendingProposals.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-slate-900 dark:text-white flex items-center gap-2">
            <Shield size={16} />
            Pending Proposals ({pendingProposals.length})
          </h3>
          {pendingProposals.map((proposal) => (
            <div
              key={proposal.id}
              className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span
                      className={cn(
                        "inline-flex px-2 py-0.5 rounded-full text-xs font-medium",
                        SYSTEM_COLORS[proposal.target_system] || "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300"
                      )}
                    >
                      {proposal.target_system}
                    </span>
                    <code className="text-xs text-slate-500 dark:text-slate-400 font-mono">
                      {proposal.parameter_path}
                    </code>
                  </div>
                  <div className="flex items-center gap-2 text-sm mb-2">
                    <span className="text-slate-500">{formatValue(proposal.current_value)}</span>
                    <span className="text-slate-400">→</span>
                    <span className="text-reclaw-600 dark:text-reclaw-400 font-medium">
                      {formatValue(proposal.proposed_value)}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-400 mb-2">
                    {proposal.reason}
                  </p>
                  {proposal.evidence && proposal.evidence.length > 0 && (
                    <div className="mb-2">
                      <div className="text-[10px] text-slate-400 uppercase font-medium mb-1">Evidence</div>
                      <ul className="text-xs text-slate-500 dark:text-slate-400 space-y-0.5">
                        {proposal.evidence.slice(0, 3).map((ev, i) => (
                          <li key={i} className="truncate">
                            {typeof ev === "object" ? JSON.stringify(ev) : String(ev)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {/* Confidence bar */}
                  <div className="flex items-center gap-2">
                    <div className="text-[10px] text-slate-400">Confidence</div>
                    <div className="flex-1 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-full max-w-[120px]">
                      <div
                        className={cn(
                          "h-full rounded-full transition-all",
                          proposal.confidence >= 0.8
                            ? "bg-green-500"
                            : proposal.confidence >= 0.5
                            ? "bg-yellow-500"
                            : "bg-red-500"
                        )}
                        style={{ width: `${Math.round(proposal.confidence * 100)}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-slate-400">
                      {Math.round(proposal.confidence * 100)}%
                    </span>
                  </div>
                  {proposal.expected_impact && (
                    <div className="text-[10px] text-slate-400 mt-1">
                      Expected impact: {proposal.expected_impact}
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => handleApprove(proposal.id)}
                    disabled={!!actionLoading[`approve-${proposal.id}`]}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400 dark:hover:bg-green-900/50 transition-colors disabled:opacity-50"
                  >
                    <Check size={12} />
                    Approve
                  </button>
                  <button
                    onClick={() => handleReject(proposal.id)}
                    disabled={!!actionLoading[`reject-${proposal.id}`]}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50 transition-colors disabled:opacity-50"
                  >
                    <X size={12} />
                    Reject
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Observations Section */}
      {observations && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-slate-900 dark:text-white flex items-center gap-2">
            <Activity size={16} />
            Observations
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "Routing Accuracy", key: "routing_accuracy", suffix: "%" },
              { label: "Promotion Rate", key: "promotion_rate", suffix: "%" },
              { label: "Skill Match Rate", key: "skill_match_rate", suffix: "%" },
              { label: "Verification Pass", key: "verification_pass_rate", suffix: "%" },
            ].map((metric) => {
              const value = observations[metric.key];
              return (
                <div
                  key={metric.key}
                  className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 text-center"
                >
                  <div className="text-2xl font-bold text-slate-900 dark:text-white">
                    {value !== undefined && value !== null
                      ? `${typeof value === "number" ? Math.round(value * 100) : value}${metric.suffix}`
                      : "--"}
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    {metric.label}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Audit Log Section */}
      {observations?.audit_log && Array.isArray(observations.audit_log) && observations.audit_log.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-slate-900 dark:text-white flex items-center gap-2">
            <Eye size={16} />
            Audit Log
          </h3>
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 max-h-64 overflow-y-auto">
            <div className="divide-y divide-slate-100 dark:divide-slate-700/50">
              {observations.audit_log.map((entry: any, i: number) => (
                <div key={i} className="px-4 py-2.5 text-xs flex items-center gap-3">
                  <span className="text-slate-400 shrink-0 font-mono">
                    {entry.timestamp ? timeAgo(entry.timestamp) : "--"}
                  </span>
                  <span className="text-slate-700 dark:text-slate-300 truncate">
                    {entry.action || entry.message || JSON.stringify(entry)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
