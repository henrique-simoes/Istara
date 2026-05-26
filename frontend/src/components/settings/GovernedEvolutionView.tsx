"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import {
  AlertTriangle,
  Archive,
  Brain,
  Check,
  ClipboardCheck,
  GitBranch,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  ShieldAlert,
  X,
} from "lucide-react";
import { dgmhArchive, improvementGovernance, reasoningBank } from "@/lib/api";
import type { DGMHArchiveVariant } from "@/lib/dgmhArchiveTypes";
import type {
  ImprovementFeatureContract,
  ImprovementGovernanceSummary,
  ImprovementProposal,
  ProposalSandboxEvaluation,
} from "@/lib/improvementGovernanceTypes";
import type { ReasoningBankSummary, ReasoningMemoryItem } from "@/lib/reasoningBankTypes";
import { useRoleCapabilities } from "@/hooks/useRoleCapabilities";
import { useProjectStore } from "@/stores/projectStore";
import { cn, formatDate } from "@/lib/utils";

type Tab = "proposals" | "archive" | "reasoning" | "contract";

const TABS: Array<{ id: Tab; label: string }> = [
  { id: "proposals", label: "Approvals" },
  { id: "archive", label: "Archive" },
  { id: "reasoning", label: "Reasoning" },
  { id: "contract", label: "Contract" },
];

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

function normalizePercent(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value)) return "--";
  const normalized = value <= 1 ? value * 100 : value;
  return `${Math.round(Math.max(0, Math.min(100, normalized)))}%`;
}

function latestSandbox(proposal: ImprovementProposal): ProposalSandboxEvaluation | null {
  const sandboxEvents = (proposal.evidence || []).filter((item) => item?.event === "sandbox_evaluation");
  return sandboxEvents.length ? sandboxEvents[sandboxEvents.length - 1] : null;
}

function summarizeSurfaces(surfaces: string[] = []) {
  if (surfaces.length <= 3) return surfaces.join(", ") || "evaluation";
  return `${surfaces.slice(0, 3).join(", ")} +${surfaces.length - 3}`;
}

export default function GovernedEvolutionView() {
  const projectId = useProjectStore((s) => s.activeProjectId);
  const capabilities = useRoleCapabilities();
  const [tab, setTab] = useState<Tab>("proposals");
  const [loading, setLoading] = useState(false);
  const [actionId, setActionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<ImprovementGovernanceSummary | null>(null);
  const [proposals, setProposals] = useState<ImprovementProposal[]>([]);
  const [variants, setVariants] = useState<DGMHArchiveVariant[]>([]);
  const [reasoningSummary, setReasoningSummary] = useState<ReasoningBankSummary | null>(null);
  const [memories, setMemories] = useState<ReasoningMemoryItem[]>([]);
  const [featureContract, setFeatureContract] = useState<ImprovementFeatureContract[]>([]);

  const fetchAll = useCallback(async () => {
    if (!capabilities.canUseGovernedEvolution || !projectId) {
      setSummary(null);
      setProposals([]);
      setVariants([]);
      setReasoningSummary(null);
      setMemories([]);
      setFeatureContract([]);
      setError(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [nextSummary, nextProposals, nextVariants, nextReasoning, nextMemories, nextContract] =
        await Promise.all([
          improvementGovernance.summary(projectId).catch(() => null),
          improvementGovernance.proposals({ project_id: projectId, limit: 12 }).catch(() => ({
            proposals: [],
          })),
          dgmhArchive.variants({ project_id: projectId, limit: 12 }).catch(() => ({ variants: [] })),
          reasoningBank.summary(projectId).catch(() => null),
          reasoningBank.memories({ project_id: projectId, limit: 8 }).catch(() => ({ memories: [] })),
          improvementGovernance.featureContract().catch(() => ({ features: [] })),
        ]);
      setSummary(nextSummary);
      setProposals(nextProposals.proposals || []);
      setVariants(nextVariants.variants || []);
      setReasoningSummary(nextReasoning);
      setMemories(nextMemories.memories || []);
      setFeatureContract(nextContract.features || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load governed evolution data");
    }
    setLoading(false);
  }, [capabilities.canUseGovernedEvolution, projectId]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const pendingCount = summary?.pending_human_approval || 0;
  const activeVariantCount = useMemo(
    () => variants.filter((variant) => ["active", "approved", "candidate"].includes(variant.status)).length,
    [variants]
  );

  const runProposalAction = async (id: string, action: "sandbox" | "approve" | "apply" | "reject" | "revert") => {
    if (!capabilities.canUseGovernedEvolution) return;
    if (!projectId) {
      setError("Select a project before reviewing governed evolution.");
      return;
    }
    setActionId(`${action}-${id}`);
    setError(null);
    try {
      if (action === "sandbox") {
        await improvementGovernance.sandboxEvaluation(id, projectId, { evidence: { source: "settings_governance_ui" } });
      } else if (action === "approve") {
        await improvementGovernance.approve(id, projectId, "Approved in governed evolution review");
      } else if (action === "apply") {
        await improvementGovernance.apply(id, projectId, { source: "settings_governance_ui" });
      } else if (action === "reject") {
        await improvementGovernance.reject(id, projectId, "Rejected in governed evolution review");
      } else {
        await improvementGovernance.revert(id, projectId, "Reverted in governed evolution review");
      }
      await fetchAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    }
    setActionId(null);
  };

  const runVariantAction = async (id: string, action: "approve" | "apply" | "confirm" | "revert" | "quarantine") => {
    if (!capabilities.canUseGovernedEvolution) return;
    if (!projectId) {
      setError("Select a project before reviewing governed evolution.");
      return;
    }
    setActionId(`${action}-${id}`);
    setError(null);
    try {
      if (action === "approve") await dgmhArchive.approve(id, projectId, "Approved in governed evolution review");
      if (action === "apply") await dgmhArchive.apply(id, projectId, { source: "settings_governance_ui" });
      if (action === "confirm") await dgmhArchive.confirm(id, projectId, "Confirmed in governed evolution review");
      if (action === "revert") await dgmhArchive.revert(id, projectId, "Reverted in governed evolution review");
      if (action === "quarantine") await dgmhArchive.quarantine(id, projectId, "Quarantined in governed evolution review");
      await fetchAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    }
    setActionId(null);
  };

  if (!capabilities.canUseGovernedEvolution) return null;

  return (
    <section className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h3 className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
          <ShieldCheck size={18} />
          Governed Evolution
        </h3>
        <button
          onClick={fetchAll}
          disabled={loading || !projectId}
          title="Refresh"
          className="inline-flex items-center gap-1.5 self-start rounded-lg bg-slate-100 px-2.5 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-200 disabled:opacity-50 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600"
        >
          <RefreshCw size={13} className={cn(loading && "animate-spin")} />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Metric label="Pending" value={pendingCount} tone={pendingCount > 0 ? "amber" : "slate"} />
        <Metric label="Applied" value={summary?.applied || 0} tone="green" />
        <Metric label="Archive" value={activeVariantCount} tone="blue" />
        <Metric label="Memories" value={reasoningSummary?.total || 0} tone="slate" />
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-300">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {TABS.map((item) => (
          <button
            key={item.id}
            onClick={() => setTab(item.id)}
            className={cn(
              "rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
              tab === item.id
                ? "bg-istara-600 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600"
            )}
          >
            {item.label}
          </button>
        ))}
      </div>

      {!projectId && <EmptyState label="Select a project to view governed evolution." />}

      {projectId && tab === "proposals" && (
        <div className="space-y-3">
          {proposals.length === 0 && <EmptyState label="No proposals found." />}
          {proposals.map((proposal) => {
            const sandbox = latestSandbox(proposal);
            const canApprove = ["draft", "proposed"].includes(proposal.status);
            const canApply =
              proposal.status === "approved" ||
              (proposal.auto_apply_allowed && !["applied", "rejected", "reverted", "quarantined"].includes(proposal.status));
            const canRevert = proposal.status === "applied";
            return (
              <article key={proposal.id} className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="min-w-0 space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={cn("rounded-full px-2 py-0.5 text-[11px] font-medium", badgeTone(proposal.status))}>
                        {proposal.status}
                      </span>
                      <span className={cn("rounded-full px-2 py-0.5 text-[11px] font-medium", badgeTone(proposal.risk_level))}>
                        {proposal.risk_level}
                      </span>
                      <span className="text-[11px] text-slate-400">{proposal.source_system}</span>
                    </div>
                    <div>
                      <h4 className="text-sm font-medium text-slate-900 dark:text-white">{proposal.title}</h4>
                      <p className="mt-1 line-clamp-2 text-xs text-slate-500 dark:text-slate-400">{proposal.summary || proposal.rationale}</p>
                    </div>
                    <div className="flex flex-wrap gap-2 text-[11px] text-slate-500 dark:text-slate-400">
                      <span>{summarizeSurfaces(proposal.affected_surfaces)}</span>
                      <span>{normalizePercent(proposal.confidence)} confidence</span>
                      <span>{proposal.evidence.length} evidence events</span>
                    </div>
                    {sandbox && (
                      <div
                        className={cn(
                          "inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] font-medium",
                          sandbox.passed
                            ? "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-300"
                            : "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300"
                        )}
                      >
                        {sandbox.passed ? <ShieldCheck size={12} /> : <ShieldAlert size={12} />}
                        {sandbox.passed ? "Sandbox passed" : `${sandbox.blockers.length} blockers`}
                        {sandbox.warnings.length > 0 && `, ${sandbox.warnings.length} warnings`}
                      </div>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2 lg:justify-end">
                    <ActionButton
                      label="Sandbox"
                      icon={<ClipboardCheck size={13} />}
                      busy={actionId === `sandbox-${proposal.id}`}
                      onClick={() => runProposalAction(proposal.id, "sandbox")}
                    />
                    {canApprove && (
                      <ActionButton
                        label="Approve"
                        icon={<Check size={13} />}
                        busy={actionId === `approve-${proposal.id}`}
                        onClick={() => runProposalAction(proposal.id, "approve")}
                      />
                    )}
                    {canApply && (
                      <ActionButton
                        label="Apply"
                        icon={<Check size={13} />}
                        busy={actionId === `apply-${proposal.id}`}
                        onClick={() => runProposalAction(proposal.id, "apply")}
                      />
                    )}
                    {canRevert && (
                      <ActionButton
                        label="Revert"
                        icon={<RotateCcw size={13} />}
                        busy={actionId === `revert-${proposal.id}`}
                        onClick={() => runProposalAction(proposal.id, "revert")}
                      />
                    )}
                    {canApprove && (
                      <ActionButton
                        label="Reject"
                        icon={<X size={13} />}
                        busy={actionId === `reject-${proposal.id}`}
                        onClick={() => runProposalAction(proposal.id, "reject")}
                      />
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {projectId && tab === "archive" && (
        <div className="space-y-3">
          {variants.length === 0 && <EmptyState label="No archive variants found." />}
          {variants.map((variant) => (
            <article key={variant.id} className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0 space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={cn("rounded-full px-2 py-0.5 text-[11px] font-medium", badgeTone(variant.status))}>
                      {variant.status}
                    </span>
                    <span className="inline-flex items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400">
                      <GitBranch size={12} />
                      gen {variant.generation}
                    </span>
                    <span className="text-[11px] text-slate-400">{variant.source_system}</span>
                  </div>
                  <h4 className="text-sm font-medium text-slate-900 dark:text-white">{variant.title}</h4>
                  <div className="flex flex-wrap gap-2 text-[11px] text-slate-500 dark:text-slate-400">
                    <span>{variant.target_system || "system"}</span>
                    <span>{variant.mutation_surface || "evaluation"}</span>
                    <span>{normalizePercent(variant.confidence)} confidence</span>
                    <span>{variant.score == null ? "no score" : `${variant.score.toFixed(3)} score`}</span>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 lg:justify-end">
                  {variant.status === "candidate" && (
                    <ActionButton
                      label="Approve"
                      icon={<Check size={13} />}
                      busy={actionId === `approve-${variant.id}`}
                      onClick={() => runVariantAction(variant.id, "approve")}
                    />
                  )}
                  {variant.status === "approved" && (
                    <ActionButton
                      label="Apply"
                      icon={<Check size={13} />}
                      busy={actionId === `apply-${variant.id}`}
                      onClick={() => runVariantAction(variant.id, "apply")}
                    />
                  )}
                  {variant.status === "active" && (
                    <ActionButton
                      label="Confirm"
                      icon={<Check size={13} />}
                      busy={actionId === `confirm-${variant.id}`}
                      onClick={() => runVariantAction(variant.id, "confirm")}
                    />
                  )}
                  {["active", "confirmed"].includes(variant.status) && (
                    <ActionButton
                      label="Revert"
                      icon={<RotateCcw size={13} />}
                      busy={actionId === `revert-${variant.id}`}
                      onClick={() => runVariantAction(variant.id, "revert")}
                    />
                  )}
                  {!["quarantined", "reverted"].includes(variant.status) && (
                    <ActionButton
                      label="Quarantine"
                      icon={<X size={13} />}
                      busy={actionId === `quarantine-${variant.id}`}
                      onClick={() => runVariantAction(variant.id, "quarantine")}
                    />
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      {projectId && tab === "reasoning" && (
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <Metric label="Successes" value={reasoningSummary?.recent_successes_24h || 0} tone="green" />
            <Metric label="Failures" value={reasoningSummary?.recent_failures_24h || 0} tone="amber" />
            <Metric label="24h" value={reasoningSummary?.recent_24h || 0} tone="blue" />
          </div>
          {memories.length === 0 && <EmptyState label="No ReasoningBank memories found." />}
          {memories.map((memory) => (
            <article key={memory.id} className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
              <div className="flex flex-wrap items-center gap-2">
                <span className={cn("rounded-full px-2 py-0.5 text-[11px] font-medium", badgeTone(memory.outcome))}>
                  {memory.outcome}
                </span>
                <span className="inline-flex items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400">
                  <Brain size={12} />
                  {memory.source_kind}
                </span>
                <span className="text-[11px] text-slate-400">{formatDate(memory.created_at)}</span>
              </div>
              <h4 className="mt-2 text-sm font-medium text-slate-900 dark:text-white">{memory.title}</h4>
              <p className="mt-1 line-clamp-2 text-xs text-slate-500 dark:text-slate-400">{memory.description || memory.content}</p>
              <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-slate-500 dark:text-slate-400">
                <span>{normalizePercent(memory.confidence)} confidence</span>
                <span>{memory.usage_count} uses</span>
                {memory.tags.slice(0, 3).map((tag) => (
                  <span key={tag} className="rounded bg-slate-100 px-1.5 py-0.5 dark:bg-slate-700">
                    {tag}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      )}

      {projectId && tab === "contract" && (
        <div className="grid gap-3 md:grid-cols-2">
          {featureContract.map((feature) => (
            <article key={feature.feature} className="rounded-lg border border-slate-200 p-3 dark:border-slate-700">
              <div className="flex items-start gap-2">
                <Archive size={15} className="mt-0.5 shrink-0 text-slate-400" />
                <div className="min-w-0">
                  <h4 className="text-sm font-medium text-slate-900 dark:text-white">{feature.feature}</h4>
                  <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">{summarizeSurfaces(feature.surfaces)}</p>
                </div>
              </div>
              <ul className="mt-2 space-y-1 text-xs text-slate-500 dark:text-slate-400">
                {feature.required_evidence.slice(0, 4).map((item) => (
                  <li key={item} className="flex gap-2">
                    <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-300 dark:bg-slate-600" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function Metric({ label, value, tone }: { label: string; value: number; tone: "amber" | "blue" | "green" | "slate" }) {
  const tones = {
    amber: "text-amber-600 dark:text-amber-300",
    blue: "text-blue-600 dark:text-blue-300",
    green: "text-green-600 dark:text-green-300",
    slate: "text-slate-700 dark:text-slate-200",
  };
  return (
    <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-900">
      <div className="text-[11px] font-medium uppercase text-slate-400">{label}</div>
      <div className={cn("mt-1 text-xl font-semibold", tones[tone])}>{value.toLocaleString()}</div>
    </div>
  );
}

function ActionButton({
  label,
  icon,
  busy,
  onClick,
}: {
  label: string;
  icon: ReactNode;
  busy: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={busy}
      title={label}
      className="inline-flex items-center gap-1.5 rounded-lg bg-slate-100 px-2.5 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-200 disabled:opacity-50 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600"
    >
      {busy ? <RefreshCw size={13} className="animate-spin" /> : icon}
      {label}
    </button>
  );
}

function EmptyState({ label }: { label: string }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-200 px-3 py-6 text-center text-sm text-slate-400 dark:border-slate-700">
      {label}
    </div>
  );
}
