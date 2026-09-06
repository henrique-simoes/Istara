"use client";

import { useState } from "react";
import {
  AlertTriangle,
  Archive,
  Brain,
  Check,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  ExternalLink,
  GitBranch,
  Layers,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  X,
  XCircle,
} from "lucide-react";
import type {
  ImprovementProposal,
  ProposalSandboxEvaluation,
} from "@/lib/improvementGovernanceTypes";
import { cn, formatDate } from "@/lib/utils";

interface ImprovementProposalDetailModalProps {
  proposal: ImprovementProposal | null;
  isOpen: boolean;
  onClose: () => void;
  onApprove?: (id: string) => Promise<void>;
  onApply?: (id: string) => Promise<void>;
  onSandbox?: (id: string) => Promise<void>;
  onReject?: (id: string) => Promise<void>;
  onRevert?: (id: string) => Promise<void>;
}

type ModalTab = "overview" | "changes" | "evidence" | "sandbox";

function badgeTone(value: string) {
  if (["applied", "active", "confirmed", "approved"].includes(value)) {
    return "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300";
  }
  if (["rejected", "reverted", "failed", "quarantined"].includes(value)) {
    return "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300";
  }
  if (["admin_required", "critical", "high"].includes(value)) {
    return "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300";
  }
  return "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300";
}

export default function ImprovementProposalDetailModal({
  proposal,
  isOpen,
  onClose,
  onApprove,
  onApply,
  onSandbox,
  onReject,
  onRevert,
}: ImprovementProposalDetailModalProps) {
  const [activeTab, setActiveTab] = useState<ModalTab>("overview");
  const [actionLoading, setActionLoading] = useState(false);

  if (!isOpen || !proposal) return null;

  const sandboxEvents = (proposal.evidence || []).filter(
    (item) => item?.event === "sandbox_evaluation"
  );
  const sandbox: ProposalSandboxEvaluation | null = sandboxEvents.length
    ? sandboxEvents[sandboxEvents.length - 1]
    : null;

  const canApprove = ["draft", "proposed"].includes(proposal.status);
  const canApply =
    proposal.status === "approved" ||
    (proposal.auto_apply_allowed &&
      !["applied", "rejected", "reverted", "quarantined"].includes(proposal.status));
  const canRevert = proposal.status === "applied";

  const handleAction = async (fn?: (id: string) => Promise<void>) => {
    if (!fn) return;
    setActionLoading(true);
    try {
      await fn(proposal.id);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-xs p-4 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-labelledby="proposal-modal-title"
    >
      <div className="relative w-full max-w-3xl rounded-2xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-2xl overflow-hidden my-8 max-h-[90vh] flex flex-col animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="p-5 border-b border-slate-200 dark:border-slate-700 flex items-start justify-between gap-4">
          <div className="min-w-0 space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={cn(
                  "rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wider",
                  badgeTone(proposal.status)
                )}
              >
                {proposal.status}
              </span>
              <span
                className={cn(
                  "rounded-full px-2.5 py-0.5 text-xs font-medium",
                  badgeTone(proposal.risk_level)
                )}
              >
                Risk: {proposal.risk_level || "standard"}
              </span>
              <span className="text-xs text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-700 px-2 py-0.5 rounded">
                Source: {proposal.source_system}
              </span>
            </div>
            <h3
              id="proposal-modal-title"
              className="text-lg font-bold text-slate-900 dark:text-white"
            >
              {proposal.title}
            </h3>
            <p className="text-xs text-slate-400">
              Proposal ID: <code className="font-mono">{proposal.id}</code>
              {proposal.created_at && ` • Created ${formatDate(proposal.created_at)}`}
              {proposal.created_by && ` by ${proposal.created_by}`}
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 hover:text-slate-600 transition-colors"
            aria-label="Close modal"
          >
            <X size={18} />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 dark:border-slate-700 px-5 bg-slate-50/50 dark:bg-slate-900/30 gap-4">
          {(
            [
              { id: "overview", label: "Overview & Rationale" },
              { id: "changes", label: "State Changes & Diff" },
              { id: "evidence", label: "Evidence & ReasoningBank" },
              { id: "sandbox", label: "Sandbox Evaluation" },
            ] as const
          ).map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={cn(
                "py-2.5 text-xs font-medium border-b-2 transition-colors",
                activeTab === t.id
                  ? "border-istara-600 text-istara-600 dark:text-istara-400 dark:border-istara-400"
                  : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
              )}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Body content */}
        <div className="p-6 overflow-y-auto space-y-4 flex-1">
          {activeTab === "overview" && (
            <div className="space-y-4">
              {/* Summary */}
              {proposal.summary && (
                <div>
                  <h4 className="text-xs font-semibold uppercase text-slate-400 tracking-wider mb-1">
                    Summary
                  </h4>
                  <p className="text-sm text-slate-800 dark:text-slate-200 bg-slate-50 dark:bg-slate-900/50 p-3 rounded-lg border border-slate-100 dark:border-slate-800">
                    {proposal.summary}
                  </p>
                </div>
              )}

              {/* What prompted it / Rationale */}
              <div>
                <h4 className="text-xs font-semibold uppercase text-slate-400 tracking-wider mb-1 flex items-center gap-1.5">
                  <Sparkles size={13} className="text-amber-500" />
                  What Prompted This Improvement & Rationale
                </h4>
                <div className="text-sm leading-relaxed text-slate-800 dark:text-slate-200 bg-amber-50/50 dark:bg-amber-950/20 p-3.5 rounded-lg border border-amber-200 dark:border-amber-900/50 whitespace-pre-wrap">
                  {proposal.rationale || "No specific rationale documented for this proposal."}
                </div>
              </div>

              {/* Grid: Surfaces & Governance Policy */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/40">
                  <h5 className="text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5 flex items-center gap-1.5">
                    <Layers size={13} />
                    Affected Surfaces
                  </h5>
                  <div className="flex flex-wrap gap-1.5">
                    {(proposal.affected_surfaces || []).length > 0 ? (
                      proposal.affected_surfaces.map((s) => (
                        <span
                          key={s}
                          className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 px-2 py-0.5 rounded text-xs font-mono text-slate-700 dark:text-slate-300"
                        >
                          {s}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-slate-400">General system</span>
                    )}
                  </div>
                </div>

                <div className="p-3.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/40">
                  <h5 className="text-xs font-semibold text-slate-600 dark:text-slate-400 mb-1.5 flex items-center gap-1.5">
                    <TrendingUp size={13} />
                    Confidence & Impact
                  </h5>
                  <div className="text-xs space-y-1 text-slate-600 dark:text-slate-300">
                    <div className="flex justify-between">
                      <span>Statistical Confidence:</span>
                      <span className="font-semibold">
                        {Math.round((proposal.confidence || 0) * 100)}%
                      </span>
                    </div>
                    {proposal.improvement_score != null && (
                      <div className="flex justify-between">
                        <span>Improvement Score:</span>
                        <span className="font-semibold text-emerald-600">
                          +{proposal.improvement_score.toFixed(3)}
                        </span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span>Policy:</span>
                      <span className="capitalize">{proposal.approval_policy || "standard_review"}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === "changes" && (
            <div className="space-y-4">
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Detailed inspectable snapshot of state changes before and after proposed improvement.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Before State */}
                <div>
                  <h4 className="text-xs font-semibold uppercase text-red-600 dark:text-red-400 tracking-wider mb-1.5">
                    Before State
                  </h4>
                  <pre className="text-xs font-mono bg-red-50/60 dark:bg-red-950/20 border border-red-200 dark:border-red-900/40 rounded-lg p-3 max-h-72 overflow-y-auto whitespace-pre-wrap text-slate-800 dark:text-slate-200">
                    {Object.keys(proposal.before_state || {}).length > 0
                      ? JSON.stringify(proposal.before_state, null, 2)
                      : "(No before state recorded)"}
                  </pre>
                </div>

                {/* Proposed Change */}
                <div>
                  <h4 className="text-xs font-semibold uppercase text-emerald-600 dark:text-emerald-400 tracking-wider mb-1.5">
                    Proposed Change
                  </h4>
                  <pre className="text-xs font-mono bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/40 rounded-lg p-3 max-h-72 overflow-y-auto whitespace-pre-wrap text-slate-800 dark:text-slate-200">
                    {Object.keys(proposal.proposed_change || {}).length > 0
                      ? JSON.stringify(proposal.proposed_change, null, 2)
                      : "(No change payload recorded)"}
                  </pre>
                </div>
              </div>

              {/* Rollback Plan */}
              {proposal.rollback_plan && Object.keys(proposal.rollback_plan).length > 0 && (
                <div>
                  <h4 className="text-xs font-semibold uppercase text-slate-500 tracking-wider mb-1.5 flex items-center gap-1.5">
                    <RotateCcw size={13} />
                    Automated Rollback Plan
                  </h4>
                  <pre className="text-xs font-mono bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg p-3 max-h-48 overflow-y-auto whitespace-pre-wrap text-slate-700 dark:text-slate-300">
                    {JSON.stringify(proposal.rollback_plan, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}

          {activeTab === "evidence" && (
            <div className="space-y-4">
              {/* ReasoningBank Links */}
              <div>
                <h4 className="text-xs font-semibold uppercase text-slate-500 tracking-wider mb-2 flex items-center gap-1.5">
                  <Brain size={14} className="text-purple-600" />
                  ReasoningBank Provenance & Linked Memories
                </h4>
                {(proposal.reasoning_memory_ids || []).length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {proposal.reasoning_memory_ids.map((id) => (
                      <span
                        key={id}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-purple-50 dark:bg-purple-950/30 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800 text-xs font-mono"
                      >
                        <Brain size={11} />
                        {id}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400">
                    No linked ReasoningBank memory IDs for this proposal.
                  </p>
                )}
              </div>

              {/* Evidence Log */}
              <div>
                <h4 className="text-xs font-semibold uppercase text-slate-500 tracking-wider mb-2">
                  Evidence Events ({proposal.evidence?.length || 0})
                </h4>
                {(proposal.evidence || []).length > 0 ? (
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {proposal.evidence.map((ev, i) => (
                      <div
                        key={i}
                        className="p-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg text-xs space-y-1"
                      >
                        <div className="flex justify-between items-center text-slate-500">
                          <span className="font-semibold text-slate-800 dark:text-slate-200 uppercase">
                            {ev.event || "Evidence record"}
                          </span>
                          <span>{ev.timestamp || ev.evaluated_at || ""}</span>
                        </div>
                        <pre className="text-[11px] font-mono text-slate-600 dark:text-slate-400 whitespace-pre-wrap overflow-x-auto">
                          {JSON.stringify(ev, null, 2)}
                        </pre>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-400">No raw evidence events attached.</p>
                )}
              </div>
            </div>
          )}

          {activeTab === "sandbox" && (
            <div className="space-y-4">
              {sandbox ? (
                <div className="space-y-3">
                  <div
                    className={cn(
                      "p-3.5 rounded-xl border flex items-center justify-between",
                      sandbox.passed
                        ? "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 text-green-800 dark:text-green-300"
                        : "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-800 dark:text-red-300"
                    )}
                  >
                    <div className="flex items-center gap-2 font-semibold text-sm">
                      {sandbox.passed ? <ShieldCheck size={18} /> : <ShieldAlert size={18} />}
                      <span>
                        {sandbox.passed
                          ? "Sandbox Verification Passed"
                          : "Sandbox Verification Failed"}
                      </span>
                    </div>
                    <span className="text-xs font-mono">{sandbox.evaluated_at}</span>
                  </div>

                  {/* Blockers */}
                  {sandbox.blockers.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold uppercase text-red-600 mb-1.5">
                        Blockers ({sandbox.blockers.length})
                      </h4>
                      <div className="space-y-1.5">
                        {sandbox.blockers.map((b) => (
                          <div
                            key={b.id}
                            className="p-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded text-xs text-red-800 dark:text-red-300"
                          >
                            <span className="font-semibold">{b.message}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Warnings */}
                  {sandbox.warnings.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold uppercase text-amber-600 mb-1.5">
                        Warnings ({sandbox.warnings.length})
                      </h4>
                      <div className="space-y-1.5">
                        {sandbox.warnings.map((w) => (
                          <div
                            key={w.id}
                            className="p-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded text-xs text-amber-800 dark:text-amber-300"
                          >
                            <span className="font-semibold">{w.message}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8 bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700">
                  <ClipboardCheck size={28} className="mx-auto text-slate-300 mb-2" />
                  <p className="text-xs text-slate-500">
                    No sandbox evaluation recorded yet. Run a sandbox evaluation below to verify this proposal safely.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="p-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/30 flex flex-wrap items-center justify-between gap-2">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-xs font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            Close
          </button>

          <div className="flex flex-wrap items-center gap-2">
            {onSandbox && (
              <button
                onClick={() => handleAction(onSandbox)}
                disabled={actionLoading}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700"
              >
                <ClipboardCheck size={13} />
                Sandbox Test
              </button>
            )}

            {canApprove && onApprove && (
              <button
                onClick={() => handleAction(onApprove)}
                disabled={actionLoading}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-green-600 hover:bg-green-700 text-white text-xs font-medium shadow-sm transition-colors"
              >
                <Check size={13} />
                Approve
              </button>
            )}

            {canApply && onApply && (
              <button
                onClick={() => handleAction(onApply)}
                disabled={actionLoading}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-istara-600 hover:bg-istara-700 text-white text-xs font-medium shadow-sm transition-colors"
              >
                <Check size={13} />
                Apply
              </button>
            )}

            {canRevert && onRevert && (
              <button
                onClick={() => handleAction(onRevert)}
                disabled={actionLoading}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white text-xs font-medium shadow-sm transition-colors"
              >
                <RotateCcw size={13} />
                Revert
              </button>
            )}

            {canApprove && onReject && (
              <button
                onClick={() => handleAction(onReject)}
                disabled={actionLoading}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-red-100 hover:bg-red-200 dark:bg-red-950/40 text-red-700 dark:text-red-300 text-xs font-medium transition-colors"
              >
                <X size={13} />
                Reject
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
